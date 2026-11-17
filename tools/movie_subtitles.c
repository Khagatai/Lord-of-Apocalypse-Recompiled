/* SPDX-License-Identifier: GPL-3.0-or-later
 * Optional title-owned captions over actual decoded pictures, using decoded
 * frame indices. No fake HLE results, guest patches, audio or movie edits. */
#include "recomp.h"
#include "movie_caption_format.h"
#include <stdio.h>
#include <stdlib.h>
static LoaCaptions captions;
static uint8_t *storage;
static int initialized,last=-1,warned;
static void initialize(void){
    if(initialized)return;
    initialized=1;
    const char *path=getenv("LOA_MOVIE_CAPTIONS");if(!path || !*path)return;
    FILE *file=fopen(path,"rb");if(!file){fprintf(stderr,"LOA_CAPTIONS: cannot open configured captions\n");return;}
    if(fseek(file,0,SEEK_END)){fclose(file);return;}
    long size=ftell(file);rewind(file);
    if(size<16 || size>64*1024*1024){fprintf(stderr,"LOA_CAPTIONS: invalid file size\n");fclose(file);return;}
    storage=malloc((size_t)size);
    if(!storage || fread(storage,1,(size_t)size,file)!=(size_t)size){free(storage);storage=NULL;fclose(file);fprintf(stderr,"LOA_CAPTIONS: failed to read pixels\n");return;}
    fclose(file);const char *error=loa_cap_parse(storage,(size_t)size,&captions);
    if(error){fprintf(stderr,"LOA_CAPTIONS: %s\n",error);free(storage);storage=NULL;return;}
    fprintf(stderr,"LOA_CAPTIONS: loaded movies=%u cues=%u; clock=decoded-picture-index; audio unchanged\n",captions.movies,captions.cues);
}
void loa_movie_caption_picture(uint32_t header_address,uint32_t frame,uint32_t buffer,uint32_t stride,uint32_t width,uint32_t height,unsigned mode){
    initialize();if(!storage)return;
    if(!header_address || !sr_guest_span_readable(header_address,144)){
        if(!warned){fprintf(stderr,"LOA_CAPTIONS: source header unavailable; picture left unchanged\n");warned=1;}
        return;
    }
    uint8_t header[144];if(!sr_guest_copy_in(header,header_address,144))return;
    int selected=loa_cap_find(&captions,header,frame);if(selected<0){last=-1;return;}
    const uint8_t *p=captions.data+captions.table+(uint32_t)selected*32;
    uint32_t x=loa_cap_u32(p+12),y=loa_cap_u32(p+16),w=loa_cap_u32(p+20),h=loa_cap_u32(p+24),offset=loa_cap_u32(p+28);
    unsigned bpp=mode==3?4:2;
    if(mode>3 || width>stride || x+w>width || y+h>height || stride>2048 ||
       (uint64_t)buffer+((uint64_t)(y+h-1)*stride+x+w)*bpp>UINT32_MAX ||
       !sr_guest_span_writable_any_view(buffer,(uint32_t)(((uint64_t)(y+h-1)*stride+x+w)*bpp))){
        if(!warned){fprintf(stderr,"LOA_CAPTIONS: unsupported picture geometry or destination; picture left unchanged\n");warned=1;}
        return;
    }
    uint8_t row[480*4];
    for(uint32_t yy=0;yy<h;yy++){
        const uint8_t *rgba=captions.data+offset+yy*w*4;
        for(uint32_t xx=0;xx<w;xx++){
            uint32_t pixel=loa_cap_pack(rgba[xx*4],rgba[xx*4+1],rgba[xx*4+2],rgba[xx*4+3],mode);
            for(unsigned byte=0;byte<bpp;byte++)row[xx*bpp+byte]=(uint8_t)(pixel>>(8*byte));
        }
        if(!sr_guest_copy_out(buffer+((y+yy)*stride+x)*bpp,row,w*bpp)){
            fprintf(stderr,"LOA_CAPTIONS: picture span changed during caption write\n");return;
        }
    }
    if(selected!=last){fprintf(stderr,"LOA_CAPTIONS: cue=%d frame=%u rectangle=%u,%u,%u,%u\n",selected,frame,x,y,w,h);last=selected;}
}
