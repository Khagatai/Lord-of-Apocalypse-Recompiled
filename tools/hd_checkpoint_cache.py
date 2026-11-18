"""Reuse verified HD jobs by pixel-processing identity across archive updates.

Archive offsets, texture keys and reference resource bytes can change without
changing a job's pixels. Canonical job IDs commit every pixel-processing input.
No generated pixels are copied. Missing/corrupt checkpoints become pending;
unknown ownership and linked paths remain explicit errors.
"""
import hashlib,json,re,struct
from pathlib import Path

FIELDS=('dimensions','source_rgba_sha256','wrap','method','model','detail_pass')
JOB=re.compile(r'[a-f0-9]{64}')
PNG=re.compile(r'tex-[0-9]{5}-[0-7]\.png')

def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def load(path):return json.loads(path.read_text(encoding='utf-8'))

def write(path,value):
    if path.is_symlink() or path.is_junction():raise ValueError('Linked HD cache metadata')
    temporary=path.with_suffix('.tmp')
    if temporary.is_symlink() or temporary.is_junction():raise ValueError('Linked HD cache temporary file')
    temporary.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8');temporary.replace(path)

def job_id(job):
    if set(job)-set(FIELDS)-{'reference'}:raise ValueError('Unknown HD pixel-processing input')
    return hashlib.sha256(json.dumps({k:job.get(k) for k in FIELDS},sort_keys=True,separators=(',',':')).encode()).hexdigest()

def owner(folder):
    if folder.is_symlink() or folder.is_junction():raise ValueError('Linked HD cache folder')
    if not folder.exists():return None
    path=folder/'owner.json'
    if not path.is_file():
        if not any(folder.iterdir()):return None
        raise ValueError('Existing HD folder has no owner; files preserved')
    if path.is_symlink():raise ValueError('Linked HD cache owner')
    result=load(path)
    if result.get('tool')!='ISO-local-HD-v1':raise ValueError('Unknown HD cache owner; files preserved')
    return result

def safe_child(folder,name,pattern):
    if not isinstance(name,str) or not pattern.fullmatch(name):raise ValueError('Unsafe HD checkpoint filename')
    path=folder/name
    if path.is_symlink() or path.is_junction() or path.resolve().parent!=folder.resolve():
        raise ValueError('Linked/escaping HD checkpoint path')
    return path

def compatible(job,previous,current,compatibility):
    if previous is None:return False
    allowed=[current['processing_sources'],*compatibility.get('legacy_processing_sources',[])]
    if previous.get('framework_commit')!=current['framework_commit'] or previous.get('processing_sources') not in allowed:return False
    if job['method']=='restore':
        model=job['model']
        names=('realesrgan-ncnn-vulkan.exe','vcomp140.dll','vcomp140d.dll',f'models/{model}.param',f'models/{model}.bin')
        before,after=previous.get('model_pins',{}),current['model_pins']
        if any(name not in after or before.get(name)!=after[name] for name in names):return False
    return True

def analyze(recipe,pack,work,identity,compatibility,progress=None):
    """Read-only plan; also usable to audit a real player's pack without changing it."""
    pack,work=Path(pack),Path(work)
    if pack.resolve()==work.resolve() or pack.is_relative_to(work) or work.is_relative_to(pack):
        raise ValueError('Separate HD pack and checkpoint folders')
    if recipe.get('schema')!=1 or recipe.get('game_pixels_included') is not False:raise ValueError('Unknown HD recipe')
    tasks=recipe['jobs']
    if any(not JOB.fullmatch(key) or key!=job_id(job) for key,job in tasks.items()):
        raise ValueError('HD job identity does not match its pixel-processing inputs')
    owners=[owner(folder) for folder in (pack,work)]
    previous=owners[1] or owners[0]
    journal=work/'cache-transition.json'
    if journal.is_symlink():raise ValueError('Linked HD cache journal')
    if journal.is_file():
        transition=load(journal)
        if transition.get('state')=='PREPARED':
            if transition.get('tool')!='HD-content-cache-v1':raise ValueError('Unknown HD cache transition')
            for actual,old in zip(owners,transition['previous_owners'],strict=True):
                if actual not in (old,transition['identity']):raise ValueError('HD cache owner changed during transition')
            previous=transition['provenance_owner']
    if not journal.is_file() or load(journal).get('state')!='PREPARED':
        if all(owners) and any(owners[0].get(k)!=owners[1].get(k) for k in ('framework_commit','model_pins','processing_sources')):
            raise ValueError('Inconsistent HD cache owners; files preserved')
    completed=work/'completed'
    retired=work/'retired-completed'
    for folder in (completed,retired):
        if folder.is_symlink() or folder.is_junction():raise ValueError('Linked HD checkpoint folder')
    verified={};retire=[];reuse=0;repair=0;seen=0
    paths=list(completed.glob('*.json'))
    for path in paths:
        if not JOB.fullmatch(path.stem) or path.is_symlink():raise ValueError('Unsafe HD checkpoint record')
        reason=None
        try:row=load(path)
        except (ValueError,UnicodeError):row={};reason='damaged checkpoint metadata'
        key=path.stem
        if key not in tasks:reason='removed or changed job'
        elif not compatible(tasks[key],previous,identity,compatibility):reason='pixel pipeline or model changed'
        elif row.get('job')!=key or not isinstance(row.get('levels'),list) or len(row['levels'])!=len(tasks[key]['dimensions']):
            reason='damaged checkpoint metadata'
        if reason is None:
            for level,(w,h) in zip(row['levels'],tasks[key]['dimensions'],strict=True):
                if not isinstance(level,dict):reason='damaged checkpoint metadata';break
                image=safe_child(pack,level.get('file'),PNG)
                if (level.get('width'),level.get('height'))!=(w*4,h*4):reason='wrong image dimensions';break
                if image.name not in verified:
                    if not image.is_file():verified[image.name]=None
                    else:
                        with image.open('rb') as stream:header=stream.read(24)
                        verified[image.name]=(sha(image),header)
                actual=verified[image.name]
                if actual is None:reason='missing image';break
                digest,header=actual
                if digest!=level.get('sha256'):reason='damaged image';break
                if (len(header)!=24 or header[:8]!=b'\x89PNG\r\n\x1a\n' or header[12:16]!=b'IHDR'
                        or struct.unpack('>II',header[16:24])!=(w*4,h*4)):
                    reason='wrong image dimensions';break
        if reason:
            retire.append(dict(file=path.name,sha256=sha(path),reason=reason))
            repair+=key in tasks
        else:reuse+=1
        seen+=1
        if progress and (seen%256==0 or seen==len(paths)):progress(seen,len(paths),reuse,len(tasks))
    hashes={name:entry[0] for name,entry in verified.items() if entry is not None}
    return dict(tool='HD-content-cache-v1',identity=identity,previous_owners=owners,provenance_owner=previous,
        reused_jobs=reuse,pending_jobs=len(tasks)-reuse,total_jobs=len(tasks),repair_jobs=repair,
        verified_unique_images=len(hashes),retire=retire,verified_files=hashes,pixel_files_copied=0)

def reconcile(recipe,pack,work,identity,compatibility,progress=None):
    """Promote only verified checkpoint metadata; keep all pixels until final build validation."""
    pack,work=Path(pack),Path(work)
    plan=analyze(recipe,pack,work,identity,compatibility,progress)
    for folder in (work,pack):
        folder.mkdir(parents=True,exist_ok=True)
        if not (folder/'owner.json').exists():write(folder/'owner.json',identity)
    # A small journal makes owner promotion retryable after cancellation.
    journal={k:v for k,v in plan.items() if k!='verified_files'}
    journal['previous_owners']=[owner(pack),owner(work)]
    write(work/'cache-transition.json',dict(journal,state='PREPARED'))
    retired=work/'retired-completed'
    if plan['retire']:retired.mkdir(exist_ok=True)
    for row in plan['retire']:
        source=safe_child(work/'completed',row['file'],re.compile(r'[a-f0-9]{64}\.json'))
        target=safe_child(retired,row['file'],re.compile(r'[a-f0-9]{64}\.json'))
        if sha(source)!=row['sha256']:raise ValueError('HD checkpoint changed after verification')
        source.replace(target)
    for folder in (pack,work):write(folder/'owner.json',identity)
    summary={k:v for k,v in plan.items() if k not in ('verified_files','previous_owners','provenance_owner')}
    write(work/'cache-reuse.json',summary)
    write(work/'cache-transition.json',dict(journal,state='DONE'))
    return plan
