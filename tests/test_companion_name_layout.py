import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from mes_codec import Bundle, GlyphTable, Message
from companion_name_layout import fit_companion_names, COMPACT, BUFFER_BYTES


class CompanionNameSafety(unittest.TestCase):
    def setUp(self):
        self.table = GlyphTable(tuple(range(128)))

    def message(self, text):
        return Message((0xffff, 0, 0, 0), (self.table.encode(text)+(0xffff,),)).build()

    def bundle(self, names):
        blocks = [self.message('Albert')]*120 + [self.message('Equipment description remains long')]*243
        for index, name in enumerate(names): blocks[index] = self.message(name)
        return Bundle(1, tuple(range(363)), b'', tuple(blocks)).build()

    def test_recruit_name_cannot_overwrite_adjacent_stack_pointer(self):
        raw = self.bundle(['Lauralone', 'Elvancia'])
        fixed = fit_companion_names(raw, self.table)
        bundle = Bundle.parse(fixed)
        name = Message.parse(bundle.blocks[0])
        self.assertEqual(self.table.decode(name.lines[0][:-1]), 'Laura')
        # Model the real 18-byte destination followed by a live pointer.
        import struct
        encoded = struct.pack('<'+'H'*len(name.lines[0]), *name.lines[0])
        destination = bytearray(b'\x00'*BUFFER_BYTES+struct.pack('<I', 0x08d81234))
        destination[:len(encoded)] = encoded
        self.assertEqual(struct.unpack_from('<I', destination, BUFFER_BYTES)[0], 0x08d81234)
        original = Bundle.parse(raw)
        self.assertEqual(bundle.blocks[1:], original.blocks[1:])
        self.assertEqual(fit_companion_names(fixed, self.table), fixed)

    def test_every_reviewed_long_name_fits_including_terminator(self):
        fixed = Bundle.parse(fit_companion_names(self.bundle(list(COMPACT)), self.table))
        for block in fixed.blocks[:len(COMPACT)]:
            self.assertLessEqual(len(Message.parse(block).lines[0])*2, BUFFER_BYTES)

    def test_unknown_overlong_name_is_refused(self):
        with self.assertRaisesRegex(ValueError, 'review required'):
            fit_companion_names(self.bundle(['Unexpected long name']), self.table)

    def test_wrong_table_is_refused(self):
        with self.assertRaisesRegex(ValueError, 'directory'):
            fit_companion_names(Bundle(1, (0,), b'', (self.message('Lauralone'),)).build(), self.table)

if __name__ == '__main__': unittest.main()
