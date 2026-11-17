import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from room_service import Rooms,RoomError
class RoomTests(unittest.TestCase):
    def setUp(self):self.now=0;self.rooms=Rooms(clock=lambda:self.now,code_factory=lambda:'00123')
    def ident(self,i):return dict(mac=f'02:00:00:00:00:{i:02x}',nickname=f'Player{i}',build='loa-native-v1-NPJH50503')
    def create(self):return self.rooms.request('create',self.ident(1))
    def join(self,i=2):return self.rooms.request('join',dict(self.ident(i),code='00123'))
    def test_code_leading_zeroes_and_peer_tokens(self):
        host=self.create();join=self.join();self.assertEqual(host['code'],'00123');self.assertEqual(join['slot'],1)
        self.assertNotEqual(host['token'],join['token']);self.assertEqual(join['peers'][0]['id'],host['session'])
        self.assertNotIn('token',join['peers'][0])
    def test_signalling_routes_only_to_same_room(self):
        host=self.create();join=self.join()
        self.rooms.request('exchange',dict(session=host['session'],signals=[dict(to=join['session'],kind='offer',sdp='synthetic SDP')]),token=host['token'])
        events=self.rooms.request('exchange',dict(session=join['session']),token=join['token'])['events']
        self.assertEqual(events[0]['from'],host['session']);self.assertEqual(events[0]['sdp'],'synthetic SDP')
        with self.assertRaises(RoomError):self.rooms.request('exchange',dict(session=join['session']),token=host['token'])
    def test_no_file_or_gameplay_upload_operation(self):
        host=self.create();join=self.join()
        with self.assertRaises(RoomError):self.rooms.request('exchange',dict(session=host['session'],signals=[dict(to=join['session'],kind='file',data='game')]),token=host['token'])
    def test_capacity_duplicate_and_code_collision(self):
        self.create();self.join(2);self.join(3);self.join(4)
        with self.assertRaises(RoomError):self.join(5)
        with self.assertRaises(RoomError):self.join(2)
        with self.assertRaises(RoomError):self.rooms.request('create',self.ident(6))
    def test_expiry_and_host_leave(self):
        host=self.create();join=self.join();self.rooms.request('leave',dict(session=host['session']),token=host['token'])
        self.assertEqual(self.rooms.request('exchange',dict(session=join['session']),token=join['token'])['events'],[dict(kind='closed')])
        self.assertFalse(self.rooms.sessions);self.assertFalse(self.rooms.rooms)
        self.create();self.now=61
        with self.assertRaises(RoomError):self.join()
    def test_guess_rate_limit_and_bad_code(self):
        for _ in range(12):
            with self.assertRaises(RoomError):self.rooms.request('join',dict(self.ident(1),code='99999'))
        with self.assertRaises(RoomError) as result:self.rooms.request('create',self.ident(1))
        self.assertEqual(result.exception.status,429)
    def test_turn_credentials_not_host_secret(self):
        rooms=Rooms(turn_secret='synthetic-secret',turn_url='turn:relay.invalid:3478')
        value=rooms.request('create',self.ident(1));ice=value['ice'][0]
        self.assertIn(value['session'],ice['username']);self.assertNotEqual(ice['password'],'synthetic-secret')
if __name__=='__main__':unittest.main()
