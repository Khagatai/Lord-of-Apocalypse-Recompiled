from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import remaster_policy as policy
import sampler_pack


class PortraitPolicyTests(unittest.TestCase):
    def test_illustrations_are_separate_from_model_atlases(self):
        for name in ('NAMED001', 'NPC211'):
            self.assertTrue(policy.original_portrait(name))
        for name in ('NPC01_00', 'NP01_00', 'MS37_00', 'DIALOG_FRAME'):
            self.assertFalse(policy.original_portrait(name))

    def test_legacy_and_sampler_aliases_are_blocked_without_provenance(self):
        key='0000000012345678abcdef01'
        catalog=[dict(name='NPC211', candidate_keys=[key])]
        keys=policy.portrait_keys(catalog)
        self.assertTrue(policy.portrait_group(dict(key=key), keys))
        for wrap in (0, 1, 256, 257):
            self.assertTrue(policy.portrait_group(dict(key=sampler_pack.tagged_key(key, wrap)), keys))
        selected=[((), [dict(name='ALIAS')], [key]),
                  ((), [dict(name='NPC01_00')], ['000000001234567812345678'])]
        kept,excluded=policy.exclude_portraits(selected,catalog)
        self.assertEqual([e[1][0]['name'] for e in kept], ['NPC01_00'])
        self.assertEqual(excluded[0]['name'], 'ALIAS')
