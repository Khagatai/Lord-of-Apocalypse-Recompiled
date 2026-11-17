import io
from pathlib import Path
import struct
import sys
import unittest
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import rgf_archive

def fixture():
    packed = zlib.compress(b"abcDEF") + b"\0" * 4
    index = struct.pack("<7I", 0x31464752, 0x10001, 2, 24, 28, 60, 28)
    index += struct.pack("<8I", 2, 0, len(packed), 6, 3, 0x60000, 3, 0x60001)
    return index, packed

class RgfArchive(unittest.TestCase):
    def test_valid_group_and_resource_boundaries(self):
        index, packed = fixture()
        groups = rgf_archive.parse_index(index, len(packed))
        self.assertEqual(list(rgf_archive.resources(io.BytesIO(packed), groups)),
                         [(0, 0x60000, b"abc"), (0, 0x60001, b"DEF")])

    def test_truncated_index_rejected(self):
        index, packed = fixture()
        with self.assertRaises(ValueError):
            rgf_archive.parse_index(index[:-1], len(packed))

    def test_archive_extent_rejected(self):
        index, packed = fixture()
        with self.assertRaises(ValueError):
            rgf_archive.parse_index(index, len(packed) - 1)

    def test_wrong_expanded_size_rejected(self):
        index, packed = fixture()
        damaged = bytearray(index)
        struct.pack_into("<I", damaged, 40, 7)
        with self.assertRaises(ValueError):
            rgf_archive.parse_index(damaged, len(packed))

    def test_corrupt_zlib_rejected(self):
        index, packed = fixture()
        group = rgf_archive.parse_index(index, len(packed))[0]
        with self.assertRaises(ValueError):
            rgf_archive.read_group(io.BytesIO(b"wrong" + packed[5:]), group)

    def test_zero_alignment_tail_allowed_but_nonzero_tail_rejected(self):
        index, packed = fixture()
        padded = bytearray(index + b"\0" * 4)
        struct.pack_into("<I", padded, 20, len(padded))
        self.assertEqual(len(rgf_archive.parse_index(padded, len(packed))), 1)
        padded[-1] = 1
        with self.assertRaises(ValueError):
            rgf_archive.parse_index(padded, len(packed))

if __name__ == "__main__":
    unittest.main()
