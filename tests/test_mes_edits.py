import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from mes_codec import Bundle, GlyphTable, Message
from mes_edits import apply_edits, digest


class MesEdits(unittest.TestCase):
    def setUp(self):
        self.table = GlyphTable((32, 65, 66))
        self.raw = Message((0xffff, 0, 0, 0), ((1, 0xffff),)).build()
        self.source = Bundle(1, (0, 1, 0), b"", (self.raw, self.raw)).build()
        self.manifest = {"source_bundle_sha256": digest(self.source), "entries": [
            {"message_index": 0, "before_sha256": digest(self.raw),
             "original_lines": ["A"], "english_lines": ["BBB"]}]}

    def test_growing_edit_preserves_other_blocks_and_alias(self):
        output = Bundle.parse(apply_edits(self.source, self.table, self.manifest))
        self.assertEqual(output.offsets, (0, 1, 0))
        self.assertEqual(output.blocks[1], self.raw)
        self.assertEqual(Message.parse(output.blocks[0]).lines, ((2, 2, 2, 0xffff),))

    def test_stale_source_message_and_text_refused(self):
        for field, value in (("before_sha256", "0" * 64), ("original_lines", ["B"])):
            manifest = copy.deepcopy(self.manifest)
            manifest["entries"][0][field] = value
            with self.assertRaises(ValueError):
                apply_edits(self.source, self.table, manifest)
        with self.assertRaises(ValueError):
            apply_edits(self.source + b"\0\0", self.table, self.manifest)

    def test_alias_conflict_and_line_count_change_refused(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["entries"].append({**manifest["entries"][0], "message_index": 2})
        with self.assertRaisesRegex(ValueError, "alias"):
            apply_edits(self.source, self.table, manifest)
        self.manifest["entries"][0]["english_lines"] = ["A", "B"]
        with self.assertRaisesRegex(ValueError, "line count"):
            apply_edits(self.source, self.table, self.manifest)

    def test_password_keys_and_aliases_stay_protected_but_notifications_editable(self):
        manifest = copy.deepcopy(self.manifest)
        manifest['resource_id'] = '000400e3'
        with self.assertRaisesRegex(ValueError, 'password keys'):
            apply_edits(self.source, self.table, manifest)
        # Index 10 is display text; it must still be refused if it aliases key 0.
        shared = Bundle(1, (0,)*11, b'', (self.raw,)).build()
        manifest['source_bundle_sha256'] = digest(shared)
        manifest['entries'][0]['message_index'] = 10
        with self.assertRaisesRegex(ValueError, 'password keys'):
            apply_edits(shared, self.table, manifest)
        distinct = Bundle(1, tuple(range(11)), b'', (self.raw,)*11).build()
        manifest['source_bundle_sha256'] = digest(distinct)
        changed = Bundle.parse(apply_edits(distinct, self.table, manifest))
        self.assertEqual(changed.blocks[:10], (self.raw,)*10)
        self.assertEqual(Message.parse(changed.blocks[10]).lines[0], (2, 2, 2, 0xffff))


if __name__ == "__main__":
    unittest.main()
