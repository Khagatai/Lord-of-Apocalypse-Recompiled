/* SPDX-License-Identifier: GPL-3.0-or-later
 * Controller editing uses the supervisor; reload only after an acknowledged save. */
#include "controller-settings-contract.h"
static int control_codes[LOA_CONTROL_CODES],control_saved[LOA_CONTROL_CODES],control_ready,control_pending,control_page,control_camera_page,control_return_focus;
static unsigned control_sequence;
static ULONGLONG control_deadline;
static char control_notice[180]="Change a binding with Left / Right or Confirm.";
extern void sdl3vk_reset_input_profile(void) __attribute__((weak));
extern void sdl3vk_init_input_profile(void) __attribute__((weak));
extern void loa_camera_set_options(int,int);
static void control_initialize(void){
    if(control_ready)return;control_ready=1;
    memcpy(control_codes,loa_control_defaults,sizeof control_codes);
    const char *text=getenv("LOA_CONTROLLER_CODES");int parsed[LOA_CONTROL_CODES],valid=text!=NULL;
    for(int i=0;valid&&i<LOA_CONTROL_CODES;i++){
        char *end;long n=strtol(text,&end,10);
        int limit=i<LOA_BINDING_CODES?LOA_CONTROL_SOURCES:i==LOA_BINDING_CODES?2:5;
        if(end==text||n<0||n>=limit){valid=0;break;}
        parsed[i]=(int)n;text=end;
    }
    if(valid)memcpy(control_codes,parsed,sizeof parsed);
    memcpy(control_saved,control_codes,sizeof control_saved);
}
static void control_submit(void){
    if(!folder[0]){strcpy(control_notice,"Start through LordOfApocalypse.exe to save controls.");return;}
    char data[512];int used=snprintf(data,sizeof data,"{\"sequence\":%u,\"codes\":[",++control_sequence);
    for(int i=0;i<LOA_CONTROL_CODES;i++)used+=snprintf(data+used,sizeof data-used,"%s%d",i?",":"",control_codes[i]);
    snprintf(data+used,sizeof data-used,"]}");
    if(!write_message(L"controller-request.json",data)){strcpy(control_notice,"Could not request a controller save.");return;}
    control_pending=1;control_deadline=GetTickCount64()+10000;strcpy(control_notice,"Saving controller bindings...");
}
static void control_poll(void){
    if(!control_pending)return;
    wchar_t target[32768];swprintf(target,32768,L"%ls\\controller-ack.json",folder);
    HANDLE file=CreateFileW(target,GENERIC_READ,FILE_SHARE_READ|FILE_SHARE_WRITE|FILE_SHARE_DELETE,NULL,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,NULL);
    if(file!=INVALID_HANDLE_VALUE){
        char text[160]={0};DWORD got=0;ReadFile(file,text,sizeof text-1,&got,NULL);CloseHandle(file);
        char error[80];NkJsonNode *ack=nk_json_parse(text,got,error,sizeof error);int64_t seq=0;
        nk_json_get_int64(nk_json_obj_get(ack,"sequence"),&seq);
        if(seq==control_sequence){
            control_pending=0;bool ok=false;nk_json_get_bool(nk_json_obj_get(ack,"ok"),&ok);
            if(ok){
                memcpy(control_saved,control_codes,sizeof control_codes);
                loa_camera_set_options(control_codes[LOA_BINDING_CODES],control_codes[LOA_BINDING_CODES+1]);
                if(sdl3vk_reset_input_profile&&sdl3vk_init_input_profile){sdl3vk_reset_input_profile();sdl3vk_init_input_profile();strcpy(control_notice,"Bindings saved and applied. Host-menu navigation is unchanged.");}
                else strcpy(control_notice,"Bindings saved. Restart to apply in this renderer.");
                if(getenv("LOA_SETTINGS_TRACE"))fprintf(stderr,"LOA_CONTROLS: saved sequence=%u reloaded=%d\n",control_sequence,sdl3vk_reset_input_profile&&sdl3vk_init_input_profile);
            }else{memcpy(control_codes,control_saved,sizeof control_codes);strcpy(control_notice,"Controller save failed. Previous bindings are kept.");}
        }
        nk_json_free(ack);
    }
    if(control_pending&&GetTickCount64()>control_deadline){control_pending=0;strcpy(control_notice,"Controller save timed out. Check this run's controller-error.txt.");}
}
NkOverlayAction __wrap_nk_overlay_page_controls(NkUi *ui,NkOverlayState *state,const NkOverlayModel *model){
    initialize();control_initialize();control_poll();
    if(getenv("LOA_SETTINGS_TRACE")){
        static NkUiId last;
        for(int n=630;n<=690;n++)if(nk_ui_button_focused(ui,ID(n))&&last!=ID(n)){last=ID(n);fprintf(stderr,"LOA_CONTROLS: focus=%d page=%d\n",n,control_page);}
    }
    NkOverlayAction result=nk_overlay_action(NK_OVERLAY_ACT_NONE,0);
    const NkUiTheme *theme=nk_ui_theme(ui);
    if(nk_overlay_page_begin(ui,model,760)<=0)return result;
    if(control_camera_page){
        nk_overlay_eyebrow(ui,ID(680),NULL,"Game paused / Camera",theme->accent_dark);
        nk_ui_text_role(ui,ID(681),"Camera rotation",NK_UI_TYPE_TITLE,theme->paper);
        for(int row=0;row<2;row++){
            int index=LOA_BINDING_CODES+row,limit=row?5:2;NkUiId id=ID(685+row);char text[160];
            snprintf(text,sizeof text,"%s: %s",row?"Rotation speed":"Camera mode",row?loa_camera_speeds[control_codes[index]]:loa_camera_modes[control_codes[index]]);
            int focused=nk_ui_button_focused(ui,id),next=control_codes[index];
            if(nk_ui_button(ui,id,text,NK_UI_BUTTON_SMALL|NK_UI_BUTTON_GROW|NK_UI_BUTTON_OWNS_HORIZONTAL|(!folder[0]?NK_UI_BUTTON_DISABLED:0))&&!control_pending)next=(next+1)%limit;
            NkUiNavDir dir=NK_UI_DIR_NONE;
            if(focused&&!control_pending&&folder[0]&&nk_ui_take_event(ui,NK_UI_EV_NAV,&dir)){
                if(dir==NK_UI_DIR_RIGHT&&next<limit-1)next++;
                if(dir==NK_UI_DIR_LEFT&&next>0)next--;
            }
            if(next!=control_codes[index]){control_codes[index]=next;control_submit();}
        }
        NkUiTextStyle foot=nk_ui_type(NK_UI_TYPE_FOOTNOTE,theme->muted);foot.wrap=true;
        nk_ui_text(ui,ID(688),"The right stick smoothly rotates and tilts the free camera. While locked on, it uses the game's original enemy and weak-point switching. Physical D-pad controls stay available. Original PSP mode keeps the original camera steps.",&foot);
        nk_ui_text(ui,ID(689),control_notice,&foot);
        if(nk_ui_button(ui,ID(690),"Back to bindings",NK_UI_BUTTON_SMALL|NK_UI_BUTTON_GROW)||nk_ui_take_event(ui,NK_UI_EV_BACK,NULL)){control_camera_page=0;control_return_focus=1;}
        nk_overlay_page_end(ui,"",NULL,0);return result;
    }
    nk_overlay_eyebrow(ui,ID(600),NULL,"Game paused / Controller",theme->accent_dark);
    nk_ui_text_role(ui,ID(601),"Controller bindings",NK_UI_TYPE_TITLE,theme->paper);
    char page[100];snprintf(page,sizeof page,"Bindings %d-%d of 12. Both inputs on a row remain active.",control_page*4+1,control_page*4+4);
    nk_ui_text_role(ui,ID(602),page,NK_UI_TYPE_FOOTNOTE,theme->muted);
    for(int row=0;row<4;row++){
        int index=control_page*4+row;
        NkUiLayout line=nk_overlay_layout(NK_UI_LAYOUT_ROW,nk_overlay_grow(),nk_overlay_fit(),8);
        if(nk_ui_begin_container(ui,ID(610+row),&line,NULL)){
            for(int slot=0;slot<2;slot++){
                int i=2*index+slot;NkUiId id=ID(630+i);char text[160];
                snprintf(text,sizeof text,"%s %s: %s",loa_control_labels[index],slot?"secondary":"primary",loa_control_sources[control_codes[i]]);
                int focused=nk_ui_button_focused(ui,id),next=control_codes[i];
                if(nk_ui_button(ui,id,text,NK_UI_BUTTON_SMALL|NK_UI_BUTTON_GROW|NK_UI_BUTTON_OWNS_HORIZONTAL|(!folder[0]?NK_UI_BUTTON_DISABLED:0))&&!control_pending)next=(next+1)%LOA_CONTROL_SOURCES;
                NkUiNavDir dir=NK_UI_DIR_NONE;
                if(focused&&!control_pending&&nk_ui_take_event(ui,NK_UI_EV_NAV,&dir)){
                    if(dir==NK_UI_DIR_RIGHT&&next<LOA_CONTROL_SOURCES-1)next++;
                    if(dir==NK_UI_DIR_LEFT&&next>0)next--;
                }
                if(next!=control_codes[i]){
                    if(next)for(int j=0;j<LOA_BINDING_CODES;j++)if(j!=i&&control_codes[j]==next)control_codes[j]=0;
                    control_codes[i]=next;control_submit();
                }
            }
            nk_ui_end_container(ui);
        }
    }
    if(nk_ui_button(ui,ID(670),"Camera rotation settings",NK_UI_BUTTON_SMALL|NK_UI_BUTTON_GROW| (control_pending?NK_UI_BUTTON_DISABLED:0))){control_camera_page=1;nk_ui_cancel_press(ui);}
    if(nk_ui_button(ui,ID(660),"Next bindings page",NK_UI_BUTTON_SMALL|NK_UI_BUTTON_GROW| (control_pending?NK_UI_BUTTON_DISABLED:0))){control_page=(control_page+1)%3;nk_ui_cancel_press(ui);}
    if(nk_ui_button(ui,ID(661),"Restore default controller bindings",NK_UI_BUTTON_SMALL|NK_UI_BUTTON_GROW|((control_pending||!folder[0])?NK_UI_BUTTON_DISABLED:0))){memcpy(control_codes,loa_control_defaults,sizeof control_codes);control_submit();}
    NkUiTextStyle foot=nk_ui_type(NK_UI_TYPE_FOOTNOTE,theme->muted);foot.wrap=true;
    nk_ui_text(ui,ID(662),control_notice,&foot);
    nk_ui_text(ui,ID(663),"Assigning a used input unbinds its old slot. Left stick moves; default right stick controls the PSP camera. Escape and host-menu controls remain available.",&foot);
    if(nk_ui_button(ui,NK_OVERLAY_ID_CONTROLS_BACK,"Back",NK_UI_BUTTON_SMALL|NK_UI_BUTTON_GROW)||nk_ui_take_event(ui,NK_UI_EV_BACK,NULL))nk_overlay_go(state,NK_OVERLAY_SCREEN_MENU,NK_OVERLAY_ID_CONTROLS);
    if(control_return_focus){control_return_focus=0;nk_ui_focus(ui,ID(670));}
    static const NkUiPromptItem prompts[]={{NK_UI_PROMPT_ACT_MOVE,"Choose"},{NK_UI_PROMPT_ACT_CONFIRM,"Change"},{NK_UI_PROMPT_ACT_BACK,"Back"}};
    nk_overlay_page_end(ui,"",prompts,sizeof prompts/sizeof prompts[0]);return result;
}
