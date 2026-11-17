from pathlib import Path
import struct
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from mes_codec import Bundle, GlyphTable
from mes_legacy import LegacyMessage
from mes_edits import apply_edits, digest


class LegacyMessages(unittest.TestCase):
    def setUp(self):
        self.table = GlyphTable((32, 65, 66, 0x3042))
        self.message = LegacyMessage((0, 1, 0, 0), ((3, 1, 0xffff),), (0,), self.table)

    def test_byte_count_roundtrip_and_ascii_edit_preserves_metadata(self):
        raw = self.message.build()
        self.assertEqual(struct.unpack_from("<H", raw, 8)[0], 3)
        self.assertEqual(LegacyMessage.parse(raw, self.table).build(), raw)
        changed = self.message.replace_line(0, "BBBB", self.table)
        self.assertEqual(struct.unpack_from("<H", changed.build(), 8)[0], 4)
        self.assertEqual(changed.header, self.message.header)
        self.assertEqual(changed.padding, self.message.padding)

    def test_bad_byte_count_and_incorrect_line_count_refused(self):
        raw = bytearray(self.message.build())
        struct.pack_into("<H", raw, 8, 2)
        with self.assertRaisesRegex(ValueError, "byte count"):
            LegacyMessage.parse(raw, self.table)
        raw = bytearray(self.message.build())
        struct.pack_into("<H", raw, 2, 2)
        with self.assertRaisesRegex(ValueError, "line count"):
            LegacyMessage.parse(raw, self.table)

    def test_manifest_rebuild_preserves_aliases_and_gates_resource_id(self):
        raw = self.message.build()
        source = Bundle(1, (0, 0), b"", (raw,)).build()
        manifest = {"resource_id": "00040008", "source_bundle_sha256": digest(source), "entries": [
            {"message_index": 0, "before_sha256": digest(raw), "original_lines": ["あA"],
             "english_lines": ["BB"], "legacy_cp932": True}]}
        rebuilt = Bundle.parse(apply_edits(source, self.table, manifest))
        self.assertEqual(rebuilt.offsets, (0, 0))
        self.assertEqual(LegacyMessage.parse(rebuilt.blocks[0], self.table).lines, ((2, 2, 0xffff),))
        with self.assertRaisesRegex(ValueError, "save/install"):
            apply_edits(source, self.table, {**manifest, "resource_id": "00040009"})


if __name__ == "__main__":
    unittest.main()
