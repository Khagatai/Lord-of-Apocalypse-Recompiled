"""Synthetic ISO/SFO fixtures only; no game payloads."""
import importlib.util
import io
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("survey", ROOT / "tools/survey-disc.py")
survey = importlib.util.module_from_spec(spec)
spec.loader.exec_module(survey)

def record(name, lba, size, directory=False):
    data = bytearray(33 + len(name) + (len(name) % 2 == 0))
    data[0] = len(data)
    struct.pack_into("<I", data, 2, lba)
    struct.pack_into(">I", data, 6, lba)
    struct.pack_into("<I", data, 10, size)
    struct.pack_into(">I", data, 14, size)
    data[25] = 2 if directory else 0
    data[32] = len(name)
    data[33:33 + len(name)] = name
    return data

def image(filename=b"TEST.ELF;1"):
    data = bytearray(24 * 2048)
    pvd = memoryview(data)[16 * 2048:17 * 2048]
    pvd[:7] = b"\x01CD001\x01"
    struct.pack_into("<H", pvd, 128, 2048)
    root = record(b"\0", 20, 2048, True)
    pvd[156:156 + len(root)] = root
    directory = root + record(b"\x01", 20, 2048, True) + record(filename, 21, 8)
    data[20 * 2048:20 * 2048 + len(directory)] = directory
    data[21 * 2048:21 * 2048 + 8] = b"fixture!"
    return data

class Intake(unittest.TestCase):
    def test_valid_iso_extent_and_content(self):
        iso = survey.ISO(io.BytesIO(image()))
        files = iso.files()
        self.assertEqual(set(files), {"TEST.ELF"})
        self.assertEqual(iso.read(files["TEST.ELF"]["lba"] * 2048, 8), b"fixture!")

    def test_endian_mismatch_rejected(self):
        data = record(b"X", 21, 8)
        data[6] ^= 1
        with self.assertRaisesRegex(ValueError, "endian"):
            survey.ISO.record(data)

    def test_multiextent_rejected(self):
        data = record(b"X", 21, 8)
        data[25] |= 0x80
        with self.assertRaisesRegex(ValueError, "multi-extent"):
            survey.ISO.record(data)

    def test_path_traversal_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unsafe"):
            survey.ISO(io.BytesIO(image(b"../escape"))).files()

    def test_read_outside_image_rejected(self):
        iso = survey.ISO(io.BytesIO(image()))
        with self.assertRaisesRegex(ValueError, "outside"):
            iso.read(24 * 2048 - 1, 2)

    def test_sfo_string_and_integer(self):
        keys = b"TITLE\0BOOTABLE\0"
        values = b"Synthetic\0" + struct.pack("<I", 1)
        entries = struct.pack("<HHIII", 0, 0x204, 10, 10, 0)
        entries += struct.pack("<HHIII", 6, 0x404, 4, 4, 10)
        data = struct.pack("<5I", 0x46535000, 0x101, 52, 52 + len(keys), 2) + entries + keys + values
        self.assertEqual(survey.sfo(data), {"TITLE": "Synthetic", "BOOTABLE": 1})

    def test_wrong_disc_rejected_before_content_parser(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "wrong.iso"
            path.write_bytes(b"not a game")
            with patch.object(sys, "argv", ["survey-disc.py", str(path)]), patch.object(survey, "ISO") as reader:
                with self.assertRaisesRegex(ValueError, "size mismatch"):
                    survey.main()
                reader.assert_not_called()

    def test_same_size_wrong_hash_rejected_before_content_parser(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "wrong.iso"
            path.write_bytes(b"synthetic")
            config = {"disc": {"iso_size": 9, "iso_sha1": "0" * 40, "iso_sha256": "0" * 64}}
            with patch.object(sys, "argv", ["survey-disc.py", str(path)]), patch.object(survey, "ISO") as reader:
                with patch.object(survey.tomllib, "loads", return_value=config):
                    with self.assertRaisesRegex(ValueError, "hash mismatch"):
                        survey.main()
                reader.assert_not_called()

if __name__ == "__main__":
    unittest.main()
