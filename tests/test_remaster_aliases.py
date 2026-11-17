import importlib.util
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
s=importlib.util.spec_from_file_location('aliases',ROOT/'tools/extend-remaster-aliases.py')
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)


class AliasTests(unittest.TestCase):
    def row(self,name='STONE',digest='a'):
        return dict(name=name,resource_id='1',source_sha256='b',texture_index=0,mip_levels=1,
                    candidate_keys=['000000001234567812345678'],authored_levels=[dict(width=32,height=32,rgba_sha256=digest)])

    def donor(self):
        return dict(key='000000008765432112345678',source_width=32,source_height=32,factor=4,wrap=0,
                    source_rgba_sha256=['a'],levels=[dict(file='tex-001-0.png',width=128,height=128,sha256='c')])

    def test_exact_alias_reuses_files_without_touching_donor(self):
        donor=self.donor();groups=[donor]
        added,refused=m.aliases([self.row()],groups)
        self.assertEqual(len(added),1);self.assertEqual(added[0]['levels'],donor['levels'])
        self.assertEqual(added[0]['alias_of'],donor['key']);self.assertNotIn('alias_of',donor)
        self.assertEqual(refused,[])

    def test_pixels_sampler_factor_and_portraits_cannot_be_substituted(self):
        donor=self.donor()
        self.assertEqual(m.aliases([self.row(digest='z')],[donor])[0],[])
        self.assertEqual(m.aliases([self.row(name='NAMED001')],[donor])[0],[])
        donor['factor']=2
        self.assertEqual(m.aliases([self.row()],[donor])[0],[])
        donor=self.donor();added,_=m.aliases([self.row()],[donor])
        self.assertEqual([a['wrap'] for a in added],[0])

    def test_conflicting_donors_are_refused(self):
        a=self.donor();b=self.donor();b['levels']=[dict(file='tex-002-0.png',width=128,height=128,sha256='d')]
        added,refused=m.aliases([self.row()],[a,b])
        self.assertEqual(added,[]);self.assertEqual(len(refused),1)
