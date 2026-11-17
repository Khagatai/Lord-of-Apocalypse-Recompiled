import hashlib,json,sys,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import upscaler_dependency as tool


class PublicTextureToolIntake(unittest.TestCase):
    def fixture(self,root):
        archive=root/'publisher.zip'
        with zipfile.ZipFile(archive,'w') as z:z.writestr('tool.exe',b'public tool');z.writestr('demo.jpg',b'unneeded demo')
        pins=dict(archive_sha256=tool.sha(archive),files={'tool.exe':hashlib.sha256(b'public tool').hexdigest()})
        return archive,pins,root/'private/package'

    def test_wrong_archive_hash_creates_no_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);archive,pins,target=self.fixture(root);pins['archive_sha256']='0'*64
            with patch.object(tool,'ROOT',root),self.assertRaisesRegex(ValueError,'archive hash'):tool.install(archive,target,pins)
            self.assertFalse((root/'private').exists())

    def test_bad_member_is_not_promoted_and_scratch_is_removed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);archive,pins,target=self.fixture(root);pins['files']['tool.exe']='0'*64
            with patch.object(tool,'ROOT',root),self.assertRaisesRegex(ValueError,'member hash'):tool.install(archive,target,pins)
            self.assertFalse(target.exists());self.assertEqual(list(target.parent.iterdir()),[])

    def test_only_required_files_are_extracted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);archive,pins,target=self.fixture(root)
            with patch.object(tool,'ROOT',root):tool.install(archive,target,pins)
            self.assertEqual((target/'tool.exe').read_bytes(),b'public tool');self.assertFalse((target/'demo.jpg').exists())


if __name__=='__main__':unittest.main()
