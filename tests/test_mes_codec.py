from pathlib import Path
import struct
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from mes_codec import Bundle, GlyphTable, Message

class MesCodec(unittest.TestCase):
    def setUp(self):
        self.table = GlyphTable((32, 65, 66, 67))

    def message(self):
        return Message((0xffff, 0, 0, 0), ((1, 0, 2, 0xfffe), (3, 0xffff)), (0,))

    def bundle(self):
        return Bundle(1, (0, 1, 0), b"", (self.message().build(), Message((1,2,3,4), ((2,0xffff),)).build()))

    def test_message_roundtrip_preserves_header_line_counts_and_padding(self):
        raw = self.message().build()
        self.assertEqual(Message.parse(raw).build(), raw)
        self.assertEqual(self.table.decode(Message.parse(raw).lines[0][:-1]), "A B")

    def test_edit_recalculates_pointers_and_preserves_aliases(self):
        bundle = self.bundle()
        changed = self.message().replace_line(0, "ABCABC", self.table)
        output = bundle.build({0: changed})
        parsed = Bundle.parse(output)
        self.assertEqual(parsed.offsets, (0,1,0))
        self.assertEqual(Message.parse(parsed.blocks[0]).lines[0], (1,2,3,1,2,3,0xfffe))
        self.assertEqual(parsed.blocks[1], bundle.blocks[1])
        self.assertEqual(parsed.build(), output)

    def test_unresolved_controls_refuse_edits_and_preserve_raw(self):
        message = Message((0xffff,0,0,0), ((1,0xfffa,0,0,0,0xffff),))
        with self.assertRaisesRegex(ValueError, "unresolved"):
            message.replace_line(0,"A",self.table)
        self.assertEqual(Message.parse(message.build()).build(), message.build())

    def test_unavailable_character_refused(self):
        with self.assertRaises(ValueError):
            self.message().replace_line(0,"Z",self.table)

    def test_bad_pointer_and_truncated_line_refused(self):
        raw = bytearray(self.bundle().build())
        struct.pack_into("<I", raw, 12, len(raw)+2)
        with self.assertRaises(ValueError):
            Bundle.parse(raw)
        with self.assertRaises(ValueError):
            Message.parse(self.message().build()[:-4])

if __name__ == "__main__":
    unittest.main()
