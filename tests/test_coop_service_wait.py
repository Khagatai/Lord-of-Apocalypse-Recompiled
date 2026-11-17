import subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import title
class CoopServiceWait(unittest.TestCase):
    def test_slow_host_io_cannot_consume_the_next_service_delay(self):
        compiler=title.SDK/'bin/gcc.exe'
        if not compiler.is_file():self.skipTest('Local native toolchain unavailable')
        with tempfile.TemporaryDirectory() as tmp:
            exe=Path(tmp)/'wait-test.exe'
            build=subprocess.run([str(compiler),'-std=c11','-O2','-Wall','-Wextra','-I'+str(ROOT/'tools'),str(ROOT/'tests/test_coop_service_wait.c'),'-o',str(exe)],env=title.environment(),capture_output=True,text=True)
            self.assertEqual(build.returncode,0,build.stderr)
            run=subprocess.run([str(exe)],capture_output=True,text=True,timeout=5)
            self.assertEqual(run.returncode,0,run.stderr);self.assertIn('all six cases',run.stdout)
if __name__=='__main__':unittest.main()
