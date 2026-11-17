from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import mip_preview
import save_storage


class IsolatedMipPreview(unittest.TestCase):
    def test_private_save_copy_preserves_source_and_never_reseeds_existing_progress(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(mip_preview,'ROOT',Path(folder)):
            root=Path(folder);source=root/'private/normal';target=root/'private/preview'
            source.mkdir(parents=True);(source/'save.dat').write_bytes(b'synthetic source save')
            before=save_storage.tree_hashes(source)
            mip_preview.seed_saves(source,target)
            self.assertEqual(save_storage.tree_hashes(target),before)
            (target/'save.dat').write_bytes(b'independent preview progress')
            mip_preview.seed_saves(source,target)
            self.assertEqual((target/'save.dat').read_bytes(),b'independent preview progress')
            self.assertEqual(save_storage.tree_hashes(source),before)

    def test_evidence_and_save_paths_cannot_leave_private(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(mip_preview,'ROOT',Path(folder)):
            with self.assertRaisesRegex(ValueError,'under private'):
                mip_preview.private_path(Path(folder)/'outside.json')
