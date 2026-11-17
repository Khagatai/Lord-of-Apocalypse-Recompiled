import importlib.util,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import network_settings as settings

class NetworkSettings(unittest.TestCase):
    def test_default_is_off_without_creating_files(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'private') as folder:
            path=Path(folder)/'network.json';value=settings.load(path)
            self.assertEqual(value['mode'],'off');self.assertFalse(path.exists())
            self.assertEqual(settings.environment(value,path)['LOA_NET_ENABLED'],'0')
    def test_identity_is_local_unicast_and_distinct(self):
        first,second=settings.defaults(),settings.defaults()
        self.assertNotEqual(first['mac'],second['mac']);self.assertEqual(int(first['mac'][:2],16)&3,2)
    def test_saved_host_and_join_profiles_roundtrip(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'private') as folder:
            path=Path(folder)/'network.json';value=dict(settings.defaults(),mode='join',host='203.0.113.12',nickname='Test player')
            settings.save(value,path);self.assertEqual(settings.load(path),value)
            env=settings.environment(value,path);self.assertEqual(env['LOA_NET_HOST'],value['host']);self.assertEqual(env['LOA_NET_ENABLED'],'1')
            value.update(mode='host',public_host='203.0.113.13');settings.save(value,path)
            self.assertEqual(settings.environment(settings.load(path),path)['LOA_NET_HOST'],'127.0.0.1')
    def test_rejects_unrecognized_or_unsafe_profile(self):
        value=settings.defaults()
        for key,invalid in [('host','example.com'),('bind','::1'),('mode','auto'),('port',True),('port',0),('offset',65536),('nickname','x\nfile'),('mac','ff:ff:ff:ff:ff:ff')]:
            with self.subTest(key=key,invalid=invalid),self.assertRaises(ValueError):settings.validate(dict(value,**{key:invalid}))
        with self.assertRaises(ValueError):settings.validate(dict(value,unknown=1))
    def test_profiles_cannot_escape_private_storage(self):
        with self.assertRaises(ValueError):settings.profile_path(ROOT/'network.json')

if __name__=='__main__':unittest.main()
