import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import shutil
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
spec=importlib.util.spec_from_file_location('mip_builder',ROOT/'tools/build-mip-texture-pack.py')
builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)


class MeasuredMipCapture(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.capture=self.root/'private/run';self.capture.mkdir(parents=True)
        self.scope=patch.object(builder,'ROOT',self.root);self.scope.start();self.addCleanup(self.scope.stop)

    def chain(self,address='08000000',content='0000000000000001',wrap=0,shade=100):
        key=address+'0000000000000001';rows=[]
        for level,side in enumerate((32,16)):
            name=f'mip-{key}-{content}-{wrap:03x}-{level}.rgba'
            (self.capture/name).write_bytes(bytes([shade,20,40,255])*side*side)
            rows.append(dict(key=key,content=content,wrap=wrap,level=level,levels=2,width=side,height=side,file=name,written=True))
        return rows

    def write(self,rows):
        (self.capture/'mip-capture.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in rows))

    def test_canonical_identity_does_not_depend_on_capture_address(self):
        self.write(self.chain()+self.chain(address='09000000'))
        chains,ambiguous=builder.captured_chains(self.capture)
        self.assertEqual(len(chains),1);self.assertEqual(ambiguous,[])
        self.assertTrue(chains[0][0].startswith('00000000'))

    def test_different_content_or_wrap_for_one_identity_is_excluded(self):
        self.write(self.chain()+self.chain(address='09000000',shade=150))
        chains,ambiguous=builder.captured_chains(self.capture)
        self.assertEqual(chains,[]);self.assertEqual(len(ambiguous),1)
        self.write(self.chain()+self.chain(address='09000000',wrap=257))
        self.assertEqual(builder.captured_chains(self.capture)[0],[])

    def test_missing_mips_and_unsafe_capture_paths_are_refused(self):
        rows=self.chain();self.write(rows[:1])
        with self.assertRaisesRegex(ValueError,'missing mip'):builder.captured_chains(self.capture)
        rows[0]['file']='../../outside.rgba';self.write(rows)
        with self.assertRaisesRegex(ValueError,'filename'):builder.captured_chains(self.capture)

    def test_merge_deduplicates_identical_runs_and_rejects_conflicting_content(self):
        self.write(self.chain())
        other=self.root/'private/second';shutil.copytree(self.capture,other)
        self.assertEqual(len(builder.merged_chains([self.capture,other])[0]),1)
        row=json.loads((other/'mip-capture.jsonl').read_text().splitlines()[1])
        (other/row['file']).write_bytes(bytes([120,20,40,255])*16*16)
        chains,excluded=builder.merged_chains([self.capture,other])
        self.assertEqual(chains,[]);self.assertEqual(len(excluded),1)

    def test_equal_pixel_bytes_with_conflicting_geometry_are_not_aliased(self):
        rows=self.chain()+self.chain(address='09000000')
        rows[2].update(width=16,height=64)
        rows[3].update(width=8,height=32)
        self.write(rows)
        self.assertEqual(builder.captured_chains(self.capture)[0],[])
