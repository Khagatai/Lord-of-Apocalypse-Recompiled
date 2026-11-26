"""Actual native IPC, JSON and agent snapshots; synthetic lobby, no Steam peers."""
import ctypes,json,os,socketserver,subprocess,sys,tempfile,threading,time,unittest
from collections import deque
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import title
from online_agent import Agent

FIXTURE=r'''
#include "online_runtime.h"
__declspec(dllexport) int fixture_poll(unsigned *fields){
 NkLobbyEvent e[8];size_t n=0;int alive=loa_online_poll(e,8,&n);
 fields[0]=(unsigned)n;fields[1]=n?(unsigned)e[0].kind:0;
 fields[2]=n?e[0].peer_id:0;return alive;
}
__declspec(dllexport) int fixture_info(int handle,unsigned *fields){
 uint16_t port=0;uint32_t pending=0;int r=loa_online_socket_info(handle,&port,&pending);
 fields[0]=port;fields[1]=pending;return r;
}
__declspec(dllexport) int fixture_cycle(int combined,unsigned *fields){
 NkAdhocTransport *t=loa_online_transport();NkLobbyEvent e[8];size_t n=0;
 int alive;uint16_t port;uint32_t pending;
 if(combined){alive=loa_online_poll(e,8,&n);if(loa_online_socket_info(0,&port,&pending))return -1;}
 else{n=t->ops->take_events(t,e,8);alive=loa_online_alive();port=loa_online_port(0);pending=loa_online_pending(0);}
 fields[0]=(unsigned)n;fields[1]=port;fields[2]=pending;return alive;
}
'''

class OnlineRuntime(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.name!='nt' or not (title.SDK/'bin/gcc.exe').is_file():raise unittest.SkipTest('Windows local native toolchain unavailable')
        cls.tmp=tempfile.TemporaryDirectory();work=Path(cls.tmp.name)
        source=work/'fixture.c';source.write_text(FIXTURE);dll=work/'online-fixture.dll'
        command=[str(title.SDK/'bin/gcc.exe'),'-O2','-Wall','-Wextra','-shared',
            '-I'+str(ROOT/'tools'),'-I'+str(title.FRAMEWORK/'src/core'),str(source),
            str(ROOT/'tools/online_runtime.c'),str(title.FRAMEWORK/'src/core/nk_json.c'),'-lws2_32','-lcrypt32','-o',str(dll)]
        build=subprocess.run(command,env=title.environment(),capture_output=True,text=True)
        if build.returncode:cls.tmp.cleanup();raise RuntimeError(build.stderr)
        cls.lib=ctypes.CDLL(str(dll));cls.dll_path=dll
        cls.lib.fixture_poll.argtypes=[ctypes.POINTER(ctypes.c_uint)]
        cls.lib.fixture_info.argtypes=[ctypes.c_int,ctypes.POINTER(ctypes.c_uint)]
        cls.lib.fixture_cycle.argtypes=[ctypes.c_int,ctypes.POINTER(ctypes.c_uint)]
        cls.agent=Agent(dict(mac='02:00:00:00:00:01',nickname='Synthetic'))
        cls.agent.room=dict(code='12345',slot=0,bssid='020102030405');cls.agent.logged=True;cls.agent.state='in-room'
        cls.agent.pdp[0]=dict(port=31000,queue=deque())
        cls.calls=[];cls.delay=0;cls.broken=False;cls.bad_stat=False
        class Handler(socketserver.StreamRequestHandler):
            def handle(self):
                for raw in self.rfile:
                    request=json.loads(raw);token=request.pop('token',None)
                    if token!='synthetic-token':return
                    cls.calls.append(request['op'])
                    if cls.broken:return
                    if cls.delay:time.sleep(cls.delay)
                    reply=cls.agent.request(request)
                    if cls.bad_stat and request['op']=='pdp_stat':reply=dict(result=0,port=31000)
                    self.wfile.write(json.dumps(reply).encode()+b'\n');self.wfile.flush()
        class Server(socketserver.ThreadingTCPServer):
            allow_reuse_address=True;daemon_threads=True
        cls.server=Server(('127.0.0.1',0),Handler)
        cls.thread=threading.Thread(target=lambda:cls.server.serve_forever(poll_interval=.01),daemon=True);cls.thread.start()
        cls.old_env={k:os.environ.get(k) for k in ('LOA_ONLINE_PORT','LOA_ONLINE_TOKEN')}
        os.environ.update(LOA_ONLINE_PORT=str(cls.server.server_address[1]),LOA_ONLINE_TOKEN='synthetic-token')
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join();cls.agent.close()
        for k,v in cls.old_env.items():
            if v is None:os.environ.pop(k,None)
            else:os.environ[k]=v
        handle=cls.lib._handle;del cls.lib
        ctypes.windll.kernel32.FreeLibrary(ctypes.c_void_p(handle));cls.tmp.cleanup()
    def setUp(self):
        self.calls.clear();self.agent.events.clear();self.agent.state='in-room'
        self.agent.pdp[0]['queue'].clear();type(self).broken=False;type(self).bad_stat=False;type(self).delay=0
    def test_native_combined_poll_returns_real_events_and_state_once(self):
        self.agent.events.append(dict(kind=3,peer_id=42));fields=(ctypes.c_uint*3)()
        self.assertEqual(self.lib.fixture_poll(fields),1);self.assertEqual(list(fields),[1,3,42]);self.assertEqual(self.calls,['poll'])
        self.agent.state='offline';self.assertEqual(self.lib.fixture_poll(fields),0)
    def test_native_socket_snapshot_preserves_sizes_and_errors(self):
        self.agent.pdp[0]['queue'].append(('020000000002',32000,b'packet'))
        fields=(ctypes.c_uint*2)();self.assertEqual(self.lib.fixture_info(0,fields),0)
        self.assertEqual(list(fields),[31000,6]);self.assertEqual(self.calls,['pdp_stat'])
        self.assertEqual(len(self.agent.pdp[0]['queue']),1)
        self.assertEqual(self.lib.fixture_info(99,fields),-7)
        type(self).bad_stat=True;self.assertEqual(self.lib.fixture_info(0,fields),-2)
    def test_broken_ipc_cannot_report_a_live_connection_and_can_reconnect(self):
        fields=(ctypes.c_uint*3)();type(self).broken=True
        self.assertEqual(self.lib.fixture_poll(fields),0);self.assertEqual(fields[0],0)
        type(self).broken=False;self.assertEqual(self.lib.fixture_poll(fields),1)
    def test_busy_cycle_halves_round_trips_without_discarding_events_or_packets(self):
        fields=(ctypes.c_uint*3)();type(self).delay=.001
        for combined,expected in ((0,['events','status','pdp_stat','pdp_stat']),(1,['poll','pdp_stat'])):
            self.calls.clear();self.agent.events.append(dict(kind=3,peer_id=42))
            self.agent.pdp[0]['queue'].clear();self.agent.pdp[0]['queue'].append(('020000000002',32000,b'packet'))
            for i in range(60):
                self.assertEqual(self.lib.fixture_cycle(combined,fields),1)
                self.assertEqual(list(fields),[1 if i==0 else 0,31000,6])
            self.assertEqual(self.calls,expected*60);self.assertEqual(len(self.agent.pdp[0]['queue']),1)

if __name__=='__main__':unittest.main()
