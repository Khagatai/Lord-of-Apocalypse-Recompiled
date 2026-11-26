"""Reuse one local PowerShell/GDI process; original renderers keep their guards."""
import json,os,queue,subprocess,threading,time
from pathlib import Path

class Renderer:
    def __init__(self,root):self.root=Path(root);self.process=None;self.number=0;self.messages=queue.Queue()
    def _read(self):
        try:
            for line in self.process.stdout:self.messages.put(line)
        finally:self.messages.put(None)
    def render(self,script,spec,output):
        if script not in ('render-texture-text.ps1','render-caption-atlas.ps1'):raise ValueError('Unknown local text renderer')
        if self.process is None:
            powershell=Path(os.environ.get('SystemRoot','C:/Windows'))/'System32/WindowsPowerShell/v1.0/powershell.exe'
            # Application-owned scripts run only in this child session. Never
            # change CurrentUser/LocalMachine policy to complete game setup.
            self.process=subprocess.Popen([str(powershell),'-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass',
                '-File',str(self.root/'tools/render-text-worker.ps1')],
                stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace',
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            self.reader=threading.Thread(target=self._read,daemon=True);self.reader.start()
        self.number+=1
        self.process.stdin.write(json.dumps(dict(id=self.number,script=script,spec=str(spec),output=str(output)))+'\n');self.process.stdin.flush()
        deadline=time.monotonic()+300;tail=[]
        while True:
            try:line=self.messages.get(timeout=max(.01,deadline-time.monotonic()))
            except queue.Empty:raise RuntimeError('Local text renderer timed out')
            if line is None:raise RuntimeError('Local text renderer exited: '+''.join(tail[-8:]))
            if not line.startswith('LOA_RENDER_RESULT '):tail.append(line[:2048]);tail=tail[-8:];continue
            value=json.loads(line.removeprefix('LOA_RENDER_RESULT '))
            if value['id']!=self.number:raise RuntimeError('Local text renderer returned a different job')
            if not value.get('ok'):raise RuntimeError('Local text renderer failed: '+value.get('error','unknown error'))
            return
    def close(self):
        if self.process:
            self.process.stdin.close()
            try:self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:self.process.kill();self.process.wait()
            self.reader.join(timeout=2);self.process.stdout.close();self.process=None
    def __enter__(self):return self
    def __exit__(self,*unused):self.close()
