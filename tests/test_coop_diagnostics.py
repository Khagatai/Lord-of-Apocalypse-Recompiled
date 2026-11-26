import subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import title

class CoopDiagnostics(unittest.TestCase):
    def test_null_callback_keeps_the_original_fatal_handler(self):
        if not (title.SDK/'bin/gcc.exe').is_file():self.skipTest('Local compiler unavailable')
        with tempfile.TemporaryDirectory() as tmp:
            work=Path(tmp);main=work/'main.c';original=work/'original.c';exe=work/'fault.exe'
            main.write_text(r'''
#include "recomp.h"
#include <stdlib.h>
uint8_t *g_mem;
uint32_t sched_current_uid(void){return 0x125;}
uint32_t sr_display_vcount(void){return 7300;}
int main(void){CpuState s={0};g_mem=calloc(1,32u*1024u*1024u);s.r[17]=0x08800000;
 s.r[4]=0x04000000;s.r[31]=0x08bf3804;s.r[29]=0x09ffe910;
 sr_null_code_pointer(&s,0x08bf386c);}
''')
            original.write_text(r'''
#include "recomp.h"
#include <stdlib.h>
#include <stdio.h>
void sr_null_code_pointer(CpuState *s,uint32_t pc){
 if(pc!=0x08bf386c || s->r[17]!=0x08800000)exit(90);
 puts("ORIGINAL_FATAL_EXECUTED");exit(23);}
''')
            build=subprocess.run([str(title.SDK/'bin/gcc.exe'),'-O2','-Wall','-Wextra',
                '-I'+str(title.FRAMEWORK/'src/rt'),str(main),str(original),str(ROOT/'tools/coop_diagnostics.c'),
                '-Wl,--wrap=sr_null_code_pointer','-o',str(exe)],env=title.environment(),capture_output=True,text=True)
            self.assertEqual(build.returncode,0,build.stderr)
            run=subprocess.run([str(exe)],capture_output=True,text=True,timeout=5)
            self.assertEqual(run.returncode,23,run.stderr);self.assertIn('ORIGINAL_FATAL_EXECUTED',run.stdout)
            self.assertIn('LOA_COOP_FAULT: pc=0x08bf386c',run.stderr)
            self.assertIn('LOA_COOP_MEMORY: owner address=08800000',run.stderr)
            self.assertNotIn('LOA_COOP_MEMORY: argument',run.stderr)

if __name__=='__main__':unittest.main()
