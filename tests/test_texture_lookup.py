import os,subprocess,sys,tempfile,unittest,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import title

FIXTURE=r'''
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
typedef struct {uint32_t words[16];} TexMipKey;
typedef struct {uint64_t key;TexMipKey mip;uint32_t content;} TexEnt;
static TexEnt s_tex[1024];static int s_tex_n;
#include "texture_lookup.h"
static uint32_t random_word(void){static uint32_t r=123456789;r^=r<<13;r^=r>>17;r^=r<<5;return r;}
static int reference(uint64_t key,const TexMipKey *mip){
 for(int i=0;i<s_tex_n;i++)if(s_tex[i].key==key && !memcmp(&s_tex[i].mip,mip,sizeof *mip))return i;
 return -1;
}
int main(int argc,char **argv){
 assert(argc==2);loa_texture_lookup_reset();
 for(int i=0;i<512;i++){s_tex[i].key=0x08800000u+(uint64_t)(i%128)*64;s_tex[i].mip.words[15]=(unsigned)i/128;}
 s_tex_n=512;
 if(!strcmp(argv[1],"fuzz")){
  for(unsigned n=0;n<100000;n++){
   if(n%29==0 && s_tex_n>1){int victim=(int)(random_word()%(unsigned)s_tex_n);s_tex[victim]=s_tex[--s_tex_n];}
   if(n%17==0 && s_tex_n<1024){TexEnt e={0};e.key=UINT64_C(0x1234567800000000)+n;s_tex[s_tex_n++]=e;}
   if(n%997==0)memset(loa_texture_hints,0xff,sizeof loa_texture_hints);
   int index=(int)(random_word()%(unsigned)s_tex_n);TexEnt e=s_tex[index];
   s_tex[index].content=random_word(); /* dirty contents must not enter the identity cache */
   assert(loa_texture_find(e.key,&e.mip)==reference(e.key,&e.mip));
   assert(loa_texture_find(e.key,&e.mip)==reference(e.key,&e.mip));
   e.mip.words[n%16]^=0x10000;assert(loa_texture_find(e.key,&e.mip)==reference(e.key,&e.mip));
  }
 }else{
  for(unsigned n=0;n<1000000;n++){
   unsigned index=(n/16*73)%512;TexEnt *e=&s_tex[index];assert(loa_texture_find(e->key,&e->mip)==(int)index);
  }
 }
 printf("{\"enabled\":%d,\"hits\":%llu,\"searches\":%llu,\"comparisons\":%llu}\n",loa_texture_lookup_enabled,
  (unsigned long long)loa_texture_hint_hits,(unsigned long long)loa_texture_searches,(unsigned long long)loa_texture_comparisons);
}
'''

class TextureLookup(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not (title.SDK/'bin/gcc.exe').is_file():raise unittest.SkipTest('Local C compiler unavailable')
        cls.tmp=tempfile.TemporaryDirectory();work=Path(cls.tmp.name);source=work/'lookup.c';source.write_text(FIXTURE);cls.exe=work/'lookup.exe'
        run=subprocess.run([str(title.SDK/'bin/gcc.exe'),'-O2','-Wall','-Wextra','-I'+str(ROOT/'tools'),str(source),'-o',str(cls.exe)],env=title.environment(),capture_output=True,text=True)
        if run.returncode:cls.tmp.cleanup();raise RuntimeError(run.stderr)
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def run_mode(self,mode,workload,verify=False):
        env=title.environment();env['LOA_TEXTURE_LOOKUP']=mode;env.pop('LOA_TEXTURE_LOOKUP_VERIFY',None)
        if verify:env['LOA_TEXTURE_LOOKUP_VERIFY']='1'
        run=subprocess.run([str(self.exe),workload],env=env,capture_output=True,text=True,timeout=20)
        self.assertEqual(run.returncode,0,run.stderr);return json.loads(run.stdout)
    def test_cache_mutation_and_full_mip_identity_match_original_search(self):
        result=self.run_mode('cached','fuzz',True);self.assertGreater(result['hits'],0)
        result=self.run_mode('linear','fuzz');self.assertEqual(result['hits'],0)
    def test_repeated_material_workload_reduces_comparisons(self):
        linear=self.run_mode('linear','repeat');cached=self.run_mode('cached','repeat')
        self.assertGreater(cached['hits'],900000);self.assertLess(cached['comparisons'],linear['comparisons']/8)
    def test_invalid_mode_fails_explicitly(self):
        env=title.environment();env['LOA_TEXTURE_LOOKUP']='unknown'
        run=subprocess.run([str(self.exe),'repeat'],env=env,capture_output=True,text=True,timeout=5)
        self.assertNotEqual(run.returncode,0);self.assertIn('invalid mode',run.stderr)

if __name__=='__main__':unittest.main()
