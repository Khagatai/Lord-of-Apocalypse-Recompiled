"""Typed bindings to our original standalone bridge, never to guessed SDK layouts."""
import ctypes as c,hashlib,json,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class Status(c.Structure):_fields_=[('user',c.c_uint64),('lobby',c.c_uint64),('owner',c.c_uint64),('state',c.c_int32),('players',c.c_int32),('overlay',c.c_int32),('name',c.c_char*128),('error',c.c_char*256)]
class Member(c.Structure):_fields_=[('user',c.c_uint64),('name',c.c_char*128),('mac',c.c_char*18)]
class Room(c.Structure):_fields_=[('lobby',c.c_uint64),('owner',c.c_uint64),('players',c.c_int32),('name',c.c_char*128)]
def text(raw):return bytes(raw).split(b'\0',1)[0].decode('utf-8',errors='replace')
class NativeSteam:
    def __init__(self,mac):
        folder=ROOT/'private/steam-test';record=folder/'bridge.json'
        if not record.is_file():raise RuntimeError('Steam test adapter is not built. Supply the official SDK, then run tools/build-steam-bridge.py.')
        metadata=json.loads(record.read_text())
        if metadata.get('app_id')!=480:raise ValueError('Unexpected Steam test App ID.')
        for name,path in [('steam_bridge.cpp',ROOT/'tools/steam_bridge.cpp'),('steam_flat.h',ROOT/'tools/steam_flat.h'),('loa_steam_bridge.dll',folder/'loa_steam_bridge.dll'),('steam_api64.dll',folder/'steam_api64.dll')]:
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=metadata['sha256'].get(name):raise ValueError('Steam adapter fingerprint differs. Rebuild with the official SDK.')
        os.environ['SteamAppId']='480';os.environ['SteamGameId']='480'
        # Steam's documented local test marker lives only in this helper's
        # private working directory, never in the user's Steam installation.
        marker=Path.cwd()/'steam_appid.txt'
        if not marker.resolve().is_relative_to(ROOT/'private'):raise ValueError('Steam helper must run from a private session directory.')
        marker.write_text('480\n')
        self.dll_dirs=[os.add_dll_directory(str(folder)),os.add_dll_directory(str(ROOT/'private/toolchain/prerequisites/msys64/ucrt64/bin'))]
        self.lib=c.CDLL(str(folder/'loa_steam_bridge.dll'));lib=self.lib;self.active=False
        signatures={
            'loa_steam_init':([c.c_char_p,c.c_void_p,c.c_uint32],c.c_int),'loa_steam_tick':([],None),'loa_steam_shutdown':([],None),
            'loa_steam_status':([c.POINTER(Status)],c.c_int),'loa_steam_create':([],c.c_int),'loa_steam_join':([c.c_uint64],c.c_int),
            'loa_steam_leave':([],None),'loa_steam_members':([c.POINTER(Member),c.c_int],c.c_int),
            'loa_steam_refresh':([],None),'loa_steam_rooms':([c.POINTER(Room),c.c_int],c.c_int),'loa_steam_invite':([],c.c_int),
            'loa_steam_send':([c.c_uint64,c.c_void_p,c.c_uint32,c.c_int],c.c_int),
            'loa_steam_receive':([c.POINTER(c.c_uint64),c.c_void_p,c.c_uint32,c.POINTER(c.c_int)],c.c_int),
            'loa_steam_connected':([c.c_uint64],c.c_int),'loa_steam_close_peer':([c.c_uint64],None)}
        for name,(args,result) in signatures.items():fn=getattr(lib,name);fn.argtypes=args;fn.restype=result
        error=c.create_string_buffer(512)
        if not lib.loa_steam_init(mac.encode('ascii'),error,len(error)):raise RuntimeError(error.value.decode(errors='replace'))
        self.active=True
    def status(self):
        out=Status()
        if not self.lib.loa_steam_status(c.byref(out)):raise RuntimeError('Steam session is unavailable.')
        return {name:text(getattr(out,name)) if name in ('name','error') else getattr(out,name) for name,_ in out._fields_}
    def members(self):
        out=(Member*4)();n=self.lib.loa_steam_members(out,4)
        return [dict(user=v.user,name=text(v.name),mac=text(v.mac)) for v in out[:n]]
    def rooms(self):
        out=(Room*16)();n=self.lib.loa_steam_rooms(out,16)
        return [dict(lobby=str(v.lobby),owner=str(v.owner),players=v.players,name=text(v.name)) for v in out[:n]]
    def send(self,peer,data,unreliable=False):
        buffer=c.create_string_buffer(data);return self.lib.loa_steam_send(int(peer),buffer,len(data),int(unreliable))
    def receive(self):
        peer=c.c_uint64();channel=c.c_int();data=c.create_string_buffer(17000)
        n=self.lib.loa_steam_receive(c.byref(peer),data,len(data),c.byref(channel))
        return (str(peer.value),channel.value,data.raw[:n]) if n>0 else None
    def close(self):
        if self.active:self.lib.loa_steam_shutdown();self.active=False
