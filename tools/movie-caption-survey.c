/* Local read-only movie survey through the pinned native decoder; no audio edits. */
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <fcntl.h>
#include <io.h>
#include "sr_h264.h"
uint8_t *g_mem;
volatile int g_sr_vram_read_pending;
int sr_perf_enabled;
uint64_t sr_perf_now_ns_impl(void){abort();} /* Profiling is disabled in this tool. */
void sr_perf_h264(uint64_t start,int result){(void)start;(void)result;}
void sr_ge_vram_write_prepare(uint32_t address,uint32_t length){(void)address;(void)length;abort();}
void sr_ge_vram_write_commit(uint32_t address,uint32_t length){(void)address;(void)length;abort();}
static uint8_t pixels[512*512*4];
static uint32_t frames,step;
static int output_frames(int decoder,int eos) {
    for(unsigned guard=0;guard<128;guard++) {
        SrH264FrameTarget target={0};SrH264FrameInfo info={0};
        target.kind=SR_H264_TARGET_HOST;target.host_buffer=pixels;
        target.host_width=target.host_height=512;target.host_stride=512*4;
        int result=sr_h264_frame_ex(decoder,eos,&target,&info);
        if(result<0)return 0;
        if(!result)return 1;
        if(info.width<1 || info.height<1 || info.width>512 || info.height>512)return 0;
        frames++;
        if((frames-1)%step==0) {
            uint32_t header[4]={0x31464f4c,frames,(uint32_t)info.width,(uint32_t)info.height};
            int64_t pts=info.has_pts?info.pts:-1;
            if(fwrite(header,sizeof header,1,stdout)!=1 || fwrite(&pts,sizeof pts,1,stdout)!=1)return 0;
            for(int y=0;y<info.height;y++)if(fwrite(pixels+y*512*4,info.width*4,1,stdout)!=1)return 0;
            fflush(stdout);
        }
    }
    return 0;
}
int main(int argc,char **argv) {
    if(argc!=5)return 2;
    uint64_t offset=strtoull(argv[2],NULL,10),remaining=strtoull(argv[3],NULL,10);
    step=(uint32_t)strtoul(argv[4],NULL,10);
    if(remaining<2048 || !step || step>300)return 2;
    FILE *source=fopen(argv[1],"rb");if(!source)return 3;
    if(_fseeki64(source,offset,SEEK_SET))return 3;
    uint8_t header[2048];if(fread(header,sizeof header,1,source)!=1 || memcmp(header,"PSMF",4))return 4;
    unsigned start=(unsigned)header[8]<<24|(unsigned)header[9]<<16|(unsigned)header[10]<<8|header[11];
    if(start<2048 || start>remaining || _fseeki64(source,offset+start,SEEK_SET))return 4;
    remaining-=start;int decoder=sr_h264_create();if(decoder<0)return 5;
    _setmode(_fileno(stdout),_O_BINARY);
    uint8_t packet[2048];
    while(remaining) {
        size_t n=remaining<sizeof packet?(size_t)remaining:sizeof packet;
        if(fread(packet,n,1,source)!=1 || sr_h264_feed(decoder,packet,(uint32_t)n)<0)return 6;
        remaining-=n;uint64_t consumed;int64_t pts;
        while(sr_h264_au_take(decoder,0,&consumed,&pts)>0){}
        if(!output_frames(decoder,0))return 7;
    }
    uint64_t consumed;int64_t pts;
    while(sr_h264_au_take(decoder,1,&consumed,&pts)>0){}
    if(!output_frames(decoder,1))return 8;
    sr_h264_destroy(decoder);fclose(source);
    fprintf(stderr,"MOVIE_SURVEY: decoded_frames=%u sampled_every=%u\n",frames,step);
    return frames?0:9;
}
