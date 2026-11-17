/* Synthetic host input test against the pinned framework's actual mapping evaluator. */
#include "nk_input_profile.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char **argv) {
    assert(argc == 2);
    FILE *f = fopen(argv[1], "rb"); assert(f);
    char json[32768], diag[512];
    size_t length = fread(json, 1, sizeof(json)-1, f); fclose(f); json[length] = 0;
    NkInputProfile profile, expected;
    nk_input_profile_init_default(&expected);
    if (nk_input_profile_parse_json(&profile, json, length, diag, sizeof(diag)) != NK_OK) {
        fprintf(stderr, "Profile refused: %s\n", diag); return 1;
    }
    const NkPspButton directions[] = {NK_PSP_BTN_UP, NK_PSP_BTN_DOWN, NK_PSP_BTN_LEFT, NK_PSP_BTN_RIGHT};
    const NkHostGamepadAxis axes[] = {NK_HOST_AXIS_RIGHTY, NK_HOST_AXIS_RIGHTY, NK_HOST_AXIS_RIGHTX, NK_HOST_AXIS_RIGHTX};
    const NkBindingSourceType types[] = {NK_BINDING_HOST_AXIS_NEG, NK_BINDING_HOST_AXIS_POS, NK_BINDING_HOST_AXIS_NEG, NK_BINDING_HOST_AXIS_POS};
    const int16_t values[] = {-20000, 20000, -20000, 20000};
    for (int i=0; i<4; ++i) {
        expected.psp_buttons[directions[i]].secondary.type = types[i];
        expected.psp_buttons[directions[i]].secondary.index = axes[i];
        expected.psp_buttons[directions[i]].secondary.threshold = 12000;
    }
    /* Full default state, including unrelated controls, keys and calibration, is retained. */
    assert(memcmp(&profile, &expected, sizeof(profile)) == 0);
    bool buttons[NK_HOST_BUTTON_COUNT] = {0};
    int16_t sticks[NK_HOST_AXIS_COUNT] = {0};
    assert(nk_input_profile_eval_buttons(&profile, buttons, sticks) == 0);
    for (int i=0; i<4; ++i) {
        memset(sticks, 0, sizeof(sticks)); sticks[axes[i]] = values[i];
        assert(nk_input_profile_eval_buttons(&profile, buttons, sticks) == nk_psp_button_bitmask(directions[i]));
        uint8_t x=0,y=0; nk_input_profile_eval_analog(&profile, sticks, &x, &y);
        assert(x == 128 && y == 128); /* Right stick does not move the PSP analog nub. */
        sticks[axes[i]] = values[i] < 0 ? -10000 : 10000;
        assert(nk_input_profile_eval_buttons(&profile, buttons, sticks) == 0);
        memset(sticks, 0, sizeof(sticks));
        buttons[expected.psp_buttons[directions[i]].primary.index] = true;
        assert(nk_input_profile_eval_buttons(&profile, buttons, sticks) == nk_psp_button_bitmask(directions[i]));
        assert(nk_input_profile_eval_navigation(&profile, buttons, sticks) != 0);
        memset(buttons, 0, sizeof(buttons));
    }
    puts("PASS: right-stick directions, deadzone, D-pad menus and unchanged remaining defaults");
    return 0;
}
