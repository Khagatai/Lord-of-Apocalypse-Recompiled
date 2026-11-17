import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from mes_codec import GlyphTable

spec = importlib.util.spec_from_file_location("draft_assembly", ROOT / "tools/assemble-local-drafts.py")
assembly = importlib.util.module_from_spec(spec)
spec.loader.exec_module(assembly)


class DraftAssembly(unittest.TestCase):
    def setUp(self):
        self.table = GlyphTable(tuple(range(32, 127)))
        self.lines = ["原文"]
        self.identity = hashlib.sha256(json.dumps(self.lines, ensure_ascii=True).encode()).hexdigest()
        self.message = {"resource_id": "00040001", "bundle_sha256": "bundle", "message_index": 0,
                        "block": 0, "before_sha256": "message", "original_lines": self.lines,
                        "status": "offline-draft-plain"}
        self.draft = {"id": self.identity, "source_lines": self.lines, "translated_lines": ["English"],
                      "status": "machine-draft-structure-checked"}

    def test_unreviewed_drafts_require_explicit_candidate_flag(self):
        manifest, report, unresolved = assembly.assemble([self.message], [self.draft], self.table, False)
        self.assertEqual(manifest["bundles"], [])
        self.assertEqual(report["unresolved_entries"], 1)
        self.assertEqual(unresolved[0]["status"], "unreviewed-not-included")
        manifest, report, unresolved = assembly.assemble([self.message], [self.draft], self.table, True)
        self.assertEqual(manifest["bundles"][0]["entries"][0]["token_mode"], "message-stream-v1")
        self.assertFalse(report["translation_complete"])
        self.assertFalse(report["quality_reviewed"])

    def test_rejected_and_duplicate_drafts_never_silently_enter_manifest(self):
        rejected = {**self.draft, "status": "blocked-review", "reason": "truncated sentence"}
        manifest, report, unresolved = assembly.assemble([self.message], [rejected], self.table, True)
        self.assertEqual(manifest["bundles"], [])
        self.assertEqual(unresolved[0]["reason"], "truncated sentence")
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            assembly.assemble([self.message], [self.draft, self.draft], self.table, True)

    def test_timed_cues_group_into_one_message_edit_without_duplicate_alias_edits(self):
        first = {**self.message, "status": "prior-human-draft", "timed_subtitles": True,
                 "cue_index": 0, "cue_before_sha256": "cue0", "english_lines": ["First"]}
        second = {**first, "cue_index": 1, "cue_before_sha256": "cue1", "english_lines": ["Second"]}
        alias = {**first, "message_index": 1}
        manifest, report, unresolved = assembly.assemble([first, second, alias], [], self.table, False)
        entries = manifest["bundles"][0]["entries"]
        self.assertEqual(len(entries), 1)
        self.assertEqual([edit["cue_index"] for edit in entries[0]["cue_edits"]], [0, 1])
        self.assertEqual(report["edited_blocks"], 1)
        self.assertEqual(report["edited_timed_cues"], 2)


if __name__ == "__main__":
    unittest.main()
