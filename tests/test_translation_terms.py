from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from translation_terms import protect, restore


class TranslationTerms(unittest.TestCase):
    def test_names_digits_and_star_ratings_restored_exactly(self):
        source, terms = protect("町<cmd:0>★★<cmd:1>２０体", {"町": "Named Town"})
        self.assertEqual(source, "<fixed:0><cmd:0><fixed:1><cmd:1><fixed:2>体")
        result = restore("<fixed:0> <cmd:0><fixed:1><cmd:1> Defeat <fixed:2>.", source, terms)
        self.assertEqual(result, "Named Town <cmd:0>★★<cmd:1> Defeat 20.")

    def test_lost_duplicate_or_reordered_command_marker_refused(self):
        source, terms = protect("<cmd:0>２０<cmd:1>", {})
        for bad in ("20", source+"<fixed:0>", "<cmd:1><fixed:0><cmd:0>"):
            with self.assertRaises(ValueError):
                restore(bad, source, terms)

    def test_embedded_identifier_digits_are_protected_completely(self):
        text, terms = protect("MCN0001 PSP1000 +2", {})
        self.assertEqual(text, "MCN<fixed:0> PSP<fixed:1> <fixed:2>")
        self.assertEqual(restore(text, text, terms), "MCN0001 PSP1000 +2")


if __name__ == "__main__":
    unittest.main()
