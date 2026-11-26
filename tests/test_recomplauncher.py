import contextlib,importlib.util,io,json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import recomplauncher as integration,graphics_settings as graphics,title,disc_images

class RecompLauncher(unittest.TestCase):
    def test_manifest_defaults_and_every_choice_use_the_real_settings_contract(self):
        m=json.loads((ROOT/'recomplauncher.json').read_text())
        defaults={key:json.loads(value) for key,value in m['config'][0]['new'].items()}
        self.assertEqual(graphics.validate(defaults),graphics.DEFAULTS)
        self.assertEqual({s['id'] for s in m['settings']},set(graphics.OPTIONS))
        for row in m['settings']:
            observed=[]
            for choice in row['choices']:
                changed={key:json.loads(value) for key,value in choice['set'].items()}
                self.assertEqual(set(changed),{row['id']})
                graphics.validate(dict(defaults,**changed));observed.append(changed[row['id']])
            expected=[list(v) if isinstance(v,tuple) else v for v in graphics.OPTIONS[row['id']]]
            self.assertEqual(observed,expected)
        self.assertEqual(m['start']['program'],m['prepare']['program'])
        self.assertEqual(m['start']['program'],['LordOfApocalypse.exe'])
        self.assertFalse(m['prepare']['options'][0]['default'])
        self.assertTrue(all(path.endswith(('/DATA.BIN','/PARAM.SFO')) for path in m['saves']))
        self.assertNotIn('check',m['inputs'][0]) # PSP IDs are not yet read by upstream's fast check.

    def test_progress_is_monotonic_and_never_claims_process_success_early(self):
        p=integration.Progress()
        self.assertIn('0.650',p.line('LOA_SETUP_PROGRESS 3 2 2 650\n'))
        self.assertIn('0.650',p.line('LOA_SETUP_PROGRESS 1 0 0 10\n'))
        self.assertIn('0.990',p.line('LOA_SETUP_PROGRESS 12 1 1 1000\n'))
        for invalid in ('LOA_SETUP_PROGRESS 99 0 0 0','LOA_SETUP_PROGRESS 0 2 1 0','LOA_SETUP_PROGRESS 0 0 0 1001','other'):
            self.assertIsNone(p.line(invalid))

    def test_supervision_preserves_errors_and_does_not_print_success_for_a_failed_stage(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(integration,'ROOT',Path(tmp)):
            output=io.StringIO()
            command=[sys.executable,'-c','import sys;print("LOA_SETUP_PROGRESS 3 1 2 400");print("a real failure",file=sys.stderr);sys.exit(9)']
            with contextlib.redirect_stdout(output):code=integration.run(command,prepare=True)
            self.assertEqual(code,9);self.assertIn('progress 0.400',output.getvalue())
            self.assertIn('a real failure',output.getvalue());self.assertNotIn('progress 1 ',output.getvalue())
            logs=list((Path(tmp)/'private/recomplauncher/logs').glob('run-*.log'))
            self.assertEqual(len(logs),1);self.assertIn('a real failure',logs[0].read_text())

    def test_source_setup_reuses_preflight_and_release_setup_reuses_the_existing_builder(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(integration,'ROOT',Path(tmp)):
            from argparse import Namespace
            args=Namespace(with_hd=False,jobs=None,memory_gib=None,hd_profile=None)
            source=integration.preparation_command(Path('dump.iso'),args)
            self.assertIn('--check-cached',source);self.assertIn('english-text-test',source)
            manifest=Path(tmp)/'private/distribution/release.json';manifest.parent.mkdir(parents=True);manifest.write_text('{}')
            args.with_hd=True;args.jobs=3;args.memory_gib=8;args.hd_profile='fast'
            release=integration.preparation_command(Path('dump with spaces.iso'),args)
            self.assertEqual(Path(release[1]).name,'local_player_setup.py')
            self.assertIn('--with-hd',release);self.assertEqual(release[release.index('--jobs')+1],'3')
            self.assertEqual(release[release.index('--image')+1],'dump with spaces.iso')

    def test_plain_iso_passes_through_without_copy_or_compiler(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'copy.iso';p.write_bytes(b'ordinary ISO fixture')
            self.assertEqual(disc_images.normalize(p),p.resolve())
            self.assertEqual(list(Path(tmp).iterdir()),[p])

    def test_public_packaging_includes_root_manifest_and_uses_a_windows_x64_name(self):
        source=(ROOT/'tools/prepare-iso-release.py').read_text()
        self.assertIn("add(ROOT/'recomplauncher.json')",source)
        self.assertIn('v{a.version}-Windows-x64.zip',source)
        spec=importlib.util.spec_from_file_location('source_export',ROOT/'tools/export-github-source.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        self.assertIn('recomplauncher.json',module.selected())
        with tempfile.TemporaryDirectory() as tmp:
            readme=Path(tmp)/'README.md';original=b'# Personal README\r\n\r\nKeep every byte.\r\n';readme.write_bytes(original)
            module.add_badge(readme);self.assertEqual(readme.read_bytes(),module.BADGE+b'\n\n'+original)
            once=readme.read_bytes();module.add_badge(readme);self.assertEqual(readme.read_bytes(),once)

    @unittest.skipUnless(sys.platform=='win32','Windows process/argument contract')
    def test_gui_executable_direct_mode_inherits_output_quotes_paths_and_keeps_child_exit(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/'game folder';folder.mkdir();exe=folder/'LordOfApocalypse.exe'
            compiler=str(title.SDK/'bin/gcc.exe');env=title.environment()
            build=subprocess.run([compiler,'-std=c11','-O2','-municode','-mwindows',str(ROOT/'tools/windows-launcher.c'),'-o',str(exe),'-lshell32','-lgdi32','-luser32'],env=env,capture_output=True,text=True)
            self.assertEqual(build.returncode,0,build.stderr)
            python=folder/'private/tools/python314/python.exe';python.parent.mkdir(parents=True)
            c=folder/'probe.c';c.write_text('''#include <stdio.h>
#include <wchar.h>
int wmain(int argc,wchar_t **argv){
 if(argc!=5 || wcscmp(argv[1],L"-u") || wcscmp(argv[3],L"--prepare") || wcscmp(argv[4],L"--game=C:\\\\games \\u03a9\\\\a $().iso"))return 91;
 puts("progress 0.5 Transport check");fputs("fixture diagnostic\\n",stderr);return 23;
}''')
            build=subprocess.run([compiler,'-municode',str(c),'-o',str(python)],env=env,capture_output=True,text=True)
            self.assertEqual(build.returncode,0,build.stderr)
            run=subprocess.run([str(exe),'--recomplauncher','--prepare','--game=C:\\games Ω\\a $().iso'],capture_output=True,text=True,timeout=15)
            self.assertEqual(run.returncode,23,run.stdout+run.stderr)
            self.assertIn('progress 0.5 Transport check',run.stdout);self.assertIn('fixture diagnostic',run.stderr)

if __name__=='__main__':unittest.main()
