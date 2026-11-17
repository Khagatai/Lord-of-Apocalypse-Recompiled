"""Build and test two native Windows networking processes on loopback only."""
import hashlib,json,subprocess,sys,threading
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import coop_lobby,title
def main():
    title.verify_inputs();folder=ROOT/'private/coop-transport';folder.mkdir(exist_ok=True)
    exe=folder/'transport-test.exe'
    command=[str(title.SDK/'bin/gcc.exe'),'-O2','-Wall','-Wextra','-Wno-misleading-indentation',
        '-I'+str(ROOT/'tools'),'-I'+str(title.FRAMEWORK/'src/core'),str(ROOT/'tools/coop-transport-test.c'),
        str(ROOT/'tools/coop_transport.c'),str(title.FRAMEWORK/'src/core/nk_adhoc_relay.c'),'-lws2_32','-o',str(exe)]
    build=subprocess.run(command,env=title.environment(),capture_output=True,text=True)
    (folder/'build.log').write_text(build.stdout+build.stderr)
    if build.returncode:raise RuntimeError(build.stderr)
    lobby=coop_lobby.Lobby(port=0);stop=threading.Event()
    def run_lobby():
        while not stop.is_set():lobby.step(.01)
    thread=threading.Thread(target=run_lobby);thread.start();children=[]
    try:
        for role in ('1','2'):
            children.append(subprocess.Popen([str(exe),role,str(lobby.address[1])],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True))
        results=[]
        for child in children:
            out,err=child.communicate(timeout=15);results.append(dict(returncode=child.returncode,stdout=out.strip(),stderr=err.strip()))
        passed=all(r['returncode']==0 for r in results)
        report=dict(scope='two-native-process-loopback-transport-not-gameplay-coop',passed=passed,gameplay_coop_validated=False,
            framework_commit=title.CONFIG['runtime']['commit'],executable_sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),results=results)
        (folder/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
        if not passed:raise SystemExit(1)
    finally:
        for child in children:
            if child.poll() is None:child.terminate();child.wait(timeout=5)
        stop.set();thread.join(timeout=2);lobby.close()
if __name__=='__main__':main()
