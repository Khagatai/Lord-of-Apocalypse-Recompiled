"""Owned loopback-only TURN fixture. Never used as a public relay."""
import contextlib,json,os,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
@contextlib.contextmanager
def local_turn(folder):
    folder=Path(folder).resolve()
    if not folder.is_relative_to(ROOT/'private'):raise ValueError('Fixture output must be private.')
    sdk=ROOT/'private/toolchain/prerequisites/msys64/ucrt64';source=ROOT/'private/tools/libdatachannel/deps/libjuice'
    env=dict(os.environ);env['PATH']=str(sdk/'bin')+os.pathsep+env['PATH']
    exe=folder/'turn-fixture.exe';ready=folder/'turn-ready.json';ready.unlink(missing_ok=True)
    command=[str(sdk/'bin/gcc.exe'),'-O2','-DJUICE_STATIC','-I'+str(source/'include'),str(ROOT/'tools/online-turn-fixture.c'),
             str(ROOT/'private/online-deps/build/datachannel/deps/libjuice/libjuice.a'),'-lws2_32','-lbcrypt','-lwinpthread','-o',str(exe)]
    build=subprocess.run(command,env=env,capture_output=True,text=True)
    (folder/'turn-build.log').write_text(build.stdout+build.stderr)
    if build.returncode:raise RuntimeError(build.stderr)
    with (folder/'turn.log').open('wb') as log:
        child=subprocess.Popen([str(exe),str(ready)],stdin=subprocess.PIPE,stdout=log,stderr=subprocess.STDOUT,env=env,creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            deadline=time.monotonic()+5
            while not ready.exists():
                if child.poll() is not None or time.monotonic()>deadline:raise RuntimeError('Local TURN fixture failed to start.')
                time.sleep(.02)
            value=json.loads(ready.read_text());yield dict(url=f'turn:127.0.0.1:{value["port"]}',username='loa-test',password='synthetic-local-test')
        finally:
            if child.poll() is None:
                child.stdin.write(b'\n');child.stdin.flush()
                try:child.wait(timeout=5)
                except subprocess.TimeoutExpired:child.terminate();child.wait(timeout=5)
            child.stdin.close()
