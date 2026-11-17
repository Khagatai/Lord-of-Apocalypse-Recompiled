"""Bounded room-code signalling service. Receives connection metadata, never game files.

Run behind an HTTPS reverse proxy for public use. TURN is configured by the
operator; this HTTP service does not relay gameplay or open arbitrary URLs.
"""
import argparse,base64,hashlib,hmac,json,os,re,secrets,threading,time
from collections import defaultdict,deque
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path

class RoomError(Exception):
    def __init__(self,status,message):self.status=status;super().__init__(message)

class Rooms:
    def __init__(self,*,clock=time.monotonic,code_factory=None,ice=None,turn_secret='',turn_url=''):
        self.clock=clock;self.code_factory=code_factory or (lambda:f'{secrets.randbelow(100000):05d}')
        self.rooms={};self.sessions={};self.attempts={};self.lock=threading.RLock()
        self.ice=ice or [];self.turn_secret=turn_secret;self.turn_url=turn_url
    def sweep(self):
        now=self.clock()
        for room in list(self.rooms.values()):
            for member in list(room['members'].values()):
                if now-member['seen']>60:self.remove(member)
            if now-room['born']>21600:
                for member in list(room['members'].values()):self.remove(member)
        self.attempts={k:v for k,v in self.attempts.items() if v and now-v[-1]<60}
    def limit(self,ip):
        now=self.clock();q=self.attempts.setdefault(ip,deque())
        while q and now-q[0]>=60:q.popleft()
        if len(q)>=12:raise RoomError(429,'Too many room attempts. Try again in a minute.')
        if len(self.attempts)>4096:raise RoomError(503,'Room service is busy.')
        q.append(now)
    @staticmethod
    def identity(body):
        mac=body.get('mac','');nick=body.get('nickname','');build=body.get('build','')
        if not isinstance(mac,str) or not re.fullmatch(r'(?:[0-9a-f]{2}:){5}[0-9a-f]{2}',mac) or int(mac[:2],16)&1 or mac=='00:00:00:00:00:00':raise RoomError(400,'Invalid console identity.')
        if not isinstance(nick,str) or not 1<=len(nick)<=32 or any(ord(c)<32 or ord(c)>126 for c in nick):raise RoomError(400,'Invalid player nickname.')
        if build!='loa-native-v1-NPJH50503':raise RoomError(409,'Incompatible multiplayer protocol or game.')
        return mac,nick,build
    def add(self,room,identity):
        mac,nick,build=identity
        if len(self.sessions)>=4000:raise RoomError(503,'Room service is full.')
        if any(m['mac']==mac for m in room['members'].values()):raise RoomError(409,'This console is already in the room.')
        if len(room['members'])>=4:raise RoomError(409,'Room is full.')
        sid=secrets.token_urlsafe(18);slot=next(i for i in range(4) if i not in {m['slot'] for m in room['members'].values()})
        m=dict(id=sid,token=secrets.token_urlsafe(32),room=room,slot=slot,mac=mac,nickname=nick,seen=self.clock(),events=deque())
        for other in room['members'].values():other['events'].append(dict(kind='joined',peer=self.public(m)))
        room['members'][sid]=m;self.sessions[sid]=m
        return m
    @staticmethod
    def public(m):return {k:m[k] for k in ('id','slot','mac','nickname')}
    def response(self,m):
        room=m['room'];ice=list(self.ice)
        if self.turn_secret and self.turn_url:
            username=f'{int(time.time())+3600}:{m["id"]}'
            credential=base64.b64encode(hmac.new(self.turn_secret.encode(),username.encode(),hashlib.sha1).digest()).decode()
            ice.append(dict(url=self.turn_url,username=username,password=credential))
        return dict(code=room['code'],session=m['id'],token=m['token'],slot=m['slot'],bssid=room['bssid'],
                    peers=[self.public(p) for p in room['members'].values() if p is not m],ice=ice)
    def remove(self,m):
        room=m['room']
        if m['id'] not in self.sessions:return
        del self.sessions[m['id']];room['members'].pop(m['id'],None)
        event=dict(kind='left',peer=m['id'])
        if m['slot']==0:
            event=dict(kind='closed')
            for other in list(room['members'].values()):
                other['events'].clear();other['events'].append(event);other['closed']=True
            self.rooms.pop(room['code'],None)
        else:
            for other in room['members'].values():
                if len(other['events'])>=128:other['events'].popleft()
                other['events'].append(event)
        if not room['members']:self.rooms.pop(room['code'],None)
    def request(self,op,body,ip='127.0.0.1',token=''):
        with self.lock:
            self.sweep()
            if op in ('create','join'):
                allowed={'mac','nickname','build'} | ({'code'} if op=='join' else set())
                if set(body)!=allowed:raise RoomError(400,'Invalid room request fields.')
                self.limit(ip);ident=self.identity(body)
                if op=='create':
                    if len(self.rooms)>=1000:raise RoomError(503,'Room service is full.')
                    for _ in range(128):
                        code=self.code_factory()
                        if code not in self.rooms:break
                    else:raise RoomError(503,'Could not allocate a room code.')
                    mac=bytearray(secrets.token_bytes(6));mac[0]=(mac[0]|2)&254
                    room=dict(code=code,bssid=mac.hex(),members={},born=self.clock());self.rooms[code]=room
                else:
                    code=body.get('code')
                    if not isinstance(code,str) or not re.fullmatch(r'[0-9]{5}',code):raise RoomError(400,'Enter exactly five digits.')
                    room=self.rooms.get(code)
                    if room is None:raise RoomError(404,'Room not found or expired.')
                try:return self.response(self.add(room,ident))
                except RoomError:
                    if not room['members']:self.rooms.pop(room['code'],None)
                    raise
            if set(body)-({'session','signals'} if op=='exchange' else {'session'}):raise RoomError(400,'Invalid session request fields.')
            m=self.sessions.get(body.get('session',''))
            if m is None or not isinstance(token,str) or not hmac.compare_digest(m['token'],token):raise RoomError(401,'Room session expired. Create or join again.')
            if op=='leave':self.remove(m);return dict(ok=True)
            if op!='exchange':raise RoomError(404,'Unknown operation.')
            if m.get('closed'):
                self.remove(m);return dict(events=[dict(kind='closed')])
            signals=body.get('signals',[])
            if not isinstance(signals,list) or len(signals)>32:raise RoomError(400,'Signal batch too large.')
            checked=[]
            for signal in signals:
                if not isinstance(signal,dict) or set(signal)-{'to','kind','sdp','candidate','mid'}:raise RoomError(400,'Invalid signalling fields.')
                peer=m['room']['members'].get(signal.get('to'))
                if peer is None or peer is m:raise RoomError(404,'Player left the room.')
                kind=signal.get('kind')
                if kind in ('offer','answer'):
                    if set(signal)!={'to','kind','sdp'} or not isinstance(signal['sdp'],str) or not 1<=len(signal['sdp'])<=16384:raise RoomError(400,'Invalid description.')
                elif kind=='candidate':
                    if set(signal)!={'to','kind','candidate','mid'} or not isinstance(signal['candidate'],str) or not 1<=len(signal['candidate'])<=2048 or not isinstance(signal['mid'],str) or not 1<=len(signal['mid'])<=64:raise RoomError(400,'Invalid ICE candidate.')
                else:raise RoomError(400,'Unknown signal type.')
                if len(peer['events'])+len(signals)>128:raise RoomError(429,'Peer signalling queue is full.')
                checked.append((peer,dict(signal,**{'from':m['id']})))
            for peer,event in checked:peer['events'].append(event)
            m['seen']=self.clock();events=list(m['events']);m['events'].clear()
            return dict(events=events)

class Server(ThreadingHTTPServer):
    daemon_threads=True
    def __init__(self,address,rooms):
        self.rooms=rooms;self.slots=threading.BoundedSemaphore(32);super().__init__(address,Handler)
    def process_request(self,request,address):
        if not self.slots.acquire(False):request.close();return
        try:super().process_request(request,address)
        except BaseException:self.slots.release();raise
    def process_request_thread(self,*args):
        try:super().process_request_thread(*args)
        finally:self.slots.release()

class Handler(BaseHTTPRequestHandler):
    protocol_version='HTTP/1.0'
    def log_message(self,*args):pass # No session tokens, SDP, IPs or codes in access logs.
    def setup(self):super().setup();self.connection.settimeout(5)
    def do_POST(self):
        try:
            if self.path not in ('/v1/create','/v1/join','/v1/exchange','/v1/leave'):raise RoomError(404,'Unknown endpoint.')
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<=65536:raise RoomError(413,'Request too large.')
            if self.headers.get('Content-Type','').split(';')[0]!='application/json':raise RoomError(415,'JSON required.')
            raw=self.rfile.read(length)
            if len(raw)!=length:raise RoomError(400,'Incomplete request.')
            body=json.loads(raw)
            if not isinstance(body,dict):raise RoomError(400,'JSON object required.')
            auth=self.headers.get('Authorization','');token=auth[7:] if auth.startswith('Bearer ') else ''
            data=self.server.rooms.request(self.path[4:],body,self.client_address[0],token);status=200
        except RoomError as error:status=error.status;data=dict(error=str(error))
        except (ValueError,TypeError,KeyError,TimeoutError):status=400;data=dict(error='Invalid request.')
        encoded=json.dumps(data,separators=(',',':')).encode();self.send_response(status)
        self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(encoded)))
        self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(encoded)

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--listen',default='127.0.0.1');parser.add_argument('--port',type=int,default=8741)
    parser.add_argument('--ready-file',type=Path);args=parser.parse_args()
    stun=os.environ.get('LOA_STUN_URL','');ice=[dict(url=stun)] if stun else []
    rooms=Rooms(ice=ice,turn_secret=os.environ.get('LOA_TURN_SECRET',''),turn_url=os.environ.get('LOA_TURN_URL',''))
    server=Server((args.listen,args.port),rooms)
    if args.ready_file:
        path=args.ready_file.resolve();root=Path(__file__).resolve().parents[1]/'private'
        if not path.is_relative_to(root):parser.error('Readiness markers must be private.')
        path.write_text(json.dumps(dict(pid=os.getpid(),port=server.server_port)))
    try:server.serve_forever(poll_interval=.2)
    except KeyboardInterrupt:pass
    finally:server.server_close()
if __name__=='__main__':main()
