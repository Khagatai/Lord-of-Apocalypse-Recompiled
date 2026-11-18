import json,os,subprocess,sys,tempfile,threading,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import graphics_settings as settings
import launcher_settings
import setup_resources
import title

class SharedLauncherSettings(unittest.TestCase):
    def test_in_game_graphics_save_preserves_the_launcher_build_choices(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'graphics.json'
            build=setup_resources.from_codes((12,3,2))
            settings.save(settings.DEFAULTS,path,setup=build)
            settings.save(dict(settings.DEFAULTS,gameplay_fps=60),path)
            graphics,stored=settings.read_preferences(path)
            self.assertEqual(stored,dict(compiler_jobs=12,memory_gib=8,hd_profile='fast'))
            self.assertEqual(graphics['gameplay_fps'],60)
            self.assertNotIn('setup',graphics)

    def test_removed_v16_profile_migrates_to_wip_without_changing_other_choices(self):
        self.assertEqual(settings.OPTIONS['variant'],('english-text-test','japanese'))
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'graphics.json';legacy=dict(settings.DEFAULTS,variant='english-v16',gameplay_fps=60)
            path.write_text(json.dumps(dict(schema=1,**legacy)));original=path.read_bytes()
            loaded=settings.load(path);self.assertEqual(loaded,dict(legacy,variant='english-text-test'));self.assertEqual(path.read_bytes(),original)
    def test_opening_settings_does_not_create_or_rewrite_preferences(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'graphics.json';value,token=launcher_settings.snapshot(path)
            self.assertEqual(value,settings.DEFAULTS);self.assertEqual(token,'missing');self.assertFalse(path.exists())
            settings.save(dict(value,gameplay_fps=60),path);before=path.read_bytes()
            loaded,token=launcher_settings.snapshot(path)
            self.assertEqual(loaded['gameplay_fps'],60);self.assertEqual(token,settings.fingerprint(path));self.assertEqual(path.read_bytes(),before)

    def test_stale_launcher_cannot_overwrite_a_new_in_game_choice(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'graphics.json';settings.save(settings.DEFAULTS,path)
            value,token=launcher_settings.snapshot(path)
            in_game=dict(value,gameplay_fps=60);settings.save(in_game,path)
            with self.assertRaisesRegex(ValueError,'changed elsewhere'):settings.save(dict(value,render_scale=1),path,expected=token)
            self.assertEqual(settings.load(path),in_game)

    @unittest.skipUnless(os.name=='nt','Windows preference mutex')
    def test_two_competing_launchers_cannot_both_save_the_same_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'graphics.json';settings.save(settings.DEFAULTS,path);token=settings.fingerprint(path)
            start=threading.Barrier(2);results=[]
            def write(scale):
                start.wait()
                try:settings.save(dict(settings.DEFAULTS,render_scale=scale),path,expected=token);results.append('saved')
                except ValueError:results.append('conflict')
            threads=[threading.Thread(target=write,args=(n,)) for n in (1,2)]
            for thread in threads:thread.start()
            for thread in threads:thread.join(timeout=10);self.assertFalse(thread.is_alive())
            self.assertCountEqual(results,['saved','conflict'])

    def test_control_reference_uses_the_actual_profile(self):
        profile=json.loads((ROOT/'config/controller-camera.json').read_text())
        text=launcher_settings.controls_reference(profile);self.assertIn('Right stick + D-pad',text);self.assertIn('A / B',text)
        for binding in profile['psp_bindings']:
            if binding['control']=='cross':binding['primary']='north'
        self.assertIn('Y / B',launcher_settings.controls_reference(profile))

    def test_native_launcher_and_f1_presets_match_python_for_all_sample_profiles(self):
        compiler=title.SDK/'bin/gcc.exe'
        if sys.platform!='win32' or not compiler.is_file():self.skipTest('Windows compiler unavailable')
        with tempfile.TemporaryDirectory() as tmp:
            exe=Path(tmp)/'contract.exe'
            result=subprocess.run([str(compiler),'-std=c11',str(ROOT/'tests/settings_contract.c'),'-o',str(exe)],env=title.environment(),capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            rows=subprocess.check_output([str(exe)],text=True).splitlines()
        lengths=[len(v) for v in settings.OPTIONS.values()];self.assertEqual(list(map(int,rows[0].split())),lengths)
        offset=1
        for sample in range(24):
            codes=[(sample+i)%length for i,length in enumerate(lengths)];profile=settings.from_menu(codes)
            for preset in ('original','balanced','quality'):
                self.assertEqual(list(map(int,rows[offset].split())),settings.menu_codes(settings.apply_preset(profile,preset)),(sample,preset));offset+=1
