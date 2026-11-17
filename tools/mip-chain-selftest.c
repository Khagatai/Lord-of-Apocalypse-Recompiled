/* SPDX-License-Identifier: GPL-3.0-or-later */
#include <stdio.h>
#include <stdlib.h>
#include "mip_chain.c"
#include "tex_scale.h"

int main(void) {
    const int sizes[][2]={{32,32},{64,16},{1,64},{128,32}};
    unsigned cells=0;
    for(unsigned s=0;s<sizeof(sizes)/sizeof(sizes[0]);s++)
    for(int f=2;f<=6;f++) for(int wrap=0;wrap<4;wrap++) {
        int w=sizes[s][0],h=sizes[s][1],levels=5;
        LoaMipLayout p;
        if(!loa_mip_layout(w,h,levels,f,&p)) return 1;
        uint32_t *atlas=calloc((size_t)p.width*p.height,4);
        uint32_t *scaled=malloc((size_t)p.width*p.height*f*f*4);
        if(!atlas || !scaled) return 2;
        for(int l=0;l<levels;l++) {
            uint32_t *src=malloc((size_t)p.w[l]*p.h[l]*4);
            if(!src) return 2;
            for(int y=0;y<p.h[l];y++) for(int x=0;x<p.w[l];x++) {
                unsigned v=(unsigned)(x*29+y*71+l*113);
                src[y*p.w[l]+x]=((v%5?255u:0u)<<24)|((v&255u)<<16)|(((v*3)&255u)<<8)|((l*41u)&255u);
            }
            loa_mip_pack(&p,l,src,wrap&1,wrap&2,atlas); free(src);
        }
        if(!nk_tex_scale_image(atlas,p.width,p.height,f,1,1,scaled)) return 3;
        for(int l=0;l<levels;l++) {
            int lw=p.w[l],lh=p.h[l],sw=lw*f,sh=lh*f;
            uint32_t *src=malloc((size_t)lw*lh*4),*ref=malloc((size_t)sw*sh*4),*row=malloc((size_t)sw*4);
            if(!src || !ref || !row) return 2;
            for(int y=0;y<lh;y++) memcpy(src+(size_t)y*lw,atlas+(size_t)(p.y[l]+y)*p.width+2,(size_t)lw*4);
            if(!nk_tex_scale_image(src,lw,lh,f,wrap&1,wrap&2,ref)) return 3;
            for(int y=0;y<sh;y++) {
                loa_mip_row(&p,l,scaled,sw,sh,y,row);
                if(memcmp(row,ref+(size_t)y*sw,(size_t)sw*4)) {
                    fprintf(stderr,"FAIL isolated mip differs: size=%u factor=%d wrap=%d level=%d row=%d\n",s,f,wrap,l,y);
                    return 4;
                }
            }
            free(src);free(ref);free(row);cells++;
        }
        memset(scaled,0,(size_t)p.width*p.height*f*f*4);
        for(int l=0;l<levels;l++) {
            int sw=(w*f)>>l,sh=(h*f)>>l;
            if(sw<1) sw=1;
            if(sh<1) sh=1;
            uint32_t *ready=malloc((size_t)sw*sh*4),*row=malloc((size_t)sw*4);
            if(!ready || !row) return 2;
            for(int i=0;i<sw*sh;i++) ready[i]=0xFF000000u|(uint32_t)(i*73+l*701);
            loa_mip_pack_ready(&p,l,ready,sw,sh,scaled);
            for(int y=0;y<sh;y++) {
                loa_mip_row(&p,l,scaled,sw,sh,y,row);
                if(memcmp(row,ready+(size_t)y*sw,(size_t)sw*4)) return 6;
            }
            free(ready);free(row);
        }
        free(atlas);free(scaled);
    }
    LoaMipLayout p;
    if(loa_mip_layout(0,32,4,4,&p) || loa_mip_layout(512,512,8,6,&p) || loa_mip_layout(32,32,9,2,&p)) return 5;
    printf("PASS: %u independently scaled mip comparisons and %u ready-PNG round trips; all factors, alpha, wrap/clamp and thin textures\n",cells,cells);
    return 0;
}
