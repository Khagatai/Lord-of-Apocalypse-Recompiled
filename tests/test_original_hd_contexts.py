import importlib.util
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
s=importlib.util.spec_from_file_location('original',ROOT/'tools/build-original-hd-pack.py')
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)


class OriginalContextTests(unittest.TestCase):
    def test_partial_sampler_and_address_aliases_are_filled_without_overwriting(self):
        a='000000001234567812345678';b='000000001234567800000000'
        kept=m.sampler_pack.tagged_key(a,1)
        pending=m.missing_contexts([a,b],{kept})
        self.assertEqual(pending[1],[b])
        for wrap in (0,256,257):self.assertEqual(pending[wrap],[a,b])

    def test_existing_canonical_fallback_remains_authoritative(self):
        key='000000001234567812345678'
        self.assertTrue(all(not keys for keys in m.missing_contexts([key],{key}).values()))
