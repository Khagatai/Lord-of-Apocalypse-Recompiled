"""Explicit, persistent co-op profiles and an owned discovery-lobby lifetime."""
import contextlib,ipaddress,json,os,secrets,subprocess,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SETTINGS=ROOT/'private/settings/network.json'
FIELDS={'schema','mode','host','public_host','bind','port','offset','nickname','mac'}
def defaults():
    mac=bytearray(secrets.token_bytes(6));mac[0]=(mac[0]|2)&254
    return dict(schema=1,mode='off',host='127.0.0.1',public_host='',bind='0.0.0.0',port=27312,offset=10000,
                nickname='Player',mac=':'.join(f'{b:02x}' for b in mac))
def validate(value):
    if not isinstance(value,dict) or set(value)!=FIELDS or type(value.get('schema')) is not int or value['schema']!=1:raise ValueError('Unrecognized network profile')
    if value['mode'] not in ('off','host','join'):raise ValueError('Choose Off, Host or Join')
    for name in ('host','bind','public_host'):
        if type(value[name]) is not str:raise ValueError('Invalid IPv4 address')
        if name=='public_host' and not value[name]:continue
        ipaddress.IPv4Address(value[name])
    for name,low,high in [('port',1,65535),('offset',0,65535)]:
        if type(value[name]) is not int or not low<=value[name]<=high:raise ValueError('Invalid network '+name)
    nick=value['nickname']
    if not isinstance(nick,str) or not 1<=len(nick)<=32 or any(ord(c)<32 or ord(c)>126 for c in nick):raise ValueError('Nickname must contain 1–32 printable ASCII characters')
    try:
        parts=value['mac'].split(':');mac=bytes(int(p,16) for p in parts)
    except (AttributeError,ValueError,OverflowError):raise ValueError('Invalid console MAC') from None
    if len(parts)!=6 or any(len(p)!=2 for p in parts) or len(mac)!=6 or mac in (b'\0'*6,b'\xff'*6) or mac[0]&1:raise ValueError('Invalid unicast console MAC')
    return dict(value)
def profile_path(path):
    path=Path(path).resolve()
    if not path.is_relative_to(ROOT/'private') or path.suffix!='.json':raise ValueError('Network profiles must remain under private/')
    return path
def load(path=SETTINGS):
    path=profile_path(path)
    return validate(json.loads(path.read_text())) if path.exists() else defaults()
def save(value,path=SETTINGS):
    path=profile_path(path);value=validate(value);path.parent.mkdir(parents=True,exist_ok=True)
    temporary=None
    try:
        with tempfile.NamedTemporaryFile('w',encoding='utf-8',dir=path.parent,suffix='.tmp',delete=False) as stream:
            temporary=Path(stream.name);stream.write(json.dumps(value,indent=2)+'\n');stream.flush();os.fsync(stream.fileno())
        os.replace(temporary,path);temporary=None
    finally:
        if temporary:temporary.unlink(missing_ok=True)
def environment(value,path=SETTINGS):
    value=validate(value)
    return dict(LOA_NET_ENABLED='0' if value['mode']=='off' else '1',LOA_NET_HOST='127.0.0.1' if value['mode']=='host' else value['host'],
        LOA_NET_PORT=str(value['port']),LOA_NET_BIND=value['bind'],LOA_NET_OFFSET=str(value['offset']),LOA_NET_MAC=value['mac'],
        LOA_NET_NICKNAME=value['nickname'],LOA_PROJECT_ROOT=str(ROOT),LOA_NET_SETTINGS_FILE=str(profile_path(path)))
@contextlib.contextmanager
def host_session(value,output):
    if value['mode']!='host':yield;return
    output=Path(output).resolve()
    if not output.is_relative_to(ROOT/'private'):raise ValueError('Lobby logs must remain private')
    ready=output/'lobby-ready.json'
    command=[str(ROOT/'private/tools/python314/python.exe'),str(ROOT/'tools/coop_lobby.py'),'--listen','0.0.0.0','--port',str(value['port']),'--ready-file',str(ready)]
    if value['public_host']:command+=['--advertise-host',value['public_host']]
    with (output/'lobby.log').open('wb') as log:
        child=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            deadline=time.monotonic()+5
            while not ready.exists():
                if child.poll() is not None or time.monotonic()>deadline:raise RuntimeError('Co-op lobby did not start; see '+str(output/'lobby.log'))
                time.sleep(.03)
            if json.loads(ready.read_text())['pid']!=child.pid:raise RuntimeError('Lobby readiness identity differs')
            yield
        finally:
            if child.poll() is None:child.terminate();child.wait(timeout=5)
