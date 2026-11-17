from pathlib import Path
import importlib.util
import json
import re
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
spec=importlib.util.spec_from_file_location('remaster_selection',ROOT/'tools/filter-archive-remaster.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class RemasterSelectionTests(unittest.TestCase):
    def test_index_exclusions_require_the_exact_batch_and_known_indices(self):
        assets=[dict(index=0),dict(index=1)]
        policy=dict(required_batch_manifest_sha256='a'*64,required_generation_sha256='c'*64,exclude_asset_indices=[1])
        self.assertEqual(module.policy_indices(policy,'a'*64,assets,'c'*64),{1})
        with self.assertRaises(ValueError):module.policy_indices(policy,'b'*64,assets,'c'*64)
        with self.assertRaises(ValueError):module.policy_indices(policy,'a'*64,assets,'d'*64)
        with self.assertRaises(ValueError):module.policy_indices(dict(exclude_asset_indices=[1]),'a'*64,assets)
        policy['exclude_asset_indices']=[2]
        with self.assertRaises(ValueError):module.policy_indices(policy,'a'*64,assets,'c'*64)

    def test_effect_index_does_not_exclude_a_body_with_the_same_name(self):
        effect=dict(index=0,references=[dict(name='MS30_01')])
        body=dict(index=1,references=[dict(name='MS30_01')])
        self.assertTrue(module.excluded(effect,[],{0}))
        self.assertFalse(module.excluded(body,[],{0}))

    def test_effect_or_text_alias_excludes_whole_shared_atlas(self):
        policy=json.loads((ROOT/'config/remaster-environment-selection.json').read_text())
        patterns=[re.compile(p) for p in policy['exclude_name_patterns']]
        def excluded(*names):return module.excluded(dict(references=[dict(name=n) for n in names]),patterns)
        for name in ('HEI_POSTER','BG05_FOG','GLD_WATER_A','UNI_GRA','SKY','OB46'):
            self.assertTrue(excluded('KAR_WALL',name),name)
        for name in ('KAR_WALL','BG29_GRASS_002','ARE_FIREDAI','BG11_KME_BUILD_A01'):
            self.assertFalse(excluded(name),name)


if __name__=='__main__':unittest.main()
