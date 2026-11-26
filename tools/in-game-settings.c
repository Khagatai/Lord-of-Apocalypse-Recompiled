/* SPDX-License-Identifier: GPL-3.0-or-later
 * Title-owned host UI, written with Codex. No guest patches or game data.
 * GNU ld wrappers extend the pinned overlay without editing upstream sources. */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <shellapi.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <wchar.h>
#include "overlay/overlay_host.h"
#include "online_runtime.h"
#include "nk_ui_theme.h"
#include "title_settings_menu.h"

/* Apply the title palette through the public getter, without changing upstream. */
const NkUiTheme *__real_nk_ui_theme_n1(void);
const NkUiTheme *__wrap_nk_ui_theme_n1(void){
    static NkUiTheme theme;static int ready;
    if(!ready){
        theme=*__real_nk_ui_theme_n1();ready=1;
        theme.ink=0x1D1C18FFu;theme.paper=0xEEF2F7FFu;theme.surface=0x0D121AFFu;
        theme.surface_raised=0x151D28FFu;theme.surface_high=0x1B2634FFu;
        theme.accent_dark=theme.focus=0xDABA7BFFu;theme.accent_light=0x92713BFFu;
        theme.accent_pressed=0xB6965BFFu;theme.accent_hover=0xEBCD91FFu;
        theme.muted=0x929FB1FFu;theme.dim=0x596777FFu;theme.error=0xF19D8BFFu;
        theme.line=0x222E3DFFu;theme.line_strong=0x2B3747FFu;theme.pressed=0x263344FFu;
        theme.scrim=0x0D121AC7u;theme.art_scrim=0x0D121AB8u;theme.art_label=0xEEF2F7FFu;
    }
    return &theme;
}
NkUiTextStyle __real_nk_ui_type(NkUiTypeRole role,uint32_t rgba);
NkUiTextStyle __wrap_nk_ui_type(NkUiTypeRole role,uint32_t rgba){
    NkUiTextStyle style=__real_nk_ui_type(role,rgba);
    if(role==NK_UI_TYPE_LABEL||role==NK_UI_TYPE_LABEL_L||role==NK_UI_TYPE_LABEL_S){
        style.font=NK_UI_FONT_BODY_SEMIBOLD;style.size_px=role==NK_UI_TYPE_LABEL_L?16:14;
        style.letter_spacing=0.0f;style.line_height=role==NK_UI_TYPE_LABEL_L?22.0f:20.0f;
    }
    return style;
}

#define ID(n) NK_OVERLAY_ID(0x00a000u+(n))
#define COUNT LOA_SETTINGS_COUNT
#define lengths loa_setting_lengths
#define labels loa_setting_labels
#define values loa_setting_values
static int choices[COUNT], saved[COUNT], initial[COUNT], initialized, tab, pending, restart, confirmation, live_apply;
static unsigned sequence;
static ULONGLONG deadline;
static char notice[200]="Choose a setting with Left / Right or Confirm.";
static wchar_t folder[32768];
/* A title-owned subpage of the pause menu keeps the framework ABI/pin intact. */
static int networking_page;
static char join_code[6]="00000",network_notice[200];
static NkJsonNode *network_status;
static ULONGLONG network_polled;
#define NETWORK_BUTTON ID(400)
static void initialize(void);
static int write_message(const wchar_t *name,const char *data);
static int support_page,support_pending;
static unsigned support_sequence;
static ULONGLONG support_deadline;
static char support_notice[200]="Reports are saved locally. Nothing is uploaded.";
#define SUPPORT_BUTTON ID(500)
static void support_send(const char *operation) {
    char data[120];
    snprintf(data,sizeof data,"{\"sequence\":%u,\"op\":\"%s\"}",++support_sequence,operation);
    if(!write_message(L"support-request.json",data)) {
        strcpy(support_notice,"Could not send the request. No action was completed.");return;
    }
    support_pending=1;support_deadline=GetTickCount64()+30000;
    strcpy(support_notice,"Working...");
}
static void support_poll(void) {
    if(!support_pending)return;
    wchar_t target[32768];swprintf(target,32768,L"%ls\\support-ack.json",folder);
    HANDLE file=CreateFileW(target,GENERIC_READ,FILE_SHARE_READ|FILE_SHARE_WRITE|FILE_SHARE_DELETE,
        NULL,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,NULL);
    if(file!=INVALID_HANDLE_VALUE) {
        char text[512],error[80];DWORD got=0;
        if(ReadFile(file,text,sizeof(text)-1,&got,NULL)) {
            text[got]=0;NkJsonNode *ack=nk_json_parse(text,got,error,sizeof error);
            int64_t seq=0;nk_json_get_int64(nk_json_obj_get(ack,"sequence"),&seq);
            if(seq==support_sequence) {
                const char *message=nk_json_get_string(nk_json_obj_get(ack,"message"));
                snprintf(support_notice,sizeof support_notice,"%s",message?message:"No result message was returned.");
                support_pending=0;
            }
            nk_json_free(ack);
        }
        CloseHandle(file);
    }
    if(support_pending && GetTickCount64()>support_deadline) {
        support_pending=0;strcpy(support_notice,"No response. Start through Start-Game.cmd to use tester support.");
    }
}
static void support_menu(NkUi *ui) {
    support_poll();
    const NkUiTheme *theme=nk_ui_theme(ui);
    NkUiTextStyle foot=nk_ui_type(NK_UI_TYPE_FOOTNOTE,theme->muted);foot.wrap=true;
    unsigned flags=NK_UI_BUTTON_SMALL|NK_UI_BUTTON_GROW|(!folder[0]?NK_UI_BUTTON_DISABLED:0);
    if(nk_ui_button(ui,ID(501),"Export bug report",flags) && !support_pending)support_send("export");
    if(nk_ui_button(ui,ID(502),"Mark audio problem",flags) && !support_pending)support_send("mark-audio");
    if(nk_ui_button(ui,ID(503),"Open report folder",flags) && !support_pending)support_send("open-reports");
    if(nk_ui_button(ui,ID(504),"Open save folder",flags) && !support_pending)support_send("open-saves");
    nk_ui_text(ui,ID(505),"Reports include build/settings and numeric audio diagnostics. Saves, game files, screenshots, audio recordings and network identities are excluded.",&foot);
    nk_ui_text(ui,ID(506),"Before play, up to five different save snapshots are kept per language. Unchanged saves are not duplicated. Backups do not include unsaved progress.",&foot);
    nk_ui_text(ui,ID(507),support_notice,&foot);
}
static const char *network_string(const char *key) {
    const char *text=nk_json_get_string(nk_json_obj_get(network_status,key));return text?text:"";
}
static void network_send(const char *fields) {
    NkJsonNode *result=loa_online_request(fields);
    const char *error=nk_json_get_string(nk_json_obj_get(result,"error"));
    snprintf(network_notice,sizeof network_notice,"%s",error?error:loa_online_result(result)==0?"":"The online helper is unavailable. Start through Start-Game.cmd.");
    nk_json_free(result);network_polled=0;
}
static void network_command(const char *op) {
    char fields[160];snprintf(fields,sizeof fields,"\"op\":\"%s\",\"code\":\"%s\"",op,join_code);network_send(fields);
}
static void steam_networking(NkUi *ui,bool configured,const char *state) {
    const NkUiTheme *theme=nk_ui_theme(ui);NkUiTextStyle foot=nk_ui_type(NK_UI_TYPE_FOOTNOTE,theme->muted);foot.wrap=true;
    const char *lobby=network_string("lobby");int in_room=*lobby!=0,busy=!strcmp(state,"creating") || !strcmp(state,"joining");
    nk_ui_text_role(ui,ID(403),!configured?"Steam test connection unavailable":busy?"Waiting for Steam...":in_room?"Steam lobby open":"Steam friends - Spacewar development test",NK_UI_TYPE_BODY,theme->paper);
    if(!configured) {
        if(nk_ui_button(ui,ID(404),"Retry Steam connection",NK_UI_BUTTON_SMALL|NK_UI_BUTTON_GROW))network_send("\"op\":\"backend\",\"backend\":\"steam\"");
    } else if(in_room) {
        int64_t players=0,connected=0;char text[140];nk_json_get_int64(nk_json_obj_get(network_status,"players"),&players);nk_json_get_int64(nk_json_obj_get(network_status,"connected"),&connected);
        snprintf(text,sizeof text,"Players: %d / 4    Confirmed peer connections: %d",(int)players,(int)connected);
        nk_ui_text_role(ui,ID(411),text,NK_UI_TYPE_BODY,theme->paper);
        bool overlay=false;nk_json_get_bool(nk_json_obj_get(network_status,"overlay_available"),&overlay);
        if(nk_ui_button(ui,ID(410),"Invite friends (Steam overlay)",NK_UI_BUTTON_SMALL|NK_UI_BUTTON_GROW|(overlay?0:NK_UI_BUTTON_DISABLED)))network_command("invite");
        if(nk_ui_button(ui,ID(412),"Leave lobby",NK_UI_BUTTON_SMALL|NK_UI_BUTTON_GROW))network_command("leave");
        nk_ui_text(ui,ID(413),"Friends can join through Steam or refresh their friend lobbies here. Once connected, use Room Select in the game. Shared missions remain experimental.",&foot);
    } else {
        unsigned disabled=busy?NK_UI_BUTTON_DISABLED:0;
        if(nk_ui_button(ui,ID(404),"Host Steam lobby",NK_UI_BUTTON_SMALL|NK_UI_BUTTON_GROW|disabled))network_command("create");
        if(nk_ui_button(ui,ID(430),"Refresh friends' lobbies",NK_UI_BUTTON_SMALL|NK_UI_BUTTON_GROW|disabled))network_command("refresh");
        NkJsonNode *rooms=nk_json_obj_get(network_status,"rooms");size_t count=nk_json_array_count(rooms);if(count>16)count=16;
        for(size_t i=0;i<count;i++) {
            NkJsonNode *room=nk_json_array_get(rooms,i);const char *id=nk_json_get_string(nk_json_obj_get(room,"lobby"));
            const char *name=nk_json_get_string(nk_json_obj_get(room,"name"));int64_t players=0;nk_json_get_int64(nk_json_obj_get(room,"players"),&players);
            if(!id || !*id || strlen(id)>20 || strspn(id,"0123456789")!=strlen(id))continue;
            char label[160];snprintf(label,sizeof label,"Join %s (%d / 4)",name?name:"friend",(int)players);
            if(nk_ui_button(ui,ID(440+i),label,NK_UI_BUTTON_SMALL|NK_UI_BUTTON_GROW|disabled)) {
                char fields[100];snprintf(fields,sizeof fields,"\"op\":\"join\",\"lobby\":\"%s\"",id);network_send(fields);
            }
        }
        if(!count)nk_ui_text(ui,ID(431),"No compatible friend lobbies found. Ask your friend to host, then refresh, or accept their Steam invitation.",&foot);
    }
    nk_ui_text(ui,ID(432),"Test App ID 480. Steam may show Spacewar as running. No five-digit code or server address is required.",&foot);
}
static void networking(NkUi *ui,const NkOverlayModel *model) {
    (void)model;
    const NkUiTheme *theme=nk_ui_theme(ui);
    if(!network_polled || GetTickCount64()-network_polled>500) {
        nk_json_free(network_status);network_status=loa_online_request("\"op\":\"status\"");network_polled=GetTickCount64();
    }
    bool configured=false;nk_json_get_bool(nk_json_obj_get(network_status,"service_configured"),&configured);
    const char *state=network_string("state"),*code=network_string("code");
    int in_room=*code!=0,busy=!strcmp(state,"creating") || !strcmp(state,"joining");
    NkUiTextStyle body=nk_ui_type(NK_UI_TYPE_BODY,theme->paper);body.wrap=true;
    NkUiTextStyle foot=nk_ui_type(NK_UI_TYPE_FOOTNOTE,theme->muted);foot.wrap=true;
    int steam=!strcmp(network_string("backend"),"steam");
    int switching=in_room || busy || *network_string("lobby");
    NkUiLayout providers=nk_overlay_layout(NK_UI_LAYOUT_ROW,nk_overlay_grow(),nk_overlay_fit(),8);
    if(nk_ui_begin_container(ui,ID(460),&providers,NULL)) {
        if(nk_ui_button(ui,ID(461),"Steam (Spacewar test)",NK_UI_BUTTON_SMALL|NK_UI_BUTTON_GROW|(steam?NK_UI_BUTTON_PRIMARY:0)|(switching?NK_UI_BUTTON_DISABLED:0)))
            network_send("\"op\":\"backend\",\"backend\":\"steam\"");
        if(nk_ui_button(ui,ID(462),"Room service",NK_UI_BUTTON_SMALL|NK_UI_BUTTON_GROW|(!steam?NK_UI_BUTTON_PRIMARY:0)|(switching?NK_UI_BUTTON_DISABLED:0)))
            network_send("\"op\":\"backend\",\"backend\":\"rooms\"");
        nk_ui_end_container(ui);
    }
    if(steam) {
        steam_networking(ui,configured,state);
        const char *error=network_string("error");if(*error)nk_ui_text(ui,ID(407),error,&foot);
        if(*network_notice)nk_ui_text(ui,ID(416),network_notice,&foot);
        return;
    }
    nk_ui_text(ui,ID(403),!configured?"Online room service is not configured.":
        busy?"Connecting to the room service...":in_room?"Room open - experimental co-op":"Create a room, or enter your friend's five-digit code.",&body);
    if(in_room) {
        char text[160];snprintf(text,sizeof text,"Room code: %s",code);nk_ui_text_role(ui,ID(409),text,NK_UI_TYPE_TITLE,theme->paper);
        if(nk_ui_button(ui,ID(410),"Copy room code",NK_UI_BUTTON_SMALL|NK_UI_BUTTON_GROW)) {
            if(OpenClipboard(NULL)) {
                HGLOBAL memory=GlobalAlloc(GMEM_MOVEABLE,6);
                if(memory) {char *out=GlobalLock(memory);if(out){memcpy(out,code,5);out[5]=0;GlobalUnlock(memory);EmptyClipboard();if(!SetClipboardData(CF_TEXT,memory))GlobalFree(memory);}else GlobalFree(memory);}
                CloseClipboard();
            }
        }
        int64_t players=0,connected=0;nk_json_get_int64(nk_json_obj_get(network_status,"players"),&players);nk_json_get_int64(nk_json_obj_get(network_status,"connected"),&connected);
        NkJsonNode *paths=nk_json_obj_get(network_status,"paths");int relayed=0;
        for(size_t i=0;i<nk_json_array_count(paths);i++){const char *p=nk_json_get_string(nk_json_array_get(paths,i));if(p&&!strcmp(p,"relayed"))relayed=1;}
        snprintf(text,sizeof text,"Players: %d / 4    Connected peers: %d%s",(int)players,(int)connected,connected?(relayed?" (relay in use)":" (direct)"):" (waiting)");
        nk_ui_text(ui,ID(411),text,&body);
        if(nk_ui_button(ui,ID(412),"Leave room",NK_UI_BUTTON_SMALL|NK_UI_BUTTON_GROW))network_command("leave");
        nk_ui_text(ui,ID(413),"Once everyone is connected, use Room Select in the game. A connected room does not yet guarantee a working mission.",&foot);
    } else {
        unsigned disabled=!configured || busy?NK_UI_BUTTON_DISABLED:0;
        if(nk_ui_button(ui,ID(404),"Create room",NK_UI_BUTTON_SMALL|NK_UI_BUTTON_GROW|disabled))network_command("create");
        NkUiLayout row=nk_overlay_layout(NK_UI_LAYOUT_ROW,nk_overlay_grow(),nk_overlay_fit(),8);
        if(nk_ui_begin_container(ui,ID(414),&row,NULL)) {
            for(int i=0;i<5;i++) {
                char digit[2]={join_code[i],0};int focused=nk_ui_button_focused(ui,ID(420+i));
                if(nk_ui_button(ui,ID(420+i),digit,NK_UI_BUTTON_SMALL|NK_UI_BUTTON_GROW|NK_UI_BUTTON_OWNS_HORIZONTAL|disabled))join_code[i]=(char)('0'+(join_code[i]-'0'+1)%10);
                NkUiNavDir direction=NK_UI_DIR_NONE;
                if(focused && !disabled && nk_ui_take_event(ui,NK_UI_EV_NAV,&direction)) {
                    if(direction==NK_UI_DIR_RIGHT)join_code[i]=(char)('0'+(join_code[i]-'0'+1)%10);
                    if(direction==NK_UI_DIR_LEFT)join_code[i]=(char)('0'+(join_code[i]-'0'+9)%10);
                }
            }
            nk_ui_end_container(ui);
        }
        if(nk_ui_button(ui,ID(415),"Paste five-digit code",NK_UI_BUTTON_SMALL|NK_UI_BUTTON_GROW|disabled) && OpenClipboard(NULL)) {
            HANDLE data=GetClipboardData(CF_TEXT);const char *text=data?GlobalLock(data):NULL;
            if(text) {if(strlen(text)==5 && strspn(text,"0123456789")==5)memcpy(join_code,text,6);else strcpy(network_notice,"Copy exactly five digits to paste a room code.");GlobalUnlock(data);}CloseClipboard();
        }
        if(nk_ui_button(ui,ID(405),"Join room",NK_UI_BUTTON_SMALL|NK_UI_BUTTON_GROW|disabled))network_command("join");
        nk_ui_text(ui,ID(406),configured?"Select each digit and change it with Left / Right, or paste the code.":"Room-code connections need the online service to be set up before they can be used.",&foot);
    }
    const char *error=network_string("error");
    if(*error)nk_ui_text(ui,ID(407),error,&foot);
    if(*network_notice)nk_ui_text(ui,ID(416),network_notice,&foot);
}
NkOverlayAction __wrap_nk_overlay_page_menu(NkUi *ui, NkOverlayState *state, const NkOverlayModel *model) {
    initialize();
    if(support_page && getenv("LOA_SETTINGS_TRACE")) {
        static NkUiId last_support_focus;
        for(unsigned i=500;i<520;i++)if(nk_ui_button_focused(ui,ID(i)) && ID(i)!=last_support_focus) {
            last_support_focus=ID(i);fprintf(stderr,"LOA_SUPPORT: focus=%u\n",i);
        }
    }
    if(networking_page && getenv("LOA_SETTINGS_TRACE")) {
        static NkUiId last_network_focus;
        for(unsigned i=400;i<470;i++)if(nk_ui_button_focused(ui,ID(i)) && ID(i)!=last_network_focus) {
            last_network_focus=ID(i);fprintf(stderr,"LOA_NETWORK: focus=%u\n",i);
        }
    }
    NkOverlayAction action=nk_overlay_action(NK_OVERLAY_ACT_NONE,0);
    const NkUiTheme *theme=nk_ui_theme(ui);
    static const NkUiPromptItem prompts[]={ {NK_UI_PROMPT_ACT_MOVE,"Move"},
        {NK_UI_PROMPT_ACT_CONFIRM,"Select"}, {NK_UI_PROMPT_ACT_BACK,"Back"} };
    if(nk_overlay_page_begin(ui,model,(networking_page || support_page)?680:480)<=0) return action;
    nk_overlay_eyebrow(ui,ID(401),NULL,"Lord of Apocalypse / Game paused",theme->accent_dark);
    nk_ui_text_role(ui,ID(402),support_page?"Tester support":networking_page?"Networking":"Lord of Apocalypse",NK_UI_TYPE_TITLE,theme->paper);
    if(support_page) {
        support_menu(ui);
        if(nk_ui_button(ui,ID(508),"Back",NK_UI_BUTTON_SMALL|NK_UI_BUTTON_GROW) || nk_ui_take_event(ui,NK_UI_EV_BACK,NULL)) {
            support_page=0;nk_overlay_go(state,NK_OVERLAY_SCREEN_MENU,SUPPORT_BUTTON);
        }
    } else if(networking_page) {
        networking(ui,model);
        if(nk_ui_button(ui,ID(408),"Back",NK_UI_BUTTON_SMALL|NK_UI_BUTTON_GROW) || nk_ui_take_event(ui,NK_UI_EV_BACK,NULL)) {
            networking_page=0;
            nk_overlay_go(state,NK_OVERLAY_SCREEN_MENU,NETWORK_BUTTON);
        }
    } else {
        if(nk_ui_button(ui,NK_OVERLAY_ID_RESUME,"Resume",NK_UI_BUTTON_PRIMARY|NK_UI_BUTTON_SMALL|NK_UI_BUTTON_GROW))
            action=nk_overlay_action(NK_OVERLAY_ACT_RESUME,0);
        if(nk_ui_button(ui,NK_OVERLAY_ID_SETTINGS,"Settings",NK_UI_BUTTON_SMALL|NK_UI_BUTTON_GROW))
            nk_overlay_go(state,NK_OVERLAY_SCREEN_SETTINGS,0);
        if(nk_ui_button(ui,NETWORK_BUTTON,"Networking",NK_UI_BUTTON_SMALL|NK_UI_BUTTON_GROW)) {
            networking_page=1;
            nk_overlay_go(state,NK_OVERLAY_SCREEN_MENU,ID(404));
            fprintf(stderr,"LOA_MENU: networking opened\n");
        }
        if(nk_ui_button(ui,NK_OVERLAY_ID_CONTROLS,"Controls",NK_UI_BUTTON_SMALL|NK_UI_BUTTON_GROW))
            nk_overlay_go(state,NK_OVERLAY_SCREEN_CONTROLS,0);
        if(nk_ui_button(ui,SUPPORT_BUTTON,"Tester support",NK_UI_BUTTON_SMALL|NK_UI_BUTTON_GROW)) {
            support_page=1;nk_overlay_go(state,NK_OVERLAY_SCREEN_MENU,ID(501));
            fprintf(stderr,"LOA_MENU: tester support opened\n");
        }
        if(model->developer && nk_ui_button(ui,NK_OVERLAY_ID_VRAM,"VRAM viewer",NK_UI_BUTTON_SMALL|NK_UI_BUTTON_GROW))
            nk_overlay_go(state,NK_OVERLAY_SCREEN_VRAM,0);
        if(model->developer && nk_ui_button(ui,NK_OVERLAY_ID_PROFILE,"Profile",NK_UI_BUTTON_SMALL|NK_UI_BUTTON_GROW))
            nk_overlay_go(state,NK_OVERLAY_SCREEN_PROFILE,0);
        if(nk_ui_button(ui,NK_OVERLAY_ID_QUIT,"Quit game",NK_UI_BUTTON_SMALL|NK_UI_BUTTON_GROW))
            nk_overlay_go(state,NK_OVERLAY_SCREEN_QUIT,0);
        if(action.kind==NK_OVERLAY_ACT_NONE && nk_ui_take_event(ui,NK_UI_EV_BACK,NULL))
            action=nk_overlay_action(NK_OVERLAY_ACT_RESUME,0);
    }
    nk_overlay_page_end(ui,"",prompts,sizeof prompts/sizeof prompts[0]);
    return action;
}

static int path(wchar_t *out, const wchar_t *name) {
    return swprintf(out,32768,L"%ls\\%ls",folder,name)>0;
}
static int write_message(const wchar_t *name, const char *data) {
    wchar_t target[32768], temporary[32768];
    path(target,name); path(temporary,L"settings-native.tmp");
    FILE *file=_wfopen(temporary,L"wb");
    if(!file) return 0;
    int ok=fputs(data,file)>=0;
    if(fclose(file)!=0) ok=0;
    if(!ok) { DeleteFileW(temporary); return 0; }
    if(!MoveFileExW(temporary,target,MOVEFILE_REPLACE_EXISTING|MOVEFILE_WRITE_THROUGH)) {
        DeleteFileW(temporary); return 0;
    }
    return 1;
}
#include "in-game-controls.h"
static void initialize(void) {
    if(initialized) return;
    initialized=1; choices[5]=1;
    const char *text=getenv("LOA_SETTINGS_CODES");
    int parsed[COUNT];
    if(text && sscanf(text,"%d %d %d %d %d %d %d %d %d %d %d %d %d %d %d",
      &parsed[0],&parsed[1],&parsed[2],&parsed[3],&parsed[4],&parsed[5],&parsed[6],
      &parsed[7],&parsed[8],&parsed[9],&parsed[10],&parsed[11],&parsed[12],&parsed[13],&parsed[14])==COUNT) {
        int valid=1; for(int i=0;i<COUNT;i++) if(parsed[i]<0 || parsed[i]>=lengths[i]) valid=0;
        if(valid) memcpy(choices,parsed,sizeof choices);
    }
    memcpy(saved,choices,sizeof choices); memcpy(initial,choices,sizeof choices);
    DWORD length=GetEnvironmentVariableW(L"LOA_SETTINGS_DIR",folder,32768);
    if(!length || length>=32768) folder[0]=0;
}
static int needs_restart(void) {
    for(int i=0;i<COUNT;i++) if(i!=2 && i!=4 && i!=6 && choices[i]!=initial[i]) return 1;
    return 0;
}
static void submit(int want_restart) {
    char data[400];
    if(!folder[0]) { strcpy(notice,"Start through Start-Game.cmd to save preferences or restart."); return; }
    sequence++;
    snprintf(data,sizeof data,"{\"sequence\":%u,\"restart\":%s,\"codes\":[%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d]}",
      sequence,want_restart?"true":"false",choices[0],choices[1],choices[2],choices[3],choices[4],choices[5],
      choices[6],choices[7],choices[8],choices[9],choices[10],choices[11],choices[12],choices[13],choices[14]);
    if(!write_message(L"settings-request.json",data)) { strcpy(notice,"Could not write settings request. Preferences were not saved."); return; }
    pending=1; restart=want_restart; deadline=GetTickCount64()+10000;
    strcpy(notice,"Saving settings...");
}

bool __real_nk_overlay_host_due(NkOverlayHost *host, double now);
bool __wrap_nk_overlay_host_due(NkOverlayHost *host, double now) {
    support_poll();
    control_poll();
    return control_pending || pending || live_apply || networking_page || support_page || support_pending || __real_nk_overlay_host_due(host,now);
}

/* Return a stock host action for safe live changes. All other choices are startup-only. */
static NkOverlayAction changed(int index, const NkOverlayModel *model) {
    confirmation=0;
    if(index==2 && model->fullscreen>0) return nk_overlay_action(NK_OVERLAY_ACT_SET_FULLSCREEN,choices[2]);
    if(index==4) return nk_overlay_action(NK_OVERLAY_ACT_SET_SCALING,choices[4]);
    if(index==6) return nk_overlay_action(NK_OVERLAY_ACT_SET_HUD,choices[6]);
    return nk_overlay_action(NK_OVERLAY_ACT_NONE,0);
}

NkOverlayAction __wrap_nk_overlay_page_settings(NkUi *ui, NkOverlayState *state, const NkOverlayModel *model) {
    initialize();
    if(getenv("LOA_SETTINGS_TRACE")) {
        static NkUiId last;
        for(unsigned n=0;n<310;n++) if(nk_ui_button_focused(ui,ID(n)) && ID(n)!=last) {
            last=ID(n); fprintf(stderr,"LOA_SETTINGS: focus=%u tab=%d\n",n,tab);
        }
    }
    NkOverlayAction action=nk_overlay_action(NK_OVERLAY_ACT_NONE,0);
    if(live_apply==3 && model->fullscreen>0) action=nk_overlay_action(NK_OVERLAY_ACT_SET_FULLSCREEN,choices[2]);
    if(live_apply==2) action=nk_overlay_action(NK_OVERLAY_ACT_SET_SCALING,choices[4]);
    if(live_apply==1) action=nk_overlay_action(NK_OVERLAY_ACT_SET_HUD,choices[6]);
    if(live_apply) live_apply--;
    const NkUiTheme *theme=nk_ui_theme(ui);
    static const NkUiPromptItem prompts[]={ {NK_UI_PROMPT_ACT_MOVE,"Move"},
      {NK_UI_PROMPT_ACT_CONFIRM,"Change / choose"}, {NK_UI_PROMPT_ACT_BACK,"Back"} };
    if(pending) {
        wchar_t ack[32768]; path(ack,L"settings-ack.json");
        char text[160]={0}; unsigned seq=0;
        /* The supervisor atomically replaces this mailbox. A CRT fopen on
         * Windows denies deletion and can make that replacement fail. */
        HANDLE file=CreateFileW(ack,GENERIC_READ,FILE_SHARE_READ|FILE_SHARE_WRITE|FILE_SHARE_DELETE,
                               NULL,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,NULL);
        if(file!=INVALID_HANDLE_VALUE) {
            DWORD got=0; ReadFile(file,text,sizeof(text)-1,&got,NULL); CloseHandle(file);
        }
        /* The supervisor writes the compact, ASCII acknowledgement. */
        if(sscanf(text,"{\"sequence\": %u",&seq)==1 && seq==sequence) {
            pending=0;
            if(strstr(text,"\"ok\": true")) {
                memcpy(saved,choices,sizeof choices);
                strcpy(notice,needs_restart()?"Settings saved. Restart to apply pending changes.":"Settings saved.");
                fprintf(stderr,"LOA_SETTINGS: saved sequence=%u restart=%d\n",sequence,restart);
                if(restart && !model->saving) {
                    char ready[80]; snprintf(ready,sizeof ready,"{\"sequence\":%u}",sequence);
                    if(write_message(L"restart-ready.json",ready)) {
                        fprintf(stderr,"LOA_SETTINGS: restart confirmed sequence=%u\n",sequence);
                        return nk_overlay_action(NK_OVERLAY_ACT_QUIT,0);
                    }
                    strcpy(notice,"Could not confirm restart. The game is still running.");
                } else if(restart) strcpy(notice,"Settings saved. Wait for the game to finish saving, then restart.");
            } else strcpy(notice,"Settings could not be saved. See this run's settings-error.txt.");
            restart=0;
        } else if(GetTickCount64()>deadline) {
            pending=restart=0; strcpy(notice,"Settings supervisor did not respond. Restart was cancelled.");
        }
    }
    if(nk_overlay_page_begin(ui,model,760)<=0) return action;
    nk_overlay_eyebrow(ui,ID(1),NULL,"Game paused / Graphics & language",theme->accent_dark);
    nk_ui_text_role(ui,ID(2),"Settings",NK_UI_TYPE_TITLE,theme->paper);
    static const char *tabs[]={"Graphics", "Display", "Advanced", "Language"};
    NkUiLayout row=nk_overlay_layout(NK_UI_LAYOUT_ROW,nk_overlay_grow(),nk_overlay_fit(),8);
    if(nk_ui_begin_container(ui,ID(3),&row,NULL)) {
        for(int i=0;i<4;i++) if(nk_ui_button(ui,ID(10+i),tabs[i],NK_UI_BUTTON_SMALL|(tab==i?NK_UI_BUTTON_PRIMARY:0))) { tab=i; confirmation=0; }
        nk_ui_end_container(ui);
    }
    const int graphics[]={1,4,7,8,14}, display[]={2,3,5,6}, advanced[]={9,10,11,12,13}, language[]={0};
    const int *items=tab==0?graphics:tab==1?display:tab==2?advanced:language;
    int count=tab==0?5:tab==1?4:tab==2?5:tab==3?1:0;
    NkUiLayout rows=nk_overlay_layout(NK_UI_LAYOUT_COLUMN,nk_overlay_grow(),nk_overlay_fit(),6);
    if(nk_ui_begin_container(ui,ID(4),&rows,NULL)) {
    for(int n=0;n<count;n++) {
        int i=items[n]; char text[180];
        snprintf(text,sizeof text,"%s: %s%s",labels[i],values[i][choices[i]],
          (i!=2 && i!=4 && i!=6 && choices[i]!=initial[i])?" (restart)":"");
        NkUiId id=ID(100+i);
        int focused=nk_ui_button_focused(ui,id), next=choices[i];
        int activated=nk_ui_button(ui,id,text,NK_UI_BUTTON_SMALL|NK_UI_BUTTON_GROW|NK_UI_BUTTON_OWNS_HORIZONTAL);
        if(activated && !pending) next=(next+1)%lengths[i];
        NkUiNavDir dir=NK_UI_DIR_NONE;
        if(focused && !pending && nk_ui_take_event(ui,NK_UI_EV_NAV,&dir)) {
            if(dir==NK_UI_DIR_RIGHT && next<lengths[i]-1) next++;
            if(dir==NK_UI_DIR_LEFT && next>0) next--;
        }
        if(next!=choices[i]) {
            choices[i]=next; action=changed(i,model); submit(0);
            fprintf(stderr,"LOA_SETTINGS: changed index=%d choice=%d live=%d\n",i,next,action.kind!=NK_OVERLAY_ACT_NONE);
        }
    }
    if(tab==1 && model->pacing>0 && nk_ui_button(ui,ID(140),model->pacing==1?
      "Frame pacing: PSP timing (this run)":"Frame pacing: No extra cap (this run)",NK_UI_BUTTON_SMALL|NK_UI_BUTTON_GROW))
        action=nk_overlay_action(NK_OVERLAY_ACT_SET_PACING,model->pacing==1?NK_OVERLAY_PACING_UNCAPPED:NK_OVERLAY_PACING_PSP);
    if(tab==3) {
        if(nk_ui_button(ui,ID(201),"Original graphics",NK_UI_BUTTON_SMALL|NK_UI_BUTTON_GROW) && !pending) {
            loa_settings_preset(choices,0);live_apply=3;submit(0);
        }
        if(nk_ui_button(ui,ID(202),"Balanced: 2x resolution / 4x filtering",NK_UI_BUTTON_SMALL|NK_UI_BUTTON_GROW) && !pending) {
            loa_settings_preset(choices,1);live_apply=3;submit(0);
        }
        nk_ui_text_role(ui,ID(203),"Versions keep separate saves. WIP English is the default.",NK_UI_TYPE_FOOTNOTE,theme->muted);
        if(nk_ui_button(ui,ID(205),"High Quality graphics",NK_UI_BUTTON_SMALL|NK_UI_BUTTON_GROW) && !pending) {
            loa_settings_preset(choices,2);live_apply=3;submit(0);
        }
        if(nk_ui_button(ui,ID(204),"Open this run's logs",NK_UI_BUTTON_SMALL|NK_UI_BUTTON_GROW|(folder[0]?0:NK_UI_BUTTON_DISABLED)))
            ShellExecuteW(NULL,L"open",folder,NULL,NULL,SW_SHOWNORMAL);
    }
    nk_ui_end_container(ui);
    }
    NkUiTextStyle foot=nk_ui_type(NK_UI_TYPE_FOOTNOTE,theme->muted); foot.wrap=true;
    nk_ui_text(ui,ID(300),tab==2?"The optional HD pack is built on restart if needed. The first build may take hours.":
      tab==0?"Movies keep original timing in both modes. Frame-rate changes require a restart.":
      "Fullscreen, scaling and HUD apply live. Other changes apply after restarting.",&foot);
    nk_ui_text(ui,ID(301),notice,&foot);
    int differs=memcmp(choices,initial,sizeof choices)!=0;
    unsigned disabled=(pending || model->saving || !folder[0])?NK_UI_BUTTON_DISABLED:0;
    if(differs || confirmation) {
        if(nk_ui_button(ui,ID(302),confirmation?"Confirm restart - unsaved progress will be lost":"Apply and restart game",
                         NK_UI_BUTTON_SMALL|NK_UI_BUTTON_GROW|NK_UI_BUTTON_PRIMARY|disabled)) {
            if(confirmation) submit(1);
            else { confirmation=1; strcpy(notice,"Save your progress in the game first. Confirm to restart with these settings."); }
        }
    }
    if(model->saving) nk_ui_text_role(ui,ID(303),"Restart unavailable while a save is in progress.",NK_UI_TYPE_FOOTNOTE,theme->muted);
    if(nk_ui_button(ui,NK_OVERLAY_ID_SETTINGS_BACK,"Back",NK_UI_BUTTON_SMALL|NK_UI_BUTTON_GROW|(pending?NK_UI_BUTTON_DISABLED:0)) ||
       (!pending && nk_ui_take_event(ui,NK_UI_EV_BACK,NULL))) {
        confirmation=0; nk_overlay_go(state,NK_OVERLAY_SCREEN_MENU,NK_OVERLAY_ID_SETTINGS);
    }
    nk_overlay_page_end(ui,"",prompts,sizeof prompts/sizeof prompts[0]);
    return action;
}
