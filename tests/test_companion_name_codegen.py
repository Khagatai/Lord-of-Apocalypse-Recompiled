from pathlib import Path
import subprocess, sys, tempfile, unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import companion_name_codegen as guard
import title

BODY = '''void convert(CpuState *s) {
    uint32_t _sp_entry = s->r[29]; (void)_sp_entry;
    sr_begin(s, 0x08c0b414u, 0x27bdffe0u);
    s->r[17]=s->r[6]; unsigned input=0;
  L_08c0b448: ;
    if (source[input]==0xffffu) goto L_08c0b488;
    sr_begin(s, 0x08c0b474u, 0xa6240000u);
    memcpy(memory+s->r[17],source+input,2);s->r[17]+=2;input++;
    goto L_08c0b448;
  L_08c0b488: ;
    sr_begin(s, 0x08c0b48cu, 0xa6240000u);
    { uint16_t end=0xffffu; memcpy(memory+s->r[17],&end,2); }
}
'''


class CompanionNameCodegen(unittest.TestCase):
    def test_refuses_changed_instructions_and_leaves_other_functions_alone(self):
        lines=BODY.splitlines()
        self.assertIs(guard.rewrite(lines,0x08804000),lines)
        with self.assertRaisesRegex(ValueError,'instruction identity'):
            guard.rewrite(BODY.replace('0xa6240000u','0xa6250000u').splitlines(),guard.FUNCTION)
        with self.assertRaisesRegex(ValueError,'emitter contract'):
            guard.rewrite(BODY.replace('L_08c0b448:','L_other:').splitlines(),guard.FUNCTION)

    def test_generated_guard_preserves_canary_and_nonparty_conversion(self):
        compiler=title.SDK/'bin/gcc.exe'
        if not compiler.is_file():self.skipTest('Local native toolchain unavailable')
        guarded='\n'.join(guard.rewrite(BODY.splitlines(),guard.FUNCTION))
        code='''#include <stdint.h>
#include <string.h>
#include <assert.h>
#include <stdio.h>
typedef struct {uint32_t r[32];} CpuState;
static unsigned char memory[256];
static uint16_t source[32];
#define sr_begin(...) ((void)0)
'''+guarded+'''
int main(void) {
    const unsigned sizes[]={0,7,8,9,14};
    for(unsigned i=0;i<5;i++)for(unsigned party=0;party<2;party++) {
        unsigned n=sizes[i]; memset(memory,0x5a,sizeof memory);
        for(unsigned k=0;k<n;k++)source[k]=(uint16_t)('A'+k);
        source[n]=0xffff;CpuState s={{0}};s.r[6]=32;
        s.r[31]=party?0x0884b4d8u:0x08804000u;convert(&s);
        unsigned expected=party&&n>8?8:n;
        for(unsigned k=0;k<expected;k++) {uint16_t v;memcpy(&v,memory+32+k*2,2);assert(v==source[k]);}
        uint16_t end;memcpy(&end,memory+32+expected*2,2);assert(end==0xffff);
        assert(memory[31]==0x5a);assert(memory[32+(expected+1)*2]==0x5a);
        if(party)for(unsigned k=50;k<60;k++)assert(memory[k]==0x5a);
    }
    puts("PASS: ten bounded and untouched conversion cases");return 0;
}
'''
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp);c=path/'name.c';exe=path/'name.exe';c.write_text(code)
            build=subprocess.run([str(compiler),'-std=c11','-O2',str(c),'-o',str(exe)],env=title.environment(),capture_output=True,text=True)
            self.assertEqual(build.returncode,0,build.stderr)
            run=subprocess.run([str(exe)],capture_output=True,text=True,timeout=10)
            self.assertEqual(run.returncode,0,run.stderr)
            self.assertIn('ten bounded',run.stdout)

if __name__=='__main__':unittest.main()
