import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import title

class DiscVariants(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "synthetic.iso"
        self.original, self.english = b"JPN!", b"ENG!"
        self.config = {"disc": {"iso_size": 4, "iso_sha256": hashlib.sha256(self.original).hexdigest()},
                       "translations": {"english_v16": {"size": 4, "sha256": hashlib.sha256(self.english).hexdigest()}}}

    def test_japanese_default_stays_exact(self):
        self.path.write_bytes(self.original)
        with patch.object(title, "CONFIG", self.config):
            self.assertEqual(title.verify_disc_image(self.path), self.config["disc"]["iso_sha256"])

    def test_english_requires_explicit_identity(self):
        self.path.write_bytes(self.english)
        with patch.object(title, "CONFIG", self.config):
            with self.assertRaisesRegex(ValueError, "hash"):
                title.verify_disc_image(self.path)
            self.assertEqual(title.verify_disc_image(self.path, "english-v16"),
                             self.config["translations"]["english_v16"]["sha256"])

    def test_same_size_unrecognized_variant_refused(self):
        self.path.write_bytes(b"BAD!")
        with patch.object(title, "CONFIG", self.config):
            for language in ("japanese", "english-v16"):
                with self.assertRaisesRegex(ValueError, "hash"):
                    title.verify_disc_image(self.path, language)

if __name__ == "__main__":
    unittest.main()
