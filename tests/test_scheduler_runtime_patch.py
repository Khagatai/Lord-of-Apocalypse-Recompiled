import hashlib,sys,tempfile,unittest,subprocess,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import scheduler_runtime_patch as patch
import title

class SchedulerRuntimePatch(unittest.TestCase):
    def test_unknown_source_is_refused_before_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'src/rt/sched.c';source.parent.mkdir(parents=True);source.write_bytes(b'unknown scheduler')
            output=root/'private/sched.c'
            with self.assertRaisesRegex(ValueError,'hash mismatch'):patch.prepare(root,output)
            self.assertFalse(output.exists())
    def test_only_two_diagnostic_guards_change_and_upstream_stays_exact(self):
        framework=ROOT/'external/nakagawa-recomp';source=framework/'src/rt/sched.c';before=source.read_bytes()
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'sched.c';first=patch.prepare(framework,output);again=patch.prepare(framework,output)
            self.assertEqual(first,again);self.assertEqual(first['upstream_sha256'],hashlib.sha256(before).hexdigest())
            restored=output.read_text(encoding='utf-8')
            for old in (patch.SLEEP,patch.WAKE):
                indent=old[:len(old)-len(old.lstrip())]
                guarded=indent+'static int loa_wakelog=-1;\n'+indent+'if(sched_env_switch(&loa_wakelog,"SR_WAKELOG")) {\n'+old+'\n'+indent+'}'
                self.assertEqual(restored.count(guarded),1);restored=restored.replace(guarded,old)
            self.assertEqual(restored,before.decode('utf-8'));self.assertEqual(source.read_bytes(),before)
    def test_pinned_native_scheduler_suite_with_logging_off_and_on(self):
        framework=title.FRAMEWORK;harness=framework/'tests/native/sched_selftest.c'
        if not harness.is_file() or not (title.SDK/'bin/gcc.exe').is_file():self.skipTest('Pinned native scheduler fixtures/compiler unavailable')
        with tempfile.TemporaryDirectory() as tmp:
            work=Path(tmp);patch.prepare(framework,work/'sched.c')
            source=work/'sched_selftest.c';source.write_bytes(harness.read_bytes())
            config=subprocess.run([str(title.PYTHON),str(framework/'tools/title_runtime_config.py'),'--output',str(work/'sr_title_config.h')],env=title.environment(),capture_output=True,text=True)
            self.assertEqual(config.returncode,0,config.stderr)
            exe=work/'scheduler.exe'
            command=[str(title.SDK/'bin/gcc.exe'),'-O2','-fno-strict-aliasing','-DSR_SCHED_LIVENESS_TEST','-DSR_FLIGHT_RECORDER_LINKED',
                '-I'+str(work),'-I'+str(framework/'src/rt'),'-I'+str(framework/'src/core'),'-I'+str(title.SDK/'include'),'-L'+str(title.SDK/'lib'),str(source)]
            command += [str(framework/'src/rt'/name) for name in ('nested_frames.c','sr_coro.c','flight_recorder.c','title_config.c','ace.c')]
            command += ['-lSDL3','-lws2_32','-lwinmm','-lm','-o',str(exe)]
            build=subprocess.run(command,env=title.environment(),capture_output=True,text=True)
            self.assertEqual(build.returncode,0,build.stderr)
            for enabled in (False,True):
                env=title.environment();env.pop('SR_WAKELOG',None)
                if enabled:env['SR_WAKELOG']='1'
                run=subprocess.run([str(exe)],env=env,capture_output=True,text=True,timeout=40)
                self.assertEqual(run.returncode,0,run.stderr[-4000:])
                self.assertIn('0 failures',run.stderr)
                self.assertEqual('DEBUG_SLEEP: ' in run.stderr,enabled)

if __name__=='__main__':unittest.main()
