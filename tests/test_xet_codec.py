import struct
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from xet_codec import Xet


def fixture():
    raw = bytearray(292)
    struct.pack_into('<4sIHH4I', raw, 0, b'XET.', 1, 1, 1, 0, 252, 268, 276)
    raw[52:56] = bytes((255, 0, 0, 255))
    raw[56:60] = bytes((0, 255, 0, 255))
    raw[112] = 0x21
    raw[128] = 0x12
    struct.pack_into('<4HI', raw, 240, 32, 8, 32, 0, 112)
    struct.pack_into('<4H2I', raw, 252, 4, 0, 0, 0, 0, 240)
    struct.pack_into('<4BI', raw, 268, 3, 0, 15, 2, 48)
    raw[276:281] = b'AUDIT'
    return raw


class XetTests(unittest.TestCase):
    def test_palette_nibble_order_and_swizzled_row(self):
        parsed = Xet.parse(bytes(fixture()))
        self.assertEqual(parsed.textures[0].name, 'AUDIT')
        width, height, pixels = parsed.preview(0)
        self.assertEqual((width, height), (32, 8))
        self.assertEqual(pixels[:8], bytes((255, 0, 0, 255, 0, 255, 0, 255)))
        self.assertEqual(pixels[width*4:width*4+8], bytes((0, 255, 0, 255, 255, 0, 0, 255)))

    def test_out_of_bounds_and_unknown_versions_refused(self):
        raw = fixture()
        struct.pack_into('<I', raw, 248, 280)
        with self.assertRaisesRegex(ValueError, 'outside resource'):
            Xet.parse(bytes(raw)).preview(0)
        raw[4] = 2
        with self.assertRaisesRegex(ValueError, 'version'):
            Xet.parse(bytes(raw))

    def test_direct_colour_alpha_and_channel_expansion(self):
        self.assertEqual(Xet.rgba(b'\x00\x80', 1), b'\0\0\0\xff')
        self.assertEqual(Xet.rgba(b'\x0f\xf0', 2), b'\xff\0\0\xff')

    def test_midrange_16bit_colours_use_psp_bit_replication(self):
        self.assertEqual(Xet.rgba(b'\x04\x80', 1), bytes((33, 0, 0, 255)))
        self.assertEqual(Xet.rgba(b'\x04\x02', 0), bytes((33, 65, 0, 255)))

    def test_one_clut_block_contains_sixteen_16bit_colours(self):
        for colour, red in ((0, 0x001f), (1, 0x801f), (2, 0xf00f)):
            with self.subTest(colour=colour):
                raw = fixture()
                raw[48:80] = bytes(32)
                struct.pack_into('<H', raw, 78, red)  # Entry 15, beyond eight colours.
                struct.pack_into('<4BI', raw, 268, colour, 0, 15, 1, 48)
                raw[112] = 0xff
                width, height, pixels = Xet.parse(bytes(raw)).preview(0)
                self.assertEqual((width, height), (32, 8))
                self.assertEqual(pixels[:8], bytes((255, 0, 0, 255))*2)

    def test_zero_clut_load_does_not_invent_retained_palette(self):
        raw = fixture()
        struct.pack_into('<4BI', raw, 268, 1, 0, 15, 0, 48)
        with self.assertRaisesRegex(ValueError, 'Palette lookup outside allocation'):
            Xet.parse(bytes(raw)).preview(0)

    def test_full_clut_block_must_fit_resource(self):
        raw = fixture()
        struct.pack_into('<4BI', raw, 268, 1, 0, 15, 1, 276)
        with self.assertRaisesRegex(ValueError, 'outside resource'):
            Xet.parse(bytes(raw)).preview(0)

    def test_authored_mip_selection_and_invalid_level_refused(self):
        from xet_codec import Texture, Mip
        base = Xet.parse(bytes(fixture()))
        # Distinct source rows prove selection reads the authored extent.
        mip = Mip(32, 8, 32, 0, 112)
        second = Mip(32, 8, 32, 0, 128)
        image = Xet(base.data, (Texture('MIPS', 4, 0, (mip, second)),), base.palettes)
        self.assertEqual(image.preview_mip(0, 1)[2][:4], bytes((0, 255, 0, 255)))
        self.assertNotEqual(image.preview_mip(0, 1)[2][:4], image.preview(0)[2][:4])
        with self.assertRaisesRegex(ValueError, 'Mip level'):
            image.preview_mip(0, 2)
        with self.assertRaisesRegex(ValueError, 'preview limit'):
            image.preview_mip(0, 0, 0)

    def test_small_swizzle_reads_padded_rows_and_refuses_truncated_span(self):
        from xet_codec import Texture, Mip
        raw = bytearray(72)
        red, green, blue, white = (bytes(c) for c in
            ((255,0,0,255),(0,255,0,255),(0,0,255,255),(255,255,255,255)))
        raw[48:56] = red+green
        raw[64:72] = blue+white  # Row two begins at 16, not logical pitch 8.
        texture = Texture('PADDED',3,0,(Mip(2,2,2,0,48),))
        self.assertEqual(Xet(bytes(raw),(texture,),()).preview(0),
                         (2,2,red+green+blue+white))
        with self.assertRaisesRegex(ValueError,'outside resource'):
            Xet(bytes(raw[:-1]),(texture,),()).preview(0)
        # In a narrow, non-power-of-two audit image, the final row need not
        # have the greatest swizzled address. Check all rows' accessed span.
        tall = Texture('NARROW',3,0,(Mip(2,10,2,0,48),))
        with self.assertRaisesRegex(ValueError,'outside resource'):
            Xet(bytes(136),(tall,),()).preview(0)

    def test_names_are_sequential_nul_strings_not_fixed_records(self):
        old = fixture()
        raw = bytearray(296)
        raw[:268] = old[:268]
        raw[268:284] = old[252:268]
        raw[284:292] = old[268:276]
        raw[292:296] = b'A\0B\0'
        struct.pack_into('<H', raw, 8, 2)
        struct.pack_into('<2I', raw, 20, 284, 292)
        self.assertEqual([item.name for item in Xet.parse(bytes(raw)).textures], ['A', 'B'])

    def test_text_edit_changes_only_approved_pixel_not_palette_or_metadata(self):
        raw = fixture()
        struct.pack_into('<H', raw, 252, 5)
        struct.pack_into('<3H', raw, 240, 16, 8, 16)
        parsed = Xet.parse(bytes(raw))
        width, height, rgba = parsed.preview(0)
        changed = bytearray(rgba)
        changed[:4] = bytes((0, 255, 0, 255))
        # An arbitrary edit outside the approved rectangle must be ignored.
        changed[4:8] = bytes((255, 0, 0, 255))
        target = parsed.replace_text_regions(0, bytes(changed), [(0, 0, 1, 1)])
        self.assertEqual([i for i, (a, b) in enumerate(zip(raw, target)) if a != b], [112])
        after = Xet.parse(target).preview(0)[2]
        self.assertEqual(after[:4], bytes((0, 255, 0, 255)))
        self.assertEqual(after[4:], rgba[4:])
        with self.assertRaisesRegex(ValueError, 'region exceeds'):
            parsed.replace_text_regions(0, rgba, [(15, 0, 2, 1)])

    def test_t4_edits_preserve_other_nibble_and_swizzle_tiles(self):
        raw = bytes(fixture())
        parsed = Xet.parse(raw)
        width, height, rgba = parsed.preview(0)
        for x, y in ((0, 0), (1, 0), (0, 1), (31, 7)):
            changed = bytearray(rgba)
            start = (y*width+x)*4
            colour = bytes((0, 255, 0, 255)) if rgba[start:start+4] != bytes((0, 255, 0, 255)) else bytes((255, 0, 0, 255))
            changed[start:start+4] = colour
            target = parsed.replace_text_regions(0, changed, [(x, y, 1, 1)])
            after = Xet.parse(target).preview(0)[2]
            self.assertEqual(after, bytes(changed))
            offsets = [i for i, (a, b) in enumerate(zip(raw, target)) if a != b]
            self.assertEqual(len(offsets), 1)
            self.assertEqual(target[:112], raw[:112])
            self.assertEqual(target[240:], raw[240:])


if __name__ == '__main__':
    unittest.main()
