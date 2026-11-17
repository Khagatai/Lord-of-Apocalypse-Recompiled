import io
from pathlib import Path
import struct
import sys
import unittest
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from rgf_archive import parse_index, resources
from rgf_edits import append_edits, digest


class RgfEdits(unittest.TestCase):
    def fixture(self):
        # Two groups with the same identifier but distinct payload variants.
        archive = b"".join(zlib.compress(raw).ljust(2048, b"\0") for raw in (b"AB", b"CD"))
        index = struct.pack("<8I", 0x31464752, 0x20001, 1, 24, 32, 80, 32, 56)
        index += struct.pack("<6I", 1, 0, 2048, 2, 2, 0x40000)
        index += struct.pack("<6I", 1, 2048, 2048, 2, 2, 0x40000)
        return index, archive

    def test_append_preserves_original_bytes_and_other_variant(self):
        index, archive = self.fixture()
        target = io.BytesIO(archive)
        rebuilt, report = append_edits(index, io.BytesIO(archive), target,
                                       {(0x40000, digest(b"AB")): b"LONGER"})
        self.assertEqual(target.getvalue()[:len(archive)], archive)
        self.assertEqual(report["changed_groups"], [0])
        groups = parse_index(rebuilt, len(target.getvalue()))
        self.assertEqual(groups[1].offset, 2048)
        self.assertEqual(list(resources(target, groups)), [(0, 0x40000, b"LONGER"), (1, 0x40000, b"CD")])

    def test_missing_variant_and_wrong_archive_size_refused(self):
        index, archive = self.fixture()
        with self.assertRaisesRegex(ValueError, "not found"):
            append_edits(index, io.BytesIO(archive), io.BytesIO(archive), {(0x40000, "wrong"): b"X"})
        with self.assertRaisesRegex(ValueError, "copy"):
            append_edits(index, io.BytesIO(archive), io.BytesIO(archive[:-1]), {(0x40000, digest(b"AB")): b"X"})


if __name__ == "__main__":
    unittest.main()
