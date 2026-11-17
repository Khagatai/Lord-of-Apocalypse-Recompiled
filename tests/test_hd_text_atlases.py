import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
spec=importlib.util.spec_from_file_location('hd_text',ROOT/'tools/build-hd-text-atlases.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class HDTextAtlasTests(unittest.TestCase):
    def test_mask_retains_every_outside_byte_and_refuses_out_of_bounds_rectangles(self):
        data=bytes(range(24))
        self.assertEqual(module.masked(data,3,2,[[1,0,1,1]]),data[:4]+bytes(4)+data[8:])
        for regions in ([[2,0,2,1]],[[-1,0,1,1]],[[0,0,0,1]]):
            with self.assertRaisesRegex(ValueError,'mask exceeds'):module.masked(data,3,2,regions)

    def fixture(self,root):
        folder=root/'set/ATLAS';folder.mkdir(parents=True);pixels=folder/'pixels.rgba'
        pixels.write_bytes(b'\xff'*16)
        plan=dict(source_png='private/source.png',blocks=[dict(x=0,y=0,width=2,height=2,paragraphs=['Existing words'])])
        path=folder.parent/'ATLAS.json';path.write_text(json.dumps(plan))
        (folder/'render.json').write_text(json.dumps(dict(width=2,height=2,spec_sha256=module.sha(path.read_bytes()))))
        row=dict(resource_id='00020000',source_sha256='b'*64,texture_index=0,width=2,height=2,authored_levels=[{}])
        report=dict(scope='verified-local-texture-text-regions',resources=[dict(resource_id='00020000',target_sha256='b'*64,
            edits=[dict(texture_index=0,rgba_path=str(pixels),rgba_sha256=module.sha(pixels.read_bytes()),regions=[[0,0,2,2]])])])
        return row,report,path

    def test_changed_english_specs_and_wrong_resource_versions_are_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);row,report,path=self.fixture(root)
            self.assertEqual(len(module.linked_plans([row],report,root)[0]),1)
            changed=dict(row,source_sha256='c'*64)
            with self.assertRaisesRegex(ValueError,'catalog does not match'):module.linked_plans([changed],report,root)
            path.write_text(path.read_text().replace('Existing words','Different words'))
            with self.assertRaisesRegex(ValueError,'spec or masks changed'):module.linked_plans([row],report,root)

    def test_missing_spec_leaves_original_fallback_without_inventing_text(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);row,report,path=self.fixture(root);path.unlink()
            chosen,excluded=module.linked_plans([row],report,root)
            self.assertEqual(chosen,[]);self.assertIn('retain existing',excluded[0]['reason'])

    def test_caption_layout_and_vector_atlas_keep_native_translated_pixels(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);row,report,path=self.fixture(root)
            report['resources'].append(dict(resource_id='000a0001',caption_layout=True))
            render=path.parent/'ATLAS/render.json'
            render.write_text(json.dumps(dict(scope='local-serif-caption-atlas')))
            chosen,excluded=module.linked_plans([row],report,root)
            self.assertEqual(chosen,[]);self.assertEqual(len(excluded),2)
            self.assertIn('native translated texture',excluded[0]['reason'])
            self.assertIn('no texture pixels',excluded[1]['reason'])


if __name__=='__main__':unittest.main()
