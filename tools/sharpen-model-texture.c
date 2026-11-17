/* SPDX-License-Identifier: GPL-3.0-or-later
 * Local, bounded texture detail pass. Alpha is copied byte for byte.
 * No generative model, source replacement or network access. */
#define STB_IMAGE_IMPLEMENTATION
#define STBI_ONLY_PNG
#define STBI_MAX_DIMENSIONS 2048
#include "stb_image.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static void detail(const unsigned char *src,unsigned char *out,int w,int h){
    const int kernel[5]={1,4,6,4,1};
    for(int y=0;y<h;y++)for(int x=0;x<w;x++){
        size_t at=((size_t)y*w+x)*4u;
        for(int c=0;c<3;c++){
            int sum=0,weight=0;
            for(int dy=-2;dy<=2;dy++)for(int dx=-2;dx<=2;dx++){
                int sx=x+dx,sy=y+dy;
                if(sx<0)sx=0;if(sx>=w)sx=w-1;if(sy<0)sy=0;if(sy>=h)sy=h-1;
                size_t from=((size_t)sy*w+sx)*4u;
                int k=kernel[dx+2]*kernel[dy+2]*src[from+3];
                sum+=k*src[from+c];weight+=k;
            }
            int delta=weight?(src[at+c]-(sum+weight/2)/weight):0;
            /* 25% detail, capped at 6/255; avoid sharpening invisible RGB. */
            delta=src[at+3]?delta/4:0;
            if(delta>6)delta=6;if(delta< -6)delta= -6;
            int value=src[at+c]+delta;out[at+c]=value<0?0:value>255?255:value;
        }
        out[at+3]=src[at+3];
    }
}
static int selftest(void){
    unsigned char src[8*8*4],out[sizeof(src)];
    memset(src,87,sizeof(src));detail(src,out,8,8);
    if(memcmp(src,out,sizeof(src)))return 10;
    for(unsigned i=0;i<sizeof(src);i++)src[i]=(unsigned char)(i*71u);
    detail(src,out,8,8);int changed=0;
    for(unsigned i=0;i<sizeof(src);i++){
        if(i%4==3 && src[i]!=out[i])return 11;
        if(abs((int)src[i]-out[i])>6)return 12;
        changed|=src[i]!=out[i];
    }
    if(!changed)return 13;
    memset(src,0,sizeof(src));detail(src,out,8,8);
    if(memcmp(src,out,sizeof(src)))return 14;
    puts("PASS: flat colour, alpha preservation, bounded detail, transparent texels");return 0;
}
int main(int argc,char **argv){
    if(argc==2 && !strcmp(argv[1],"--self-test"))return selftest();
    if(argc!=3)return 2;
    int w,h,n;unsigned char *src=stbi_load(argv[1],&w,&h,&n,4);
    if(!src || w<1 || h<1 || w>2048 || h>2048){stbi_image_free(src);return 3;}
    unsigned char *out=malloc((size_t)w*h*4u);
    if(!out){stbi_image_free(src);return 4;}
    detail(src,out,w,h);
    FILE *file=fopen(argv[2],"wb");int ok=file && fwrite(out,4,(size_t)w*h,file)==(size_t)w*h;
    if(file && fclose(file))ok=0;
    free(out);stbi_image_free(src);return ok?0:5;
}
