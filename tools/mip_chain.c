/* SPDX-License-Identifier: GPL-3.0-or-later
 * Title-owned pure packing helpers. Each authored mip keeps a separate two-
 * texel border; xBRZ can process the atlas in one bounded worker job without
 * sampling a neighbouring mip. No guest addresses or game bytes live here. */
#include <stdint.h>
#include <stddef.h>
#include <string.h>

typedef struct {
    int width, height, levels, factor;
    int w[8], h[8], y[8];
    uint64_t gpu_bytes;
} LoaMipLayout;

static int loa_mip_layout(int w,int h,int levels,int factor,LoaMipLayout *out) {
    if(!out || w<1 || h<1 || w>512 || h>512 || levels<2 || levels>8 || factor<2 || factor>6 ||
       w*factor>2048 || h*factor>2048) return 0;
    memset(out,0,sizeof(*out));
    out->width=w+4; out->levels=levels; out->factor=factor;
    int max_side=w*factor>h*factor?w*factor:h*factor, max_levels=1;
    while(max_side>1) { max_side>>=1; max_levels++; }
    if(levels>max_levels) return 0;
    for(int l=0;l<levels;l++) {
        out->w[l]=(w>>l)>0?w>>l:1; out->h[l]=(h>>l)>0?h>>l:1;
        out->y[l]=out->height+2; out->height+=out->h[l]+4;
        int sw=(w*factor)>>l,sh=(h*factor)>>l;
        out->gpu_bytes+=(uint64_t)(sw>0?sw:1)*(uint64_t)(sh>0?sh:1)*4u;
    }
    return 1;
}

static int loa_mip_edge(int v,int extent,int clamp) {
    if(clamp) return v<0?0:v>=extent?extent-1:v;
    v%=extent; return v<0?v+extent:v;
}

static void loa_mip_pack(const LoaMipLayout *p,int level,const uint32_t *src,
                         int clamp_u,int clamp_v,uint32_t *atlas) {
    int w=p->w[level],h=p->h[level],start=p->y[level]-2;
    for(int y=0;y<h+4;y++) for(int x=0;x<p->width;x++)
        atlas[(size_t)(start+y)*p->width+x]=src[(size_t)loa_mip_edge(y-2,h,clamp_v)*w+loa_mip_edge(x-2,w,clamp_u)];
}

/* Copy one scaled mip row from the worker's atlas. Very thin mip tails are
 * reduced to Vulkan's actual dimensions, instead of creating an invalid image. */
static void loa_mip_row(const LoaMipLayout *p,int level,const uint32_t *atlas,
                        int target_w,int target_h,int row,uint32_t *out) {
    int sw=p->w[level]*p->factor,sh=p->h[level]*p->factor;
    size_t stride=(size_t)p->width*p->factor;
    size_t y=(size_t)p->y[level]*p->factor+(size_t)row*sh/target_h;
    const uint32_t *src=atlas+y*stride+2*p->factor;
    for(int x=0;x<target_w;x++) out[x]=src[(size_t)x*sw/target_w];
}

/* Ready-made PNG mips already have their final dimensions. Scatter them onto
 * exactly the samples loa_mip_row will gather, including narrow Vulkan tails. */
static void loa_mip_pack_ready(const LoaMipLayout *p,int level,const uint32_t *src,
                               int w,int h,uint32_t *atlas) {
    size_t stride=(size_t)p->width*p->factor;
    int sw=p->w[level]*p->factor,sh=p->h[level]*p->factor;
    for(int y=0;y<h;y++) for(int x=0;x<w;x++) {
        size_t ay=(size_t)p->y[level]*p->factor+(size_t)y*sh/h;
        size_t ax=2u*(size_t)p->factor+(size_t)x*sw/w;
        atlas[ay*stride+ax]=src[(size_t)y*w+x];
    }
}
