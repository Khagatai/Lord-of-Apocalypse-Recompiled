import importlib.util
import re
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from mes_codec import GlyphTable

spec = importlib.util.spec_from_file_location("local_dialogue", ROOT / "tools/draft-local-dialogue.py")
local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local)


class LocalDialogue(unittest.TestCase):
    def setUp(self):
        self.table = GlyphTable(tuple(range(32, 127)))

    def test_wrap_keeps_all_words_and_commands_without_clipping(self):
        text = "First <cmd:0>colored words<cmd:1> and the final words."
        lines = local.wrap_paragraph(text, 4, width=16)
        self.assertEqual(" ".join(line for line in lines if line), text)
        self.assertEqual(len(lines), 4)
        with self.assertRaisesRegex(ValueError, "budget"):
            local.wrap_paragraph(text, 1, width=16)

    def test_numeric_changes_japanese_and_missing_commands_refused(self):
        with self.assertRaisesRegex(ValueError, "numeric"):
            local.check(["Defeat 30 monsters."], ["Defeat 20 monsters."], self.table)
        with self.assertRaisesRegex(ValueError, "Untranslated"):
            local.check(["日本語"], ["original"], self.table)
        with self.assertRaisesRegex(ValueError, "stream"):
            local.check(["English"], ["<cmd:0>source"], self.table)

    def test_reflow_can_move_command_across_lines_without_reordering(self):
        result = local.check(["<cmd:0>English<cmd:1>", "text"],
                             ["<cmd:0>source", "text<cmd:1>"], self.table)
        self.assertEqual(result, ["<cmd:0>English<cmd:1>", "text"])

    def test_japanese_script_detection_does_not_classify_list_punctuation_as_prose(self):
        self.assertIsNone(local.JAPANESE.search("・English 【List】"))
        self.assertIsNotNone(local.JAPANESE.search("・日本語"))

    def test_written_japanese_numeral_can_become_a_digit_without_permitting_extra_stats(self):
        self.assertEqual(local.check(["Model 2"], ["二式"], self.table), ["Model 2"])
        self.assertEqual(local.check(["Year 2026"], ["二〇二六年"], self.table), ["Year 2026"])
        self.assertEqual(local.check(["10,000 points"], ["一万"], self.table), ["10,000 points"])
        self.assertEqual(local.check(["2,000 points"], ["2000"], self.table), ["2,000 points"])
        with self.assertRaisesRegex(ValueError, "numeric"):
            local.check(["Sword +1 +1"], ["Sword +1"], self.table)

    def test_protected_marker_pattern_cannot_escape_json_string_delimiters(self):
        pattern = local.protected_schema(["<cmd:0>", "<fixed:0>"])["pattern"]
        self.assertIsNotNone(re.fullmatch(pattern, "before <cmd:0>word <fixed:0> after"))
        for bad in ('text"} <cmd:0><fixed:0>', "<fixed:0><cmd:0>", "<cmd:0>\n<fixed:0>"):
            self.assertIsNone(re.fullmatch(pattern, bad))
        for bad in ("20 <cmd:0><fixed:0>", "★<cmd:0><fixed:0>"):
            self.assertIsNone(re.fullmatch(pattern, bad))

    def test_whitespace_before_command_cannot_overflow_full_line(self):
        lines = local.wrap_paragraph('A'*48+' <cmd:0>next<cmd:1>', 2)
        self.assertTrue(all(len(local.mes_tokens.TAG.sub('', line)) <= 48 for line in lines))
        self.assertEqual(lines, ['A'*48, '<cmd:0>next<cmd:1>'])

    def test_japanese_numeric_multiplier_preserves_actual_value(self):
        self.assertEqual(local.check(['3,000,000'], ['300万'], self.table), ['3,000,000'])
        with self.assertRaisesRegex(ValueError, 'numeric'):
            local.check(['300'], ['300万'], self.table)
        with self.assertRaisesRegex(ValueError, 'numeric'):
            local.check(['3,000,000 10,000'], ['300万'], self.table)


if __name__ == "__main__":
    unittest.main()
