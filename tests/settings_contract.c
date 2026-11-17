#include <stdio.h>
#include "../tools/title_settings_menu.h"
int main(void){
    for(int i=0;i<LOA_SETTINGS_COUNT;i++)printf("%d%c",loa_setting_lengths[i],i==LOA_SETTINGS_COUNT-1?'\n':' ');
    for(int sample=0;sample<24;sample++)for(int preset=0;preset<3;preset++){
        int codes[LOA_SETTINGS_COUNT];for(int i=0;i<LOA_SETTINGS_COUNT;i++)codes[i]=(sample+i)%loa_setting_lengths[i];
        loa_settings_preset(codes,preset);
        for(int i=0;i<LOA_SETTINGS_COUNT;i++)printf("%d%c",codes[i],i==LOA_SETTINGS_COUNT-1?'\n':' ');
    }
    return 0;
}
