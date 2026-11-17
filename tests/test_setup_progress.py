import contextlib,io,json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import setup_progress as progress
import title,local_player_setup

class SetupProgress(unittest.TestCase):
    def test_count_bounds_and_completion_gate(self):
        output=io.StringIO()
        with contextlib.redirect_stdout(output):
            progress.emit('hd',42,100)
            progress.emit('verify',1,1)
            progress.emit('ready',1,1)
        lines=output.getvalue().splitlines()
        self.assertTrue(lines[0].startswith('LOA_SETUP_PROGRESS 10 42 100 '))
        self.assertTrue(lines[1].endswith(' 999'));self.assertTrue(lines[2].endswith(' 1000'))
        with self.assertRaises(ValueError):progress.emit('hd',101,100)
        with self.assertRaises(ValueError):progress.emit('ready')

    def test_timing_write_failure_does_not_mask_stage_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            timings=progress.Timings(Path(tmp)/'timings.json')
            with patch.object(Path,'write_text',side_effect=OSError('disk unavailable')),contextlib.redirect_stderr(io.StringIO()) as errors:
                timings.record('compile',2.0,7)
            self.assertEqual(timings.rows[0]['exit_code'],7)
            self.assertIn('Could not save setup timings',errors.getvalue())

    def test_real_parallel_make_counts_finished_outputs_and_failure(self):
        make=title.SDK/'bin/mingw32-make.exe';gcc=title.SDK/'bin/gcc.exe'
        if sys.platform!='win32' or not make.is_file():self.skipTest('Local Windows toolchain unavailable')
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);out=folder/'out';out.mkdir()
            (folder/'a.c').write_text('int a(void){return 1;}')
            (folder/'b.c').write_text('int b(void){return 2;}')
            (folder/'bad.c').write_text('#error intentional failure')
            (folder/'Makefile').write_text('all: out/a.o out/b.o\nfailed: out/bad.o\nout/%.o: %.c\n\t"'+gcc.as_posix()+'" -c $< -o $@\n')
            env=title.environment();plan=subprocess.run([str(make),'-n','all'],cwd=folder,env=env,capture_output=True,text=True,check=True)
            targets=progress.compile_targets(plan.stdout,folder,out);self.assertEqual(len(targets),2)
            self.assertEqual(list(out.iterdir()),[])
            captured=io.StringIO()
            with contextlib.redirect_stdout(captured):
                tracker=progress.CompileProgress(targets,folder,out)
                process=subprocess.Popen([str(make),'--output-sync=target','-j2','all'],cwd=folder,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
                with process.stdout:
                    for line in process.stdout:tracker.line(line)
                self.assertEqual(process.wait(),0)
            self.assertEqual(tracker.done,targets)
            self.assertIn('LOA_SETUP_PROGRESS 3 2 2',captured.getvalue())
            self.assertIn('LOA_SETUP_PROGRESS 4 0 0',captured.getvalue())
            plan=subprocess.run([str(make),'-n','failed'],cwd=folder,env=env,capture_output=True,text=True,check=True)
            with contextlib.redirect_stdout(io.StringIO()):
                tracker=progress.CompileProgress(progress.compile_targets(plan.stdout,folder,out),folder,out)
                result=subprocess.run([str(make),'--output-sync=target','failed'],cwd=folder,env=env,capture_output=True,text=True)
                for line in result.stdout.splitlines():tracker.line(line)
            self.assertNotEqual(result.returncode,0);self.assertFalse(tracker.done)

    def test_child_failure_keeps_partial_counts_and_records_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'tools').mkdir()
            (root/'tools/build-local-hd-pack.py').write_text('print("Preparing HD textures: 16 / 100 jobs complete",flush=True)\nraise SystemExit(7)\n')
            timings=progress.Timings(root/'timings.json');output=io.StringIO()
            with patch.object(local_player_setup,'ROOT',root),patch.object(local_player_setup,'TIMINGS',timings),contextlib.redirect_stdout(output):
                with self.assertRaisesRegex(RuntimeError,'exit 7'):local_player_setup.run('build-local-hd-pack.py')
            self.assertIn('LOA_SETUP_PROGRESS 10 16 100',output.getvalue())
            self.assertNotIn('LOA_SETUP_PROGRESS 12',output.getvalue())
            report=json.loads((root/'timings.json').read_text());self.assertEqual(report['stages'][0]['exit_code'],7)
            self.assertGreaterEqual(report['stages'][0]['seconds'],0)

    def test_plan_ignores_non_compile_and_external_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);out=folder/'out'
            text='gcc -c a.c -o "out/a.o"\ngcc out/a.o -o out/game.exe\ngcc -c b.c -o ../outside.o\n'
            self.assertEqual(progress.compile_targets(text,folder,out),{out/'a.o'})

if __name__=='__main__':unittest.main()
