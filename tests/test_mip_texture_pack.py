import copy
import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from texture_pack import verify_sample


class VerifiedMipPack(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.pack=self.root/'pack';self.pack.mkdir()
        self.key='000000000000000000000001';levels=[]
        for l,side in enumerate((64,32)):
            name=f'tex-000-{l}.png'
            # Header fixture only; real complete PNG decode is exercised on Vulkan.
            data=b'\x89PNG\r\n\x1a\n'+b'\0\0\0\rIHDR'+struct.pack('>II',side,side)
            (self.pack/name).write_bytes(data)
            levels.append(dict(file=name,width=side,height=side,sha256=hashlib.sha256(data).hexdigest()))
        self.ini=f'[options]\nhash = quick\n[games]\nNPJH50503 = textures.ini\n[hashes]\n{self.key}_0 = tex-000-0.png\n{self.key}_1 = tex-000-1.png\n'
        (self.pack/'textures.ini').write_text(self.ini)
        self.report=dict(scope='verified-mip-texture-pack',textures=[dict(key=self.key,source_width=16,source_height=16,factor=4,levels=levels)],
                         ini_sha256=hashlib.sha256((self.pack/'textures.ini').read_bytes()).hexdigest())
        self.write()

    def write(self): (self.pack/'sample.json').write_text(json.dumps(self.report))

    def test_complete_chain_verifies_and_modified_lower_mip_fails(self):
        result=verify_sample(self.pack,self.root)
        self.assertEqual(result['mip_chains'],1);self.assertEqual(result['images'],2)
        (self.pack/'tex-000-1.png').write_bytes(b'modified')
        with self.assertRaisesRegex(ValueError,'hash mismatch'):verify_sample(self.pack,self.root)

    def test_false_dimensions_are_rejected_even_when_hash_and_manifest_agree(self):
        path=self.pack/'tex-000-1.png';data=path.read_bytes()[:16]+struct.pack('>II',33,32)
        path.write_bytes(data)
        self.report['textures'][0]['levels'][1].update(width=33,sha256=hashlib.sha256(data).hexdigest());self.write()
        with self.assertRaisesRegex(ValueError,'halving chain'):verify_sample(self.pack,self.root)

    def test_ini_cannot_silently_omit_a_verified_lower_mip(self):
        (self.pack/'textures.ini').write_text(self.ini.replace(f'{self.key}_1 = tex-000-1.png\n',''))
        self.report['ini_sha256']=hashlib.sha256((self.pack/'textures.ini').read_bytes()).hexdigest();self.write()
        with self.assertRaisesRegex(ValueError,'exactly match'):verify_sample(self.pack,self.root)

    def test_impossible_small_image_level_count_is_rejected(self):
        group=self.report['textures'][0]
        group.update(source_width=1,source_height=1,factor=2)
        group['levels'].append(copy.deepcopy(group['levels'][1]));self.write()
        with self.assertRaisesRegex(ValueError,'Vulkan image level count'):verify_sample(self.pack,self.root)

    def test_unsafe_names_and_duplicate_images_are_rejected(self):
        original=copy.deepcopy(self.report)
        self.report['textures'][0]['levels'][1]['file']='../outside.png';self.write()
        with self.assertRaisesRegex(ValueError,'filename'):verify_sample(self.pack,self.root)
        self.report=original
        self.report['textures'].append(copy.deepcopy(self.report['textures'][0]));self.write()
        with self.assertRaisesRegex(ValueError,'duplicate'):verify_sample(self.pack,self.root)

    def test_shared_images_require_identical_hashes_and_geometry(self):
        alias=copy.deepcopy(self.report['textures'][0]);alias['key']='000000000000000000000002'
        self.report['textures'].append(alias)
        ini=self.ini+''.join(f"{alias['key']}_{l} = {entry['file']}\n" for l,entry in enumerate(alias['levels']))
        (self.pack/'textures.ini').write_text(ini)
        self.report['ini_sha256']=hashlib.sha256((self.pack/'textures.ini').read_bytes()).hexdigest();self.write()
        result=verify_sample(self.pack,self.root)
        self.assertEqual(result['images'],2);self.assertEqual(result['mip_chains'],2)
        alias['levels'][1]['sha256']='0'*64;self.write()
        with self.assertRaisesRegex(ValueError,'Conflicting'):verify_sample(self.pack,self.root)
