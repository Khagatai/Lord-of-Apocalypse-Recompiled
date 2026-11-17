"""Two-process real networking-HLE test; synthetic RAM/callbacks, no game data."""
import argparse,contextlib,hashlib,json,os,subprocess,sys,threading,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import coop_lobby,title
def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--online',action='store_true');args=parser.parse_args()
    title.verify_inputs();folder=ROOT/('private/coop-hle-online' if args.online else 'private/coop-hle');folder.mkdir(exist_ok=True);exe=folder/'hle-test.exe'
    command=[str(title.SDK/'bin/gcc.exe'),'-O2','-Wall','-Wextra','-DSR_FLIGHT_RECORDER_LINKED','-Wno-misleading-indentation',
        '-I'+str(ROOT/'tools'),'-I'+str(title.FRAMEWORK/'src/rt'),'-I'+str(title.FRAMEWORK/'src/core'),
        '-I'+str(title.FRAMEWORK/'src/rt/atrac3p'),'-I'+str(title.FRAMEWORK/'src/rt/atrac3p/libavcodec'),'-I'+str(title.FRAMEWORK/'src/rt/atrac3p/libavutil'),
        str(ROOT/'tools/coop-hle-test.c'),str(ROOT/'tools/coop_transport.c'),str(title.FRAMEWORK/'src/core/nk_adhoc_relay.c')]
    if args.online:command += [str(ROOT/'tools/online_runtime.c'),str(title.FRAMEWORK/'src/core/nk_json.c'),'-lcrypt32']
    command += ['-lws2_32','-o',str(exe)]
    build=subprocess.run(command,env=title.environment(),capture_output=True,text=True);(folder/'build.log').write_text(build.stdout+build.stderr)
    if build.returncode:raise RuntimeError(build.stderr)
    lobby=coop_lobby.Lobby(port=0);stop=threading.Event()
    def serve():
        while not stop.is_set():lobby.step(.005)
    thread=threading.Thread(target=serve);thread.start();children=[]
    stack=contextlib.ExitStack();room_server=None
    try:
        environments=[dict(os.environ),dict(os.environ)]
        if args.online:
            from room_service import Rooms,Server
            from online_session import Session
            from importlib.machinery import SourceFileLoader
            wait=SourceFileLoader('online_check',str(ROOT/'tools/check-online.py')).load_module().wait
            room_server=Server(('127.0.0.1',0),Rooms());room_thread=threading.Thread(target=room_server.serve_forever,daemon=True);room_thread.start()
            sessions=[]
            for i in range(2):
                work=folder/str(i);work.mkdir(exist_ok=True)
                session=Session(work,dict(mac=f'02:00:00:00:00:0{i+1}',nickname='Test host' if i==0 else 'Test guest'),service=f'http://127.0.0.1:{room_server.server_port}')
                environments[i].update(stack.enter_context(session));sessions.append(session)
            x,y=[s.client for s in sessions];assert x.call('create')['result']==0
            code=wait(lambda:x.call('status')['code']);assert y.call('join',code=code)['result']==0
            wait(lambda:x.call('status')['connected']==1 and y.call('status')['connected']==1)
        children=[subprocess.Popen([str(exe),str(role),str(lobby.address[1])],env=environments[role-1],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True) for role in (1,2)]
        results=[]
        for child in children:
            out,err=child.communicate(timeout=18);results.append(dict(returncode=child.returncode,stdout=out.strip(),stderr=err.strip()))
        passed=all(r['returncode']==0 for r in results)
        report=dict(scope='real-HLE-native-WebRTC-synthetic-guest-fiber-harness-not-gameplay' if args.online else 'real-HLE-native-network-synthetic-guest-fiber-harness-not-gameplay',passed=passed,gameplay_coop_validated=False,
                    executable_sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),results=results)
        (folder/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
        if not passed:raise SystemExit(1)
    finally:
        for child in children:
            if child.poll() is None:child.terminate();child.wait(timeout=5)
        stack.close()
        if room_server:room_server.shutdown();room_server.server_close()
        stop.set();thread.join(timeout=2);lobby.close()
if __name__=='__main__':main()
