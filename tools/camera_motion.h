/* SPDX-License-Identifier: GPL-3.0-or-later */
#ifndef LOA_CAMERA_MOTION_H
#define LOA_CAMERA_MOTION_H
#include <math.h>
typedef struct { float yaw,velocity; } LoaCameraMotion;
static float loa_camera_axis(int raw){
    float value=raw<0?raw/32768.0f:raw/32767.0f;
    const float deadzone=0.24f;
    if(fabsf(value)<=deadzone)return 0;
    return copysignf((fabsf(value)-deadzone)/(1.0f-deadzone),value);
}
static void loa_camera_integrate(LoaCameraMotion *state,float axis,float seconds,float speed){
    /* Integrate the exponential velocity response analytically. Equal elapsed
     * time gives the same rotation at 30 and 60 updates per second. */
    const float tau=0.07f,pi=3.14159265358979323846f;
    float target=axis*speed*2.09439510239319549f;
    float decay=expf(-seconds/tau);
    state->yaw+=target*seconds+(state->velocity-target)*tau*(1.0f-decay);
    state->velocity=target+(state->velocity-target)*decay;
    state->yaw=remainderf(state->yaw,2.0f*pi);
}
static void loa_camera_integrate_pitch(LoaCameraMotion *state,float axis,float seconds,float speed){
    /* Same response as yaw, with a lower vertical speed and no pole crossing.
     * yaw is the angle member for either axis. Never wrap a clamped pitch. */
    loa_camera_integrate(state,axis,seconds,speed*0.6f);
    const float limit=1.3962634015954636f; /* 80 degrees either side of level */
    if(state->yaw>limit){state->yaw=limit;if(state->velocity>0)state->velocity=0;}
    if(state->yaw<-limit){state->yaw=-limit;if(state->velocity<0)state->velocity=0;}
}
#endif
