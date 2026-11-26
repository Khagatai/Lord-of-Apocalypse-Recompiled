import subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import password_codegen as codegen,title

class PasswordAliases(unittest.TestCase):
    def test_seam_identity_and_unrelated_code(self):
        rows=['void f_08c9f680(CpuState *s) {',f' sr_begin(s, 0x{codegen.PC:08x}u, 0x{codegen.WORD:08x}u); original();','}']
        result='\n'.join(codegen.rewrite(rows,codegen.START))
        self.assertEqual(result.count('loa_password_translate(s->r[16]);'),1)
        self.assertIn(rows[1].strip(),result)
        self.assertEqual(codegen.rewrite(rows,codegen.START+4),rows)
        with self.assertRaises(ValueError):codegen.rewrite([r.replace('34040000','34040001') for r in rows],codegen.START)

    @unittest.skipUnless(sys.platform=='win32','Bundled compiler')
    def test_alias_expansion_validates_complete_local_data_before_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)
            (p/'recomp.h').write_text('''#include <stdint.h>
#include <string.h>
extern unsigned char ram[0x2000000];
static int sr_guest_span_readable(uint32_t p,uint32_t n){return p>=0x08800000u && n<=sizeof ram && p-0x08800000u<=sizeof ram-n;}
#define sr_guest_span_writable sr_guest_span_readable
static uint32_t read32(uint32_t p){uint32_t v;memcpy(&v,ram+p-0x08800000u,4);return v;}
static uint16_t read16(uint32_t p){uint16_t v;memcpy(&v,ram+p-0x08800000u,2);return v;}
static void write16(uint32_t p,uint16_t v){memcpy(ram+p-0x08800000u,&v,2);}
#define MEM_R32 read32
#define MEM_R16 read16
#define MEM_W16 write16
''')
            (p/'check.c').write_text('''#include "recomp.h"
#include "password_alias.h"
#include <assert.h>
unsigned char ram[0x2000000];
void loa_password_translate(uint32_t);
static void w32(uint32_t p,uint32_t v){memcpy(ram+p-0x08800000u,&v,4);}
static const uint32_t obj=0x08900000u,mes=0x08901000u,glyph=0x08910000u;
static void input(const char *s,int full){for(unsigned i=0;i<32;i++)MEM_W16(obj+4+2*i,0);for(unsigned i=0;s[i];i++)MEM_W16(obj+4+2*i,(uint16_t)(s[i]+(full?0xfee0:0)));}
int main(void){
 w32(obj+0x2ac,mes);w32(mes,0x53454d2e);w32(mes+4,1);w32(mes+8,28);
 w32(0x08d1bf64u,glyph);w32(0x08d1bf68u,100);
 for(unsigned i=0;i<100;i++)MEM_W16(glyph+2*i,(uint16_t)(0x3000+i));
 for(unsigned i=0;i<28;i++){uint32_t m=mes+0x100+16*i;w32(mes+12+4*i,0x100+16*i);MEM_W16(m+8,3);MEM_W16(m+10,(uint16_t)(i+1));MEM_W16(m+12,(uint16_t)(i+2));MEM_W16(m+14,0xffff);}
 for(unsigned i=0;i<13;i++)for(int full=0;full<2;full++){
  input(loa_password_aliases[i].text,full);loa_password_translate(obj);
  assert(MEM_R16(obj+4)==0x3001+loa_password_aliases[i].message);
  assert(MEM_R16(obj+6)==0x3002+loa_password_aliases[i].message);
  for(unsigned j=2;j<32;j++)assert(MEM_R16(obj+4+2*j)==0);
 }
 input("DENGEKIPS",0);loa_password_translate(obj);assert(MEM_R16(obj+4)==0x3017);
 unsigned char before[64];
 input("wrong",0);memcpy(before,ram+obj+4-0x08800000u,64);loa_password_translate(obj);assert(!memcmp(before,ram+obj+4-0x08800000u,64));
 input("4gamer",0);memcpy(before,ram+obj+4-0x08800000u,64);
 /* Truncation, malformed tables, missing terminator and unknown glyphs fail closed. */
 w32(mes+12,0xfffffff0u);loa_password_translate(obj);assert(!memcmp(before,ram+obj+4-0x08800000u,64));w32(mes+12,0x100);
 MEM_W16(mes+0x100+14,0xfffe);loa_password_translate(obj);assert(!memcmp(before,ram+obj+4-0x08800000u,64));MEM_W16(mes+0x100+14,0xffff);
 MEM_W16(mes+0x100+12,100);loa_password_translate(obj);assert(!memcmp(before,ram+obj+4-0x08800000u,64));MEM_W16(mes+0x100+12,2);
 w32(0x08d1bf64u,0x09ffffffu);loa_password_translate(obj);assert(!memcmp(before,ram+obj+4-0x08800000u,64));
 loa_password_translate(0xfffffff0u);return 0;
}''')
            exe=p/'check.exe'
            run=subprocess.run([str(title.SDK/'bin/gcc.exe'),'-O2','-I'+str(p),'-I'+str(ROOT/'tools'),str(p/'check.c'),str(ROOT/'tools/password_runtime.c'),'-o',str(exe)],env=title.environment(),capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stderr)
            result=subprocess.run([str(exe)],env=title.environment(),capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)

if __name__=='__main__':unittest.main()
