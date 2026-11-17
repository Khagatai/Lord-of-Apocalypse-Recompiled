"""Spacewar development lobbies and Steam messages behind the existing PSP IPC.

Steam lobby membership is not a successful game connection. Peers must exchange
actual protocol hello/ack packets before being reported connected.
"""
import hashlib,re,struct,sys,time,zlib
from online_agent import Agent,OK,AGAIN,BAD,NOT_LOGGED
from steam_native import NativeSteam
MAGIC=b'LOAS1'
MAC=re.compile(r'(?:[0-9a-f]{2}:){5}[0-9a-f]{2}')
def mac_ok(value):return isinstance(value,str) and MAC.fullmatch(value) is not None and not int(value[:2],16)&1 and value!='00:00:00:00:00:00'
class SteamPeer:
    def __init__(self,native,identity,local_mac):
        self.native=native;self.identity=identity;self.local_mac=bytes.fromhex(local_mac.replace(':',''));self.group='';self.announced=False;self.path_announced=''
        self.failed=False;self.closed=False;self.hello=False;self.ack=False;self.due=0;self.born=time.monotonic()
    def ready(self):return not self.closed and not self.failed and self.hello and self.ack and bool(self.native.lib.loa_steam_connected(int(self.identity['id'])))
    def handshake(self):
        now=time.monotonic()
        if now>=self.due:
            self.native.send(self.identity['id'],MAGIC+b'H'+self.local_mac);self.due=now+(5 if self.ready() else 1)
        if now-self.born>30 and not self.ready():self.failed=True
    def receive(self,channel,data):
        if not data.startswith(MAGIC):raise ValueError('Wrong Steam packet protocol.')
        value=data[len(MAGIC):]
        if value[:1] in (b'H',b'h'):
            if channel!=0 or len(value)!=7 or value[1:]!=bytes.fromhex(self.identity['mac'].replace(':','')):raise ValueError('Wrong Steam peer identity.')
            if value[:1]==b'H':self.hello=True;self.native.send(self.identity['id'],MAGIC+b'h'+self.local_mac)
            else:self.ack=True
            return None
        if not self.ready():return None
        if (value[:1]==b'P')!=(channel==1):raise ValueError('Wrong Steam data channel.')
        return value
    def send(self,data,unreliable=False):return self.native.send(self.identity['id'],MAGIC+data,unreliable) if self.ready() else AGAIN
    def path(self):return 'steam'
    def close(self):
        if not self.closed:self.native.lib.loa_steam_close_peer(int(self.identity['id']));self.closed=True

class SteamAgent(Agent):
    def __init__(self,identity,*,factory=NativeSteam):
        super().__init__(identity);self.steam=None;self.rooms=[];self.last_roster=0;self.last_lobby=0;self.steam_status={};self.last_native_state=None
        try:self.steam=factory(identity['mac'])
        except (OSError,ValueError,RuntimeError) as error:self.state='error';self.error=str(error)
    def status(self):
        return dict(backend='steam',state=self.state,error=self.error,code='',lobby=str(self.last_lobby) if self.last_lobby else '',
                    players=self.steam_status.get('players',0),connected=sum(p.ready() for p in self.peers.values()),
                    paths=['steam' for p in self.peers.values() if p.ready()],service_configured=self.steam is not None,
                    rooms=self.rooms,app_id=480,overlay_available=bool(self.steam_status.get('overlay',0)))
    def create_or_join(self,op,code=''):
        if not self.steam:return dict(result=NOT_LOGGED,error=self.error or 'Steam is unavailable.')
        if self.room or self.state in ('creating','joining'):return dict(result=BAD,error='Leave the current lobby first.')
        if op=='create':accepted=self.steam.lib.loa_steam_create()
        else:
            if not isinstance(code,str) or not code.isdecimal() or not 1<=len(code)<=20 or not 0<int(code)<2**64:return dict(result=BAD,error='Choose a Steam friend lobby.')
            accepted=self.steam.lib.loa_steam_join(int(code))
        if not accepted:return dict(result=BAD,error='Steam did not accept the lobby request.')
        self.state='creating' if op=='create' else 'joining';self.error='';return dict(result=OK)
    def leave(self):
        if self.state in ('creating','joining'):return dict(result=AGAIN,error='Wait for the pending Steam lobby request.')
        if self.steam:self.steam.lib.loa_steam_leave()
        self.reset();self.last_lobby=0;return dict(result=OK)
    def request(self,body):
        op=body.get('op')
        if op=='join':return self.create_or_join('join',body.get('lobby',''))
        if op=='refresh':
            if not self.steam:return dict(result=NOT_LOGGED,error=self.error)
            self.steam.lib.loa_steam_refresh();return dict(result=OK)
        if op=='invite':
            if not self.steam or not self.room:return dict(result=NOT_LOGGED,error='Create or join a lobby first.')
            opened=bool(self.steam.lib.loa_steam_invite())
            return dict(result=OK if opened else BAD,error='Choose friends in the Steam overlay. No invitation is sent automatically.' if opened else 'Steam overlay is unavailable. Friends can join using Refresh friends\' lobbies.')
        return super().request(body)
    def tick(self):
        if not self.steam:return
        self.steam.lib.loa_steam_tick();value=self.steam.status();self.steam_status=value
        if value['state']!=self.last_native_state:
            self.last_native_state=value['state'];print(f'LOA_STEAM: state={value["state"]} members={value["players"]}',file=sys.stderr,flush=True)
        self.rooms=self.steam.rooms()
        if value['error']:self.error=value['error']
        if value['state']!=3:
            if self.room:self.reset();self.last_lobby=0
            self.state={1:'creating',2:'joining',-1:'error'}.get(value['state'],'offline');return
        lobby=value['lobby'];self.state='in-room'
        if self.last_lobby!=lobby:
            self.reset();self.last_lobby=lobby;raw=bytearray(hashlib.sha256(struct.pack('!Q',lobby)).digest()[:6]);raw[0]=(raw[0]|2)&254
            self.room=dict(code='',slot=0 if value['user']==value['owner'] else 1,bssid=raw.hex());self.state='in-room'
        now=time.monotonic()
        if now-self.last_roster>=.2:
            rows=self.steam.members();alive=set();used_mac={self.identity['mac']};used_ids=set()
            for row in rows:
                if row['user']==value['user']:continue
                who=str(row['user']);alive.add(who)
                if not mac_ok(row['mac']):continue # Member data can arrive after the join callback.
                slot=zlib.crc32(struct.pack('!Q',row['user']))&0x7fffffff
                if row['mac'] in used_mac or slot in used_ids:self.error='Duplicate peer identity in the Steam lobby.';continue
                used_mac.add(row['mac']);used_ids.add(slot)
                if who not in self.peers and len(self.peers)<3:
                    identity=dict(id=who,slot=slot,mac=row['mac'],nickname=row['name'][:128])
                    self.peers[who]=SteamPeer(self.steam,identity,self.identity['mac'])
            for who,peer in list(self.peers.items()):
                if who not in alive:
                    if self.group and peer.group==self.group:self.emit(dict(kind=3,peer_id=peer.identity['slot']+1))
                    peer.close();del self.peers[who]
                    for stream in self.streams.values():
                        if stream['peer']==who:stream['closed']=True
            self.last_roster=now
        for _ in range(64):
            packet=self.steam.receive()
            if packet is None:break
            who,channel,data=packet;peer=self.peers.get(who)
            if not peer:continue
            try:
                value=peer.receive(channel,data)
                if value is not None:self.packet(peer,value)
            except (ValueError,KeyError,TypeError):peer.failed=True;self.error='Invalid Steam multiplayer packet.'
        for peer in self.peers.values():
            peer.handshake()
            if peer.ready() and not peer.announced:
                peer.announced=self.announce(peer)
                if peer.announced:print('LOA_STEAM: peer confirmed by actual protocol hello/ack',file=sys.stderr,flush=True)
            if peer.failed:self.error='Steam peer connection failed or timed out.'
    def close(self):
        self.reset()
        if self.steam:self.steam.close();self.steam=None
        self.executor.shutdown(wait=True,cancel_futures=True)
