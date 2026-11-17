/* Own synthetic media contexts; exercise production tracking and exact errors. */
#include "recomp.h"
#include <assert.h>
#include <stdlib.h>
#include <stdio.h>
static HleFn registered[5];
static uint32_t result;
static unsigned calls;
uint32_t sr_display_vcount(void){return 120;}
void __real_sr_hle_register(uint32_t nid,const char *name,HleFn fn){
    (void)name;
    const uint32_t ids[]={0xd8c5f121u,0x606a4649u,0x95a84ee5u,0x1078c008u,0x9b71a274u};
    for(int i=0;i<5;i++)if(ids[i]==nid){registered[i]=fn;return;}
    assert(0);
}
static uint32_t real_handler(CpuState *s){(void)s;calls++;return result;}
void __wrap_sr_hle_register(uint32_t,const char *,HleFn);
int loa_fps_enabled(void);
int loa_fps_movie_restore(void);
int loa_fps_update(CpuState *,uint32_t,uint32_t);
int main(int argc,char **argv){
    assert(argc==2);int enabled=atoi(argv[1])==60;
    const uint32_t ids[]={0xd8c5f121u,0x606a4649u,0x95a84ee5u,0x1078c008u,0x9b71a274u};
    for(int i=0;i<5;i++)__wrap_sr_hle_register(ids[i],"synthetic",real_handler);
    CpuState s={0};s.r[4]=0x1000;s.f[12]=2.0f;
    assert(loa_fps_enabled()==enabled);
    result=0x80010086;assert(registered[0](&s)==result);
    assert(loa_fps_enabled()==enabled && calls==1);
    result=0;assert(!registered[0](&s));assert(!loa_fps_enabled());
    assert(loa_fps_movie_restore()==enabled);assert(!loa_fps_update(&s,0,0x40000000u));
    assert(s.fi[22]==(enabled?0x40000000u:0u));
    s.r[4]=0x2000;assert(!registered[0](&s));
    s.r[4]=0x1000;assert(!registered[1](&s));assert(!loa_fps_enabled());
    s.r[4]=0x2000;assert(!registered[1](&s));assert(loa_fps_enabled()==enabled);
    s.r[4]=0x3000;assert(!registered[2](&s));assert(!loa_fps_enabled());
    result=0x80010086;assert(registered[3](&s)==result);assert(!loa_fps_enabled());
    result=0;assert(!registered[3](&s));assert(loa_fps_enabled()==enabled);
    assert(!registered[4](&s));assert(loa_fps_enabled()==enabled);
    assert(loa_fps_update(&s,0,0x40000000u)==enabled);
    for(int i=1;i<=17;i++){s.r[4]=(uint32_t)i;assert(!registered[0](&s));}
    for(int i=1;i<=17;i++){s.r[4]=(uint32_t)i;assert(!registered[1](&s));}
    assert(!loa_fps_enabled());assert(loa_fps_movie_restore()==enabled);
    puts("PASS: media protection, multiple contexts, errors, restore and conservative overflow");
    return 0;
}
