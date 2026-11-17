import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from ui_pack import merge
from texture_pack import verify_sample


class MergedUiPack(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root=Path(self.temporary.name)
        self.a=self.sample('a','000000000000000000000001')
        self.b=self.sample('b','000000000000000000000002')

    def sample(self,name,key):
        folder=self.root/name
        folder.mkdir()
        # Header-only fixture: native PNG decode is tested separately on real local samples.
        data=b'\x89PNG\r\n\x1a\n'+b'\0\0\0\rIHDR'+struct.pack('>II',256,512)
        (folder/'ui-sample.png').write_bytes(data)
        ini=('[options]\nhash = quick\n[hashes]\n'+key+' = ui-sample.png\n').encode()
        (folder/'textures.ini').write_bytes(ini)
        report={'scope':'one-region-vector-typeset-ui-sample','factor':4,'width':256,'height':512,
                'png_sha256':hashlib.sha256(data).hexdigest(),'ini_sha256':hashlib.sha256(ini).hexdigest()}
        (folder/'sample.json').write_text(json.dumps(report))
        return folder

    def test_merges_verified_atlases_and_detects_modified_image(self):
        output=self.root/'merged'
        result=merge([self.a,self.b],output,self.root)
        checked=verify_sample(output,self.root)
        self.assertEqual(len(checked['textures']),2)
        self.assertEqual(result['textures'][0]['file'],'ui-000.png')
        (output/'ui-001.png').write_bytes(b'modified')
        with self.assertRaisesRegex(ValueError,'hash mismatch'):
            verify_sample(output,self.root)

    def test_rejects_duplicate_texture_identity_before_creating_pack(self):
        duplicate=self.sample('duplicate','000000000000000000000001')
        output=self.root/'duplicate-output'
        with self.assertRaisesRegex(ValueError,'duplicate texture identity'):
            merge([self.a,duplicate],output,self.root)
        self.assertFalse(output.exists())

    def test_rejects_ini_changes_and_unsafe_image_names(self):
        output=self.root/'merged'
        merge([self.a,self.b],output,self.root)
        original=(output/'textures.ini').read_bytes()
        (output/'textures.ini').write_bytes(b'[options]\nhash=xxh32\n')
        with self.assertRaisesRegex(ValueError,'INI missing or hash mismatch'):
            verify_sample(output,self.root)
        (output/'textures.ini').write_bytes(original)
        report=json.loads((output/'sample.json').read_text())
        report['textures'][0]['file']='../outside.png'
        (output/'sample.json').write_text(json.dumps(report))
        with self.assertRaisesRegex(ValueError,'filename'):
            verify_sample(output,self.root)

    def test_output_stays_private_and_does_not_overwrite(self):
        output=self.root/'merged'
        merge([self.a],output,self.root)
        with self.assertRaisesRegex(ValueError,'fresh private'):
            merge([self.b],output,self.root)
        with self.assertRaisesRegex(ValueError,'fresh private'):
            merge([self.a],self.root.parent/'outside-pack',self.root)

    def test_complete_ascii_pack_exceeds_old_limit_but_remains_bounded(self):
        samples=[self.sample(f'page-{i}',f'{i+10:024x}') for i in range(52)]
        result=merge(samples,self.root/'ascii-pack',self.root)
        self.assertEqual(len(verify_sample(self.root/'ascii-pack',self.root)['textures']),52)
        self.assertEqual(len(result['textures']),52)
        with self.assertRaisesRegex(ValueError,'1 to 256'):
            merge([self.a]*257,self.root/'oversized',self.root)
        self.assertFalse((self.root/'oversized').exists())


if __name__=='__main__':
    unittest.main()
