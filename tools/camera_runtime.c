/* SPDX-License-Identifier: GPL-3.0-or-later
 * Optional right-stick orbit at the measured player-camera rotation boundary. */
#include "recomp.h"
#include <SDL3/SDL.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "camera_motion.h"
static int ready,mode,speed=2;
static const float speeds[]={0.5f,0.75f,1.0f,1.5f,2.0f};
static uint32_t last_v,object;
static LoaCameraMotion motion;
static LoaCameraMotion pitch_motion;
static int pitch_active;
static uint32_t pitch_object,pitch_v;
static int tracking;
static float neutral_yaw,neutral_pitch;
static uint32_t neutral_object,neutral_v;
static int neutral_valid;
static void stop_tracking(void){tracking=0;neutral_valid=0;pitch_active=0;}
void loa_camera_set_options(int selected_mode,int selected_speed){
    if(selected_mode<0||selected_mode>1||selected_speed<0||selected_speed>4)return;
    ready=1;mode=selected_mode;speed=selected_speed;stop_tracking();
}
static void initialize(void){
    if(ready)return;
    const char *m=getenv("LOA_CAMERA_MODE"),*v=getenv("LOA_CAMERA_SPEED");
    int selected=m&&!strcmp(m,"smooth")?1:0,rate=2;
    if(v&&strlen(v)==1&&v[0]>='0'&&v[0]<='4')rate=v[0]-'0';
    loa_camera_set_options(selected,rate);
}
static int active_camera(uint32_t camera){
    const uint32_t manager=0x08d852c8u;
    return camera>=0x08800000u&&camera<=0x09ffff00u&&
        sr_guest_span_readable(manager,0x194u)&&MEM_R8(manager+0x190u)==3&&
        MEM_R32(manager+16u)==camera&&sr_guest_span_readable(camera,0xb9u)&&
        MEM_R32(camera+4u)==0x08cefc5cu;
}
int loa_camera_free_input(void){
    initialize();if(!mode)return 0;
    const uint32_t manager=0x08d852c8u;
    if(!sr_guest_span_readable(manager+16u,4u))return 0;
    uint32_t camera=MEM_R32(manager+16u);
    /* 08872700 stores whether the original camera has a target actor at +a4.
     * Input polling runs on the guest scheduler / GUI thread. Read its current
     * state here instead of caching a host-thread lock-on approximation. */
    return active_camera(camera)&&MEM_R32(camera+0xa4u)==0&&MEM_R8(camera+0xb8u)==0;
}
void loa_camera_update(CpuState *s,uint32_t camera,uint32_t player){
    (void)s;initialize();if(!mode)return;
    /* Measured NPJH50503 camera manager, slot and vtable. Gates prevent writes
     * to inactive/scripted cameras or a changed title layout. */
    const uint32_t manager=0x08d852c8u;
    if(getenv("LOA_CAMERA_TRACE")){
        static uint32_t sampled;
        uint32_t now=sr_display_vcount();
        if(now-sampled>=120){sampled=now;fprintf(stderr,"LOA_CAMERA_GATE: v=%u camera=%08x player=%08x active=%u slot=%08x vtable=%08x\n",now,camera,player,MEM_R8(manager+0x190u),MEM_R32(manager+16u),sr_guest_span_readable(camera+4u,4u)?MEM_R32(camera+4u):0u);}
    }
    if(camera<0x08800000u||camera>0x09ffff00u||player<0x08800000u||player>0x09ffd000u){stop_tracking();return;}
    if(!active_camera(camera)||MEM_R32(camera+0xa4u)!=0||
       !sr_guest_span_writable(camera+0x7cu,8u)||
       !sr_guest_span_writable(player+0x2728u,4u)){stop_tracking();return;}
    int count=0;SDL_JoystickID *ids=SDL_GetGamepads(&count);SDL_Gamepad *pad=NULL;
    if(ids)for(int i=0;i<count&&!pad;i++)pad=SDL_GetGamepadFromID(ids[i]);
    SDL_free(ids);
    if(!pad){stop_tracking();return;}
    float axis=loa_camera_axis(SDL_GetGamepadAxis(pad,SDL_GAMEPAD_AXIS_RIGHTX));
    float vertical=loa_camera_axis(SDL_GetGamepadAxis(pad,SDL_GAMEPAD_AXIS_RIGHTY));
    uint32_t eye=s->r[29]+0xa8u,target=s->r[29]+0x9cu;
    if(MEM_R8(camera+0xb8u)!=0||!sr_guest_span_writable(eye,12u)||!sr_guest_span_readable(target,12u)){stop_tracking();return;}
    float ex,ey,ez,tx,ty,tz,current;
    uint32_t word=MEM_R32(eye);memcpy(&ex,&word,4);word=MEM_R32(eye+8u);memcpy(&ez,&word,4);
    word=MEM_R32(target);memcpy(&tx,&word,4);word=MEM_R32(target+8u);memcpy(&tz,&word,4);
    word=MEM_R32(eye+4u);memcpy(&ey,&word,4);word=MEM_R32(target+4u);memcpy(&ty,&word,4);
    float dx=ex-tx,dz=ez-tz,radius=hypotf(dx,dz);
    float distance=hypotf(radius,ey-ty),current_pitch=atan2f(ey-ty,radius);
    if(!isfinite(radius)||!isfinite(distance)||!isfinite(tx)||!isfinite(ty)||!isfinite(tz)||radius<0.01f||distance>10000){stop_tracking();return;}
    current=atan2f(dx,dz);
    uint32_t v=sr_display_vcount(),elapsed=v-last_v;
    if(pitch_active&&(pitch_object!=camera||v-pitch_v>6))pitch_active=0;
    uint32_t pitch_elapsed=pitch_active?v-pitch_v:elapsed;
    int starting=!tracking||object!=camera||elapsed>6;
    if(starting){
        /* The PSP D-pad update has already run. Start from the last neutral
         * orbit, so a simultaneous digital direction cannot add an initial step. */
        motion.yaw=axis!=0&&neutral_valid&&neutral_object==camera&&v-neutral_v<=6?neutral_yaw:current;
        motion.velocity=0;object=camera;
        elapsed=getenv("LOA_GAMEPLAY_FPS")&&!strcmp(getenv("LOA_GAMEPLAY_FPS"),"60")?1:2;
    }
    if(!pitch_active&&vertical!=0){
        pitch_motion.yaw=neutral_valid&&neutral_object==camera&&v-neutral_v<=6?neutral_pitch:current_pitch;
        pitch_motion.velocity=0;pitch_active=1;pitch_object=camera;pitch_elapsed=elapsed;
    }
    last_v=v;
    int yaw_active=axis!=0||(tracking&&fabsf(motion.velocity)>=0.002f);
    tracking=yaw_active;
    if(!yaw_active){
        neutral_valid=1;neutral_yaw=current;neutral_pitch=current_pitch;neutral_object=camera;neutral_v=v;
    }
    if(!yaw_active&&!pitch_active)return;
    if(!elapsed)return;
    uint32_t angles[]={camera+0x7cu,camera+0x80u,player+0x2728u};float angle_values[3];
    for(int i=0;i<3;i++){
        word=MEM_R32(angles[i]);memcpy(&angle_values[i],&word,4);
        if(!isfinite(angle_values[i])||fabsf(angle_values[i])>1000){stop_tracking();return;}
    }
    float yaw=current;
    if(yaw_active){
        if(starting&&getenv("LOA_CAMERA_TRACE"))fprintf(stderr,"LOA_CAMERA_BEGIN: v=%u from=%.6f original=%.6f\n",v,motion.yaw,current);
        loa_camera_integrate(&motion,-axis,elapsed/59.94005994f,speeds[speed]);yaw=motion.yaw;
        float delta=remainderf(yaw-current,6.28318530717958647692f);
        for(int i=0;i<3;i++){
            float value=remainderf(angle_values[i]+delta,6.28318530717958647692f);memcpy(&word,&value,4);MEM_W32(angles[i],word);
        }
    }
    if(pitch_active){
        /* PPSSPP's original D-pad Up lowers the final view direction's Y angle.
         * The orbit eye/target pair has the opposite orientation at this seam. */
        loa_camera_integrate_pitch(&pitch_motion,-vertical,pitch_elapsed/59.94005994f,speeds[speed]);pitch_v=v;
        radius=distance*cosf(pitch_motion.yaw);ey=ty+distance*sinf(pitch_motion.yaw);
        memcpy(&word,&ey,4);MEM_W32(eye+4u,word);
        if(getenv("LOA_CAMERA_TRACE"))fprintf(stderr,"LOA_CAMERA_PITCH: v=%u axis=%.6f pitch=%.6f dt=%.6f distance=%.6f\n",v,vertical,pitch_motion.yaw,pitch_elapsed/59.94005994f,distance);
    }
    ex=tx+radius*sinf(yaw);ez=tz+radius*cosf(yaw);
    memcpy(&word,&ex,4);MEM_W32(eye,word);memcpy(&word,&ez,4);MEM_W32(eye+8u,word);
    if(yaw_active&&getenv("LOA_CAMERA_TRACE"))fprintf(stderr,"LOA_CAMERA: v=%u camera=%08x player=%08x axis=%.6f yaw=%.6f dt=%.6f\n",v,camera,player,axis,yaw,elapsed/59.94005994f);
}
