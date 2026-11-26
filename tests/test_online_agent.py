import base64,json,struct,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from online_agent import Agent,service_url
class Peer:
    identity=dict(id='peer',slot=1,mac='02:00:00:00:00:02',nickname='Peer')
    group='LOATEST';failed=False
    def ready(self):return True
    def send(self,*args):return 0
    def close(self):pass
class AgentTests(unittest.TestCase):
    def setUp(self):self.agent=Agent(dict(mac='02:00:00:00:00:01',nickname='Player'))
    def tearDown(self):self.agent.close()
    def connected(self):
        self.agent.room=dict(code='12345',slot=0,bssid='020102030405');self.agent.logged=True;self.agent.group='LOATEST';self.agent.peers={'peer':Peer()}
    def test_public_service_requires_https_and_no_credentials_or_queries(self):
        self.assertEqual(service_url('http://127.0.0.1:1234'),'http://127.0.0.1:1234')
        self.assertEqual(service_url('https://rooms.example.test/'),'https://rooms.example.test')
        for url in ('http://rooms.example.test','https://user:password@rooms.example.test','https://rooms.example.test/?token=secret','https://rooms.example.test/elsewhere'):
            with self.assertRaises(ValueError):service_url(url)
    def test_unconfigured_create_never_generates_code(self):
        self.assertEqual(self.agent.request(dict(op='create'))['result'],-3);self.assertEqual(self.agent.status()['code'],'')
        self.assertEqual(self.agent.request(dict(op='pdp_open',port=31000))['result'],-3)
    def test_poll_reports_actual_lobby_state_and_preserves_login_failure(self):
        self.assertEqual(self.agent.request(dict(op='poll')),dict(result=-3,state='offline'))
        self.connected();self.agent.state='in-room';self.agent.logged=False
        self.assertEqual(self.agent.request(dict(op='poll')),dict(result=-3,state='in-room'))
    def test_poll_consumes_only_the_requested_events_without_changing_packets(self):
        self.connected();self.agent.state='in-room'
        for i in range(10):self.agent.emit(dict(kind=3,peer_id=i))
        first=self.agent.request(dict(op='poll',max=8));second=self.agent.request(dict(op='poll',max=8))
        self.assertEqual(first,dict(result=0,state='in-room',events=[dict(kind=3,peer_id=i) for i in range(8)]))
        self.assertEqual(second['events'],[dict(kind=3,peer_id=8),dict(kind=3,peer_id=9)])
        for bad in (-1,9,True,'8',None):self.assertEqual(self.agent.request(dict(op='poll',max=bad))['result'],-2)
    def test_datagram_short_buffer_retains_exact_sender_and_payload(self):
        self.connected();handle=self.agent.request(dict(op='pdp_open',port=31000))['result'];peer=self.agent.peers['peer']
        self.agent.packet(peer,b'P'+struct.pack('!HH',32000,31000)+b'payload')
        self.assertEqual(self.agent.request(dict(op='pdp_recv',handle=handle,capacity=1)),dict(result=-9,size=7))
        result=self.agent.request(dict(op='pdp_recv',handle=handle,capacity=10));self.assertEqual(result['port'],32000);self.assertEqual(base64.b64decode(result['data']),b'payload')
    def test_datagram_port_collision_bounded_queue_and_drop_count(self):
        self.connected();self.agent.request(dict(op='pdp_open',port=31000))
        self.assertEqual(self.agent.request(dict(op='pdp_open',port=31000))['result'],-5)
        for _ in range(33):self.agent.packet(self.agent.peers['peer'],b'P'+struct.pack('!HH',32000,31000)+b'data')
        self.assertEqual(len(self.agent.pdp[0]['queue']),32);self.assertEqual(self.agent.request(dict(op='drops'))['pdp'],1)
    def test_non_group_packet_dropped(self):
        self.connected();self.agent.request(dict(op='pdp_open',port=31000));peer=self.agent.peers['peer'];peer.group='OTHER'
        self.agent.packet(peer,b'P'+struct.pack('!HH',32000,31000)+b'data');self.assertFalse(self.agent.pdp[0]['queue'])
    def test_stream_connect_requires_real_accept_ack(self):
        self.connected();handle=self.agent.request(dict(op='ptp_open',port=32001,remote=32002,mac='020000000002',backlog=0))['result']
        self.assertEqual(self.agent.request(dict(op='ptp_connect',handle=handle))['result'],-1)
        s=self.agent.ptp[handle];self.agent.packet(self.agent.peers['peer'],b'A'+bytes.fromhex(s['nonce']))
        self.assertEqual(self.agent.request(dict(op='ptp_connect',handle=handle))['result'],0)
        with self.assertRaises(ValueError):self.agent.packet(self.agent.peers['peer'],b'W'+bytes.fromhex(s['nonce'])+struct.pack('!I',1))
if __name__=='__main__':unittest.main()
