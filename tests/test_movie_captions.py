import hashlib,json,os,struct,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import movie_captions as cap
import title

class MovieCaptions(unittest.TestCase):
    def fixture(self):
        header=b'PSMF'+bytes(140)
        return header,cap.build([header],[(0,10,20,1,2,2,1,b'\xff'*8),(0,25,30,1,2,2,1,b'\0'*8)])

    def test_invalid_counts_intervals_pixels_and_bounds_refused(self):
        header,_=self.fixture()
        cases=[([],[]),([header,header],[(0,1,2,0,0,1,1,b'\0'*4)]),
               ([header],[(0,0,2,0,0,1,1,b'\0'*4)]),([header],[(0,1,2,480,0,1,1,b'\0'*4)]),
               ([header],[(0,1,2,0,0,1,1,b'\0')]),
               ([header],[(0,1,4,0,0,1,1,b'\0'*4),(0,3,5,0,0,1,1,b'\0'*4)])]
        for headers,cues in cases:
            with self.assertRaises(ValueError):cap.build(headers,cues)

    def test_multiple_movie_identities_share_pixels_without_sharing_timing(self):
        first=b'PSMF'+bytes(140);second=b'PSMF'+b'\x01'+bytes(139)
        data=cap.build([first,second],[(0,10,20,0,0,1,1,b'\xff'*4),(1,10,30,0,0,1,1,b'\xff'*4)])
        self.assertEqual(struct.unpack_from('<2I',data,8),(2,2))
        table=16+288
        a=struct.unpack_from('<8I',data,table);b=struct.unpack_from('<8I',data,table+32)
        self.assertEqual(a[0:3],(0,10,20));self.assertEqual(b[0:3],(1,10,30))
        self.assertEqual(a[-1],b[-1]);self.assertEqual(len(data),table+64+4)

    def test_only_reviewed_wip_bundle_enables_and_hash_tampering_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);_,data=self.fixture();(root/'captions.bin').write_bytes(data)
            report=dict(approved_for_launch=False,bundle_sha256=hashlib.sha256(data).hexdigest())
            (root/'result.json').write_text(json.dumps(report))
            self.assertEqual(cap.environment('english-text-test',root)['LOA_MOVIE_CAPTIONS'],'')
            report['approved_for_launch']=True;(root/'result.json').write_text(json.dumps(report))
            self.assertTrue(cap.environment('english-text-test',root)['LOA_MOVIE_CAPTIONS'])
            for variant in ('japanese','english-v16'):self.assertEqual(cap.environment(variant,root)['LOA_MOVIE_CAPTIONS'],'')
            (root/'captions.bin').write_bytes(data+b'!')
            with self.assertRaisesRegex(ValueError,'hash differs'):cap.environment('english-text-test',root)

    @unittest.skipUnless(os.name=='nt' and (title.SDK/'bin/gcc.exe').is_file(),'Windows pinned compiler')
    def test_native_parser_selection_corruption_and_pixel_formats(self):
        with tempfile.TemporaryDirectory(prefix='caption-core-test-',dir=ROOT/'private') as tmp:
            root=Path(tmp);_,blob=self.fixture();(root/'captions.bin').write_bytes(blob)
            source=root/'test.c';source.write_text(r'''
#include "movie_caption_format.h"
#include <assert.h>
#include <stdio.h>
int main(int argc,char **argv){
 uint8_t data[4096],header[144];FILE *f=fopen(argv[1],"rb");assert(f);size_t n=fread(data,1,sizeof data,f);fclose(f);
 LoaCaptions view;assert(!loa_cap_parse(data,n,&view));memcpy(header,data+16,144);
 assert(loa_cap_find(&view,header,9)==-1);assert(loa_cap_find(&view,header,10)==0);
 assert(loa_cap_find(&view,header,19)==0);assert(loa_cap_find(&view,header,20)==-1);
 assert(loa_cap_find(&view,header,25)==1);header[4]=1;assert(loa_cap_find(&view,header,10)==-1);
 assert(loa_cap_pack(255,255,255,255,0)==65535);assert(loa_cap_pack(255,0,0,255,1)==0x801f);
 assert(loa_cap_pack(255,0,0,255,2)==0xf00f);assert(loa_cap_pack(1,2,3,255,3)==0xff030201);
 for(size_t i=0;i<16;i++)assert(loa_cap_parse(data,i,&view));
 uint32_t t=16+144;data[t+28]=1;data[t+29]=data[t+30]=data[t+31]=0;
 assert(loa_cap_parse(data,n,&view));return 0;
}
''')
            exe=root/'test.exe';run=subprocess.run([str(title.SDK/'bin/gcc.exe'),'-std=c11','-Wall','-Wextra','-I'+str(ROOT/'tools'),str(source),'-o',str(exe)],env=title.environment(),capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stderr)
            run=subprocess.run([str(exe),str(root/'captions.bin')],env=title.environment(),capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stderr)

    @unittest.skipUnless(os.name=='nt' and (title.SDK/'bin/gcc.exe').is_file(),'Windows pinned compiler')
    def test_actual_writer_preserves_stride_padding_and_unmatched_pictures(self):
        with tempfile.TemporaryDirectory(prefix='caption-writer-test-',dir=ROOT/'private') as tmp:
            root=Path(tmp);header,blob=self.fixture();(root/'captions.bin').write_bytes(blob)
            (root/'recomp.h').write_text('''#include <stdint.h>
int sr_guest_span_readable(uint32_t,uint32_t);
int sr_guest_span_writable_any_view(uint32_t,uint32_t);
int sr_guest_copy_in(void*,uint32_t,uint32_t);
int sr_guest_copy_out(uint32_t,const void*,uint32_t);
''')
            (root/'test.c').write_text(r'''
#include <assert.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include "movie_caption_format.h"
static uint8_t mem[4096];
int sr_guest_span_readable(uint32_t a,uint32_t n){return a && a<sizeof mem && n<=sizeof mem-a;}
int sr_guest_span_writable_any_view(uint32_t a,uint32_t n){return sr_guest_span_readable(a,n);}
int sr_guest_copy_in(void *p,uint32_t a,uint32_t n){if(!sr_guest_span_readable(a,n))return 0;memcpy(p,mem+a,n);return 1;}
int sr_guest_copy_out(uint32_t a,const void *p,uint32_t n){if(!sr_guest_span_readable(a,n))return 0;memcpy(mem+a,p,n);return 1;}
void loa_movie_caption_picture(uint32_t,uint32_t,uint32_t,uint32_t,uint32_t,uint32_t,unsigned);
int main(void){
 memset(mem,0,sizeof mem);memcpy(mem+16,"PSMF",4);
 for(unsigned mode=0;mode<4;mode++){
  unsigned bpp=mode==3?4:2;memset(mem+1024,0xcc,256);
  loa_movie_caption_picture(16,10,1024,6,4,4,mode);
  for(unsigned i=0;i<256;i++)assert(mem[1024+i]==(i>=13*bpp && i<15*bpp?255:0xcc));
 }
 for(unsigned i=0;i<4;i++){
  memset(mem+1024,0xcc,256);
  if(i==0)loa_movie_caption_picture(16,9,1024,6,4,4,3);
  if(i==1)loa_movie_caption_picture(16,20,1024,6,4,4,3);
  if(i==2){mem[20]=1;loa_movie_caption_picture(16,10,1024,6,4,4,3);mem[20]=0;}
  if(i==3)loa_movie_caption_picture(16,10,1024,3,4,4,3);
  for(unsigned j=0;j<256;j++)assert(mem[1024+j]==0xcc);
 }
 return 0;
}
''')
            exe=root/'writer.exe'
            run=subprocess.run([str(title.SDK/'bin/gcc.exe'),'-std=c11','-Wall','-Wextra','-I'+str(root),'-I'+str(ROOT/'tools'),str(root/'test.c'),str(ROOT/'tools/movie_subtitles.c'),'-o',str(exe)],env=title.environment(),capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stderr)
            env=title.environment();env['LOA_MOVIE_CAPTIONS']=str(root/'captions.bin')
            run=subprocess.run([str(exe)],env=env,capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stderr)

if __name__=='__main__':unittest.main()
