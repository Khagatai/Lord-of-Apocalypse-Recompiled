import importlib.util,json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import title
import launcher_settings
spec=importlib.util.spec_from_file_location('preview_controller_test',ROOT/'tools/launch-preview.py')
preview=importlib.util.module_from_spec(spec);spec.loader.exec_module(preview)

class ControllerConfiguration(unittest.TestCase):
    def test_sony_drivers_default_on_before_sdl_starts(self):
        env={};result=preview.configure_controller_environment(env)
        self.assertEqual(result,{key:'1' for key in (preview.CONTROLLER_HIDAPI,*preview.PLAYSTATION_HIDAPI)})
        self.assertEqual(env,result)

    def test_explicit_overrides_are_preserved(self):
        env={preview.CONTROLLER_HIDAPI:'0','SDL_JOYSTICK_HIDAPI_PS5':'1','unrelated':'keep'}
        result=preview.configure_controller_environment(env)
        self.assertEqual(result['SDL_JOYSTICK_HIDAPI_PS4'],'0')
        self.assertEqual(result['SDL_JOYSTICK_HIDAPI_PS5'],'1')
        self.assertEqual(env['unrelated'],'keep')

    def test_launcher_explains_both_layouts_from_the_profile(self):
        profile=json.loads((ROOT/'config/controller-camera.json').read_text())
        text=launcher_settings.controls_reference(profile)
        for label in ('PLAYSTATION / XBOX','Cross/A','Circle/B','Square/X','Triangle/Y','L1/LB','R1/RB','Options/Menu','Create/View'):
            self.assertIn(label,text)
        self.assertIn('Right stick + D-pad',text)
        self.assertLessEqual(len(text.splitlines()),10)  # Existing launcher panel height.

@unittest.skipUnless(os.name=='nt','Windows SDL runtime')
class NativeGamepads(unittest.TestCase):
    def test_sony_and_xbox_virtual_devices_through_real_sdl_and_profile(self):
        gcc=title.SDK/'bin/gcc.exe'
        if not gcc.is_file():self.skipTest('Bundled compiler unavailable')
        core=title.FRAMEWORK/'src/core'
        with tempfile.TemporaryDirectory(prefix='sony-input-',dir=ROOT/'private') as folder:
            exe=Path(folder)/'gamepads.exe'
            command=[str(gcc),'-O2','-ffunction-sections','-fdata-sections','-I'+str(core),'-I'+str(title.SDK/'include'),
                str(ROOT/'tests/test_playstation_gamepad.c'),str(core/'nk_input_profile.c'),str(core/'nk_json.c'),
                str(core/'nk_shared_helpers.c'),str(core/'nk_platform_win32.c'),'-L'+str(title.SDK/'lib'),'-lSDL3',
                '-lshell32','-lole32','-luuid','-luser32','-ladvapi32','-lshlwapi','-Wl,--gc-sections','-o',str(exe)]
            build=subprocess.run(command,env=title.environment(),capture_output=True,text=True,timeout=90)
            self.assertEqual(build.returncode,0,build.stderr)
            env=title.environment();preview.configure_controller_environment(env)
            run=subprocess.run([str(exe),str(ROOT/'config/controller-camera.json')],env=env,capture_output=True,text=True,timeout=30)
            self.assertEqual(run.returncode,0,run.stdout+run.stderr)
            self.assertIn('PASS: DualSense',run.stdout);self.assertIn('PASS: DualShock 4',run.stdout);self.assertIn('PASS: Xbox',run.stdout)
            print(run.stdout,end='')

if __name__=='__main__':unittest.main()
