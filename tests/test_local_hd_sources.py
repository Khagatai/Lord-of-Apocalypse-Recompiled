import hashlib
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
spec=importlib.util.spec_from_file_location('local_hd_audit',ROOT/'tools/audit-local-hd-sources.py')
audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)


class LocalHdSourceProof(unittest.TestCase):
    def fixture(self):
        raw=b'synthetic archive resource';pixels=bytes([1,2,3,255])*4
        ref=dict(source_sha256=hashlib.sha256(raw).hexdigest(),texture_index=0,name='PB00_00')
        texture=SimpleNamespace(textures=[SimpleNamespace(name='PB00_00',mips=[object()])],
            preview_mip=lambda index,level,limit:(2,2,pixels))
        return raw,pixels,ref,texture

    def test_wrong_archive_hash_is_rejected_before_decode(self):
        raw,pixels,ref,texture=self.fixture()
        with patch.object(audit.Xet,'parse') as decode:
            with self.assertRaisesRegex(ValueError,'resource identity'):
                audit.verify_reference(raw+b'changed',ref,[hashlib.sha256(pixels).hexdigest()])
            decode.assert_not_called()

    def test_name_match_does_not_admit_different_mip_pixels(self):
        raw,pixels,ref,texture=self.fixture()
        with patch.object(audit.Xet,'parse',return_value=texture):
            with self.assertRaisesRegex(ValueError,'mip pixels differ'):
                audit.verify_reference(raw,ref,['0'*64])

    def test_negative_texture_index_is_rejected(self):
        raw,pixels,ref,texture=self.fixture();ref['texture_index']=-1
        with patch.object(audit.Xet,'parse',return_value=texture):
            with self.assertRaisesRegex(ValueError,'index differs'):
                audit.verify_reference(raw,ref,[hashlib.sha256(pixels).hexdigest()])

    def test_valid_source_proof_returns_measured_dimensions(self):
        raw,pixels,ref,texture=self.fixture()
        with patch.object(audit.Xet,'parse',return_value=texture):
            self.assertEqual(audit.verify_reference(raw,ref,[hashlib.sha256(pixels).hexdigest()]),[[2,2]])


if __name__=='__main__':unittest.main()
