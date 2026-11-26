/* Synthetic SDL devices exercise the real SDL DLL and pinned native evaluator.
 * This does not emulate or validate a physical USB/Bluetooth HID transport. */
#include <SDL3/SDL.h>
#include "nk_input_profile.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

static void state(SDL_Gamepad *pad, bool *buttons, int16_t *axes) {
    SDL_UpdateGamepads();
    for(int i=0;i<NK_HOST_BUTTON_COUNT;i++) buttons[i]=SDL_GetGamepadButton(pad,(SDL_GamepadButton)i);
    for(int i=0;i<NK_HOST_AXIS_COUNT;i++) axes[i]=SDL_GetGamepadAxis(pad,(SDL_GamepadAxis)i);
}

static void test_pad(NkInputProfile *profile,const char *name,Uint16 vendor,Uint16 product) {
    SDL_VirtualJoystickDesc desc;SDL_INIT_INTERFACE(&desc);
    desc.type=SDL_JOYSTICK_TYPE_GAMEPAD;desc.vendor_id=vendor;desc.product_id=product;
    desc.naxes=SDL_GAMEPAD_AXIS_COUNT;desc.nbuttons=SDL_GAMEPAD_BUTTON_COUNT;
    desc.axis_mask=(1u<<SDL_GAMEPAD_AXIS_COUNT)-1u;
    desc.button_mask=(1u<<SDL_GAMEPAD_BUTTON_COUNT)-1u;desc.name=name;
    SDL_JoystickID id=SDL_AttachVirtualJoystick(&desc);assert(id);
    SDL_Gamepad *pad=SDL_OpenGamepad(id);
    if(!pad){fprintf(stderr,"SDL_OpenGamepad: %s\n",SDL_GetError());assert(pad);}
    SDL_Joystick *joy=SDL_GetGamepadJoystick(pad);assert(joy);
    /* Virtual joystick axes are signed; SDL normalizes trigger rest to zero. */
    assert(SDL_SetJoystickVirtualAxis(joy,SDL_GAMEPAD_AXIS_LEFT_TRIGGER,SDL_JOYSTICK_AXIS_MIN));
    assert(SDL_SetJoystickVirtualAxis(joy,SDL_GAMEPAD_AXIS_RIGHT_TRIGGER,SDL_JOYSTICK_AXIS_MIN));
    bool buttons[NK_HOST_BUTTON_COUNT]={0};int16_t axes[NK_HOST_AXIS_COUNT]={0};
    state(pad,buttons,axes);assert(nk_input_profile_eval_buttons(profile,buttons,axes)==0);
    const int source[]={SDL_GAMEPAD_BUTTON_SOUTH,SDL_GAMEPAD_BUTTON_EAST,SDL_GAMEPAD_BUTTON_WEST,SDL_GAMEPAD_BUTTON_NORTH,
        SDL_GAMEPAD_BUTTON_LEFT_SHOULDER,SDL_GAMEPAD_BUTTON_RIGHT_SHOULDER,SDL_GAMEPAD_BUTTON_START,SDL_GAMEPAD_BUTTON_BACK,
        SDL_GAMEPAD_BUTTON_DPAD_UP,SDL_GAMEPAD_BUTTON_DPAD_DOWN,SDL_GAMEPAD_BUTTON_DPAD_LEFT,SDL_GAMEPAD_BUTTON_DPAD_RIGHT};
    const NkPspButton target[]={NK_PSP_BTN_CROSS,NK_PSP_BTN_CIRCLE,NK_PSP_BTN_SQUARE,NK_PSP_BTN_TRIANGLE,
        NK_PSP_BTN_LTRIGGER,NK_PSP_BTN_RTRIGGER,NK_PSP_BTN_START,NK_PSP_BTN_SELECT,
        NK_PSP_BTN_UP,NK_PSP_BTN_DOWN,NK_PSP_BTN_LEFT,NK_PSP_BTN_RIGHT};
    for(unsigned i=0;i<sizeof source/sizeof source[0];i++) {
        assert(SDL_SetJoystickVirtualButton(joy,source[i],true));state(pad,buttons,axes);
        assert(nk_input_profile_eval_buttons(profile,buttons,axes)==nk_psp_button_bitmask(target[i]));
        if(i>=8)assert(nk_input_profile_eval_navigation(profile,buttons,axes));
        assert(SDL_SetJoystickVirtualButton(joy,source[i],false));state(pad,buttons,axes);
        assert(nk_input_profile_eval_buttons(profile,buttons,axes)==0);
    }
    const int stick_axis[]={SDL_GAMEPAD_AXIS_RIGHTX,SDL_GAMEPAD_AXIS_RIGHTX,SDL_GAMEPAD_AXIS_RIGHTY,SDL_GAMEPAD_AXIS_RIGHTY};
    const int stick_value[]={-20000,20000,-20000,20000};
    const NkPspButton direction[]={NK_PSP_BTN_LEFT,NK_PSP_BTN_RIGHT,NK_PSP_BTN_UP,NK_PSP_BTN_DOWN};
    for(int i=0;i<4;i++) {
        assert(SDL_SetJoystickVirtualAxis(joy,stick_axis[i],stick_value[i]));state(pad,buttons,axes);
        assert(nk_input_profile_eval_buttons(profile,buttons,axes)==nk_psp_button_bitmask(direction[i]));
        uint8_t x,y;nk_input_profile_eval_analog(profile,axes,&x,&y);assert(x==128&&y==128);
        assert(SDL_SetJoystickVirtualAxis(joy,stick_axis[i],0));state(pad,buttons,axes);
        assert(nk_input_profile_eval_buttons(profile,buttons,axes)==0);
    }
    for(int i=0;i<2;i++) {
        int axis=i?SDL_GAMEPAD_AXIS_RIGHT_TRIGGER:SDL_GAMEPAD_AXIS_LEFT_TRIGGER;
        assert(SDL_SetJoystickVirtualAxis(joy,axis,20000));state(pad,buttons,axes);
        assert(nk_input_profile_eval_buttons(profile,buttons,axes)==nk_psp_button_bitmask(i?NK_PSP_BTN_RTRIGGER:NK_PSP_BTN_LTRIGGER));
        assert(SDL_SetJoystickVirtualAxis(joy,axis,SDL_JOYSTICK_AXIS_MIN));state(pad,buttons,axes);
    }
    assert(SDL_SetJoystickVirtualAxis(joy,SDL_GAMEPAD_AXIS_LEFTX,25000));state(pad,buttons,axes);
    uint8_t x,y;nk_input_profile_eval_analog(profile,axes,&x,&y);assert(x>128&&y==128);
    assert(SDL_SetJoystickVirtualAxis(joy,SDL_GAMEPAD_AXIS_LEFTX,0));state(pad,buttons,axes);
    SDL_GamepadType type=SDL_GetGamepadType(pad);
    if(vendor==0x054c) {
        assert(type==(product==0x0ce6?SDL_GAMEPAD_TYPE_PS5:SDL_GAMEPAD_TYPE_PS4));
        assert(SDL_GetGamepadButtonLabel(pad,SDL_GAMEPAD_BUTTON_SOUTH)==SDL_GAMEPAD_BUTTON_LABEL_CROSS);
        assert(SDL_GetGamepadButtonLabel(pad,SDL_GAMEPAD_BUTTON_EAST)==SDL_GAMEPAD_BUTTON_LABEL_CIRCLE);
        assert(SDL_GetGamepadButtonLabel(pad,SDL_GAMEPAD_BUTTON_WEST)==SDL_GAMEPAD_BUTTON_LABEL_SQUARE);
        assert(SDL_GetGamepadButtonLabel(pad,SDL_GAMEPAD_BUTTON_NORTH)==SDL_GAMEPAD_BUTTON_LABEL_TRIANGLE);
    }
    printf("PASS: %s (SDL type=%d) face buttons, shoulders, triggers, Options/Create, D-pad, both sticks\n",name,type);
    SDL_CloseGamepad(pad);assert(SDL_DetachVirtualJoystick(id));SDL_UpdateGamepads();
    /* Reconnection must reopen without a held input from the removed device. */
    id=SDL_AttachVirtualJoystick(&desc);assert(id);pad=SDL_OpenGamepad(id);assert(pad);
    state(pad,buttons,axes);assert(nk_input_profile_eval_buttons(profile,buttons,axes)==0);
    SDL_CloseGamepad(pad);assert(SDL_DetachVirtualJoystick(id));
}

int main(int argc,char **argv) {
    assert(argc==2);FILE *file=fopen(argv[1],"rb");assert(file);char json[32768],diag[512];
    size_t length=fread(json,1,sizeof json-1,file);fclose(file);json[length]=0;
    NkInputProfile profile;assert(nk_input_profile_parse_json(&profile,json,length,diag,sizeof diag)==NK_OK);
    assert(SDL_Init(SDL_INIT_GAMEPAD));
    int physical=0;SDL_JoystickID *existing=SDL_GetGamepads(&physical);SDL_free(existing);
    printf("Existing SDL gamepads before synthetic devices: %d\n",physical);
    test_pad(&profile,"DualSense virtual input",0x054c,0x0ce6);
    test_pad(&profile,"DualShock 4 virtual input",0x054c,0x09cc);
    test_pad(&profile,"Xbox virtual regression",0x045e,0x02ea);
    SDL_Quit();return 0;
}
