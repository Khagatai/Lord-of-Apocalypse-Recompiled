from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from mes_codec import Bundle, GlyphTable
from mes_edits import apply_edits, digest
from mes_subtitles import Cue, TimedMessage


class TimedSubtitles(unittest.TestCase):
    def setUp(self):
        self.table = GlyphTable((32, 65, 66, 67))
        self.cue = Cue((0, 0, 8, 227, 0, 0, 9, 501), ((1, 0xfffe),), 0xffff)
        self.message = TimedMessage((0xff, 2, 0, 0), (self.cue,), (0,))

    def test_roundtrip_and_edit_leave_clocks_boundaries_header_unchanged(self):
        raw = self.message.build()
        self.assertEqual(TimedMessage.parse(raw).build(), raw)
        changed = self.message.replace_cue(0, ["BBB"], self.table)
        self.assertEqual(changed.cues[0].timing, self.cue.timing)
        self.assertEqual(changed.cues[0].ending, self.cue.ending)
        self.assertEqual(changed.header, self.message.header)
        self.assertEqual(changed.padding, self.message.padding)
        with self.assertRaisesRegex(ValueError, "line count"):
            self.message.replace_cue(0, ["A", "B"], self.table)

    def test_manifest_edits_only_selected_cue_and_preserves_alias(self):
        raw = self.message.build()
        source = Bundle(1, (0, 0), b"", (raw,)).build()
        edit = {"cue_index": 0, "before_sha256": digest(self.cue.build()), "original_lines": ["A"], "english_lines": ["BC"]}
        manifest = {"resource_id": "00040001", "source_bundle_sha256": digest(source), "entries": [
            {"message_index": 0, "before_sha256": digest(raw), "timed_subtitles": True, "cue_edits": [edit]}]}
        result = Bundle.parse(apply_edits(source, self.table, manifest))
        changed = TimedMessage.parse(result.blocks[0])
        self.assertEqual(result.offsets, (0, 0))
        self.assertEqual(changed.cues[0].lines, ((2, 3, 0xfffe),))
        self.assertEqual(changed.cues[0].timing, self.cue.timing)

    def test_record_count_and_missing_terminator_refused(self):
        with self.assertRaises(ValueError):
            TimedMessage.parse(self.message.build()[:-6])
        bad = TimedMessage((0xff, 99, 0, 0), (self.cue,))
        with self.assertRaisesRegex(ValueError, "record count"):
            TimedMessage.parse(bad.build())


if __name__ == "__main__":
    unittest.main()
