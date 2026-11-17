"""Offline adapter-contract tests. These do not simulate successful Steam sessions."""
import ctypes,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from steam_agent import SteamAgent,SteamPeer,MAGIC
from steam_native import Status,Member,Room
import online_config
class Native:
    def __init__(self):self.lib=self;self.connected=False;self.sent=[]
    def loa_steam_connected(self,peer):return int(self.connected)
    def loa_steam_close_peer(self,peer):pass
    def send(self,peer,data,unreliable=False):self.sent.append((peer,data,unreliable));return 0
class SteamContract(unittest.TestCase):
    def peer(self):
        native=Native();peer=SteamPeer(native,dict(id='123',slot=1,mac='02:00:00:00:00:02'),'02:00:00:00:00:01');return native,peer
    def test_membership_or_successful_send_is_not_connection_confirmation(self):
        native,peer=self.peer();native.connected=True;peer.handshake();self.assertTrue(native.sent);self.assertFalse(peer.ready())
        peer.receive(0,MAGIC+b'H'+bytes.fromhex('020000000002'));self.assertFalse(peer.ready())
        peer.receive(0,MAGIC+b'h'+bytes.fromhex('020000000002'));self.assertTrue(peer.ready())
        native.connected=False;self.assertFalse(peer.ready());self.assertEqual(peer.send(b'game'),-1)
    def test_reject_wrong_project_identity_and_channel(self):
        native,peer=self.peer()
        for channel,value in [(0,b'other app'),(1,MAGIC+b'H'+bytes.fromhex('020000000002')),(0,MAGIC+b'H'+bytes.fromhex('020000000003'))]:
            with self.assertRaises(ValueError):peer.receive(channel,value)
    def test_unavailable_sdk_returns_real_failure(self):
        def missing(mac):raise RuntimeError('Synthetic missing SDK fixture')
        agent=SteamAgent(dict(mac='02:00:00:00:00:01',nickname='Test'),factory=missing)
        try:
            status=agent.request(dict(op='status'));self.assertFalse(status['service_configured']);self.assertFalse(status['lobby'])
            self.assertEqual(agent.request(dict(op='create'))['result'],-3);self.assertEqual(agent.request(dict(op='pdp_open',port=31000))['result'],-3)
        finally:agent.close()
    def test_bridge_struct_layout_is_windows_x64_contract(self):
        self.assertEqual(ctypes.sizeof(Status),424);self.assertEqual(ctypes.sizeof(Member),160);self.assertEqual(ctypes.sizeof(Room),152)
    def test_provider_selection_roundtrip_and_legacy_config(self):
        folder=ROOT/'private/test-online-config';folder.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=folder) as temp:
            path=Path(temp)/'online.json';self.assertEqual(online_config.load(path),dict(backend='rooms',url=''))
            online_config.save(dict(backend='steam'),path);self.assertEqual(online_config.load(path),dict(backend='steam',url=''))
            path.write_text(json.dumps(dict(url='http://127.0.0.1:8741')));self.assertEqual(online_config.load(path)['backend'],'rooms')
            with self.assertRaises(ValueError):online_config.save(dict(backend='steam',token='must-not-persist'),path)
if __name__=='__main__':unittest.main()
