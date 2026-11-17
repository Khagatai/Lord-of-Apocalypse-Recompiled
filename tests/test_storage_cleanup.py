"""Synthetic cleanup guards: corrupt archives must never remove their sources."""
import hashlib,importlib.util,json,shutil,tempfile,unittest,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('storage_cleanup',ROOT/'tools/apply-storage-cleanup.py')
cleanup=importlib.util.module_from_spec(spec);spec.loader.exec_module(cleanup)
class CleanupTests(unittest.TestCase):
    def setUp(self):
        self.folder=Path(tempfile.mkdtemp(prefix='hd-cleanup-selftest-',dir=ROOT/'private')).resolve()
        self.assertEqual(self.folder.parent,(ROOT/'private').resolve())
        self.previous_archives=cleanup.ARCHIVES;cleanup.ARCHIVES=self.folder/'archives';cleanup.ARCHIVES.mkdir()
    def tearDown(self):
        cleanup.ARCHIVES=self.previous_archives
        if self.folder.resolve().parent!=(ROOT/'private').resolve() or not self.folder.name.startswith('hd-cleanup-selftest-'):raise ValueError('Unsafe synthetic cleanup path.')
        shutil.rmtree(self.folder)
    def frame(self):
        path=self.folder/'synthetic.ppm';data=b'Only synthetic lossless archive test bytes.\n'*100
        path.write_bytes(data);row=dict(path=path.relative_to(ROOT).as_posix(),bytes=len(data),mtime_ns=path.stat().st_mtime_ns)
        return path,data,row
    def test_refuse_path_escape_and_active_data(self):
        for value in ('../game.iso','private/hd-test/../../settings/file','private/hd-test/file:stream','C:/game.iso'):
            with self.assertRaises(ValueError):cleanup.safe_path(value)
        for value,kind in [('private/native-release/lordofapocalypse/lordofapocalypse.exe','delete'),('private/memstick/save.ppm','archive'),(cleanup.RECOVERY,'delete')]:
            with self.assertRaises(ValueError):cleanup.validate_row(dict(path=value,bytes=1,mtime_ns=0),kind)
    def test_lossless_archive_verified_before_source_removal(self):
        path,data,row=self.frame();result=cleanup.apply_group(self.folder.name,[row],'synthetic-proposal')
        self.assertTrue(result['verified']);self.assertFalse(path.exists())
        archive=ROOT/result['path'];manifest=cleanup.verify_archive(archive,[row],'synthetic-proposal')
        self.assertEqual(manifest['files'][0]['sha256'],hashlib.sha256(data).hexdigest())
        with zipfile.ZipFile(archive) as stream:self.assertEqual(stream.read(row['path']),data)
    def test_corrupt_archive_keeps_source(self):
        path,data,row=self.frame();archive=cleanup.ARCHIVES/(self.folder.name+'.zip')
        manifest=dict(proposal_sha256='synthetic-proposal',files=[dict(row,sha256='0'*64)])
        with zipfile.ZipFile(archive,'w') as stream:stream.writestr(row['path'],data);stream.writestr('MANIFEST.json',json.dumps(manifest))
        with self.assertRaises(ValueError):cleanup.apply_group(self.folder.name,[row],'synthetic-proposal')
        self.assertEqual(path.read_bytes(),data)
    def test_changed_candidate_is_not_removed(self):
        path,data,row=self.frame();path.write_bytes(data+b'new data')
        with self.assertRaises(ValueError):cleanup.apply_group(self.folder.name,[row],'synthetic-proposal')
        self.assertTrue(path.exists())
if __name__=='__main__':unittest.main()
