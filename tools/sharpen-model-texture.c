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
#include "model-detail.h"
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
