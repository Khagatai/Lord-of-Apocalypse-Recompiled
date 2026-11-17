"""First-setup progress protocol. Overall progress is a weighted estimate, not ETA."""
import json,os,re,sys,time
from pathlib import Path

# IDs are consumed by the native launcher; append IDs rather than renumbering.
STAGES={name:(i,start,end) for i,(name,start,end) in enumerate([
    ('checking',0,1),('inputs',1,2),('generate',2,3),('compile',3,6),
    ('link',6,7),('text',7,8),('archives',8,9),('captions',9,10),
    ('tools',10,11),('catalog',11,12),('hd',12,98),('verify',98,100),('ready',100,100)])}

PROFILE_ENV = 'LOA_SETUP_PROGRESS_PROFILE'
BASE_SPANS = {'inputs': (1, 3), 'generate': (3, 15), 'compile': (15, 65),
              'link': (65, 73), 'text': (73, 81), 'archives': (81, 88), 'captions': (88, 98)}
profile = os.environ.get(PROFILE_ENV)

def emit(stage,done=0,total=0):
    if not isinstance(done,int) or not isinstance(total,int) or not 0<=done<=total<=1000000:
        raise ValueError('Invalid setup progress counts')
    if stage=='ready' and (done,total)!=(1,1):raise ValueError('Ready requires explicit completion')
    identity,start,end=STAGES[stage]
    if profile == 'base':
        start, end = BASE_SPANS.get(stage, (start, end))
    percent=start*10+(end-start)*10*done//total if total else start*10
    if stage!='ready':percent=min(percent,999)
    print(f'LOA_SETUP_PROGRESS {identity} {done} {total} {percent}',flush=True)

def compile_targets(text,cwd,destination):
    """Count only compiler outputs in Make's dry-run plan, never started jobs."""
    destination=Path(destination).resolve();targets=set()
    for line in text.splitlines():
        if not re.search(r'(?:^|\s)-c\s',line):continue
        match=re.search(r'(?:^|\s)-o\s+(?:"([^"]+)"|(\S+))',line)
        if not match:continue
        path=(Path(cwd)/(match[1] or match[2])).resolve()
        if path.suffix.lower() not in ('.o','.obj') or not path.is_relative_to(destination):continue
        targets.add(path)
    return targets

def stamp(path):
    try:
        s=path.stat();return s.st_mtime_ns,s.st_size
    except FileNotFoundError:return None

class CompileProgress:
    def __init__(self,targets,cwd,destination):
        self.targets=set(targets);self.cwd=Path(cwd);self.destination=Path(destination)
        self.before={p:stamp(p) for p in targets};self.done=set()
        emit('compile') if not targets else emit('compile',0,len(targets))
    def line(self,line):
        for path in compile_targets(line,self.cwd,self.destination):
            self.complete(path)
    def complete(self,path):
        if path not in self.targets or path in self.done:return
        current=stamp(path)
        if not current or not current[1] or current==self.before[path]:return
        self.done.add(path);emit('compile',len(self.done),len(self.targets))
        if self.done==self.targets:emit('link')

class Timings:
    def __init__(self,path,started=None):
        self.path=Path(path);self.started=time.monotonic() if started is None else started;self.rows=[]
    def record(self,stage,seconds,exit_code):
        self.rows.append(dict(stage=stage,seconds=round(seconds,3),exit_code=exit_code))
        value=dict(schema=1,elapsed_seconds=round(time.monotonic()-self.started,3),stages=self.rows)
        temporary=self.path.with_suffix('.tmp')
        try:
            temporary.write_text(json.dumps(value,indent=2)+'\n');temporary.replace(self.path)
        except OSError as error:print('Could not save setup timings: '+str(error),file=sys.stderr,flush=True)
