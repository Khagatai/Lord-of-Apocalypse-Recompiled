"""Synthetic import ABI only; native entry comparison covers the real fixture."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("import_trace_adapter", ROOT / "tools/import_trace_codegen.py")
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)

class ImportTrace(unittest.TestCase):
    def test_legacy_emitter_has_unpaired_end(self):
        text = adapter.ORIGINAL_IMPORT_EMITTER(0x08801000, "Synthetic", 0x12345678)
        self.assertIn("sr_end(s, 0u, 0)", text)
        self.assertNotIn("sr_begin(", text)

    def test_jr_and_syscall_have_separate_paired_boundaries(self):
        text = adapter.traced_import(0x08801000, "Synthetic", 0x12345678)
        begin = text.index("sr_begin(s, 0x08801000u")
        jr_end = text.index("sr_end(s, 0u, 0)")
        syscall_begin = text.index("sr_begin(s, 0x08801004u")
        call = text.index("sr_syscall(s, 0x12345678u)")
        syscall_end = text.rindex("sr_end(s, 0u, 0)")
        self.assertLess(begin, jr_end)
        self.assertLess(jr_end, syscall_begin)
        self.assertLess(syscall_begin, call)
        self.assertLess(call, syscall_end)
        self.assertEqual(text.count("sr_syscall("), 1)
        self.assertEqual(text.count("sr_begin("), text.count("sr_end("))

    def test_lle_failure_flow_is_preserved(self):
        original = adapter.ORIGINAL_IMPORT_EMITTER(0x08801000, "Synthetic", 0x12345678, True)
        text = adapter.traced_import(0x08801000, "Synthetic", 0x12345678, True)
        self.assertIn("sr_import_call(s, 0x12345678u, 0x08801000u)", text)
        failure = "if (s->flow_kind != 0u) { sr_end(s, 0u, 0); return; }"
        self.assertIn(failure, original)
        self.assertIn(failure, text)

if __name__ == "__main__":
    unittest.main()
