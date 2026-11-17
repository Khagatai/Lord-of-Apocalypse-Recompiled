"""ctypes bindings to pinned native libdatachannel, data channels only."""
import ctypes as c,hashlib,json,os,queue
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class Configuration(c.Structure):
    _fields_=[('iceServers',c.POINTER(c.c_char_p)),('iceServersCount',c.c_int),('proxyServer',c.c_char_p),('bindAddress',c.c_char_p),
              ('certificateType',c.c_int),('iceTransportPolicy',c.c_int),('enableIceTcp',c.c_bool),('enableIceUdpMux',c.c_bool),
              ('disableAutoNegotiation',c.c_bool),('forceMediaTransport',c.c_bool),('portRangeBegin',c.c_uint16),('portRangeEnd',c.c_uint16),('mtu',c.c_int),('maxMessageSize',c.c_int)]
class Reliability(c.Structure):_fields_=[('unordered',c.c_bool),('unreliable',c.c_bool),('maxPacketLifeTime',c.c_uint),('maxRetransmits',c.c_uint)]
class ChannelInit(c.Structure):_fields_=[('reliability',Reliability),('protocol',c.c_char_p),('negotiated',c.c_bool),('manualStream',c.c_bool),('stream',c.c_uint16)]
DESCRIPTION=c.CFUNCTYPE(None,c.c_int,c.c_char_p,c.c_char_p,c.c_void_p)
CANDIDATE=c.CFUNCTYPE(None,c.c_int,c.c_char_p,c.c_char_p,c.c_void_p)
STATE=c.CFUNCTYPE(None,c.c_int,c.c_int,c.c_void_p)
MESSAGE=c.CFUNCTYPE(None,c.c_int,c.c_void_p,c.c_int,c.c_void_p)
class NativeRTC:
    def __init__(self):
        self.dll_dirs=[os.add_dll_directory(str(ROOT/'private/toolchain/prerequisites/msys64/ucrt64/bin'))] if os.name=='nt' else []
        path=ROOT/'private/online-deps/build/datachannel/libdatachannel.dll'
        build=json.loads((ROOT/'private/online-deps/build.json').read_text())
        pins=json.loads((ROOT/'config/online-dependencies.json').read_text())
        if build['pins']!=pins or hashlib.sha256(path.read_bytes()).hexdigest()!=build['dll_sha256']:raise ValueError('Native online dependency fingerprint differs. Rebuild online dependencies.')
        self.lib=c.CDLL(str(path));lib=self.lib
        signatures={
          'rtcCreatePeerConnection':([c.POINTER(Configuration)],c.c_int),
          'rtcSetLocalDescriptionCallback':([c.c_int,DESCRIPTION],c.c_int),'rtcSetLocalCandidateCallback':([c.c_int,CANDIDATE],c.c_int),
          'rtcSetStateChangeCallback':([c.c_int,STATE],c.c_int),'rtcSetMessageCallback':([c.c_int,MESSAGE],c.c_int),
          'rtcSetLocalDescription':([c.c_int,c.c_char_p],c.c_int),'rtcSetRemoteDescription':([c.c_int,c.c_char_p,c.c_char_p],c.c_int),
          'rtcAddRemoteCandidate':([c.c_int,c.c_char_p,c.c_char_p],c.c_int),'rtcCreateDataChannelEx':([c.c_int,c.c_char_p,c.POINTER(ChannelInit)],c.c_int),
          'rtcSendMessage':([c.c_int,c.c_void_p,c.c_int],c.c_int),'rtcGetBufferedAmount':([c.c_int],c.c_int),
          'rtcIsOpen':([c.c_int],c.c_bool),'rtcDeleteDataChannel':([c.c_int],c.c_int),'rtcDeletePeerConnection':([c.c_int],c.c_int),
          'rtcGetSelectedCandidatePair':([c.c_int,c.c_void_p,c.c_int,c.c_void_p,c.c_int],c.c_int)}
        for name,(args,result) in signatures.items():fn=getattr(lib,name);fn.argtypes=args;fn.restype=result
    @staticmethod
    def checked(result):
        if result<0:raise RuntimeError('Native peer connection failed ('+str(result)+').')
        return result

class Peer:
    def __init__(self,native,identity,ice,inbox,*,relay=False):
        self.native=native;self.lib=native.lib;self.identity=identity;self.inbox=inbox;self.callbacks=[];self.closed=False;self.failed=False;self.candidates=[];self.remote_set=False;self.relay_endpoints=set();self.relay_policy=relay;self.remote_relay=False
        from urllib.parse import quote,urlsplit
        urls=[]
        for server in ice:
            url=server['url']
            if server.get('username'):
                scheme,tail=url.split(':',1);url=scheme+'://'+quote(server['username'],safe='')+':'+quote(server['password'],safe='')+'@'+tail.lstrip('/')
            urls.append(url.encode())
        servers=(c.c_char_p*len(urls))(*urls);conf=Configuration();conf.iceServers=servers;conf.iceServersCount=len(urls)
        conf.disableAutoNegotiation=True;conf.maxMessageSize=65536;conf.iceTransportPolicy=int(relay)
        self.pc=native.checked(self.lib.rtcCreatePeerConnection(c.byref(conf)))
        def emit(kind,value):
            if self.closed:return
            try:inbox.put_nowait((identity['id'],kind,value))
            except queue.Full:self.failed=True
        @DESCRIPTION
        def description(pc,sdp,kind,ptr):emit('signal',dict(kind=kind.decode(),sdp=sdp.decode()))
        @CANDIDATE
        def candidate(pc,value,mid,ptr):
            text=value.decode();self.remember_relay(text);emit('signal',dict(kind='candidate',candidate=text,mid=mid.decode()))
        @STATE
        def state(pc,value,ptr):emit('state',value)
        self.callbacks.extend((description,candidate,state))
        native.checked(self.lib.rtcSetLocalDescriptionCallback(self.pc,description));native.checked(self.lib.rtcSetLocalCandidateCallback(self.pc,candidate));native.checked(self.lib.rtcSetStateChangeCallback(self.pc,state))
        self.channels=[]
        for index in range(2):
            init=ChannelInit();init.negotiated=True;init.manualStream=True;init.stream=index
            init.reliability=Reliability(bool(index),bool(index),0,0)
            dc=native.checked(self.lib.rtcCreateDataChannelEx(self.pc,b'control-stream' if index==0 else b'pdp',c.byref(init)))
            @MESSAGE
            def message(dc,data,size,ptr,_stream=index):
                if 0<size<=65536:emit('packet',(_stream,c.string_at(data,size)))
                else:emit('invalid',None)
            self.callbacks.append(message);native.checked(self.lib.rtcSetMessageCallback(dc,message));self.channels.append(dc)
    def offer(self):self.native.checked(self.lib.rtcSetLocalDescription(self.pc,b'offer'))
    def signal(self,value):
        kind=value['kind']
        if kind=='candidate':
            self.remember_relay(value['candidate'])
            if self.remote_set:self.native.checked(self.lib.rtcAddRemoteCandidate(self.pc,value['candidate'].encode(),value['mid'].encode()))
            elif len(self.candidates)<64:self.candidates.append(value)
            else:raise ValueError('Too many remote ICE candidates.')
        else:
            self.native.checked(self.lib.rtcSetRemoteDescription(self.pc,value['sdp'].encode(),kind.encode()));self.remote_set=True
            for pending in self.candidates:self.signal(pending)
            self.candidates.clear()
            if kind=='offer':self.native.checked(self.lib.rtcSetLocalDescription(self.pc,b'answer'))
    def ready(self):return not self.closed and not self.failed and all(self.lib.rtcIsOpen(dc) for dc in self.channels)
    def send(self,data,unreliable=False):
        if not self.ready():return -1
        dc=self.channels[int(unreliable)]
        if self.lib.rtcGetBufferedAmount(dc)>262144:return -1
        buffer=c.create_string_buffer(data)
        return self.lib.rtcSendMessage(dc,buffer,len(data))
    @staticmethod
    def endpoint(candidate):
        parts=candidate.split();return tuple(parts[4:6]) if len(parts)>=8 else None
    def remember_relay(self,candidate):
        if ' typ relay' in candidate:self.relay_endpoints.add(self.endpoint(candidate))
    def path(self):
        if self.relay_policy or self.remote_relay:return 'relayed'
        local=c.create_string_buffer(2048);remote=c.create_string_buffer(2048)
        if self.lib.rtcGetSelectedCandidatePair(self.pc,local,len(local),remote,len(remote))<0:return 'connecting'
        # A selected peer-reflexive candidate can hide its original relay type.
        # Keep the relay endpoints exchanged during signalling for that case.
        candidates=[local.value.decode(),remote.value.decode()]
        return 'relayed' if any(' typ relay' in v or self.endpoint(v) in self.relay_endpoints for v in candidates) else 'direct'
    def close(self):
        if self.closed:return
        self.closed=True
        for dc in self.channels:self.lib.rtcDeleteDataChannel(dc)
        self.lib.rtcDeletePeerConnection(self.pc)
