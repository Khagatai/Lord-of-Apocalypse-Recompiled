/* SPDX-License-Identifier: GPL-3.0-or-later */
#ifndef LOA_CONTROLLER_SETTINGS_CONTRACT_H
#define LOA_CONTROLLER_SETTINGS_CONTRACT_H
#define LOA_CONTROL_COUNT 12
#define LOA_BINDING_CODES 24
#define LOA_CONTROL_CODES 26
#define LOA_CONTROL_SOURCES 21
static const int loa_control_defaults[LOA_CONTROL_CODES]={1,0,2,0,3,0,4,0,9,15,10,16,6,0,5,0,11,17,12,18,13,19,14,20,0,2};
static const char *loa_camera_modes[]={"Original PSP","Smooth 360 camera (experimental)"};
static const char *loa_camera_speeds[]={"0.5x","0.75x","1x","1.5x","2x"};
static const char *loa_control_labels[LOA_CONTROL_COUNT]={"Cross","Circle","Square","Triangle","L shoulder","R shoulder","Start","Select","D-pad up","D-pad down","D-pad left","D-pad right"};
static const char *loa_control_sources[LOA_CONTROL_SOURCES]={"Unbound","Cross / A","Circle / B","Square / X","Triangle / Y","Create / View","Options / Menu","L3 / LS click","R3 / RS click","L1 / LB","R1 / RB","D-pad up","D-pad down","D-pad left","D-pad right","L2 / LT","R2 / RT","Right stick up","Right stick down","Right stick left","Right stick right"};
#endif
