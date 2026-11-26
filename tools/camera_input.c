/* SPDX-License-Identifier: GPL-3.0-or-later
 * Keep the game's direction inputs for target / weak-point switching. */
#include "nk_input_profile.h"

extern int loa_camera_free_input(void);
extern uint32_t __real_nk_input_profile_eval_buttons(const NkInputProfile *,
    const bool [NK_HOST_BUTTON_COUNT],const int16_t [NK_HOST_AXIS_COUNT]);

uint32_t __wrap_nk_input_profile_eval_buttons(const NkInputProfile *profile,
    const bool buttons[NK_HOST_BUTTON_COUNT],const int16_t axes[NK_HOST_AXIS_COUNT]){
    if(!profile||!loa_camera_free_input())
        return __real_nk_input_profile_eval_buttons(profile,buttons,axes);
    /* Filter bindings, rather than clearing output bits: a physical D-pad can
     * be held at the same time and must retain its original PSP behaviour.
     * Other actions and the separate host-menu evaluator stay unchanged. */
    NkInputProfile filtered=*profile;
    const NkPspButton directions[]={NK_PSP_BTN_UP,NK_PSP_BTN_DOWN,NK_PSP_BTN_LEFT,NK_PSP_BTN_RIGHT};
    for(unsigned i=0;i<sizeof directions/sizeof *directions;i++){
        NkDigitalBinding *binding=&filtered.psp_buttons[directions[i]];
        NkBindingSource *slots[]={&binding->primary,&binding->secondary};
        for(unsigned j=0;j<2;j++){
            NkBindingSource *source=slots[j];
            if((source->type==NK_BINDING_HOST_AXIS_POS||source->type==NK_BINDING_HOST_AXIS_NEG)&&
               (source->index==NK_HOST_AXIS_RIGHTX||source->index==NK_HOST_AXIS_RIGHTY))
                source->type=NK_BINDING_NONE;
        }
    }
    return __real_nk_input_profile_eval_buttons(&filtered,buttons,axes);
}
