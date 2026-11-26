"""Owned local room client: HTTPS signalling and native WebRTC gameplay channels.

The loopback IPC accepts only an unguessable per-launch token. No file/asset
upload operations exist. All state is private to this game session.
"""
import argparse,base64,concurrent.futures,hashlib,hmac,ipaddress,json,os,queue,re,secrets,selectors,socket,struct,sys,time,urllib.error,urllib.parse,urllib.request
from collections import deque
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from online_rtc import NativeRTC,Peer
ROOT=Path(__file__).resolve().parents[1]
OK=0;AGAIN=-1;BAD=-2;NOT_LOGGED=-3;NOT_GROUP=-4;PORT_USED=-5;TOO_BIG=-6;NO_SOCKET=-7;NO_SLOT=-8;SHORT=-9
BUILD='loa-native-v1-NPJH50503'

def service_url(value):
    parsed=urllib.parse.urlsplit(value)
    if parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ('','/'):raise ValueError('Room service URL must be an HTTPS origin.')
    if parsed.scheme!='https':
        try:loopback=ipaddress.ip_address(parsed.hostname).is_loopback
        except ValueError:loopback=parsed.hostname=='localhost'
        if parsed.scheme!='http' or not loopback:raise ValueError('Public room services require HTTPS.')
    if not parsed.hostname:raise ValueError('Missing room service hostname.')
    return value.rstrip('/')

class RoomHTTP:
    def __init__(self,url):self.url=service_url(url)
    def call(self,operation,body,token=''):
        data=json.dumps(body,separators=(',',':')).encode()
        request=urllib.request.Request(self.url+'/v1/'+operation,data=data,headers={'Content-Type':'application/json','Authorization':'Bearer '+token})
        try:
            class NoRedirect(urllib.request.HTTPRedirectHandler):
                def redirect_request(self,*args):return None
            with urllib.request.build_opener(NoRedirect).open(request,timeout=5) as response:raw=response.read(65537)
        except urllib.error.HTTPError as error:
            try:message=json.loads(error.read(65536)).get('error','Room request failed.')
            except ValueError:message='Room request failed.'
            raise RuntimeError(message) from None
        except (OSError,urllib.error.URLError):raise RuntimeError('Cannot reach the room service. Check your internet connection.') from None
        if len(raw)>65536:raise ValueError('Room service response too large.')
        value=json.loads(raw)
        if not isinstance(value,dict):raise ValueError('Invalid room service response.')
        return value

class Agent:
    def __init__(self,identity,url='',*,relay=False,native=None):
        self.identity=identity;self.service=RoomHTTP(url) if url else None;self.native=native;self.relay=relay
        self.executor=concurrent.futures.ThreadPoolExecutor(max_workers=1);self.future=None;self.operation='';self.epoch=0
        self.inbox=queue.Queue(1024);self.signals=deque();self.peers={};self.room=None;self.state='offline';self.error='';self.next_poll=0;self.last_poll=0
        self.group='';self.logged=False;self.events=deque();self.pdp={};self.ptp={};self.streams={};self.closed=False;self.pdp_drops=0
    def status(self):
        return dict(state=self.state,error=self.error,code=self.room['code'] if self.room else '',slot=self.room['slot'] if self.room else -1,
                    players=1+len(self.peers) if self.room else 0,connected=sum(p.ready() for p in self.peers.values()),
                    paths=[p.path() for p in self.peers.values() if p.ready()],service_configured=self.service is not None)
    def submit(self,op,body,token=''):
        self.operation=op;self.future=self.executor.submit(self.service.call,op,body,token)
    def create_or_join(self,op,code=''):
        if self.room or self.future:return dict(result=BAD,error='Leave the current room first.')
        if not self.service:return dict(result=NOT_LOGGED,error='The public room service is not configured yet.')
        if op=='join' and not re.fullmatch(r'[0-9]{5}',code):return dict(result=BAD,error='Enter exactly five digits.')
        self.error='';self.state='creating' if op=='create' else 'joining'
        self.submit(op,dict(self.identity,build=BUILD,**({'code':code} if op=='join' else {})))
        return dict(result=OK) # Request accepted locally; no room/code until HTTP success.
    def leave(self):
        if self.future:return dict(result=AGAIN,error='A room request is still pending. Try again shortly.')
        if self.room:self.submit('leave',dict(session=self.room['session']),self.room['token'])
        self.reset();return dict(result=OK)
    def reset(self):
        self.epoch+=1
        for peer in self.peers.values():peer.close()
        self.peers.clear();self.signals.clear();self.room=None;self.group='';self.logged=False
        self.pdp.clear();self.ptp.clear();self.streams.clear();self.events.clear();self.state='offline'
        while True:
            try:self.inbox.get_nowait()
            except queue.Empty:break
    def peer_add(self,identity):
        if identity['id'] in self.peers:return
        if len(self.peers)>=3:raise ValueError('Room peer limit exceeded.')
        if not self.native:self.native=NativeRTC()
        peer=Peer(self.native,identity,self.room.get('ice',[]),self.inbox,relay=self.relay);peer.group='';peer.announced=False;peer.path_announced=''
        self.peers[identity['id']]=peer
        if self.room['slot']<identity['slot']:peer.offer()
    def emit(self,event):
        if len(self.events)>=64:raise RuntimeError('Game lobby event queue overflow.')
        self.events.append(event)
    def connect_event(self,peer):
        return dict(kind=2,peer_id=peer.identity['slot']+1,mac=peer.identity['mac'].replace(':',''),nickname=peer.identity['nickname'])
    def update_group(self,peer,group):
        old=peer.group;peer.group=group
        if self.group and old==self.group and old!=group:self.emit(dict(kind=3,peer_id=peer.identity['slot']+1))
        if self.group and group==self.group and old!=group:self.emit(self.connect_event(peer))
    def bssid(self,group):
        raw=bytearray(hashlib.sha256(bytes.fromhex(self.room['bssid'])+group.encode()).digest()[:6]);raw[0]=(raw[0]|2)&254
        return raw.hex()
    def announce(self,peer):
        if peer.send(b'G'+self.group.encode())<0:return False
        return True
    def tick(self):
        now=time.monotonic()
        if self.future and self.future.done():
            future=self.future;self.future=None;op=self.operation
            try:
                value=future.result()
                if op in ('create','join'):
                    if not re.fullmatch(r'[0-9]{5}',value.get('code','')) or not 0<=value.get('slot',-1)<4 or not re.fullmatch('[0-9a-f]{12}',value.get('bssid','')):raise ValueError('Invalid room response.')
                    self.room=value;self.state='in-room';self.last_poll=now
                    for identity in value['peers']:self.peer_add(identity)
                elif op=='exchange':
                    self.last_poll=now
                    for event in value.get('events',[]):
                        kind=event['kind']
                        if kind=='joined':self.peer_add(event['peer'])
                        elif kind=='left':
                            peer=self.peers.pop(event['peer'],None)
                            if peer:
                                if peer.group==self.group and self.group:self.emit(dict(kind=3,peer_id=peer.identity['slot']+1))
                                peer.close()
                                for stream in self.streams.values():
                                    if stream['peer']==event['peer']:stream['closed']=True
                        elif kind=='closed':self.reset();self.error='The host closed the room.';break
                        else:
                            peer=self.peers.get(event.get('from'))
                            if peer:peer.signal(event)
            except Exception as error:
                self.error=str(error)
                if op in ('create','join'):self.reset();self.state='error'
                elif op=='exchange' and now-self.last_poll>15:self.reset();self.state='error'
            self.next_poll=now+.2
        for _ in range(128):
            try:who,kind,value=self.inbox.get_nowait()
            except queue.Empty:break
            peer=self.peers.get(who)
            if not peer:continue
            if kind=='signal':
                if len(self.signals)>=128:self.error='Connection signalling queue overflow.';peer.failed=True
                else:self.signals.append(dict(value,to=who))
            elif kind=='packet':
                try:
                    channel,data=value
                    if (data[:1]==b'P')!=(channel==1):raise ValueError('Wrong data channel')
                    self.packet(peer,data)
                except (ValueError,KeyError,TypeError):peer.failed=True;self.error='Invalid multiplayer packet.'
            elif kind=='state' and value in (3,4,5):
                if peer.group and self.group==peer.group:self.emit(dict(kind=3,peer_id=peer.identity['slot']+1))
                peer.group='';peer.announced=False
                if value==4:self.error='Peer connection failed. A relay may be required for this network.'
        for peer in self.peers.values():
            if peer.ready() and not peer.announced:peer.announced=self.announce(peer)
            if peer.ready() and peer.path()!=peer.path_announced:
                path=peer.path()
                if path!='connecting' and peer.send(b'R'+(b'1' if path=='relayed' else b'0'))>=0:peer.path_announced=path
            if peer.failed:self.error=self.error or 'Peer connection queue overflow.'
        if self.room and not self.future and now>=self.next_poll:
            batch=[self.signals.popleft() for _ in range(min(32,len(self.signals)))]
            self.submit('exchange',dict(session=self.room['session'],signals=batch),self.room['token'])
    def peer_for(self,mac):return next((p for p in self.peers.values() if p.identity['mac'].replace(':','')==mac and p.group==self.group and self.group and p.ready()),None)
    def packet(self,peer,data):
        if data in (b'R0',b'R1'):
            peer.remote_relay=data==b'R1';return
        if data[:1]==b'G':
            group=data[1:].decode('ascii')
            if not re.fullmatch('[A-Za-z0-9]{0,8}',group):raise ValueError('Invalid group')
            self.update_group(peer,group);return
        if not self.group or peer.group!=self.group:return
        if data[:1]==b'P':
            if not 5<=len(data)<=10245:raise ValueError('Invalid PDP')
            src,dst=struct.unpack('!HH',data[1:5]);sock=next((s for s in self.pdp.values() if s['port']==dst),None)
            if sock and len(sock['queue'])<32:sock['queue'].append((peer.identity['mac'].replace(':',''),src,data[5:]))
            elif sock:self.pdp_drops+=1
            return
        if len(data)<17:raise ValueError('Invalid stream packet')
        tag=data[:1];nonce=data[1:17].hex();stream=self.streams.get(nonce)
        if tag==b'O':
            if len(data)!=21 or stream:return
            src,dst=struct.unpack('!HH',data[17:]);listener=next((s for s in self.ptp.values() if s['state']==1 and s['local_port']==dst),None)
            if not listener or len(listener['pending'])>=listener['backlog']:peer.send(b'C'+bytes.fromhex(nonce));return
            if sum(len(s.get('pending',[])) for s in self.ptp.values())>=16:peer.send(b'C'+bytes.fromhex(nonce));return
            if any(nonce==n for s in self.ptp.values() for n,_ in s.get('pending',[])):return
            listener['pending'].append((nonce,dict(peer=peer.identity['id'],local_port=dst,peer_port=src)))
            return
        if not stream or stream['peer']!=peer.identity['id']:return
        if tag==b'A' and len(data)==17:stream['state']=4
        elif tag==b'C' and len(data)==17:stream['closed']=True
        elif tag==b'D' and 17<len(data)<=16401:
            if len(stream['data'])+len(data)-17>65536:raise ValueError('Stream receive window exceeded')
            stream['data'].extend(data[17:])
        elif tag==b'W' and len(data)==21:
            credit=struct.unpack('!I',data[17:])[0]
            if stream['credit']+credit>65536:raise ValueError('Invalid stream credit')
            stream['credit']+=credit
        else:raise ValueError('Unknown stream packet')
    def stream_send(self,s,tag,data=b''):
        peer=self.peers.get(s['peer'])
        return peer.send(tag+bytes.fromhex(s['nonce'])+data) if peer else AGAIN
    def request(self,body):
        op=body.get('op');result=OK
        if op=='status':return dict(result=OK,**self.status())
        if op=='poll':
            # One authenticated snapshot replaces consecutive events/status IPC.
            limit=body.get('max',8)
            if type(limit) is not int or not 0<=limit<=8:return dict(result=BAD)
            reply=self.request(dict(op='events',max=limit))
            return dict(reply,state=self.state)
        if op in ('create','join'):return self.create_or_join(op,body.get('code',''))
        if op=='leave':return self.leave()
        if op=='stop':self.closed=True;return dict(result=OK)
        if op=='drops':return dict(result=OK,pdp=self.pdp_drops)
        if not self.room:return dict(result=NOT_LOGGED)
        if op=='login':
            if self.logged or body.get('mac')!=self.identity['mac'].replace(':','') or body.get('product')!='NPJH50503':result=BAD
            else:self.logged=True
        elif op=='logout':self.group='';self.logged=False;self.pdp.clear();self.ptp.clear();self.streams.clear();self.events.clear();[self.announce(p) for p in self.peers.values() if p.ready()]
        elif not self.logged:return dict(result=NOT_LOGGED)
        elif op=='group':
            group=body.get('group','')
            if self.group or not re.fullmatch('[A-Za-z0-9]{1,8}',group):result=BAD
            else:
                self.group=group
                for peer in self.peers.values():
                    if peer.ready():
                        self.announce(peer)
                        if peer.group==group:self.emit(self.connect_event(peer))
                self.emit(dict(kind=6,mac=self.bssid(group)))
        elif op=='disconnect':
            if not self.group:result=NOT_GROUP
            else:
                self.group=''
                for peer in self.peers.values():
                    if peer.ready():self.announce(peer)
                for stream in self.streams.values():stream['closed']=True
        elif op=='scan':
            if self.group:result=BAD
            else:
                for group in sorted({p.group for p in self.peers.values() if p.group and p.ready()}):self.emit(dict(kind=4,group=group,mac=self.bssid(group)))
                self.emit(dict(kind=5))
        elif op=='events':
            events=[self.events.popleft() for _ in range(min(body.get('max',8),len(self.events),8))];return dict(result=OK,events=events)
        elif op=='pdp_open':
            port=int(body['port'])
            if any(s['port']==port for s in self.pdp.values()) and port:result=PORT_USED
            elif len(self.pdp)>=16:result=NO_SLOT
            elif not 0<=port<=65535:result=BAD
            else:
                handle=next(i for i in range(16) if i not in self.pdp)
                if not port:port=next(i for i in range(40000,40032) if all(s['port']!=i for s in self.pdp.values()))
                self.pdp[handle]=dict(port=port,queue=deque());return dict(result=handle)
        elif op.startswith('pdp_'):
            s=self.pdp.get(int(body['handle']))
            if s is None:return dict(result=NO_SOCKET)
            if op=='pdp_close':del self.pdp[body['handle']]
            elif op=='pdp_stat':return dict(result=OK,port=s['port'],pending=len(s['queue'][0][2]) if s['queue'] else 0)
            elif op=='pdp_send':
                peer=self.peer_for(body['mac']);data=base64.b64decode(body['data'],validate=True)
                if len(data)>10240:result=TOO_BIG
                elif not peer:result=NOT_GROUP
                else:result=OK if peer.send(b'P'+struct.pack('!HH',s['port'],int(body['port']))+data,True)>=0 else AGAIN
            elif op=='pdp_recv':
                if not s['queue']:result=AGAIN
                else:
                    mac,port,data=s['queue'][0]
                    if len(data)>int(body['capacity']):return dict(result=SHORT,size=len(data))
                    s['queue'].popleft();return dict(result=OK,mac=mac,port=port,data=base64.b64encode(data).decode(),size=len(data))
            else:result=BAD
        elif op=='ptp_open':
            port=int(body['port']);backlog=int(body['backlog'])
            if not 0<=port<=65535 or not 0<=backlog<=16:result=BAD
            elif len(self.ptp)>=16:result=NO_SLOT
            elif port and any(s['local_port']==port for s in self.ptp.values()):result=PORT_USED
            else:
                handle=next(i for i in range(16) if i not in self.ptp);port=port or 42000+handle
                self.ptp[handle]=dict(state=1 if backlog else 0,local_port=port,peer_port=int(body['remote']),mac=body['mac'],pending=deque(),backlog=backlog)
                return dict(result=handle)
        elif op.startswith('ptp_'):
            s=self.ptp.get(int(body['handle']))
            if s is None:return dict(result=NO_SOCKET)
            if op=='ptp_connect':
                if s['state']==0:
                    peer=self.peer_for(s['mac'])
                    if not peer:return dict(result=NOT_GROUP)
                    nonce=secrets.token_hex(16);s.update(state=2,nonce=nonce,peer=peer.identity['id'],data=bytearray(),credit=65536,closed=False);self.streams[nonce]=s
                    if self.stream_send(s,b'O',struct.pack('!HH',s['local_port'],s['peer_port']))<0:
                        self.streams.pop(nonce);s['state']=0;return dict(result=AGAIN)
                result=NOT_GROUP if s.get('closed') else OK if s['state']==4 else AGAIN if s['state']==2 else BAD
            elif op=='ptp_accept':
                if s['state']!=1:result=BAD
                elif not s['pending']:result=AGAIN
                elif len(self.ptp)>=16:result=NO_SLOT
                else:
                    nonce,info=s['pending'][0];peer=self.peers.get(info['peer'])
                    if not peer or not peer.ready():s['pending'].popleft();return dict(result=AGAIN)
                    new=dict(info,state=4,nonce=nonce,data=bytearray(),credit=65536,closed=False,mac=peer.identity['mac'].replace(':',''))
                    if self.stream_send(new,b'A')<0:return dict(result=AGAIN)
                    s['pending'].popleft();handle=next(i for i in range(16) if i not in self.ptp);self.ptp[handle]=new;self.streams[nonce]=new;return dict(result=handle)
            elif op=='ptp_close':
                if 'nonce' in s:self.stream_send(s,b'C');self.streams.pop(s['nonce'],None)
                del self.ptp[body['handle']]
            elif op=='ptp_stat':return dict(result=OK,port=s['local_port'],remote=s['peer_port'],mac=s['mac'],state=0 if s.get('closed') else s['state'],pending=len(s.get('data',b'')))
            elif s['state']!=4 or s.get('closed'):result=NOT_GROUP
            elif op=='ptp_send':
                data=base64.b64decode(body['data'],validate=True);data=data[:min(16384,s['credit'])]
                if not data:result=AGAIN
                elif self.stream_send(s,b'D',data)<0:result=AGAIN
                else:s['credit']-=len(data);return dict(result=OK,size=len(data))
            elif op=='ptp_recv':
                size=min(int(body['capacity']),len(s['data']))
                if not size:result=AGAIN
                elif self.stream_send(s,b'W',struct.pack('!I',size))<0:result=AGAIN
                else:
                    data=bytes(s['data'][:size]);del s['data'][:size];return dict(result=OK,size=size,data=base64.b64encode(data).decode())
            else:result=BAD
        else:result=BAD
        return dict(result=result)
    def close(self):
        if self.future:
            try:self.future.result(timeout=6)
            except Exception:pass
        if self.room and self.service:
            try:self.service.call('leave',dict(session=self.room['session']),self.room['token'])
            except Exception:pass
        self.reset();self.executor.shutdown(wait=True,cancel_futures=True)

def serve(agent,ready,token,parent=None):
    listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen(8);listener.setblocking(False)
    selector=selectors.DefaultSelector();selector.register(listener,selectors.EVENT_READ);clients={}
    ready.write_text(json.dumps(dict(pid=os.getpid(),port=listener.getsockname()[1],token=token)))
    try:
        while not agent.closed:
            if parent and parent():break
            agent.tick()
            for key,mask in selector.select(.005):
                sock=key.fileobj
                if sock is listener:
                    sock,_=listener.accept();sock.setblocking(False);sock.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1)
                    if len(clients)>=8:sock.close();continue
                    clients[sock]=dict(rx=bytearray(),tx=bytearray(),seen=time.monotonic());selector.register(sock,selectors.EVENT_READ);continue
                client=clients[sock]
                try:
                    if mask&selectors.EVENT_READ:
                        data=sock.recv(65536)
                        if not data:raise ConnectionError()
                        client['rx'].extend(data)
                        if len(client['rx'])>65536:raise ValueError('IPC input limit')
                        while b'\n' in client['rx']:
                            raw,_,rest=client['rx'].partition(b'\n');client['rx']=bytearray(rest);request=json.loads(raw)
                            if not hmac.compare_digest(str(request.pop('token','')),token):raise ValueError('Invalid IPC token')
                            response=agent.request(request);client['tx'].extend(json.dumps(response,separators=(',',':')).encode()+b'\n');client['seen']=time.monotonic()
                            if len(client['tx'])>65536:raise ValueError('IPC output limit')
                        if client['tx']:selector.modify(sock,selectors.EVENT_READ|selectors.EVENT_WRITE)
                    if mask&selectors.EVENT_WRITE and client['tx']:
                        count=sock.send(client['tx']);del client['tx'][:count]
                        if not client['tx']:selector.modify(sock,selectors.EVENT_READ)
                except (OSError,ValueError,KeyError,TypeError):selector.unregister(sock);sock.close();clients.pop(sock,None)
            for sock,client in list(clients.items()):
                if time.monotonic()-client['seen']>30:selector.unregister(sock);sock.close();del clients[sock]
    finally:
        for sock in clients:sock.close()
        listener.close();selector.close();agent.close()

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--ready-file',type=Path,required=True);parser.add_argument('--identity',type=Path,required=True);parser.add_argument('--service',default='');parser.add_argument('--relay',action='store_true');parser.add_argument('--parent-pid',type=int)
    parser.add_argument('--backend',choices=('rooms','steam'),default='rooms');parser.add_argument('--preferences',type=Path);args=parser.parse_args()
    ready=args.ready_file.resolve();identity=args.identity.resolve()
    if not all(p.is_relative_to(ROOT/'private') for p in (ready,identity)):parser.error('Session files must be private.')
    dead=None;handle=None
    if args.parent_pid and os.name=='nt':
        import ctypes
        kernel=ctypes.WinDLL('kernel32',use_last_error=True);kernel.OpenProcess.argtypes=(ctypes.c_ulong,ctypes.c_int,ctypes.c_ulong);kernel.OpenProcess.restype=ctypes.c_void_p
        kernel.WaitForSingleObject.argtypes=(ctypes.c_void_p,ctypes.c_ulong);kernel.CloseHandle.argtypes=(ctypes.c_void_p,)
        handle=kernel.OpenProcess(0x00100000,False,args.parent_pid)
        if not handle:raise ctypes.WinError(ctypes.get_last_error())
        dead=lambda:kernel.WaitForSingleObject(handle,0)==0
    value=json.loads(identity.read_text())
    from online_router import Router
    try:serve(Router(dict(mac=value['mac'],nickname=value['nickname']),args.service,relay=args.relay,backend=args.backend,preferences=args.preferences),ready,secrets.token_urlsafe(32),dead)
    finally:
        if handle:kernel.CloseHandle(handle)
if __name__=='__main__':main()
