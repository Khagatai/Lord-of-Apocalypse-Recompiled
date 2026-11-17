import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from mes_codec import Bundle, GlyphTable, Message
from mes_edits import digest

spec = importlib.util.spec_from_file_location("translation_batch", ROOT / "tools/build-translation-batch.py")
batch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(batch)


class TranslationBatch(unittest.TestCase):
    def setUp(self):
        self.table = GlyphTable((32, 65, 66))
        raw = Message((0xffff, 0, 0, 0), ((1, 0xffff),)).build()
        self.source = Bundle(1, (0, 0), b"", (raw,)).build()
        self.key = 0x40001, digest(self.source)
        self.manifest = {"resource_id": "00040001", "source_bundle_sha256": self.key[1],
                         "entries": [{"message_index": 0, "before_sha256": digest(raw),
                                      "original_lines": ["A"], "english_lines": ["BBB"]}]}

    def test_counts_aliases_and_prepares_exact_variant(self):
        replacements, affected = batch.prepare_replacements([self.manifest], {self.key: self.source}, self.table)
        self.assertEqual(affected, 2)
        self.assertEqual(set(replacements), {self.key})
        bundle = Bundle.parse(replacements[self.key])
        self.assertEqual(bundle.offsets, (0, 0))
        self.assertEqual(Message.parse(bundle.blocks[0]).lines, ((2, 2, 2, 0xffff),))

    def test_duplicate_variant_refused(self):
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            batch.prepare_replacements([self.manifest, self.manifest], {self.key: self.source}, self.table)

    def test_audio_and_missing_variant_refused(self):
        with self.assertRaisesRegex(ValueError, "not found"):
            batch.prepare_replacements([self.manifest], {}, self.table)
        manifest = {**self.manifest, "resource_id": "00080001"}
        with self.assertRaisesRegex(ValueError, "only MES"):
            batch.prepare_replacements([manifest], {(0x80001, self.key[1]): self.source}, self.table)


if __name__ == "__main__":
    unittest.main()
