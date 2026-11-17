import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import movie_captions
spec=importlib.util.spec_from_file_location('caption_audit',ROOT/'tools/audit-caption-rebuild.py')
audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)


class CaptionRebuildAudit(unittest.TestCase):
    def fixture(self,root):
        pixels=bytes([64,64,64,255])
        header=b'PSMF'+bytes(140)
        reference=movie_captions.build([header],[(0,1,3,16,224,1,1,pixels)])
        recipe=dict(schema=1,expected_bundle_sha256=hashlib.sha256(reference).hexdigest(),movies=[dict(
            movie='MOVIE01.PMF',credit_pages=False,cues=[dict(id=1,first_frame=1,end_frame=3,x=16,y=224,
            width=1,height=1,english_lines=['Test'],expected_pixels_sha256=hashlib.sha256(pixels).hexdigest())])])
        folder=root/'MOVIE01/rendered';folder.mkdir(parents=True)
        path=folder/'cue-0001.rgba';path.write_bytes(pixels+bytes(448*48*4-4))
        return recipe,reference,path

    def test_exact_render_is_diagnostic_and_not_approved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);recipe,ref,path=self.fixture(root)
            result=audit.audit(recipe,ref,root)
            self.assertEqual(result['exact_matches'],1)
            self.assertEqual(result['status'],'DIAGNOSTIC_ONLY')
            self.assertNotIn('approved_for_launch',result)

    def test_shading_change_is_reported_as_distinct_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);recipe,ref,path=self.fixture(root);before=json.dumps(recipe)
            raw=bytearray(path.read_bytes());raw[:3]=bytes([51,51,51]);path.write_bytes(raw)
            result=audit.audit(recipe,ref,root,True)
            self.assertEqual(result['maxima']['differing_pixels'],1)
            self.assertEqual(result['maxima']['maximum_RGB_delta'],13)
            self.assertEqual(result['maxima']['ink_mask_changes'],0)
            candidate=result['candidate_recipe']
            self.assertFalse(candidate['approved_for_launch'])
            self.assertNotEqual(candidate['expected_bundle_sha256'],recipe['expected_bundle_sha256'])
            self.assertEqual(json.dumps(recipe),before)

    def test_wrong_reference_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);recipe,ref,path=self.fixture(root)
            with self.assertRaisesRegex(ValueError,'Reference bundle identity'):
                audit.audit(recipe,ref+b'wrong',root)

    def test_truncated_render_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);recipe,ref,path=self.fixture(root);path.write_bytes(b'')
            with self.assertRaisesRegex(ValueError,'extent'):
                audit.audit(recipe,ref,root)


if __name__=='__main__':unittest.main()
