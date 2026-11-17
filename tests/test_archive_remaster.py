from pathlib import Path
import importlib.util
import re
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
spec=importlib.util.spec_from_file_location('archive_remaster',ROOT/'tools/build-archive-remaster.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class ArchiveRemasterTests(unittest.TestCase):
    def row(self,name='NAMED001',digest='a'*64,opaque=True,key='0000000012345678abcdef01'):
        return dict(name=name,mip_levels=1,candidate_keys=[key],authored_levels=[
            dict(width=128,height=128,rgba_sha256=digest,opaque=opaque)])

    def test_conflicting_key_outside_selected_family_is_refused(self):
        rows=[self.row(),self.row(name='OTHER',digest='b'*64)]
        selected,excluded=module.select(rows,re.compile('NAMED.*'),True)
        self.assertEqual(selected,[])
        self.assertEqual(excluded[0]['reason'],'ambiguous or wildcard identity')

    def test_exact_aliases_deduplicate_but_distinct_palette_keys_remain(self):
        rows=[self.row(),self.row(key='0000000087654321abcdef01'),self.row()]
        selected,excluded=module.select(rows,re.compile('NAMED.*'),True)
        self.assertEqual(len(selected),1);self.assertEqual(len(selected[0][2]),2)
        self.assertEqual(excluded,[])

    def test_alpha_requires_explicit_admission_and_wildcards_never_admitted(self):
        rows=[self.row(opaque=False)]
        self.assertEqual(module.select(rows,re.compile('NAMED.*'),False)[0],[])
        self.assertEqual(len(module.select(rows,re.compile('NAMED.*'),True)[0]),1)
        rows=[self.row(key='000000001234567800000000')]
        self.assertEqual(module.select(rows,re.compile('NAMED.*'),True)[0],[])

    def test_missing_palette_decode_and_nonhalving_mips_are_not_completed(self):
        row=self.row();row['authored_levels'][0].pop('rgba_sha256')
        self.assertEqual(module.select([row],re.compile('NAMED.*'),True)[0],[])
        row=self.row();row['mip_levels']=2
        row['authored_levels'].append(dict(width=32,height=64,rgba_sha256='b'*64,opaque=True))
        self.assertEqual(module.select([row],re.compile('NAMED.*'),True)[0],[])

    def test_alpha_only_excludes_opaque_and_protects_existing_context(self):
        opaque=self.row();alpha=self.row(name='PH00',digest='b'*64,opaque=False)
        selected,_=module.select([opaque,alpha],re.compile('.*'),True,True)
        # Deliberately shared identities still fail the global collision guard.
        self.assertEqual(selected,[])
        alpha['candidate_keys']=['0000000087654321abcdef01']
        selected,_=module.select([opaque,alpha],re.compile('.*'),True,True)
        self.assertEqual(len(selected),1)
        key=module.sampler_pack.tagged_key(alpha['candidate_keys'][0],256)
        admitted,retained=module.uncovered(selected,dict(textures=[dict(key=key)]))
        self.assertEqual(admitted,[])
        self.assertEqual(retained[0]['reason'],'existing replacement retained')

    def test_small_authored_ui_uses_explicit_original_scaler_admission(self):
        row=self.row(name='COM_BUT')
        row['authored_levels'][0].update(width=8,height=8)
        self.assertEqual(module.select([row],re.compile('.*'),True)[0],[])
        selected,_=module.select([row],re.compile('.*'),True,minimum_dimension=1)
        self.assertEqual(len(selected),1)
        row['authored_levels'][0]['width']=7
        self.assertEqual(module.select([row],re.compile('.*'),True,minimum_dimension=1)[0],[])

    def test_small_ui_still_requires_complete_authored_mip_geometry(self):
        row=self.row(name='COM_BUT');row['mip_levels']=3
        row['authored_levels']=[dict(width=w,height=w,rgba_sha256=str(i)*64,opaque=True)
                                for i,w in enumerate((8,4,2))]
        self.assertEqual(len(module.select([row],re.compile('.*'),True,minimum_dimension=1)[0]),1)
        row['authored_levels'][2]['height']=1
        self.assertEqual(module.select([row],re.compile('.*'),True,minimum_dimension=1)[0],[])

    def test_zero_source_hash_requires_explicit_namespaced_admission(self):
        row=self.row(name='WHITE',key='000000001234567800000000')
        self.assertEqual(module.select([row],re.compile('.*'),True)[0],[])
        selected,_=module.select([row],re.compile('.*'),True,allow_zero_source_hash=True)
        self.assertEqual(len(selected),1)
        for wrap in (0,1,256,257):
            self.assertNotEqual(int(module.sampler_pack.tagged_key(row['candidate_keys'][0],wrap)[-8:],16),0)

    def test_shared_mip_count_alias_uses_longest_exact_prefix(self):
        short=self.row(name='SHORT');long=self.row(name='LONG')
        long['mip_levels']=2
        long['authored_levels'].append(dict(width=64,height=64,rgba_sha256='b'*64,opaque=True))
        selected,excluded=module.select([short,long],re.compile('.*'),True)
        self.assertEqual(len(selected),1);self.assertEqual(len(selected[0][0]),2)
        self.assertEqual(excluded[0]['reason'],'compatible shorter mip alias uses full chain')
        long['authored_levels'][0]['rgba_sha256']='c'*64
        self.assertEqual(module.select([short,long],re.compile('.*'),True)[0],[])

    def test_explicit_context_completion_retains_legacy_but_fills_missing_tags(self):
        row=self.row();selected,_=module.select([row],re.compile('.*'),True)
        key=row['candidate_keys'][0]
        base=dict(textures=[dict(key=key)])
        self.assertEqual(module.uncovered(selected,base)[0],[])
        self.assertEqual(module.incomplete_contexts(selected,base),selected)
        base['textures'] += [dict(key=module.sampler_pack.tagged_key(key,w)) for w in (0,1,256,257)]
        self.assertEqual(module.incomplete_contexts(selected,base),[])


if __name__=='__main__':unittest.main()
