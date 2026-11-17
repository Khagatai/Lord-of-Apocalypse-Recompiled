/* SPDX-License-Identifier: GPL-3.0-or-later
 * Title timing enhancement. Real media handlers always execute and retain errors.
 * Context lifetime conservatively blocks the enhancement throughout movies. */
#include "recomp.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int initialized, requested, uncertain;
static uint32_t contexts[16], players[16];
static HleFn handlers[5];
static unsigned long updates, enhanced, media_blocked, wait_checks;
static double delta_total;
static uint32_t first_v,last_v,sample_v;


static void summary(void) {
    fprintf(stderr,"LOA_FPS: exit (requested=%d updates=%lu enhanced=%lu media_blocked=%lu wait_checks=%lu delta_sum=%.3f first_v=%u last_v=%u uncertain=%d)\n",
        requested,updates,enhanced,media_blocked,wait_checks,delta_total,first_v,last_v,uncertain);
}
static void initialize(void) {
    if(initialized)return;
    initialized=1;
    const char *value=getenv("LOA_GAMEPLAY_FPS");
    if(value && strcmp(value,"30") && strcmp(value,"60")){
        fprintf(stderr,"LOA_FPS: invalid LOA_GAMEPLAY_FPS; use 30 or 60\n");exit(1);
    }
    requested=value && !strcmp(value,"60")?60:30;
    atexit(summary);
    fprintf(stderr,"LOA_FPS: gameplay=%d; movie-context protection=on; guest timing enhancement=%s\n",requested,requested==60?"on":"off");
}
static int busy(void) {
    if(uncertain)return 1;
    for(int i=0;i<16;i++)if(contexts[i] || players[i])return 1;
    return 0;
}
static void track(uint32_t *slots,uint32_t key,int add) {
    if(!key){uncertain=1;return;}
    for(int i=0;i<16;i++)if(slots[i]==key){if(!add)slots[i]=0;return;}
    if(!add)return; /* A successful stop/delete of an idle player is legitimate. */
    for(int i=0;i<16;i++)if(!slots[i]){slots[i]=key;return;}
    uncertain=1;
}
int loa_fps_enabled(void) {
    initialize();wait_checks++;
    return requested==60 && !busy();
}
int loa_fps_movie_restore(void) {
    initialize();
    return requested==60 && busy();
}
int loa_fps_update(CpuState *s,uint32_t object,uint32_t delta_bits) {
    initialize();
    uint32_t v=sr_display_vcount();
    if(!updates)first_v=v;
    float delta;memcpy(&delta,&delta_bits,sizeof delta);
    updates++;last_v=v;delta_total+=delta;
    int active=requested==60 && !busy();
    /* A movie may be created inside this update's callback, after its delta
     * was calculated. Restore the floor at this boundary too, before decode. */
    if(requested==60 && busy())s->fi[22]=0x40000000u;
    enhanced+=active;media_blocked+=requested==60 && busy();
    if(getenv("LOA_FPS_TRACE") && v-sample_v>=120){
        sample_v=v;
        fprintf(stderr,"LOA_FPS: sample v=%u object=%08x enhanced=%d media=%d delta=%.6f min=%.6f updates=%lu sum=%.3f\n",
            v,object,active,busy(),delta,s->f[22],updates,delta_total);
    }
    return active;
}

void __real_sr_hle_register(uint32_t,const char *,HleFn);
static uint32_t media(CpuState *s,int which) {
    initialize();
    uint32_t key=s->r[4];
    uint32_t result=handlers[which](s);
    if(result==0){
        if(which<2)track(contexts,key,which==0);
        else track(players,key,which==2);
        fprintf(stderr,"LOA_FPS: media event=%d key=%08x protected=%d result=%08x v=%u\n",which,key,busy(),result,sr_display_vcount());
    }
    return result;
}
static uint32_t create(CpuState *s){return media(s,0);}
static uint32_t destroy(CpuState *s){return media(s,1);}
static uint32_t start(CpuState *s){return media(s,2);}
static uint32_t stop(CpuState *s){return media(s,3);}
static uint32_t remove_player(CpuState *s){return media(s,4);}
void __wrap_sr_hle_register(uint32_t nid,const char *name,HleFn fn) {
    extern HleFn loa_net_handler(uint32_t) __attribute__((weak));
    if(loa_net_handler){HleFn replacement=loa_net_handler(nid);if(replacement)fn=replacement;}
    static const uint32_t nids[]={0xd8c5f121u,0x606a4649u,0x95a84ee5u,0x1078c008u,0x9b71a274u};
    static HleFn wrappers[]={create,destroy,start,stop,remove_player};
    for(int i=0;i<5;i++)if(nid==nids[i]){
        if(fn==wrappers[i]){fprintf(stderr,"LOA_FPS: recursive media registration refused\n");abort();}
        handlers[i]=fn;fn=wrappers[i];break;
    }
    __real_sr_hle_register(nid,name,fn);
}
