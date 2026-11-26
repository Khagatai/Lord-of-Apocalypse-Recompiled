"""Real rendering under a process-only Restricted policy; no registry changes."""
import importlib.util,json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from text_render_worker import Renderer

def module(name,file):
    s=importlib.util.spec_from_file_location(name,ROOT/'tools'/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

@unittest.skipUnless(os.name=='nt','Windows PowerShell/GDI')
class RenderPolicy(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='restricted policy ',dir=ROOT/'private');self.addCleanup(self.temp.cleanup)
        self.folder=Path(self.temp.name)
        self.powershell=Path(os.environ.get('SystemRoot','C:/Windows'))/'System32/WindowsPowerShell/v1.0/powershell.exe'
        # Match an Explorer-launched Windows PowerShell environment, rather
        # than importing incompatible PS7 modules inherited from the test shell.
        modules=patch.dict(os.environ,PSModulePath=str(self.powershell.parent/'Modules'))
        modules.start();self.addCleanup(modules.stop)
        self.before=self.persistent_policy()
        self.addCleanup(lambda:self.assertEqual(self.persistent_policy(),self.before))

    def persistent_policy(self):
        query='@{user=[string](Get-ExecutionPolicy -Scope CurrentUser);machine=[string](Get-ExecutionPolicy -Scope LocalMachine)} | ConvertTo-Json -Compress'
        r=subprocess.run([str(self.powershell),'-NoProfile','-NonInteractive','-Command',query],capture_output=True,text=True,timeout=20)
        self.assertEqual(r.returncode,0,r.stderr)
        return json.loads(r.stdout)

    def caption_plan(self):
        plan=self.folder/'caption.json';plan.write_text(json.dumps(dict(width=128,height=32,blocks=[dict(x=2,y=2,width=120,height=26,text='Test')])));return plan

    def test_original_file_invocation_is_blocked_under_restricted_policy(self):
        env=dict(os.environ,PSExecutionPolicyPreference='Restricted')
        run=subprocess.run([str(self.powershell),'-NoProfile','-NonInteractive','-File',str(ROOT/'tools/render-text-worker.ps1')],
            env=env,input='',capture_output=True,text=True,timeout=20)
        self.assertNotEqual(run.returncode,0)
        self.assertIn('UnauthorizedAccess',run.stderr)

    def test_persistent_worker_renders_ui_and_caption_without_changing_parent_policy(self):
        png=module('policy_png','inventory-textures.py');source=self.folder/'source.png'
        source.write_bytes(png.png(64,32,bytes((30,40,50,255))*64*32))
        plan=self.folder/'ui.json';plan.write_text(json.dumps(dict(source_png=source.relative_to(ROOT).as_posix(),blocks=[
            dict(x=4,y=4,width=56,height=20,paragraphs=['Hello'],line_height=12,font_pixels=10,color='#ffffff',background='#000000')])))
        with patch.dict(os.environ,PSExecutionPolicyPreference='Restricted'):
            with Renderer(ROOT) as worker:
                worker.render('render-texture-text.ps1',plan,self.folder/'ui')
                pid=worker.process.pid
                worker.render('render-caption-atlas.ps1',self.caption_plan(),self.folder/'caption')
                self.assertEqual(worker.process.pid,pid)
                self.assertEqual(len((self.folder/'ui/pixels.rgba').read_bytes()),64*32*4)
                self.assertTrue(any((self.folder/'caption/pixels.rgba').read_bytes()[3::4]))
            self.assertEqual(os.environ['PSExecutionPolicyPreference'],'Restricted')

    def test_movie_caption_output_matches_with_restricted_parent_policy(self):
        captions=module('policy_movie','build-local-movie-captions.py')
        draft=self.folder/'draft.json';draft.write_text(json.dumps(dict(cues=[dict(id=1,english_lines=['Test subtitle'])])))
        captions.run_render('render-movie-captions.ps1',['-Draft',str(draft),'-Output',str(self.folder/'normal')])
        with patch.dict(os.environ,PSExecutionPolicyPreference='Restricted'):
            captions.run_render('render-movie-captions.ps1',['-Draft',str(draft),'-Output',str(self.folder/'restricted')])
            self.assertEqual(os.environ['PSExecutionPolicyPreference'],'Restricted')
        self.assertEqual((self.folder/'normal/cue-0001.rgba').read_bytes(),(self.folder/'restricted/cue-0001.rgba').read_bytes())

    def test_renderer_keeps_bounds_validation_under_restricted_parent_policy(self):
        plan=self.folder/'bad.json';plan.write_text(json.dumps(dict(width=128,height=32,blocks=[dict(x=120,y=0,width=100,height=24,text='Test')])))
        with patch.dict(os.environ,PSExecutionPolicyPreference='Restricted'),Renderer(ROOT) as worker:
            with self.assertRaisesRegex(RuntimeError,'Local text renderer failed'):
                worker.render('render-caption-atlas.ps1',plan,self.folder/'bad')

if __name__=='__main__':unittest.main()
