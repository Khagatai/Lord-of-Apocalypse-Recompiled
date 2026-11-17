from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import sampler_pack


class SamplerPackKeys(unittest.TestCase):
    def test_wrap_contexts_have_distinct_keys_and_preserve_address_and_palette_geometry(self):
        original='000000001234567889abcdef'
        keys=[sampler_pack.tagged_key(original,w) for w in (0,1,256,257)]
        self.assertEqual(len(set(keys)),4)
        self.assertTrue(all(k[:16]==original[:16] for k in keys))
        for index,key in enumerate(keys):
            self.assertEqual(int(key[16:],16)^int(original[16:],16),0x4c4f4100|index)

    def test_unknown_context_and_namespace_are_refused(self):
        with self.assertRaisesRegex(ValueError,'context'):
            sampler_pack.tagged_key('0'*24,2)
        with self.assertRaisesRegex(ValueError,'identity'):
            sampler_pack.tagged_key('../bad',0)
        with self.assertRaisesRegex(ValueError,'namespace'):
            sampler_pack.validate({'version':2})
        with self.assertRaisesRegex(ValueError,'wildcard'):
            sampler_pack.tagged_key('00000000000000004c4f4100',0)
        self.assertIsNone(sampler_pack.validate(None))

    def test_namespaced_pack_cannot_silently_use_an_old_or_different_executable(self):
        sampler_pack.require_runtime(None,{},'new')
        metadata={'renderer':{'sampler_namespace_version':1},'executable_sha256':'new'}
        sampler_pack.require_runtime(sampler_pack.NAMESPACE,metadata,'new')
        for invalid in ({},{'renderer':{},'executable_sha256':'new'},dict(metadata,executable_sha256='old')):
            with self.assertRaisesRegex(ValueError,'matching rebuilt'):
                sampler_pack.require_runtime(sampler_pack.NAMESPACE,invalid,'new')
