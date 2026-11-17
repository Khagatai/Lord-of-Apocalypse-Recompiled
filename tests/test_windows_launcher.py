import importlib.util,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import title
class WindowsLauncher(unittest.TestCase):
    @unittest.skipUnless(sys.platform=='win32','Windows native path preflight')
    def test_native_path_error_precedes_unreadable_game_start(self):
        spec=importlib.util.spec_from_file_location('launch_preview',ROOT/'tools/launch-preview.py')
        preview=importlib.util.module_from_spec(spec);spec.loader.exec_module(preview)
        preview.verify_native_location(Path('C:/Games/LoA'),Path('C:/Games/dump.iso'))
        with self.assertRaisesRegex(ValueError,'Move the entire extracted folder'):
            preview.verify_native_location(Path('C:/Games/LoA Ω'))
        with self.assertRaisesRegex(ValueError,'direct Japanese play'):
            preview.verify_native_location(Path('C:/Games/LoA'),Path('C:/Games/日本語.iso'))
    def test_arguments_are_windows_quoted_without_a_shell(self):
        compiler=title.SDK/'bin/gcc.exe'
        if sys.platform!='win32' or not compiler.is_file():self.skipTest('Local Windows compiler unavailable')
        with tempfile.TemporaryDirectory() as tmp:
            exe=Path(tmp)/'launcher-quote-test.exe'
            result=subprocess.run([str(compiler),'-std=c11','-O2','-municode',str(ROOT/'tests/test_windows_launcher.c'),'-o',str(exe),'-lshell32','-lgdi32','-luser32'],env=title.environment(),capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            run=subprocess.run([str(exe)],capture_output=True,text=True,timeout=10)
            self.assertEqual(run.returncode,0,run.stderr);self.assertIn('round trip',run.stdout)
