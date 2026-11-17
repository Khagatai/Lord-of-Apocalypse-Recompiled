/* SPDX-License-Identifier: GPL-3.0-or-later
 * In-process adapters for the SAME pinned xBRZ, stb PNG decoder and detail pass.
 * Caller-owned bounded buffers; no file I/O, assets or network operations. */
#define STB_IMAGE_IMPLEMENTATION
#define STBI_ONLY_PNG
#define STBI_MAX_DIMENSIONS 4096
#include "stb_image.h"
#include "tex_scale.h"
#include <stdint.h>
#include <string.h>
#define EXPORT __declspec(dllexport)
EXPORT int loa_scale(const unsigned char *src,size_t bytes,int w,int h,int factor,int wrap,unsigned char *out,size_t capacity){
    if(!src||!out||w<1||h<1||w>512||h>512||factor<2||factor>6||w*factor>2048||h*factor>2048||
       (wrap!=0&&wrap!=1&&wrap!=256&&wrap!=257)||bytes!=(size_t)w*h*4||capacity!=(size_t)w*h*factor*factor*4)return 0;
    return nk_tex_scale_image((const uint32_t *)src,w,h,factor,wrap&1,(wrap>>8)&1,(uint32_t *)out);
}
EXPORT int loa_crop(const unsigned char *png,size_t bytes,int ew,int eh,int x,int y,int w,int h,unsigned char *out,size_t capacity){
    if(!png||!out||bytes<8||bytes>128u*1024u*1024u||ew<1||eh<1||ew>4096||eh>4096||x<0||y<0||w<1||h<1||w>ew||h>eh||x>ew-w||y>eh-h||capacity!=(size_t)w*h*4)return 0;
    int aw,ah,channels;unsigned char *pixels=stbi_load_from_memory(png,(int)bytes,&aw,&ah,&channels,4);
    if(!pixels||aw!=ew||ah!=eh){stbi_image_free(pixels);return 0;}
    for(int row=0;row<h;row++)memcpy(out+(size_t)row*w*4,pixels+((size_t)(row+y)*ew+x)*4,(size_t)w*4);
    stbi_image_free(pixels);return 1;
}
/* Shared verbatim with the legacy CLI, including integer rounding and alpha. */
#include "model-detail.h"
EXPORT int loa_detail(const unsigned char *src,size_t bytes,int w,int h,unsigned char *out,size_t capacity){
    if(!src||!out||w<1||h<1||w>2048||h>2048||bytes!=(size_t)w*h*4||capacity!=bytes)return 0;
    detail(src,out,w,h);return 1;
}
EXPORT int loa_merge(const unsigned char *restored,size_t bytes,const unsigned char *scaled,size_t scaled_bytes,unsigned char *out,size_t capacity){
    if(!restored||!scaled||!out||!bytes||bytes%4||bytes!=scaled_bytes||bytes!=capacity||bytes>64u*1024u*1024u)return 0;
    memcpy(out,scaled,bytes);
    for(size_t i=0;i<bytes;i+=4){
        if(restored[i+3]!=255)return 0;
        if(scaled[i+3])memcpy(out+i,restored+i,3);
    }
    return 1;
}
static int coord(int n,int size,int clamp){
    if(clamp)return n<0?0:n>=size?size-1:n;
    return (n%size+size)%size;
}
EXPORT int loa_pad(const unsigned char *src,size_t bytes,int w,int h,int border,int wrap,unsigned char *out,size_t capacity){
    if(!src||!out||w<1||h<1||w>512||h>512||border<1||border>128||bytes!=(size_t)w*h*4||
       (wrap!=0&&wrap!=1&&wrap!=256&&wrap!=257)||capacity!=(size_t)(w+2*border)*(h+2*border)*4)return 0;
    int n=w*h,opaque=1,visible=0;
    for(int i=0;i<n;i++){opaque&=src[i*4+3]==255;visible|=src[i*4+3]>0;}
    if(!visible)return 0;
    int *owners=NULL,*queue=NULL;
    if(!opaque){
        owners=malloc((size_t)n*sizeof(int));queue=malloc((size_t)n*sizeof(int));
        if(!owners||!queue){free(owners);free(queue);return 0;}
        int begin=0,end=0;
        for(int i=0;i<n;i++){owners[i]=src[i*4+3]>0?i:-1;if(owners[i]>=0)queue[end++]=i;}
        while(begin<end){
            int i=queue[begin++],x=i%w,y=i/w;
            int xs[4]={x-1,x+1,x,x},ys[4]={y,y,y-1,y+1};
            for(int k=0;k<4;k++){
                int nx=xs[k],ny=ys[k];
                if(nx<0||nx>=w){if(wrap&1)continue;nx=coord(nx,w,0);}
                if(ny<0||ny>=h){if(wrap&256)continue;ny=coord(ny,h,0);}
                int next=ny*w+nx;
                if(owners[next]<0){owners[next]=owners[i];queue[end++]=next;}
            }
        }
    }
    int ow=w+2*border,oh=h+2*border;
    for(int y=0;y<oh;y++)for(int x=0;x<ow;x++){
        int i=coord(y-border,h,wrap&256)*w+coord(x-border,w,wrap&1);
        if(owners)i=owners[i];size_t at=((size_t)y*ow+x)*4;
        memcpy(out+at,src+(size_t)i*4,3);out[at+3]=255;
    }
    free(owners);free(queue);return 1;
}
