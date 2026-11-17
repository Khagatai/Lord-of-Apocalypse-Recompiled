import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import translation_candidate
from test_intake import image


class TranslationCandidate(unittest.TestCase):
    def check(self, changed=False, wrong_hash=False):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            private = root / "private"
            private.mkdir()
            source = bytes(image())
            reference = private / "reference.iso"
            reference.write_bytes(source)
            data = bytearray(source)
            if changed:
                data[21 * 2048] ^= 1
            candidate = private / "candidate.iso"
            candidate.write_bytes(data)
            source_hash = hashlib.sha256(source).hexdigest()
            from iso_edits import survey,extent_hash
            with reference.open('rb') as stream:
                files={name:dict(size=row['size'],sha256=extent_hash(stream,row['lba']*2048,row['size'])) for name,row in survey.ISO(stream).files().items()}
            report = {"source_iso_sha256": source_hash, "all_file_payloads_verified": True,
                      "candidate_iso_size": len(data),
                      "candidate_iso_sha256": "0" * 64 if wrong_hash else hashlib.sha256(data).hexdigest()}
            report_path = private / "result.json"
            report_path.write_text(json.dumps(report))
            with patch.object(translation_candidate.title, "ROOT", root), \
                 patch.object(translation_candidate, "baseline_manifest", return_value=dict(source_iso_sha256=source_hash,files=files)):
                return translation_candidate.verify(candidate, report_path)

    def test_matching_candidate_admitted(self):
        digest, report_digest = self.check()
        self.assertEqual(len(digest), 64)
        self.assertEqual(len(report_digest), 64)

    def test_candidate_hash_mismatch_refused(self):
        with self.assertRaisesRegex(ValueError, "hash"):
            self.check(wrong_hash=True)

    def test_non_message_file_change_refused_even_with_matching_report(self):
        with self.assertRaisesRegex(ValueError, "non-message"):
            self.check(changed=True)


if __name__ == "__main__":
    unittest.main()
