/* Offline validation of the actual caption writer. Guest memory is bounded
 * test storage; this does not substitute any emulated PSP operation. */
#include "movie_caption_format.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
static uint8_t mem[1024+512*272*4+64];
int sr_guest_span_readable(uint32_t a,uint32_t n){return a&&a<sizeof mem&&n<=sizeof mem-a;}
int sr_guest_span_writable_any_view(uint32_t a,uint32_t n){return sr_guest_span_readable(a,n);}
int sr_guest_copy_in(void *p,uint32_t a,uint32_t n){if(!sr_guest_span_readable(a,n))return 0;memcpy(p,mem+a,n);return 1;}
int sr_guest_copy_out(uint32_t a,const void *p,uint32_t n){if(!sr_guest_span_readable(a,n))return 0;memcpy(mem+a,p,n);return 1;}
void loa_movie_caption_picture(uint32_t,uint32_t,uint32_t,uint32_t,uint32_t,uint32_t,unsigned);
int main(int argc,char **argv){
 assert(argc==2);FILE*f=fopen(argv[1],"rb");assert(f);assert(!fseek(f,0,SEEK_END));long length=ftell(f);assert(length>0&&length<=64*1024*1024);rewind(f);
 uint8_t*data=malloc(length);assert(data);assert(fread(data,1,length,f)==(size_t)length);fclose(f);
 LoaCaptions v;assert(!loa_cap_parse(data,length,&v));
 uint32_t movies=loa_cap_u32(data+8),count=loa_cap_u32(data+12);size_t table=16+144*movies;unsigned pictures=0;
 for(uint32_t i=0;i<count;i++){
  const uint8_t*r=data+table+32*i;uint32_t m=loa_cap_u32(r),first=loa_cap_u32(r+4),end=loa_cap_u32(r+8),x=loa_cap_u32(r+12),y=loa_cap_u32(r+16),w=loa_cap_u32(r+20),h=loa_cap_u32(r+24),off=loa_cap_u32(r+28);
  memcpy(mem+16,data+16+144*m,144);
  assert(loa_cap_find(&v,mem+16,first)==(int)i);assert(loa_cap_find(&v,mem+16,end-1)==(int)i);
  for(unsigned mode=0;mode<4;mode++)for(unsigned edge=0;edge<2;edge++){
   unsigned bpp=mode==3?4:2;memset(mem+1024,0xcc,sizeof mem-1024);
   loa_movie_caption_picture(16,edge?end-1:first,1024,512,480,272,mode);
   for(unsigned py=0;py<272;py++)for(unsigned px=0;px<512;px++){
    uint32_t expected=bpp==4?0xcccccccc:0xcccc;
    if(px>=x&&px<x+w&&py>=y&&py<y+h){const uint8_t*p=data+off+((py-y)*w+px-x)*4;expected=loa_cap_pack(p[0],p[1],p[2],p[3],mode);}
    uint32_t actual=0;memcpy(&actual,mem+1024+(py*512+px)*bpp,bpp);assert(actual==expected);
   }
   for(size_t j=1024+512*272*bpp;j<sizeof mem;j++)assert(mem[j]==0xcc);
   pictures++;
  }
 }
 printf("{\"movies\":%u,\"cues\":%u,\"actual_writer_pictures\":%u,\"pixel_formats\":4,\"stride_padding_preserved\":true}\n",movies,count,pictures);
 free(data);return 0;
}
