/* SPDX-License-Identifier: GPL-3.0-or-later
 * Shared launcher/F1 labels, choices and presets. Codes follow graphics_settings. */
#ifndef LOA_TITLE_SETTINGS_MENU_H
#define LOA_TITLE_SETTINGS_MENU_H
#define LOA_SETTINGS_COUNT 15
static const int loa_setting_lengths[LOA_SETTINGS_COUNT]={2,4,2,6,3,2,2,2,5,2,2,2,6,2,2};
static const char *loa_setting_labels[LOA_SETTINGS_COUNT]={"Language / version","Internal resolution","Display mode","Window resolution",
 "Image scaling","VSync","Performance HUD","FSR 1 upscaling","Texture filtering","Reduce texture shimmer","Reduce colour banding",
 "Supersampling","3D texture smoothing (xBRZ)","Local HD pack (English)","Gameplay frame rate"};
static const char *loa_setting_values[LOA_SETTINGS_COUNT][6]={
 {"English WIP","Japanese"},
 {"1x (480 x 272)","2x (960 x 544)","3x (1440 x 816)","4x (1920 x 1088)"},
 {"Windowed","Borderless fullscreen"},
 {"960 x 544","1280 x 720","1600 x 900","1920 x 1080","2560 x 1440","3840 x 2160"},
 {"Sharp","Integer","Smooth"},{"Off","On"},{"Off","On"},{"Off","On"},
 {"Off","2x","4x","8x","16x"},{"Off","On"},{"Off","On"},{"Off","2x"},
 {"Off","2x","3x","4x","5x","6x"},{"Off","On"},{"Original 30 FPS","Upgraded 60 FPS (experimental)"}};
/* 0 Original, 1 Balanced, 2 High Quality. */
static void loa_settings_preset(int codes[LOA_SETTINGS_COUNT],int preset){
    if(preset==2){codes[1]=3;codes[7]=1;codes[8]=4;codes[9]=codes[10]=codes[11]=1;codes[12]=3;return;}
    int old[LOA_SETTINGS_COUNT];for(int i=0;i<LOA_SETTINGS_COUNT;i++){old[i]=codes[i];codes[i]=0;}
    codes[0]=old[0];codes[5]=1;
    if(preset==1){codes[2]=old[2];codes[3]=old[3];codes[6]=old[6];codes[13]=old[13];codes[14]=old[14];codes[1]=1;codes[8]=2;}
}
#endif
