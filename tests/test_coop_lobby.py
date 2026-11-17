import socket,sys,threading,time,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from coop_lobby import Lobby

class CoopLobby(unittest.TestCase):
    def setUp(self):
        self.lobby=Lobby(port=0);self.stop=threading.Event();self.clients=[]
        def serve():
            while not self.stop.is_set():self.lobby.step(.005)
        self.thread=threading.Thread(target=serve);self.thread.start()
    def tearDown(self):
        for client in self.clients:client.close()
        self.stop.set();self.thread.join(timeout=2);self.lobby.close()
    def client(self,index,product=b'NPJH50503',mac=None):
        client=socket.socket();client.settimeout(2);client.bind(('127.0.0.'+str(index+1),0));client.connect(self.lobby.address);self.clients.append(client)
        address=mac or bytes([2,0,0,0,0,index]);packet=b'\x01'+address+('Player '+str(index)).encode().ljust(128,b'\0')+product
        client.sendall(packet);return client,address
    def read(self,client,size):
        result=b''
        while len(result)<size:
            block=client.recv(size-len(result))
            if not block:raise EOFError('Lobby closed')
            result+=block
        return result
    def test_join_events_and_leave_notify_real_peers(self):
        first,ma=self.client(1);first.sendall(b'\x02ROOM0001');bssid=self.read(first,7);self.assertEqual(bssid[0],6)
        second,mb=self.client(2);second.sendall(b'\x02ROOM0001')
        to_first=self.read(first,139);to_second=self.read(second,139);second_bssid=self.read(second,7)
        self.assertEqual(to_first[129:135],mb);self.assertEqual(to_second[129:135],ma);self.assertEqual(second_bssid,bssid)
        second.sendall(b'\x03');left=self.read(first,5);self.assertEqual(left,b'\x03'+socket.inet_aton('127.0.0.3'))
    def test_scan_is_product_isolated(self):
        first,_=self.client(1);first.sendall(b'\x02ROOM0001');self.read(first,7)
        second,_=self.client(2,b'ULUS12345');second.sendall(b'\x04');self.assertEqual(self.read(second,1),b'\x05')
        third,_=self.client(3);third.sendall(b'\x04');self.assertEqual(self.read(third,16)[0:9],b'\x04ROOM0001')
    def test_duplicate_identity_closes_connection(self):
        first,mac=self.client(1);first.sendall(b'\x02ROOM0001');self.read(first,7)
        second,_=self.client(2,mac=mac);self.assertEqual(second.recv(1),b'')
    def test_invalid_or_oversized_login_fails_closed(self):
        client,_=self.client(1,product=b'bad title');self.assertEqual(client.recv(1),b'')
    def test_cannot_scan_while_in_group(self):
        client,_=self.client(1);client.sendall(b'\x02ROOM0001');self.read(client,7);client.sendall(b'\x04');self.assertEqual(client.recv(1),b'')
    def test_partial_packets_are_retained(self):
        client=socket.socket();client.settimeout(2);client.bind(('127.0.0.2',0));client.connect(self.lobby.address);self.clients.append(client)
        packet=b'\x01'+bytes([2,0,0,0,0,1])+b'Partial'.ljust(128,b'\0')+b'NPJH50503'
        client.sendall(packet[:20]);time.sleep(.02);client.sendall(packet[20:]+b'\x02ROOM0001');self.assertEqual(self.read(client,7)[0],6)

if __name__=='__main__':unittest.main()
