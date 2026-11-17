import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import art_capture


class ObservedArtTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.capture=self.root/'private/run';self.capture.mkdir(parents=True)
        self.catalog=self.root/'private/catalog';self.catalog.mkdir()
        self.scope=patch.object(art_capture,'ROOT',self.root);self.scope.start();self.addCleanup(self.scope.stop)
        self.key='080000000000000000000001';self.content='0000000000000001'
        self.file=f'art-{self.key}-{self.content}-000.rgba'
        pixels=bytes([10,20,30,255])*32*32;(self.capture/self.file).write_bytes(pixels)
        row=dict(key=self.key,content=self.content,wrap=0,level=0,levels=1,width=32,height=32,
                 through=False,decoded=True,written=True,file=self.file)
        (self.capture/'art-capture.jsonl').write_text(json.dumps(row)+'\n')
        entry=dict(mip_levels=1,width=32,height=32,resource_id='00020001',texture_index=0,name='BODY',
                   source_sha256='1'*64,candidate_keys=['00000000'+self.key[8:]],
                   authored_levels=[dict(rgba_sha256=hashlib.sha256(pixels).hexdigest())])
        (self.catalog/'catalog.json').write_text(json.dumps([entry]))

    def test_exact_archive_pixels_required_and_runtime_address_is_normalized(self):
        chosen,report=art_capture.observed_art(self.capture,self.catalog)
        self.assertEqual(len(chosen),1);self.assertTrue(chosen[0][0].startswith('00000000'))
        (self.capture/self.file).write_bytes(bytes([11,20,30,255])*32*32)
        chosen,report=art_capture.observed_art(self.capture,self.catalog)
        self.assertEqual(chosen,[]);self.assertEqual(len(report['unmatched']),1)

    def test_failed_capture_and_unsafe_filename_are_refused(self):
        path=self.capture/'art-capture.jsonl';row=json.loads(path.read_text());row['written']=False
        path.write_text(json.dumps(row))
        with self.assertRaisesRegex(ValueError,'failed'):art_capture.observed_art(self.capture,self.catalog)
        row['written']=True;row['file']='../outside.rgba';path.write_text(json.dumps(row))
        with self.assertRaisesRegex(ValueError,'filename'):art_capture.observed_art(self.capture,self.catalog)
