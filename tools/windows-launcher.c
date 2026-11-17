/* SPDX-License-Identifier: GPL-3.0-or-later
 * Windows x64 front end for the bundled, verified Python launch path.
 * No shell, downloaded code, game assets or embedded game executable.
 */
#define UNICODE
#define _UNICODE
#include <windows.h>
#include <shellapi.h>
#include <wchar.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "title_settings_menu.h"

#define ID_PLAY 101
#define ID_SAFE 102
#define ID_LOG 103
#define ID_DETAILS 104
#define ID_EXPAND 105
#define ID_SETTINGS 106
#define ID_SETTINGS_BACK 107
#define ID_SETTINGS_SAVE 108
#define ID_SETTINGS_TAB 120
#define ID_SETTING_ROW 200
#define ID_PRESET 230
static HWND main_window,status_label,play_button,safe_box,details,log_button,expand_button,hover_button;
static HWND settings_button,settings_back,settings_save,settings_tabs[5],settings_rows[LOA_SETTINGS_COUNT],preset_buttons[3];
static int settings_page,settings_tab,settings_loaded,child_mode,settings_codes[LOA_SETTINGS_COUNT],settings_saved[LOA_SETTINGS_COUNT];
static char settings_token[65],settings_output[8192];static size_t settings_output_length;
static wchar_t settings_controls[4096];
static HFONT font,title_font,logo_font,logo_small_font,small_font,mono_font,button_font;
static HBRUSH panel_brush,details_brush,background_brush;
static WNDPROC button_proc,safe_proc;
static UINT dpi=96;
static int expanded,launch_error,animation;
static HICON app_icon;
static HANDLE child,read_pipe;
static wchar_t root[32768],log_path[32768];
static HANDLE log_file=INVALID_HANDLE_VALUE;
static int game_started;
static char pending[32768];
static size_t pending_len;

#define BG RGB(13,18,26)
#define PANEL RGB(21,29,40)
#define EDGE RGB(43,55,71)
#define INK RGB(238,242,247)
#define MUTED RGB(146,159,177)
#define GOLD RGB(218,186,123)
#define ERROR_INK RGB(241,157,139)
static int px(int v){return MulDiv(v,(int)dpi,96);}
static UINT fitted_dpi(UINT requested,RECT work){
    int horizontal=MulDiv(work.right-work.left-32,96,916),vertical_limit=MulDiv(work.bottom-work.top-48,96,600);
    int limit=horizontal<vertical_limit?horizontal:vertical_limit;if(limit<72)limit=72;
    return requested>(UINT)limit?(UINT)limit:requested;
}
static int vertical(int v){RECT r;GetClientRect(main_window,&r);return MulDiv(v,r.bottom,560);}
static int content_x(void){return px(356);}
static int content_width(void){RECT r;GetClientRect(main_window,&r);return r.right-content_x()-px(36);}
static void layout(void);
static void settings_layout(void);
static void settings_paint(HDC dc,int x,int width);
static int settings_draw_button(const DRAWITEMSTRUCT *item);
static void settings_request(int save);
static void settings_finish(DWORD code);
static void settings_create(HWND parent);
static void settings_fonts(void);
static void settings_change(int index,int direction);
static int settings_command(int id);
static void set_status(const wchar_t *value,int error){
    launch_error=error;SetWindowTextW(status_label,value);InvalidateRect(main_window,NULL,FALSE);
}
static void show_details(int show){
    expanded=show;SetWindowTextW(expand_button,show?L"Hide launch details":L"Show launch details");layout();RedrawWindow(main_window,NULL,NULL,RDW_INVALIDATE|RDW_ALLCHILDREN|RDW_UPDATENOW);
}
static HFONT make_font(int size,int weight,const wchar_t *face){return CreateFontW(-px(size),0,0,0,weight,FALSE,FALSE,FALSE,DEFAULT_CHARSET,0,0,CLEARTYPE_QUALITY,DEFAULT_PITCH,face);}
static void release_fonts(void){
    HFONT fonts[]={font,title_font,logo_font,logo_small_font,small_font,mono_font,button_font};
    for(unsigned i=0;i<sizeof fonts/sizeof fonts[0];i++)if(fonts[i])DeleteObject(fonts[i]);
}
static void create_fonts(void){
    release_fonts();font=make_font(14,FW_NORMAL,L"Segoe UI");title_font=make_font(34,FW_SEMIBOLD,L"Segoe UI");
    logo_font=make_font(27,FW_NORMAL,L"Georgia");logo_small_font=make_font(21,FW_NORMAL,L"Georgia");
    small_font=make_font(11,FW_NORMAL,L"Segoe UI");mono_font=make_font(12,FW_NORMAL,L"Consolas");button_font=make_font(17,FW_SEMIBOLD,L"Segoe UI");
    if(status_label)SendMessageW(status_label,WM_SETFONT,(WPARAM)font,TRUE);
    if(details)SendMessageW(details,WM_SETFONT,(WPARAM)mono_font,TRUE);
    HWND buttons[]={play_button,safe_box,expand_button,log_button};
    for(unsigned i=0;i<sizeof buttons/sizeof buttons[0];i++)if(buttons[i])SendMessageW(buttons[i],WM_SETFONT,(WPARAM)font,TRUE);
    settings_fonts();
}
static void fill(HDC dc,RECT r,COLORREF color){HBRUSH b=CreateSolidBrush(color);FillRect(dc,&r,b);DeleteObject(b);}
static void box(HDC dc,RECT r,COLORREF color,COLORREF border,int radius){
    HBRUSH b=CreateSolidBrush(color);HPEN p=CreatePen(PS_SOLID,1,border);HGDIOBJ oldb=SelectObject(dc,b),oldp=SelectObject(dc,p);
    RoundRect(dc,r.left,r.top,r.right,r.bottom,px(radius),px(radius));SelectObject(dc,oldb);SelectObject(dc,oldp);DeleteObject(b);DeleteObject(p);
}
static void focus_frame(HDC dc,RECT r,COLORREF color){
    InflateRect(&r,-px(3),-px(3));HPEN p=CreatePen(PS_SOLID,1,color);
    HGDIOBJ oldp=SelectObject(dc,p),oldb=SelectObject(dc,GetStockObject(HOLLOW_BRUSH));
    RoundRect(dc,r.left,r.top,r.right,r.bottom,px(8),px(8));SelectObject(dc,oldp);SelectObject(dc,oldb);DeleteObject(p);
}
static void label(HDC dc,HFONT face,COLORREF color,RECT r,const wchar_t *text,UINT flags){
    HGDIOBJ old=SelectObject(dc,face);SetBkMode(dc,TRANSPARENT);SetTextColor(dc,color);DrawTextW(dc,text,-1,&r,flags|DT_NOPREFIX);SelectObject(dc,old);
}
static void line(HDC dc,int x1,int y1,int x2,int y2,COLORREF color,int width){
    HPEN p=CreatePen(PS_SOLID,width,color);HGDIOBJ old=SelectObject(dc,p);MoveToEx(dc,x1,y1,NULL);LineTo(dc,x2,y2);SelectObject(dc,old);DeleteObject(p);
}
static HICON create_icon(void){
    BITMAPINFO info={0};info.bmiHeader.biSize=sizeof(BITMAPINFOHEADER);info.bmiHeader.biWidth=32;info.bmiHeader.biHeight=-32;
    info.bmiHeader.biPlanes=1;info.bmiHeader.biBitCount=32;info.bmiHeader.biCompression=BI_RGB;
    uint32_t *pixels=NULL;HDC screen=GetDC(NULL),dc=CreateCompatibleDC(screen);
    HBITMAP image=CreateDIBSection(screen,&info,DIB_RGB_COLORS,(void **)&pixels,NULL,0);ReleaseDC(NULL,screen);
    if(!image||!pixels){if(image)DeleteObject(image);DeleteDC(dc);return NULL;}
    HGDIOBJ old=SelectObject(dc,image);RECT r={0,0,32,32};fill(dc,r,RGB(21,29,40));
    line(dc,16,4,6,16,GOLD,2);line(dc,6,16,16,26,GOLD,2);line(dc,16,26,26,16,GOLD,2);line(dc,26,16,16,4,GOLD,2);
    line(dc,16,4,16,29,GOLD,2);line(dc,6,18,26,18,GOLD,2);GdiFlush();
    for(int i=0;i<32*32;i++)pixels[i]|=0xff000000u;
    SelectObject(dc,old);DeleteDC(dc);uint32_t mask_bits[32]={0};HBITMAP mask=CreateBitmap(32,32,1,1,mask_bits);
    ICONINFO icon={0};icon.fIcon=TRUE;icon.hbmColor=image;icon.hbmMask=mask;HICON result=CreateIconIndirect(&icon);
    DeleteObject(image);DeleteObject(mask);return result;
}
static void emblem(HDC dc,int cx,int cy,int radius){
    HPEN p=CreatePen(PS_SOLID,px(1),RGB(91,85,67));HGDIOBJ oldp=SelectObject(dc,p),oldb=SelectObject(dc,GetStockObject(HOLLOW_BRUSH));
    Ellipse(dc,cx-radius,cy-radius,cx+radius,cy+radius);
    POINT diamond[5]={{cx,cy-radius-px(18)},{cx+radius+px(18),cy},{cx,cy+radius+px(18)},{cx-radius-px(18),cy},{cx,cy-radius-px(18)}};
    Polyline(dc,diamond,5);SelectObject(dc,oldb);SelectObject(dc,oldp);DeleteObject(p);
    int a=radius/2;
    line(dc,cx,cy-radius+px(8),cx,cy+radius-px(8),GOLD,px(2));
    line(dc,cx,cy-radius+px(8),cx-a,cy,GOLD,px(2));line(dc,cx-a,cy,cx,cy+a,GOLD,px(2));
    line(dc,cx,cy-radius+px(8),cx+a,cy,GOLD,px(2));line(dc,cx+a,cy,cx,cy+a,GOLD,px(2));
    line(dc,cx-a-px(8),cy+px(5),cx+a+px(8),cy+px(5),GOLD,px(2));
    line(dc,cx-px(8),cy+radius-px(8),cx+px(8),cy+radius-px(8),GOLD,px(2));
}
static void paint_background(HDC dc){
    RECT client;GetClientRect(main_window,&client);fill(dc,client,BG);int left=px(320);
    for(int y=0;y<client.bottom;y++){
        int v=client.bottom?y*10/client.bottom:0;RECT row={0,y,left,y+1};fill(dc,row,RGB(21-v,30-v,42-v));
    }
    line(dc,left,0,left,client.bottom,EDGE,1);
    RECT stamp={px(36),vertical(32),left-px(36),vertical(53)};
    label(dc,small_font,GOLD,stamp,L"R E C O M P I L E D",DT_LEFT|DT_SINGLELINE|DT_VCENTER);
    line(dc,px(36),vertical(75),px(74),vertical(75),GOLD,px(2));
    /* Original procedural artwork; no game image is embedded in the launcher. */
    line(dc,px(12),vertical(280),px(300),vertical(98),RGB(32,43,56),1);
    line(dc,px(20),vertical(103),px(305),vertical(286),RGB(32,43,56),1);
    emblem(dc,px(160),vertical(192),px(64));
    RECT a={px(24),vertical(320),left-px(24),vertical(352)},b={px(12),vertical(354),left-px(12),vertical(397)};
    label(dc,logo_small_font,INK,a,L"L O R D   O F",DT_CENTER|DT_SINGLELINE|DT_VCENTER);
    label(dc,logo_font,INK,b,L"APOCALYPSE",DT_CENTER|DT_SINGLELINE|DT_VCENTER);
    RECT foot={px(36),vertical(501),left-px(24),vertical(526)};
    label(dc,small_font,MUTED,foot,L"A NEW HOME FOR THE HUNT",DT_SINGLELINE|DT_VCENTER);
    int x=content_x(),w=content_width();
    RECT eyebrow={x,vertical(35),x+w,vertical(59)};label(dc,small_font,MUTED,eyebrow,L"G A M E   L A U N C H E R",DT_SINGLELINE|DT_VCENTER);
    RECT badge={x+w-px(91),vertical(33),x+w,vertical(58)};box(dc,badge,PANEL,EDGE,8);
    label(dc,small_font,GOLD,badge,L"WIP BUILD",DT_CENTER|DT_VCENTER|DT_SINGLELINE);
    if(settings_page){settings_paint(dc,x,w);return;}
    RECT title={x,vertical(94),x+w,vertical(141)};
    label(dc,title_font,INK,title,launch_error?L"Launch needs attention":child?L"Preparing your game":L"Ready to play",DT_SINGLELINE|DT_VCENTER);
    RECT sub={x,vertical(150),x+w,vertical(184)};
    label(dc,font,MUTED,sub,L"Pick up where you left off. Your settings stay with you.",DT_WORDBREAK);
    RECT state={x,vertical(294),x+w,vertical(368)};box(dc,state,PANEL,EDGE,12);
    int dotx=x+px(21),doty=vertical(315);RECT dot={dotx-px(3),doty-px(3),dotx+px(3),doty+px(3)};
    box(dc,dot,launch_error?ERROR_INK:GOLD,launch_error?ERROR_INK:GOLD,6);
    if(child){
        RECT track={x,vertical(278),x+w,vertical(280)};fill(dc,track,EDGE);
        int span=w/4,at=(animation*px(8))%(w+span)-span;
        RECT active={x+(at<0?0:at),track.top,x+(at+span>w?w:at+span),track.bottom};fill(dc,active,GOLD);
    }
    if(expanded){RECT panel={x,vertical(382),x+w,vertical(479)};box(dc,panel,RGB(10,16,24),EDGE,8);}
    else{
        RECT help={x+px(47),vertical(465),x+w,vertical(483)};
        label(dc,small_font,MUTED,help,L"Use this if the game has trouble starting.",DT_WORDBREAK);
    }
    RECT tip={x,vertical(534),x+w,vertical(554)};
    label(dc,small_font,MUTED,tip,L"F1 in game  /  Graphics, controls & networking",DT_SINGLELINE|DT_VCENTER);
}
static void layout(void){
    if(!play_button)return;int x=content_x(),w=content_width();
    HWND home[]={play_button,safe_box,details,expand_button,log_button,settings_button};
    for(unsigned i=0;i<sizeof home/sizeof home[0];i++)if(home[i])ShowWindow(home[i],settings_page?SW_HIDE:SW_SHOW);
    if(settings_page){MoveWindow(status_label,x,vertical(150),w,vertical(35),TRUE);settings_layout();return;}
    MoveWindow(play_button,x,vertical(208),w,vertical(64),TRUE);
    MoveWindow(status_label,x+px(38),vertical(306),w-px(52),vertical(53),TRUE);
    MoveWindow(settings_button,x,vertical(382),w,vertical(40),TRUE);ShowWindow(settings_button,expanded?SW_HIDE:SW_SHOW);EnableWindow(settings_button,!child);
    MoveWindow(safe_box,x,vertical(433),w,vertical(32),TRUE);ShowWindow(safe_box,expanded?SW_HIDE:SW_SHOW);
    MoveWindow(details,x+px(12),vertical(391),w-px(24),vertical(77),TRUE);ShowWindow(details,expanded?SW_SHOW:SW_HIDE);
    MoveWindow(expand_button,x,vertical(490),px(226),vertical(34),TRUE);
    MoveWindow(log_button,x+w-px(112),vertical(490),px(112),vertical(34),TRUE);
    settings_layout();
}
static void draw_button(const DRAWITEMSTRUCT *item){
    if(settings_draw_button(item))return;
    RECT r=item->rcItem;int disabled=(item->itemState&ODS_DISABLED)!=0,hover=item->hwndItem==hover_button,pressed=(item->itemState&ODS_SELECTED)!=0;
    fill(item->hDC,r,BG);
    if(item->CtlID==ID_PLAY){
        COLORREF color=disabled?RGB(75,75,67):pressed?RGB(182,150,91):hover?RGB(235,204,145):GOLD;
        box(item->hDC,r,color,color,12);RECT text=r;text.left+=px(24);
        label(item->hDC,button_font,disabled?RGB(176,176,163):RGB(29,28,24),text,disabled?L"Preparing...":L"Play",DT_VCENTER|DT_SINGLELINE);
        int cx=r.right-px(30),cy=(r.top+r.bottom)/2;
        line(item->hDC,cx-px(7),cy,cx+px(7),cy,RGB(41,37,29),px(2));
        line(item->hDC,cx+px(7),cy,cx,cy-px(7),RGB(41,37,29),px(2));line(item->hDC,cx+px(7),cy,cx,cy+px(7),RGB(41,37,29),px(2));
    }else{
        if((hover||item->CtlID==ID_SETTINGS)&&!disabled)box(item->hDC,r,PANEL,EDGE,8);
        wchar_t text[128];GetWindowTextW(item->hwndItem,text,128);RECT content=r;content.left+=px(8);
        label(item->hDC,font,disabled?RGB(85,98,113):MUTED,content,text,DT_SINGLELINE|DT_VCENTER);
    }
    if(item->itemState&ODS_FOCUS)focus_frame(item->hDC,r,item->CtlID==ID_PLAY?RGB(145,119,70):EDGE);
}
static void track_button(HWND hwnd){
    if(hover_button!=hwnd){hover_button=hwnd;TRACKMOUSEEVENT event={sizeof event,TME_LEAVE,hwnd,0};TrackMouseEvent(&event);InvalidateRect(hwnd,NULL,FALSE);}
}
static LRESULT CALLBACK styled_button_proc(HWND hwnd,UINT msg,WPARAM wp,LPARAM lp){
    int id=GetDlgCtrlID(hwnd);
    if(id>=ID_SETTING_ROW&&id<ID_SETTING_ROW+LOA_SETTINGS_COUNT){
        if(msg==WM_GETDLGCODE&&(wp==VK_LEFT||wp==VK_RIGHT))return DLGC_WANTARROWS|DLGC_BUTTON;
        if(msg==WM_KEYDOWN&&(wp==VK_LEFT||wp==VK_RIGHT)&&IsWindowEnabled(hwnd)){settings_change(id-ID_SETTING_ROW,wp==VK_LEFT?-1:1);return 0;}
    }
    if(msg==WM_MOUSEMOVE)track_button(hwnd);
    if(msg==WM_MOUSELEAVE){if(hover_button==hwnd)hover_button=NULL;InvalidateRect(hwnd,NULL,FALSE);}
    return CallWindowProcW(button_proc,hwnd,msg,wp,lp);
}
static LRESULT CALLBACK styled_safe_proc(HWND hwnd,UINT msg,WPARAM wp,LPARAM lp){
    if(msg==WM_MOUSEMOVE)track_button(hwnd);
    if(msg==WM_MOUSELEAVE){if(hover_button==hwnd)hover_button=NULL;InvalidateRect(hwnd,NULL,FALSE);}
    if(msg==WM_ERASEBKGND)return 1;
    if(msg==WM_PAINT){
        PAINTSTRUCT paint;HDC dc=BeginPaint(hwnd,&paint);RECT r;GetClientRect(hwnd,&r);fill(dc,r,BG);
        int checked=SendMessageW(hwnd,BM_GETCHECK,0,0)==BST_CHECKED,enabled=IsWindowEnabled(hwnd);int cy=r.bottom/2;
        RECT toggle={0,cy-px(9),px(34),cy+px(9)};box(dc,toggle,checked?GOLD:PANEL,checked?GOLD:EDGE,18);
        int center=checked?px(24):px(10);RECT knob={center-px(5),cy-px(5),center+px(5),cy+px(5)};box(dc,knob,checked?BG:MUTED,checked?BG:MUTED,10);
        RECT text={px(47),0,r.right,r.bottom};label(dc,font,enabled?INK:MUTED,text,L"Basic graphics",DT_SINGLELINE|DT_VCENTER);
        if(GetFocus()==hwnd)focus_frame(dc,text,EDGE);
        EndPaint(hwnd,&paint);return 0;
    }
    LRESULT result=CallWindowProcW(safe_proc,hwnd,msg,wp,lp);
    if(msg==BM_SETCHECK||msg==WM_ENABLE||msg==WM_SETFOCUS||msg==WM_KILLFOCUS)InvalidateRect(hwnd,NULL,FALSE);
    return result;
}

/* CommandLineToArgvW's inverse for one argument, including trailing slashes. */
static int quote_arg(wchar_t *out,size_t cap,size_t *used,const wchar_t *arg) {
    if(*used+2>=cap)return 0;
    out[(*used)++]=L'"';
    while(*arg) {
        size_t slashes=0;while(arg[slashes]==L'\\')slashes++;
        arg+=slashes;
        size_t count=(*arg==L'"'||!*arg)?slashes*2:slashes;
        if(*used+count+3>=cap)return 0;
        while(count--)out[(*used)++]=L'\\';
        if(!*arg)break;
        if(*arg==L'"')out[(*used)++]=L'\\';
        out[(*used)++]=*arg++;
    }
    out[(*used)++]=L'"';out[*used]=0;return 1;
}
static int argument(wchar_t *out,size_t cap,size_t *used,const wchar_t *arg) {
    if(*used) {if(*used+1>=cap)return 0;out[(*used)++]=L' ';}
    return quote_arg(out,cap,used,arg);
}
#include "launcher-settings-ui.h"
static void append_text(const wchar_t *text) {
    int length=GetWindowTextLengthW(details);
    if(length>60000)SetWindowTextW(details,L"Earlier output is in the launcher log.\r\n");
    SendMessageW(details,EM_SETSEL,(WPARAM)-1,(LPARAM)-1);
    SendMessageW(details,EM_REPLACESEL,FALSE,(LPARAM)text);
}
static void output_line(const char *bytes,int length) {
    wchar_t text[32768];
    if(length<=0)return;
    int n=MultiByteToWideChar(CP_UTF8,0,bytes,length,text,32764);
    text[n]=0;
    if(strstr(bytes,"LOA_LAUNCHER_GAME_STARTED")) {
        game_started=1;set_status(L"Game running. Use F1 for settings and networking.",0);
        ShowWindow(main_window,SW_MINIMIZE);
    } else {
        if(!game_started && n){
            unsigned completed_jobs=0,total_jobs=0;
            if(sscanf(bytes,"Preparing HD textures: %u / %u jobs complete",&completed_jobs,&total_jobs)==2 && total_jobs && total_jobs<=1000000u && completed_jobs<=total_jobs){
                wchar_t progress[220];
                swprintf(progress,220,L"Building HD textures: %u / %u jobs (%u%%). This runs once; completed batches resume after errors.",completed_jobs,total_jobs,completed_jobs*100u/total_jobs);
                set_status(progress,0);
            }
            else if(strstr(bytes,"Starting Lord"))set_status(L"Checking your game files...",0);
            else if(strstr(bytes,"Checking HD textures"))set_status(L"Verifying HD textures. The first check may take a little longer.",0);
            else if(strstr(bytes,"Preparing HD textures"))set_status(L"Building HD textures locally. This can take a long time; completed batches resume.",0);
            else if(strstr(bytes,"Preparing HD tools"))set_status(L"Downloading and verifying public texture tools. Your game files stay on this PC.",0);
            else if(strstr(bytes,"generate: running pinned framework"))set_status(L"Generating native game code from your verified ISO...",0);
            else if(strstr(bytes,"build: running pinned framework"))set_status(L"Compiling the native Windows game. This is required once on first setup.",0);
            else if(strstr(bytes,"Preparing native Windows"))set_status(L"Compiling the native game from your ISO. This is required once on first launch.",0);
            else if(strstr(bytes,"Preparing "))set_status(L"Preparing your English game files. Your original ISO stays unchanged.",0);
            else if(strstr(bytes,"Checks complete"))set_status(L"Everything is ready. Opening the game...",0);
        }
        text[n++]=L'\r';text[n++]=L'\n';text[n]=0;append_text(text);
    }
}
static void consume(const char *data,DWORD length) {
    if(child_mode){
        size_t available=sizeof settings_output-1-settings_output_length;
        size_t count=length<available?length:available;memcpy(settings_output+settings_output_length,data,count);settings_output_length+=count;settings_output[settings_output_length]=0;return;
    }
    DWORD written;
    if(log_file!=INVALID_HANDLE_VALUE)WriteFile(log_file,data,length,&written,NULL);
    for(DWORD i=0;i<length;i++) {
        char c=data[i];
        if(c=='\r')continue;
        if(c=='\n'||pending_len==sizeof pending-1) {
            pending[pending_len]=0;output_line(pending,(int)pending_len);pending_len=0;
            if(c=='\n')continue;
        }
        pending[pending_len++]=c;
    }
}
static void finish(void) {
    if(pending_len){pending[pending_len]=0;output_line(pending,(int)pending_len);pending_len=0;}
    DWORD code=1;GetExitCodeProcess(child,&code);CloseHandle(child);child=NULL;
    CloseHandle(read_pipe);read_pipe=NULL;
    if(log_file!=INVALID_HANDLE_VALUE){CloseHandle(log_file);log_file=INVALID_HANDLE_VALUE;}
    if(child_mode){settings_finish(code);return;}
    EnableWindow(play_button,TRUE);EnableWindow(safe_box,TRUE);EnableWindow(log_button,TRUE);
    EnableWindow(settings_button,TRUE);
    if(!code){DestroyWindow(main_window);return;}
    ShowWindow(main_window,SW_RESTORE);SetForegroundWindow(main_window);
    set_status(L"The game could not start or exited with an error. Check the launch details below.",1);show_details(1);
    wchar_t error[128];swprintf(error,128,L"\r\nLauncher returned exit code %lu.\r\n",(unsigned long)code);append_text(error);
}
static void launch(int argc,wchar_t **argv) {
    child_mode=0;
    wchar_t python[32768],script[32768],manifest[32768],command[32768]={0};size_t used=0;
    swprintf(python,32768,L"%ls\\private\\tools\\python314\\python.exe",root);
    swprintf(manifest,32768,L"%ls\\private\\distribution\\release.json",root);
    swprintf(script,32768,L"%ls\\tools\\%ls",root,
        GetFileAttributesW(manifest)!=INVALID_FILE_ATTRIBUTES?L"tester-start.py":L"launch-preview.py");
    if(GetFileAttributesW(python)==INVALID_FILE_ATTRIBUTES || GetFileAttributesW(script)==INVALID_FILE_ATTRIBUTES) {
        set_status(L"Required launcher files are missing. Extract the entire ZIP first.",1);return;
    }
    int ok=argument(command,32768,&used,python)&&argument(command,32768,&used,L"-u")&&argument(command,32768,&used,script);
    if(GetFileAttributesW(manifest)==INVALID_FILE_ATTRIBUTES)ok=ok&&argument(command,32768,&used,L"--variant")&&argument(command,32768,&used,L"saved");
    for(int i=1;i<argc;i++)ok=ok&&argument(command,32768,&used,argv[i]);
    if(SendMessageW(safe_box,BM_GETCHECK,0,0)==BST_CHECKED)ok=ok&&argument(command,32768,&used,L"--graphics-preset")&&argument(command,32768,&used,L"original");
    if(!ok){set_status(L"The launch command is too long.",1);return;}
    SECURITY_ATTRIBUTES sa={sizeof sa,NULL,TRUE};HANDLE write_pipe=NULL;
    if(!CreatePipe(&read_pipe,&write_pipe,&sa,0)){set_status(L"Cannot create the launcher output pipe.",1);return;}
    SetHandleInformation(read_pipe,HANDLE_FLAG_INHERIT,0);
    wchar_t folder[32768];swprintf(folder,32768,L"%ls\\private",root);CreateDirectoryW(folder,NULL);
    swprintf(folder,32768,L"%ls\\private\\launcher",root);CreateDirectoryW(folder,NULL);
    swprintf(log_path,32768,L"%ls\\latest.log",folder);
    log_file=CreateFileW(log_path,GENERIC_WRITE,FILE_SHARE_READ,NULL,CREATE_ALWAYS,FILE_ATTRIBUTE_NORMAL,NULL);
    HANDLE input=CreateFileW(L"NUL",GENERIC_READ,FILE_SHARE_READ|FILE_SHARE_WRITE,&sa,OPEN_EXISTING,0,NULL);
    STARTUPINFOW si={0};si.cb=sizeof si;si.dwFlags=STARTF_USESTDHANDLES|STARTF_USESHOWWINDOW;
    si.wShowWindow=SW_HIDE;si.hStdOutput=write_pipe;si.hStdError=write_pipe;si.hStdInput=input;
    PROCESS_INFORMATION pi={0};
    /* A hidden console is inherited by Python's CLI children, preventing
     * console flashes while leaving ISO dialogs and the SDL game window visible. */
    SetEnvironmentVariableW(L"PYTHONUTF8",L"1");SetEnvironmentVariableW(L"PYTHONUNBUFFERED",L"1");
    SetEnvironmentVariableW(L"LOA_GUI_LAUNCHER",L"1");
    BOOL started=CreateProcessW(python,command,NULL,NULL,TRUE,CREATE_NEW_CONSOLE,NULL,root,&si,&pi);
    DWORD error=GetLastError();CloseHandle(write_pipe);if(input!=INVALID_HANDLE_VALUE)CloseHandle(input);
    if(!started) {
        CloseHandle(read_pipe);read_pipe=NULL;
        if(log_file!=INVALID_HANDLE_VALUE){CloseHandle(log_file);log_file=INVALID_HANDLE_VALUE;}
        wchar_t text[200];swprintf(text,200,L"Windows could not start the bundled launcher (error %lu).",(unsigned long)error);
        set_status(text,1);return;
    }
    CloseHandle(pi.hThread);child=pi.hProcess;game_started=0;pending_len=0;
    EnableWindow(play_button,FALSE);EnableWindow(safe_box,FALSE);
    EnableWindow(settings_button,FALSE);
    EnableWindow(log_button,GetFileAttributesW(log_path)!=INVALID_FILE_ATTRIBUTES);
    SetWindowTextW(details,L"");set_status(L"Checking game files. First-time setup can take several minutes...",0);
}
static LRESULT CALLBACK window_proc(HWND hwnd,UINT msg,WPARAM wp,LPARAM lp) {
    static int argc;static wchar_t **argv;
    switch(msg) {
    case WM_CREATE:
        argv=CommandLineToArgvW(GetCommandLineW(),&argc);
        /* WM_CREATE runs before CreateWindow returns the handle to wWinMain. */
        main_window=hwnd;
        panel_brush=CreateSolidBrush(PANEL);details_brush=CreateSolidBrush(RGB(10,16,24));background_brush=CreateSolidBrush(BG);
        status_label=CreateWindowW(L"STATIC",L"Game files will be checked before launch.",WS_CHILD|WS_VISIBLE|SS_LEFT,0,0,0,0,hwnd,NULL,NULL,NULL);
        play_button=CreateWindowW(L"BUTTON",L"Play",WS_CHILD|WS_VISIBLE|WS_TABSTOP|BS_OWNERDRAW,0,0,0,0,hwnd,(HMENU)ID_PLAY,NULL,NULL);
        safe_box=CreateWindowW(L"BUTTON",L"Basic graphics for troubleshooting",WS_CHILD|WS_VISIBLE|WS_TABSTOP|BS_AUTOCHECKBOX,0,0,0,0,hwnd,(HMENU)ID_SAFE,NULL,NULL);
        details=CreateWindowExW(0,L"EDIT",L"Launch output appears here. Open the log to view the previous session.",WS_CHILD|WS_VSCROLL|ES_MULTILINE|ES_READONLY|ES_AUTOVSCROLL|WS_TABSTOP,0,0,0,0,hwnd,(HMENU)ID_DETAILS,NULL,NULL);
        SendMessageW(details,EM_SETLIMITTEXT,65536,0);
        HMODULE theme=LoadLibraryExW(L"uxtheme.dll",NULL,0x00000800);
        if(theme){typedef HRESULT (WINAPI *SetTheme)(HWND,LPCWSTR,LPCWSTR);SetTheme apply=(SetTheme)(void *)GetProcAddress(theme,"SetWindowTheme");if(apply)apply(details,L"DarkMode_Explorer",NULL);FreeLibrary(theme);}
        expand_button=CreateWindowW(L"BUTTON",L"Show launch details",WS_CHILD|WS_VISIBLE|WS_TABSTOP|BS_OWNERDRAW,0,0,0,0,hwnd,(HMENU)ID_EXPAND,NULL,NULL);
        log_button=CreateWindowW(L"BUTTON",L"Open log",WS_CHILD|WS_VISIBLE|WS_TABSTOP|BS_OWNERDRAW,0,0,0,0,hwnd,(HMENU)ID_LOG,NULL,NULL);
        settings_button=CreateWindowW(L"BUTTON",L"Settings",WS_CHILD|WS_VISIBLE|WS_TABSTOP|BS_OWNERDRAW,0,0,0,0,hwnd,(HMENU)ID_SETTINGS,NULL,NULL);
        button_proc=(WNDPROC)SetWindowLongPtrW(play_button,GWLP_WNDPROC,(LONG_PTR)styled_button_proc);
        SetWindowLongPtrW(expand_button,GWLP_WNDPROC,(LONG_PTR)styled_button_proc);SetWindowLongPtrW(log_button,GWLP_WNDPROC,(LONG_PTR)styled_button_proc);
        SetWindowLongPtrW(settings_button,GWLP_WNDPROC,(LONG_PTR)styled_button_proc);
        safe_proc=(WNDPROC)SetWindowLongPtrW(safe_box,GWLP_WNDPROC,(LONG_PTR)styled_safe_proc);
        settings_create(hwnd);create_fonts();layout();EnableWindow(log_button,GetFileAttributesW(log_path)!=INVALID_FILE_ATTRIBUTES);
        SetTimer(hwnd,1,50,NULL);return 0;
    case WM_COMMAND:
        if(settings_command(LOWORD(wp)))return 0;
        if(LOWORD(wp)==ID_PLAY && !child&&!settings_page)launch(argc,argv);
        else if(LOWORD(wp)==ID_LOG && *log_path)ShellExecuteW(hwnd,L"open",log_path,NULL,root,SW_SHOWNORMAL);
        else if(LOWORD(wp)==ID_EXPAND)show_details(!expanded);
        return 0;
    case DM_GETDEFID:return MAKELRESULT(settings_page?ID_SETTINGS_SAVE:ID_PLAY,DC_HASDEFID);
    case WM_SIZE:layout();InvalidateRect(hwnd,NULL,FALSE);return 0;
    case WM_DPICHANGED:{
        RECT *r=(RECT *)lp;MONITORINFO monitor={0};monitor.cbSize=sizeof monitor;GetMonitorInfoW(MonitorFromRect(r,MONITOR_DEFAULTTONEAREST),&monitor);
        dpi=fitted_dpi(HIWORD(wp),monitor.rcWork);create_fonts();
        int width=r->right-r->left,height=r->bottom-r->top;
        if(dpi!=HIWORD(wp)){width=px(900)+px(16);height=px(560)+px(40);}
        SetWindowPos(hwnd,NULL,r->left,r->top,width,height,SWP_NOZORDER|SWP_NOACTIVATE);layout();return 0;
    }
    case WM_ERASEBKGND:return 1;
    case WM_PRINTCLIENT:paint_background((HDC)wp);return 0;
    case WM_PAINT:{
        PAINTSTRUCT paint;HDC dc=BeginPaint(hwnd,&paint);RECT r;GetClientRect(hwnd,&r);
        HDC back=CreateCompatibleDC(dc);HBITMAP bitmap=CreateCompatibleBitmap(dc,r.right,r.bottom);HGDIOBJ old=SelectObject(back,bitmap);
        paint_background(back);BitBlt(dc,0,0,r.right,r.bottom,back,0,0,SRCCOPY);
        SelectObject(back,old);DeleteObject(bitmap);DeleteDC(back);EndPaint(hwnd,&paint);return 0;
    }
    case WM_DRAWITEM:draw_button((const DRAWITEMSTRUCT *)lp);return TRUE;
    case WM_CTLCOLORSTATIC:
        SetTextColor((HDC)wp,(HWND)lp==details?MUTED:launch_error?ERROR_INK:MUTED);
        SetBkColor((HDC)wp,(HWND)lp==details?RGB(10,16,24):settings_page?BG:PANEL);
        return (LRESULT)((HWND)lp==details?details_brush:settings_page?background_brush:panel_brush);
    case WM_TIMER:
        if(child) {
            if(!game_started&&!IsIconic(hwnd)){animation++;RECT track={content_x(),vertical(276),content_x()+content_width(),vertical(282)};InvalidateRect(hwnd,&track,FALSE);}
            DWORD available=0;
            while(PeekNamedPipe(read_pipe,NULL,0,NULL,&available,NULL)&&available) {
                char bytes[4096];DWORD got=0;
                if(!ReadFile(read_pipe,bytes,available<sizeof bytes?available:sizeof bytes,&got,NULL)||!got)break;
                consume(bytes,got);
            }
            if(WaitForSingleObject(child,0)==WAIT_OBJECT_0)finish();
        }
        return 0;
    case WM_CLOSE:
        /* Leave the supervised game/setup running safely; never kill a save or
         * an image generation operation when the launcher is closed. */
        if(child){ShowWindow(hwnd,SW_MINIMIZE);return 0;}
        DestroyWindow(hwnd);return 0;
    case WM_DESTROY:
        if(argv)LocalFree(argv);release_fonts();DeleteObject(panel_brush);DeleteObject(details_brush);DeleteObject(background_brush);PostQuitMessage(0);return 0;
    }
    return DefWindowProcW(hwnd,msg,wp,lp);
}
#ifndef LOA_LAUNCHER_TEST
int WINAPI wWinMain(HINSTANCE instance,HINSTANCE previous,LPWSTR command,int show) {
    (void)previous;(void)command;(void)show;
    HMODULE user=GetModuleHandleW(L"user32.dll");
    typedef BOOL (WINAPI *DpiAware)(HANDLE);DpiAware aware=(DpiAware)(void *)GetProcAddress(user,"SetProcessDpiAwarenessContext");
    if(aware)aware((HANDLE)(LONG_PTR)-4);
    typedef UINT (WINAPI *DpiSystem)(void);DpiSystem system_dpi=(DpiSystem)(void *)GetProcAddress(user,"GetDpiForSystem");if(system_dpi)dpi=system_dpi();
    RECT desktop_work;SystemParametersInfoW(SPI_GETWORKAREA,0,&desktop_work,0);dpi=fitted_dpi(dpi,desktop_work);
    if(!GetModuleFileNameW(NULL,root,32768))return 1;
    wchar_t *slash=wcsrchr(root,L'\\');if(!slash)return 1;*slash=0;
    if(wcslen(root)>32000)return 1;
    swprintf(log_path,32768,L"%ls\\private\\launcher\\latest.log",root);
    WNDCLASSW wc={0};wc.hInstance=instance;wc.lpfnWndProc=window_proc;wc.lpszClassName=L"LoaNativeLauncher";
    app_icon=(HICON)LoadImageW(instance,MAKEINTRESOURCEW(1),IMAGE_ICON,GetSystemMetrics(SM_CXICON),GetSystemMetrics(SM_CYICON),0);
    if(!app_icon)app_icon=create_icon();wc.hCursor=LoadCursorW(NULL,IDC_ARROW);wc.hIcon=app_icon?app_icon:LoadIconW(NULL,IDI_APPLICATION);wc.hbrBackground=NULL;
    if(!RegisterClassW(&wc))return 1;
    DWORD style=WS_OVERLAPPED|WS_CAPTION|WS_SYSMENU|WS_MINIMIZEBOX|WS_CLIPCHILDREN;
    RECT bounds={0,0,px(900),px(560)},work;AdjustWindowRectEx(&bounds,style,FALSE,0);SystemParametersInfoW(SPI_GETWORKAREA,0,&work,0);
    int width=bounds.right-bounds.left,height=bounds.bottom-bounds.top;
    if(height>work.bottom-work.top-px(20))height=work.bottom-work.top-px(20);
    main_window=CreateWindowW(wc.lpszClassName,L"Lord of Apocalypse",style,
        work.left+(work.right-work.left-width)/2,work.top+(work.bottom-work.top-height)/2,width,height,NULL,NULL,instance,NULL);
    HMODULE dwm=LoadLibraryExW(L"dwmapi.dll",NULL,0x00000800);
    if(dwm){typedef HRESULT (WINAPI *DwmAttribute)(HWND,DWORD,LPCVOID,DWORD);DwmAttribute attr=(DwmAttribute)(void *)GetProcAddress(dwm,"DwmSetWindowAttribute");BOOL dark=TRUE;if(attr)attr(main_window,20,&dark,sizeof dark);FreeLibrary(dwm);}
    if(!main_window)return 1;ShowWindow(main_window,SW_SHOW);UpdateWindow(main_window);SetFocus(play_button);
    MSG msg;while(GetMessageW(&msg,NULL,0,0)>0){if(!IsDialogMessageW(main_window,&msg)){TranslateMessage(&msg);DispatchMessageW(&msg);}}
    if(app_icon)DestroyIcon(app_icon);return (int)msg.wParam;
}
#endif
