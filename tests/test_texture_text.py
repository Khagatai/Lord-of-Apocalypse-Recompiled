from pathlib import Path
import struct
import tempfile
import unittest

from test_xet_codec import fixture
from texture_text import digest, reconstruct, verify
from xet_codec import Xet


class TextureTextTests(unittest.TestCase):
    def setup_record(self, root):
        raw = fixture()
        struct.pack_into('<H', raw, 252, 5)
        struct.pack_into('<3H', raw, 240, 16, 8, 16)
        source = bytes(raw)
        pixels = bytearray(Xet.parse(source).preview(0)[2])
        pixels[:4] = bytes((0, 255, 0, 255))
        path = root/'pixels.rgba'
        path.write_bytes(pixels)
        record = {'resource_id': '00020001', 'source_sha256': digest(source),
                  'edits': [{'rgba_path': str(path), 'rgba_sha256': digest(pixels),
                             'texture_index': 0, 'regions': [(0, 0, 1, 1)]}]}
        return source, record

    def test_reconstruction_and_metadata_tamper_rejection(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source, record = self.setup_record(root)
            target = reconstruct(source, record, root)
            record['target_sha256'] = digest(target)
            verify(source, target, record, root)
            forged = bytearray(target)
            forged[276] ^= 1
            record['target_sha256'] = digest(forged)
            with self.assertRaisesRegex(ValueError, 'approved text regions'):
                verify(source, bytes(forged), record, root)

    def test_stale_pixels_and_non_texture_kinds_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source, record = self.setup_record(root)
            record['resource_id'] = '00080001'
            with self.assertRaisesRegex(ValueError, 'Only XET'):
                reconstruct(source, record, root)
            record['resource_id'] = '00020001'
            Path(record['edits'][0]['rgba_path']).write_bytes(b'stale')
            with self.assertRaisesRegex(ValueError, 'reviewed hash'):
                reconstruct(source, record, root)


if __name__ == '__main__':
    unittest.main()
