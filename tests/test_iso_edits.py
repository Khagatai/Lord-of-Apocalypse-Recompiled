import io
from pathlib import Path
import struct
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from iso_edits import append_files, survey
from test_intake import image


class IsoEdits(unittest.TestCase):
    def fixture(self):
        raw = image()
        struct.pack_into("<I", raw, 16 * 2048 + 80, 24)
        struct.pack_into(">I", raw, 16 * 2048 + 84, 24)
        raw[17 * 2048:17 * 2048 + 7] = b"\xffCD001\x01"
        return bytes(raw)

    def test_append_updates_endian_fields_and_preserves_original_extent(self):
        raw = self.fixture()
        target = io.BytesIO(raw)
        replacement = b"longer replacement!"
        report = append_files(io.BytesIO(raw), target, {"TEST.ELF": io.BytesIO(replacement)})
        self.assertTrue(report["all_file_payloads_verified"])
        iso = survey.ISO(target)
        record = iso.files()["TEST.ELF"]
        self.assertEqual(record["lba"], 24)
        self.assertEqual(iso.read(record["lba"] * 2048, record["size"]), replacement)
        self.assertEqual(iso.read(21 * 2048, 8), b"fixture!")
        self.assertEqual(struct.unpack_from("<I", target.getvalue(), 16 * 2048 + 80)[0], 25)
        self.assertEqual(struct.unpack_from(">I", target.getvalue(), 16 * 2048 + 84)[0], 25)

    def test_other_descriptor_layout_and_unknown_path_refused(self):
        raw = bytearray(self.fixture())
        raw[17 * 2048] = 2
        with self.assertRaisesRegex(ValueError, "terminator"):
            append_files(io.BytesIO(raw), io.BytesIO(raw), {"TEST.ELF": io.BytesIO(b"X")})
        raw = self.fixture()
        with self.assertRaisesRegex(ValueError, "path"):
            append_files(io.BytesIO(raw), io.BytesIO(raw), {"OTHER": io.BytesIO(b"X")})


if __name__ == "__main__":
    unittest.main()
