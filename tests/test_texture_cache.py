import hashlib,json,os,struct,sys,tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import texture_cache
from texture_pack import verify_sample

@unittest.skipUnless(os.name=='nt','Windows file identity cache')
class TextureCache(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve();self.pack=self.root/'pack';self.pack.mkdir()
        self.cache=self.root/'cache.json';self.png=self.pack/'tex-000-0.png'
        data=b'\x89PNG\r\n\x1a\n'+b'\0\0\0\rIHDR'+struct.pack('>II',64,64)
        self.png.write_bytes(data);key='000000000000000000000001'
        ini=f'[options]\nhash = quick\n[games]\nNPJH50503 = textures.ini\n[hashes]\n{key}_0 = tex-000-0.png\n'
        (self.pack/'textures.ini').write_text(ini)
        self.report=dict(scope='verified-mip-texture-pack',ini_sha256=hashlib.sha256((self.pack/'textures.ini').read_bytes()).hexdigest(),
            textures=[dict(key=key,source_width=16,source_height=16,factor=4,
                levels=[dict(file=self.png.name,width=64,height=64,sha256=hashlib.sha256(data).hexdigest())])])
        self.manifest=self.pack/'sample.json';self.manifest.write_text(json.dumps(self.report))

    def verify(self):return verify_sample(self.pack,self.root,cache_path=self.cache)

    def test_unchanged_png_is_not_reopened_on_warm_verification(self):
        self.assertEqual(self.verify()['verification_cache']['pngs_hashed'],1)
        original=Path.read_bytes
        def read(path):
            if path.suffix=='.png':raise AssertionError('Warm cache reread unchanged PNG')
            return original(path)
        with patch.object(Path,'read_bytes',read):result=self.verify()
        self.assertEqual(result['verification_cache']['unchanged_pngs_reused'],1)

    def test_same_size_edit_with_restored_mtime_is_rehashed_and_refused(self):
        self.verify();before=self.png.stat();data=bytearray(self.png.read_bytes());data[-1]^=1
        self.png.write_bytes(data);os.utime(self.png,ns=(before.st_atime_ns,before.st_mtime_ns))
        with self.assertRaisesRegex(ValueError,'hash mismatch'):self.verify()

    def test_missing_file_and_changed_manifest_hash_cannot_hit_cache(self):
        self.verify();self.report['textures'][0]['levels'][0]['sha256']='0'*64
        self.manifest.write_text(json.dumps(self.report))
        with self.assertRaisesRegex(ValueError,'hash mismatch'):self.verify()
        self.png.unlink()
        with self.assertRaisesRegex(ValueError,'missing'):self.verify()

    def test_ini_semantics_are_checked_even_when_every_png_is_cached(self):
        self.verify();ini=self.pack/'textures.ini'
        ini.write_text(ini.read_text().replace('hash = quick','hash = other'))
        self.report['ini_sha256']=hashlib.sha256(ini.read_bytes()).hexdigest()
        self.manifest.write_text(json.dumps(self.report))
        with self.assertRaisesRegex(ValueError,'INI'):self.verify()

    def test_corrupt_cache_or_unsupported_query_falls_back_to_hashing(self):
        self.verify();self.cache.write_text('{broken')
        self.assertEqual(self.verify()['verification_cache']['pngs_hashed'],1)
        with patch.object(texture_cache,'directory_snapshot',side_effect=OSError('unsupported')):
            result=self.verify()['verification_cache']
        self.assertFalse(result['metadata_supported']);self.assertEqual(result['pngs_hashed'],1)

    def test_reparse_point_and_change_during_validation_are_refused(self):
        self.verify();before=texture_cache.directory_snapshot(self.pack)
        linked={name:list(value) for name,value in before.items()};linked[self.png.name][-1]|=0x400
        with patch.object(texture_cache,'directory_snapshot',return_value=linked):
            with self.assertRaisesRegex(ValueError,'reparse'):self.verify()
        changed={name:list(value) for name,value in before.items()};changed[self.png.name][2]+=1
        changed_again={name:list(value) for name,value in changed.items()};changed_again[self.png.name][2]+=1
        with patch.object(texture_cache,'directory_snapshot',side_effect=[before,changed,changed,changed_again]):
            with self.assertRaisesRegex(ValueError,'changed during'):self.verify()

    def test_one_metadata_race_retries_with_full_hashing_then_reuses_cache(self):
        self.verify();before=texture_cache.directory_snapshot(self.pack)
        changed={name:list(value) for name,value in before.items()};changed[self.png.name][2]+=1
        with patch.object(texture_cache,'directory_snapshot',side_effect=[before,changed,changed,changed]):
            stats=self.verify()['verification_cache']
        self.assertEqual(stats['validation_retries'],1)
        self.assertEqual(stats['pngs_hashed'],1)
        self.assertEqual(stats['unchanged_pngs_reused'],0)

    def test_retry_does_not_accept_corruption_after_a_cached_first_pass(self):
        self.verify();before=texture_cache.directory_snapshot(self.pack)
        changed={name:list(value) for name,value in before.items()};changed[self.png.name][2]+=1
        calls=0
        def snapshot(folder):
            nonlocal calls
            calls+=1
            if calls==1:return before
            if calls==2:
                data=bytearray(self.png.read_bytes());data[-1]^=1;self.png.write_bytes(data)
            return changed
        with patch.object(texture_cache,'directory_snapshot',side_effect=snapshot):
            with self.assertRaisesRegex(ValueError,'hash mismatch'):self.verify()

    def test_cache_write_failure_does_not_hide_validation_failure(self):
        with patch.object(texture_cache.os,'replace',side_effect=PermissionError('busy')):
            result=self.verify()['verification_cache']
        self.assertEqual(result['pngs_hashed'],1);self.assertIn('busy',result['warning'])
        self.assertFalse(self.cache.exists())
