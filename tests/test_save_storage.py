from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import save_storage

class SaveStorage(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name).resolve()
        self.source = self.root / "private/preview-fixture/memstick"
        save = self.source / "PSP/SAVEDATA/SYNTHETIC"
        save.mkdir(parents=True)
        (save / "DATA.BIN").write_bytes(b"synthetic tutorial progress")

    def test_paths_persist_across_launches_and_separate_languages(self):
        a = save_storage.memstick_path(self.root, "japanese")
        self.assertEqual(a, save_storage.memstick_path(self.root, "japanese"))
        self.assertNotEqual(a, save_storage.memstick_path(self.root, "english-v16"))

    def test_recovery_preserves_source_and_verified_backup(self):
        before = save_storage.tree_hashes(self.source)
        report = save_storage.recover(self.root, self.source, "japanese")
        self.assertEqual(save_storage.tree_hashes(self.source), before)
        self.assertEqual(save_storage.tree_hashes(Path(report["backup"])), before)
        self.assertEqual(save_storage.tree_hashes(Path(report["destination"])), before)

    def test_existing_saves_are_never_overwritten(self):
        destination = save_storage.memstick_path(self.root, "japanese")
        destination.mkdir(parents=True)
        (destination / "existing.bin").write_bytes(b"keep")
        with self.assertRaisesRegex(ValueError, "overwrite"):
            save_storage.recover(self.root, self.source, "japanese")
        self.assertEqual((destination / "existing.bin").read_bytes(), b"keep")

    def test_concurrent_writer_refused_and_lock_reusable(self):
        path = save_storage.memstick_path(self.root, "japanese")
        with save_storage.save_session(path):
            with self.assertRaisesRegex(RuntimeError, "Another preview"):
                with save_storage.save_session(path):
                    self.fail("Concurrent save writer accepted")
        with save_storage.save_session(path):
            pass

    def test_recovery_while_source_locked_excludes_runtime_lock(self):
        with save_storage.save_session(self.source):
            before = save_storage.tree_hashes(self.source)
            report = save_storage.recover(self.root, self.source, "english-text-test")
            self.assertEqual(save_storage.tree_hashes(self.source), before)
        for name in ("backup", "destination"):
            target = Path(report[name])
            self.assertFalse((target / ".preview.lock").exists())
            self.assertEqual(save_storage.tree_hashes(target), before)

    def test_automatic_backups_are_distinct_bounded_and_do_not_touch_saves(self):
        data=self.source/'PSP/SAVEDATA/SYNTHETIC/DATA.BIN'
        before=save_storage.tree_hashes(self.source)
        first=save_storage.snapshot_saves(self.root,'japanese',self.source,keep=3)
        self.assertEqual(first['status'],'created')
        self.assertEqual(save_storage.snapshot_saves(self.root,'japanese',self.source,keep=3)['status'],'unchanged')
        self.assertEqual(save_storage.tree_hashes(self.source),before)
        backups=Path(first['backup']).parent
        unrelated=backups/'keep-me.txt';unrelated.write_text('leave alone')
        for n in range(4):
            data.write_bytes(b'new progress '+bytes([n]))
            save_storage.snapshot_saves(self.root,'japanese',self.source,keep=3)
        self.assertEqual(len(list(backups.glob('*.zip'))),3)
        self.assertEqual(unrelated.read_text(),'leave alone')
        with zipfile.ZipFile(sorted(backups.glob('*.zip'),key=lambda p:p.stat().st_mtime_ns)[-1]) as archive:
            self.assertEqual(archive.read('SYNTHETIC/DATA.BIN'),data.read_bytes())
            self.assertNotIn('.preview.lock',archive.namelist())

    def test_empty_saves_do_not_create_backup_and_corruption_prevents_rotation(self):
        self.assertEqual(save_storage.snapshot_saves(self.root,'japanese')['status'],'no-saves')
        result=save_storage.snapshot_saves(self.root,'japanese',self.source)
        backup=Path(result['backup']);backup.write_bytes(b'corrupt')
        with self.assertRaises(zipfile.BadZipFile):
            save_storage.snapshot_saves(self.root,'japanese',self.source)
        self.assertEqual(backup.read_bytes(),b'corrupt')

if __name__ == "__main__":
    unittest.main()
