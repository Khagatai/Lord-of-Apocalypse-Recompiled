import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import graphics_settings
import texture_pack


class TextureSample(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root=Path(self.temporary.name)
        self.pack=self.root/'sample'
        self.pack.mkdir()
        # Only header metadata is used here; the real native reader validates full PNG data.
        data=b'\x89PNG\r\n\x1a\n'+b'\0\0\0\rIHDR'+struct.pack('>II',256,512)
        (self.pack/'ui-sample.png').write_bytes(data)
        (self.pack/'textures.ini').write_text('[options]\nhash=quick\n')
        self.report={'scope':'one-region-vector-typeset-ui-sample','factor':4,'width':256,'height':512,
                     'png_sha256':hashlib.sha256(data).hexdigest(),
                     'ini_sha256':hashlib.sha256((self.pack/'textures.ini').read_bytes()).hexdigest()}
        self.manifest=self.pack/'sample.json'
        self.manifest.write_text(json.dumps(self.report),encoding='utf-8-sig')

    def test_verified_private_sample_and_tampered_image(self):
        result=texture_pack.verify_sample(self.pack,self.root)
        self.assertFalse(result['complete_hd_pack'])
        with (self.pack/'ui-sample.png').open('ab') as stream:
            stream.write(b'changed')
        with self.assertRaisesRegex(ValueError,'hash mismatch'):
            texture_pack.verify_sample(self.pack,self.root)

    def test_refuses_wrong_dimensions_and_untrusted_root(self):
        with self.assertRaisesRegex(ValueError,'under private'):
            texture_pack.verify_sample(self.pack,self.root/'elsewhere')
        self.report['width']=999
        self.manifest.write_text(json.dumps(self.report))
        with self.assertRaisesRegex(ValueError,'dimensions'):
            texture_pack.verify_sample(self.pack,self.root)

    def test_feature_opt_in_preserves_audio_and_existing_enhancements(self):
        env=graphics_settings.environment(graphics_settings.DEFAULTS)
        texture_pack.enable(env,self.pack)
        self.assertIn('texpack=on',env['SR_ACE'])
        self.assertIn('sas=off',env['SR_ACE'])
        self.assertIn('smooth=off',env['SR_ACE'])
        advanced=graphics_settings.environment(dict(graphics_settings.DEFAULTS,anisotropy=16,supersampling=2))
        texture_pack.enable(advanced,self.pack)
        self.assertIn('af=16',advanced['SR_ACE'])
        self.assertIn('ssaa=2',advanced['SR_ACE'])

    def test_multi_region_sample_and_invalid_region_count(self):
        self.report.update(scope='multi-region-vector-typeset-ui-sample',region_count=7)
        self.manifest.write_text(json.dumps(self.report))
        self.assertEqual(texture_pack.verify_sample(self.pack,self.root)['scope'],self.report['scope'])
        self.report['region_count']=0
        self.manifest.write_text(json.dumps(self.report))
        with self.assertRaisesRegex(ValueError,'region count'):
            texture_pack.verify_sample(self.pack,self.root)


if __name__=='__main__':
    unittest.main()
