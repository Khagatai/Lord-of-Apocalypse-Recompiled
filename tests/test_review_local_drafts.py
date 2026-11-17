import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from mes_codec import GlyphTable
spec = importlib.util.spec_from_file_location("review_drafts", ROOT / "tools/review-local-drafts.py")
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)


class ReviewDrafts(unittest.TestCase):
    def setUp(self):
        self.table = GlyphTable(tuple(range(32, 127)) + (0x2605, 0x2606))

    def test_exact_literal_uses_canonical_glossary_without_semantic_pass(self):
        row = {"source_lines": ["名称"], "translated_lines": None, "status": "blocked-review"}
        result = review.review(row, self.table, {}, {"名称": "Canonical Name"})
        self.assertEqual(result["translated_lines"], ["Canonical Name"])
        self.assertFalse(result["quality_reviewed"])

    def test_changed_rating_and_missing_commands_stay_blocked(self):
        row = {"source_lines": ["★★"], "translated_lines": ["★"]}
        self.assertEqual(review.review(row, self.table, {})["status"], "blocked-review")
        row = {"source_lines": ["<cmd:0>source"], "translated_lines": ["English"]}
        self.assertEqual(review.review(row, self.table, {})["status"], "blocked-review")

    def test_latin_rendering_normalization_does_not_strip_japanese_voicing(self):
        self.assertEqual(review.latin_ascii("Shōnen"), "Shonen")
        self.assertEqual(review.latin_ascii("ガ"), "ガ")

    def test_derived_terminology_does_not_override_contextual_translation(self):
        row = {"source_lines": ["ロード"], "translated_lines": ["Lord"]}
        result = review.review(row, self.table, {"ロード": "Load"})
        self.assertEqual(result["translated_lines"], ["Lord"])
        self.assertEqual(result["review_flags"][0]["kind"], "terminology-review")

    def test_prompt_leak_is_blocked_even_after_valid_english(self):
        row = {'source_lines': ['名前'], 'translated_lines': ['Name. Earlier rejected draft: more text']}
        self.assertEqual(review.review(row, self.table, {})['status'], 'blocked-review')

    def test_overlong_lines_can_reflow_without_clipping_or_losing_commands(self):
        text = 'A long translated sentence that fits across two lines with <cmd:0>formatting<cmd:1>.'
        row = {'source_lines': ['<cmd:0>原文', '本文<cmd:1>'], 'translated_lines': [text, '']}
        result = review.review(row, self.table, {})
        self.assertEqual(result['status'], 'machine-draft-structure-checked')
        self.assertEqual(' '.join(result['translated_lines']), text)
        self.assertFalse(result['quality_reviewed'])


if __name__ == "__main__":
    unittest.main()
