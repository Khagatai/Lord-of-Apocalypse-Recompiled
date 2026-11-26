import json,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import controller_settings as controls,title

class ControllerSettings(unittest.TestCase):
    def test_smooth_profile_preserves_bindings_for_contextual_target_switching(self):
        codes=controls.defaults();codes[-2]=1
        smooth=controls.profile(codes)
        rows={r['control']:r for r in smooth['psp_bindings']}
        for direction in ('up','down','left','right'):
            self.assertEqual(rows[direction]['primary'],'dpad_'+direction)
            self.assertEqual(rows[direction]['secondary'],dict(up='-righty@12000',down='+righty@12000',left='-rightx@12000',right='+rightx@12000')[direction])
        original=controls.profile(controls.defaults())
        self.assertEqual(smooth['navigation_bindings'],original['navigation_bindings'])
        self.assertEqual(smooth['calibration'],original['calibration'])
        codes=controls.assign(codes,0,17)
        self.assertEqual(next(r for r in controls.profile(codes)['psp_bindings'] if r['control']=='cross')['primary'],'-righty@12000')
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.root=Path(tmp.name)
        self.preferences=self.root/'controller.json';self.profile_path=self.root/'profile.json'
    def test_defaults_preserve_psp_mapping_and_host_menu(self):
        base=json.loads((ROOT/'config/controller-camera.json').read_text())
        profile=controls.profile(controls.defaults())
        self.assertEqual(profile['navigation_bindings'],base['navigation_bindings'])
        self.assertEqual(profile['calibration'],base['calibration'])
        for row in profile['psp_bindings']:
            old=next(r for r in base['psp_bindings'] if r['control']==row['control'])
            self.assertEqual(row['primary'],old['primary'])
            self.assertEqual(row.get('secondary','none'),old.get('secondary','none'))
        self.assertNotIn('guide',controls.SOURCES)
    def test_invalid_data_never_overwrites_existing_profile(self):
        controls.save(controls.defaults(),self.preferences,self.profile_path)
        before=self.preferences.read_bytes(),self.profile_path.read_bytes()
        for bad in ([],[0]*23,[True]*24,[21]*24,[-1]*24):
            with self.assertRaises(ValueError):controls.save(bad,self.preferences,self.profile_path)
        self.assertEqual((self.preferences.read_bytes(),self.profile_path.read_bytes()),before)
    def test_custom_bindings_survive_reload_and_restore_defaults(self):
        codes=controls.assign(controls.defaults(),0,controls.SOURCES.index('right_shoulder'))
        controls.save(codes,self.preferences,self.profile_path,expected='missing')
        self.assertEqual(controls.load(self.preferences),codes)
        saved=json.loads(self.profile_path.read_text())
        self.assertEqual(next(r for r in saved['psp_bindings'] if r['control']=='cross')['primary'],'right_shoulder')
        with self.assertRaisesRegex(ValueError,'changed elsewhere'):controls.save(controls.defaults(),self.preferences,self.profile_path,expected='missing')
        self.assertEqual(controls.load(self.preferences),codes)
        controls.save(controls.defaults(),self.preferences,self.profile_path)
        self.assertEqual(controls.load(self.preferences),controls.defaults())
    def test_assignment_releases_previous_owner_and_rejects_conflicts(self):
        original=controls.defaults();moved=controls.assign(original,0,2)
        self.assertEqual(moved[0],2);self.assertEqual(moved[2],0)
        self.assertEqual(original,controls.defaults())
        duplicate=controls.defaults();duplicate[0]=2
        self.assertEqual(controls.edited_codes(original,duplicate),moved)
        with self.assertRaises(ValueError):controls.save(duplicate,self.preferences,self.profile_path)
        self.assertFalse(self.preferences.exists())
        self.assertEqual(controls.assign(moved,0,0)[0],0)
    def test_legacy_bindings_and_camera_preferences(self):
        self.preferences.write_text(json.dumps(dict(schema=1,codes=controls.defaults()[:24])))
        self.assertEqual(controls.load(self.preferences),controls.defaults())
        selected=controls.defaults();selected[-2:]=[1,4]
        controls.save(selected,self.preferences,self.profile_path)
        env=controls.Bridge(self.root,self.preferences,self.profile_path).environment()
        self.assertEqual(env['LOA_CAMERA_MODE'],'smooth');self.assertEqual(env['LOA_CAMERA_SPEED'],'4')
        for values in ([2,0],[0,5],[True,2]):
            invalid=selected[:24]+values
            with self.assertRaises(ValueError):controls.save(invalid,self.preferences,self.profile_path)
        self.assertEqual(controls.load(self.preferences),selected)
    def test_supervisor_acknowledges_only_valid_requests_and_ignores_stale_ones(self):
        bridge=controls.Bridge(self.root,self.preferences,self.profile_path);env=bridge.environment()
        self.assertEqual(Path(env['NK_INPUT_PROFILE']),self.profile_path)
        codes=controls.assign(controls.defaults(),0,controls.SOURCES.index('north'))
        request=self.root/'controller-request.json'
        request.write_text(json.dumps(dict(sequence=1,codes=codes)));bridge.poll()
        self.assertEqual(json.loads((self.root/'controller-ack.json').read_text()),dict(sequence=1,ok=True))
        self.assertEqual(controls.load(self.preferences),codes)
        request.write_text(json.dumps(dict(sequence=1,codes=controls.defaults())));bridge.poll()
        self.assertEqual(controls.load(self.preferences),codes)
        request.write_text(json.dumps(dict(sequence=2,codes=[100]*24)));bridge.poll()
        self.assertEqual(json.loads((self.root/'controller-ack.json').read_text()),dict(sequence=2,ok=False))
        self.assertEqual(controls.load(self.preferences),codes)
    @unittest.skipUnless(sys.platform=='win32','Windows native input parser')
    def test_custom_profile_uses_real_native_parser_and_keeps_navigation(self):
        compiler=title.SDK/'bin/gcc.exe'
        if not compiler.exists():self.skipTest('Bundled compiler unavailable')
        codes=[0]*controls.COUNT;codes[0]=controls.SOURCES.index('right_shoulder')
        controls.save(codes,self.preferences,self.profile_path)
        reassigned=self.root/'reassigned.json';reassigned.write_text(json.dumps(controls.profile(controls.assign(controls.defaults(),0,10))))
        smooth=self.root/'smooth.json';smooth_codes=controls.defaults();smooth_codes[-2]=1;smooth.write_text(json.dumps(controls.profile(smooth_codes)))
        c=self.root/'check.c';exe=self.root/'check.exe'
        c.write_text('''#include "nk_input_profile.h"
#include "controller-settings-contract.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static int free_camera;
int loa_camera_free_input(void){return free_camera;}
int main(int argc,char **argv){
 NkInputProfile p;char diag[512];assert(argc==4);
 assert(nk_input_profile_load(&p,argv[1],diag,sizeof diag)==NK_OK);
 bool buttons[NK_HOST_BUTTON_COUNT]={0};int16_t axes[NK_HOST_AXIS_COUNT]={0};
 buttons[NK_HOST_BUTTON_RIGHT_SHOULDER]=true;
 assert(nk_input_profile_eval_buttons(&p,buttons,axes)==nk_psp_button_bitmask(NK_PSP_BTN_CROSS));
 buttons[NK_HOST_BUTTON_RIGHT_SHOULDER]=false;buttons[NK_HOST_BUTTON_SOUTH]=true;
 assert(nk_input_profile_eval_buttons(&p,buttons,axes)==0);
 assert(nk_input_profile_eval_navigation(&p,buttons,axes)!=0);
 assert(nk_input_profile_load(&p,argv[2],diag,sizeof diag)==NK_OK);
 buttons[NK_HOST_BUTTON_SOUTH]=false;buttons[NK_HOST_BUTTON_RIGHT_SHOULDER]=true;
 assert(nk_input_profile_eval_buttons(&p,buttons,axes)==nk_psp_button_bitmask(NK_PSP_BTN_CROSS));
 assert(nk_input_profile_load(&p,argv[3],diag,sizeof diag)==NK_OK);
 buttons[NK_HOST_BUTTON_RIGHT_SHOULDER]=false;
 axes[NK_HOST_AXIS_RIGHTX]=32767;axes[NK_HOST_AXIS_RIGHTY]=-32768;
 /* Locked-on, original PSP, and inactive cameras use the real mapping. */
 assert(nk_input_profile_eval_buttons(&p,buttons,axes)==(NK_PSP_BTN_RIGHT_BIT|NK_PSP_BTN_UP_BIT));
 NkInputProfile before=p;
 free_camera=1;
 assert(nk_input_profile_eval_buttons(&p,buttons,axes)==0);
 buttons[NK_HOST_BUTTON_DPAD_UP]=true;
 assert(nk_input_profile_eval_buttons(&p,buttons,axes)==NK_PSP_BTN_UP_BIT);
 assert(nk_input_profile_eval_navigation(&p,buttons,axes)!=0);
 assert(memcmp(&p,&before,sizeof p)==0); /* Filtering never changes saved bindings. */
 buttons[NK_HOST_BUTTON_DPAD_UP]=false;
 axes[NK_HOST_AXIS_RIGHTX]=-32768;axes[NK_HOST_AXIS_RIGHTY]=32767;
 assert(nk_input_profile_eval_buttons(&p,buttons,axes)==0);
 buttons[NK_HOST_BUTTON_DPAD_LEFT]=true;
 assert(nk_input_profile_eval_buttons(&p,buttons,axes)==NK_PSP_BTN_LEFT_BIT);
 free_camera=0;
 assert(nk_input_profile_eval_buttons(&p,buttons,axes)==(NK_PSP_BTN_LEFT_BIT|NK_PSP_BTN_DOWN_BIT));
 /* An axis explicitly reassigned to a different PSP action still works. */
 p.psp_buttons[NK_PSP_BTN_CROSS].primary=p.psp_buttons[NK_PSP_BTN_LEFT].secondary;
 p.psp_buttons[NK_PSP_BTN_LEFT].secondary.type=NK_BINDING_NONE;
 free_camera=1;
 assert(nk_input_profile_eval_buttons(&p,buttons,axes)==(NK_PSP_BTN_LEFT_BIT|NK_PSP_BTN_CROSS_BIT));
 for(int i=0;i<LOA_CONTROL_CODES;i++)printf("%d ",loa_control_defaults[i]);
 puts("");for(int i=0;i<LOA_CONTROL_SOURCES;i++)puts(loa_control_sources[i]);
 return 0;
}''')
        core=title.FRAMEWORK/'src/core'
        result=subprocess.run([str(compiler),'-O2','-ffunction-sections','-fdata-sections','-I'+str(core),'-I'+str(ROOT/'tools'),str(c),
            str(ROOT/'tools/camera_input.c'),str(core/'nk_input_profile.c'),str(core/'nk_json.c'),str(core/'nk_platform_win32.c'),str(core/'nk_shared_helpers.c'),
            '-o',str(exe),'-lshell32','-lole32','-luuid','-luser32','-ladvapi32','-lshlwapi','-Wl,--gc-sections','-Wl,--wrap=nk_input_profile_eval_buttons'],env=title.environment(),capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        run=subprocess.run([str(exe),str(self.profile_path),str(reassigned),str(smooth)],env=title.environment(),capture_output=True,text=True)
        self.assertEqual(run.returncode,0,run.stdout+run.stderr)
        rows=run.stdout.splitlines();self.assertEqual(list(map(int,rows[0].split())),controls.defaults())
        self.assertEqual(rows[1:],list(controls.SOURCE_LABELS))

if __name__=='__main__':unittest.main()
