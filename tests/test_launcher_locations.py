import contextlib,hashlib,io,json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import launcher_locations as locations

class LauncherLocations(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.folder=Path(temporary.name);self.host=self.folder/'launcher';self.host.mkdir()
        self.game=self.folder/'game files';self.make_game(self.game)
        self.iso=self.folder/'日本語 dump.iso';self.iso.write_bytes(b'identified synthetic disc')
        self.expected=dict(size=self.iso.stat().st_size,sha256=hashlib.sha256(self.iso.read_bytes()).hexdigest())

    def make_game(self,root):
        for name in ('tools/launch-preview.py','tools/launcher_settings.py','config/controller-camera.json','private/tools/python314/python.exe'):
            path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('fixture')
        (root/'config/lordofapocalypse.toml').write_text('[disc]\nid="NPJH50503"\n')

    def test_iso_selection_validates_and_preserves_existing_generated_files(self):
        keep=self.game/'private/hd-remaster-pack/checkpoint.png';keep.parent.mkdir();keep.write_bytes(b'local checkpoint fixture')
        before=(keep.read_bytes(),keep.stat().st_mtime_ns)
        locations.select_iso(self.iso,self.game,self.expected)
        self.assertEqual(locations.iso_path(self.game),str(self.iso.resolve()))
        self.assertEqual((keep.read_bytes(),keep.stat().st_mtime_ns),before)

    def test_wrong_or_missing_iso_keeps_previous_selection(self):
        locations.select_iso(self.iso,self.game,self.expected)
        state=self.game/'private/distribution/local-image.json';before=state.read_bytes()
        wrong=self.folder/'wrong.iso';wrong.write_bytes(b'x'*self.expected['size'])
        with self.assertRaisesRegex(ValueError,'SHA256'):locations.select_iso(wrong,self.game,self.expected)
        with self.assertRaises(OSError):locations.select_iso(self.folder/'missing.iso',self.game,self.expected)
        self.assertEqual(state.read_bytes(),before)

    def test_select_existing_game_folder_changes_only_host_pointer(self):
        save=self.game/'private/memstick/save';save.parent.mkdir();save.write_bytes(b'player progress fixture')
        before={p.relative_to(self.game):p.read_bytes() for p in self.game.rglob('*') if p.is_file()}
        locations.select_game_directory(self.game,self.host)
        self.assertEqual(locations.game_directory(self.host),self.game.resolve())
        after={p.relative_to(self.game):p.read_bytes() for p in self.game.rglob('*') if p.is_file() and p.name!='session.lock'}
        self.assertEqual(before,after)
        self.assertFalse((self.host/'private/memstick').exists())

    def test_invalid_folder_keeps_selected_game(self):
        locations.select_game_directory(self.game,self.host)
        wrong=self.folder/'another game';self.make_game(wrong)
        (wrong/'config/lordofapocalypse.toml').write_text('[disc]\nid="WRONG"\n')
        for folder in (wrong,self.host,self.folder/'missing'):
            with self.assertRaises((OSError,ValueError)):locations.select_game_directory(folder,self.host)
        self.assertEqual(locations.game_directory(self.host),self.game.resolve())

    def test_missing_selected_folder_is_reported_without_fallback_or_overwrite(self):
        locations.select_game_directory(self.game,self.host)
        for file in self.game.rglob('*.py'):file.unlink()
        with self.assertRaisesRegex(ValueError,'Missing'):locations.dispatch('launch',[],self.host)
        self.assertEqual(locations.game_directory(self.host),self.game.resolve())

    def test_settings_and_game_dispatch_use_selected_folder_without_shell(self):
        locations.select_game_directory(self.game,self.host)
        with patch.object(locations.subprocess,'call',return_value=0) as call:
            locations.dispatch('settings',['--read','--include-build'],self.host)
            args,kwargs=call.call_args
            self.assertEqual(Path(args[0][0]),self.game/'private/tools/python314/python.exe')
            self.assertEqual(Path(args[0][2]),self.game/'tools/launcher_settings.py')
            self.assertEqual(kwargs,dict(cwd=self.game.resolve()))
            locations.dispatch('launch',['--check-cached'],self.host)
            self.assertEqual(call.call_args.args[0][-3:],['--variant','saved','--check-cached'])
            (self.game/'private/distribution').mkdir();(self.game/'private/distribution/release.json').write_text('{}')
            locations.dispatch('launch',['--graphics-preset','original'],self.host)
            self.assertEqual(Path(call.call_args.args[0][2]),self.game/'tools/tester-start.py')

    def test_locations_packet_uses_selected_iso_and_game(self):
        locations.select_game_directory(self.game,self.host);locations.select_iso(self.iso,self.game,self.expected)
        stream=io.StringIO()
        with contextlib.redirect_stdout(stream):locations.emit(self.host,'saved')
        self.assertEqual(stream.getvalue().splitlines(),['LOA_LOCATIONS 1',str(self.game.resolve()),str(self.iso.resolve()),'saved'])

    @unittest.skipUnless(os.name=='nt','Windows file-sharing lock')
    def test_second_launcher_cannot_use_selected_installation(self):
        with locations.target_session(self.game,self.host):
            with self.assertRaisesRegex(OSError,'in use'):locations.select_game_directory(self.game,self.host)
        self.assertFalse((self.host/'private/launcher/locations.json').exists())
        locations.select_game_directory(self.game,self.host)

    def test_cancelled_picker_does_not_change_locations(self):
        with patch.object(locations,'choose',return_value=None),patch.object(locations,'emit') as emit:
            self.assertEqual(locations.main(['iso']),0)
            self.assertIn('cancelled',emit.call_args.kwargs['message'])
        self.assertFalse((self.game/'private/distribution/local-image.json').exists())

if __name__=='__main__':unittest.main()
