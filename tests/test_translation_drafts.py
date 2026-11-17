import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("translation_drafts", ROOT / "tools/prepare-translation-batch.py")
drafts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(drafts)


class TranslationDrafts(unittest.TestCase):
    def setUp(self):
        self.source = [{"id": 0, "lines": ["original"]}]
        self.draft = {"translations": [["translated"]]}
        self.row = {"resource_id": "00040001", "bundle_sha256": "bundle", "message_index": 0,
                    "block": 0, "raw_sha256": "message", "lines": ["original"], "editable_plain_text": True}

    def test_alias_entries_generate_one_edit_with_original_identity(self):
        manifest, stats = drafts.assemble([(self.source, self.draft)], [self.row, {**self.row, "message_index": 1}])
        self.assertEqual(stats["affected_entries"], 2)
        self.assertEqual(stats["edited_blocks"], 1)
        self.assertEqual(manifest["bundles"][0]["entries"][0]["before_sha256"], "message")

    def test_conflicting_translation_and_changed_line_count_refused(self):
        with self.assertRaisesRegex(ValueError, "Conflicting"):
            drafts.assemble([(self.source, self.draft), (self.source, {"translations": [["different"]]})], [self.row])
        with self.assertRaisesRegex(ValueError, "line count"):
            drafts.assemble([(self.source, {"translations": [["one", "two"]]})], [self.row])

    def test_unresolved_commands_and_unmatched_drafts_refused(self):
        with self.assertRaisesRegex(ValueError, "no editable"):
            drafts.assemble([(self.source, self.draft)], [{**self.row, "editable_plain_text": False}])
        with self.assertRaisesRegex(ValueError, "no editable"):
            drafts.assemble([(self.source, self.draft)], [])


if __name__ == "__main__":
    unittest.main()
