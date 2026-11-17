"""Owned online-agent lifetime and authenticated loopback IPC for normal launches."""
import json,os,socket,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CONFIG=ROOT/'private/settings/online-service.json'
class Client:
    def __init__(self,ready):self.port=ready['port'];self.token=ready['token'];self.socket=None;self.input=bytearray()
    def call(self,op,**fields):
        if not self.socket:self.socket=socket.create_connection(('127.0.0.1',self.port),timeout=2);self.socket.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1)
        self.socket.sendall(json.dumps(dict(fields,op=op,token=self.token),separators=(',',':')).encode()+b'\n')
        while b'\n' not in self.input:
            data=self.socket.recv(65536)
            if not data:raise ConnectionError('Online agent closed the connection.')
            self.input.extend(data)
            if len(self.input)>65536:raise ValueError('Online IPC response too large.')
        raw,_,rest=self.input.partition(b'\n');self.input=bytearray(rest);return json.loads(raw)
    def close(self):
        if self.socket:self.socket.close();self.socket=None
class Session:
    def __init__(self,folder,identity,*,service=None,relay=False,backend=None,preferences=None):
        self.folder=Path(folder).resolve();self.identity=identity;self.service=service;self.relay=relay;self.backend=backend;self.preferences=preferences;self.child=None;self.client=None;self.log=None
        if not self.folder.is_relative_to(ROOT/'private'):raise ValueError('Online session must be private.')
    def __enter__(self):
        try:
            service=self.service
            backend=self.backend or 'rooms'
            if service is None:
                import online_config
                config=online_config.load();service=config['url'];backend=self.backend or config['backend']
            from online_agent import service_url
            if service:service_url(service)
            identity=self.folder/'online-identity.json';identity.write_text(json.dumps({k:self.identity[k] for k in ('mac','nickname')}))
            ready=self.folder/'online-ready.json';ready.unlink(missing_ok=True)
            command=[str(ROOT/'private/tools/python314/python.exe'),str(ROOT/'tools/online_agent.py'),'--ready-file',str(ready),'--identity',str(identity),'--parent-pid',str(os.getpid()),'--backend',backend]
            preferences=self.preferences or (CONFIG if self.service is None else None)
            if preferences:
                import online_config
                online_config.load(preferences);command+=['--preferences',str(Path(preferences).resolve())]
            if backend=='steam':(self.folder/'steam_appid.txt').write_text('480\n')
            if service:command+=['--service',service]
            if self.relay:command+=['--relay']
            self.log=(self.folder/'online.log').open('wb')
            self.child=subprocess.Popen(command,cwd=self.folder,stdout=self.log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
            deadline=time.monotonic()+5
            while True:
                if self.child.poll() is not None or time.monotonic()>deadline:raise RuntimeError('Online helper did not start. See online.log.')
                if ready.exists():
                    try:value=json.loads(ready.read_text())
                    except ValueError:time.sleep(.02);continue
                    if value.get('pid')!=self.child.pid:raise ValueError('Online helper identity differs.')
                    self.client=Client(value);break
                time.sleep(.02)
            return dict(LOA_ONLINE_PORT=str(self.client.port),LOA_ONLINE_TOKEN=self.client.token,LOA_NET_ENABLED='1')
        except BaseException:self.__exit__(None,None,None);raise
    def __exit__(self,*args):
        if self.child and self.child.poll() is None:
            try:
                if self.client:self.client.call('stop')
                self.child.wait(timeout=8)
            except (OSError,ValueError,subprocess.TimeoutExpired):self.child.terminate();self.child.wait(timeout=5)
        if self.client:self.client.close()
        if self.log:self.log.close()
