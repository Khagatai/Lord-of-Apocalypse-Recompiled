/* SPDX-License-Identifier: GPL-3.0-or-later
 * Private bitmap caption format. No game content belongs in this source. */
#ifndef LOA_MOVIE_CAPTION_FORMAT_H
#define LOA_MOVIE_CAPTION_FORMAT_H
#include <stdint.h>
#include <stddef.h>
#include <string.h>
typedef struct {const uint8_t *data;size_t size;uint32_t movies,cues,table;} LoaCaptions;
static uint32_t loa_cap_u32(const uint8_t *p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static const char *loa_cap_parse(const uint8_t *data,size_t size,LoaCaptions *out){
    if(size<16 || size>64u*1024u*1024u || memcmp(data,"LOACAP1\0",8))return "invalid caption header";
    uint32_t movies=loa_cap_u32(data+8),cues=loa_cap_u32(data+12);
    if(!movies || movies>32 || !cues || cues>2048)return "invalid caption count";
    uint32_t table=16+movies*144,body=table+cues*32;
    if(body>size)return "truncated caption table";
    for(uint32_t i=0;i<movies;i++){
        if(memcmp(data+16+i*144,"PSMF",4))return "invalid movie identity";
        for(uint32_t j=0;j<i;j++)if(!memcmp(data+16+i*144,data+16+j*144,144))return "duplicate movie identity";
    }
    for(uint32_t i=0;i<cues;i++){
        const uint8_t *p=data+table+i*32;
        uint32_t movie=loa_cap_u32(p),first=loa_cap_u32(p+4),end=loa_cap_u32(p+8),x=loa_cap_u32(p+12),y=loa_cap_u32(p+16),w=loa_cap_u32(p+20),h=loa_cap_u32(p+24),offset=loa_cap_u32(p+28);
        if(movie>=movies || !first || first>=end || end>1000000)return "invalid caption interval";
        if(!w || w>480 || !h || h>272 || x>480-w || y>272-h)return "invalid caption rectangle";
        if(offset<body || offset>size || (uint64_t)offset+(uint64_t)w*h*4>size)return "invalid caption pixels";
        for(uint32_t j=0;j<i;j++){
            const uint8_t *q=data+table+j*32;
            if(movie==loa_cap_u32(q) && first<loa_cap_u32(q+8) && loa_cap_u32(q+4)<end)return "overlapping caption intervals";
        }
    }
    *out=(LoaCaptions){data,size,movies,cues,table};return NULL;
}
static int loa_cap_find(const LoaCaptions *view,const uint8_t header[144],uint32_t frame){
    uint32_t movie=view->movies;
    for(uint32_t i=0;i<view->movies;i++)if(!memcmp(view->data+16+i*144,header,144)){movie=i;break;}
    if(movie==view->movies)return -1;
    for(uint32_t i=0;i<view->cues;i++){
        const uint8_t *p=view->data+view->table+i*32;
        if(loa_cap_u32(p)==movie && frame>=loa_cap_u32(p+4) && frame<loa_cap_u32(p+8))return (int)i;
    }
    return -1;
}
static uint32_t loa_cap_pack(uint8_t r,uint8_t g,uint8_t b,uint8_t a,unsigned mode){
    if(mode==0)return (r>>3)|((uint32_t)(g>>2)<<5)|((uint32_t)(b>>3)<<11);
    if(mode==1)return (r>>3)|((uint32_t)(g>>3)<<5)|((uint32_t)(b>>3)<<10)|((uint32_t)(a>>7)<<15);
    if(mode==2)return (r>>4)|((uint32_t)(g>>4)<<4)|((uint32_t)(b>>4)<<8)|((uint32_t)(a>>4)<<12);
    return (uint32_t)r|(uint32_t)g<<8|(uint32_t)b<<16|(uint32_t)a<<24;
}
#endif
