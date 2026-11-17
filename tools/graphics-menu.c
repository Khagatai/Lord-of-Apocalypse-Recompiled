/* Title-owned Win32 graphics panel. Game data and runtime sources stay separate. */
#ifndef UNICODE
#define UNICODE
#endif
#ifndef _UNICODE
#define _UNICODE
#endif
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <commctrl.h>
#include <shellapi.h>
#include <stdio.h>
#include <stdlib.h>
#include <wchar.h>

#define COUNT 15
#define ID_SAVE 400
#define ID_PLAY 401
#define ID_ORIGINAL 402
#define ID_BALANCED 403
#define ID_LOG 404
#define ID_QUALITY 405
static HWND controls[COUNT], status, main_window, play_button;
static HFONT font, heading;
static wchar_t root[32768], python[32768];
static HANDLE game;
static int dpi = 96;
static const int defaults[COUNT] = {0,0,0,0,0,1,0,0,0,0,0,0,0,0,0};
static const int lengths[COUNT] = {2,4,2,6,3,2,2,2,5,2,2,2,6,2,2};
static const int checkboxes[COUNT] = {0,0,0,0,0,1,1,1,0,1,1,0,0,1,0};
static int px(int value) { return MulDiv(value, dpi, 96); }

static HWND widget(const wchar_t *cls, const wchar_t *text, DWORD style, int id,
                   int x, int y, int w, int h) {
    if(wcscmp(cls,L"STATIC")==0) style |= SS_NOPREFIX;
    HWND window = CreateWindowExW(0, cls, text, WS_CHILD|WS_VISIBLE|style,
        px(x), px(y), px(w), px(h), main_window, (HMENU)(INT_PTR)id, GetModuleHandleW(NULL), NULL);
    SendMessageW(window, WM_SETFONT, (WPARAM)font, TRUE);
    return window;
}
static void label(const wchar_t *text, int x, int y, int w, int h) {
    widget(L"STATIC", text, 0, 0, x, y, w, h);
}
static void combo(int index, int x, int y, int width, const wchar_t *const *items) {
    controls[index] = widget(WC_COMBOBOXW, L"", CBS_DROPDOWNLIST|WS_TABSTOP|WS_VSCROLL,
                              200+index, x,y,width,260);
    for (int i=0; i<lengths[index]; i++) SendMessageW(controls[index], CB_ADDSTRING, 0, (LPARAM)items[i]);
}
static void check(int index, const wchar_t *text, int x, int y, int width) {
    controls[index] = widget(L"BUTTON", text, BS_AUTOCHECKBOX|WS_TABSTOP, 200+index,x,y,width,24);
}
static void set_choices(const int values[COUNT]) {
    for (int i=0;i<COUNT;i++)
        SendMessageW(controls[i], checkboxes[i] ? BM_SETCHECK : CB_SETCURSEL, values[i], 0);
    EnableWindow(controls[3], values[2]==0);
}
static void get_choices(int values[COUNT]) {
    for (int i=0;i<COUNT;i++) values[i]=(int)SendMessageW(controls[i], checkboxes[i] ? BM_GETCHECK : CB_GETCURSEL,0,0);
}

/* Invoke only the project-owned helper, directly through CreateProcess, without a shell. */
static int helper(const wchar_t *arguments, char output[8192]) {
    SECURITY_ATTRIBUTES sa={sizeof(sa),NULL,TRUE};
    HANDLE read_pipe=NULL, write_pipe=NULL;
    if (!CreatePipe(&read_pipe,&write_pipe,&sa,65536)) return 0;
    SetHandleInformation(read_pipe,HANDLE_FLAG_INHERIT,0);
    STARTUPINFOW start={0}; start.cb=sizeof(start); start.dwFlags=STARTF_USESTDHANDLES;
    start.hStdOutput=write_pipe; start.hStdError=write_pipe;
    start.hStdInput=GetStdHandle(STD_INPUT_HANDLE);
    wchar_t command[65536];
    swprintf(command,65536,L"\"%ls\" \"%ls\\tools\\graphics_settings.py\" %ls",python,root,arguments);
    PROCESS_INFORMATION process={0};
    int opened=CreateProcessW(python,command,NULL,NULL,TRUE,CREATE_NO_WINDOW,NULL,root,&start,&process);
    CloseHandle(write_pipe);
    if (!opened) { CloseHandle(read_pipe); return 0; }
    DWORD wait=WaitForSingleObject(process.hProcess,20000), exit_code=1;
    if (wait==WAIT_TIMEOUT) { TerminateProcess(process.hProcess,1); WaitForSingleObject(process.hProcess,5000); }
    GetExitCodeProcess(process.hProcess,&exit_code);
    DWORD read=0; output[0]=0;
    if (ReadFile(read_pipe,output,8191,&read,NULL)) output[read]=0;
    CloseHandle(read_pipe); CloseHandle(process.hThread); CloseHandle(process.hProcess);
    return wait==WAIT_OBJECT_0 && exit_code==0;
}
static void helper_error(const char *detail) {
    wchar_t message[8500]={0};
    MultiByteToWideChar(CP_UTF8,0,detail,-1,message,8500);
    MessageBoxW(main_window,message[0]?message:L"The settings helper could not run. Keep this launcher in its project folder.",
                 L"Settings could not be applied",MB_OK|MB_ICONERROR);
}
static int save_choices(void) {
    int values[COUNT]; get_choices(values);
    wchar_t arguments[512]; wcscpy(arguments,L"--set-menu");
    for(int i=0;i<COUNT;i++) {
        if(values[i]<0 || values[i]>=lengths[i]) return 0;
        wchar_t number[24]; swprintf(number,24,L" %d",values[i]); wcscat(arguments,number);
    }
    char output[8192]={0};
    if(!helper(arguments,output)) { helper_error(output); return 0; }
    SetWindowTextW(status,L"Settings saved. They will be used the next time you start a game.");
    return 1;
}
static void launch(void) {
    if(game || !save_choices()) return;
    const wchar_t *variants[]={L"english-text-test",L"japanese"};
    int values[COUNT]; get_choices(values);
    wchar_t command[65536], log_path[32768];
    swprintf(command,65536,L"\"%ls\" \"%ls\\tools\\launch-preview.py\" --variant %ls",python,root,variants[values[0]]);
    swprintf(log_path,32768,L"%ls\\private\\settings\\launcher.log",root);
    SECURITY_ATTRIBUTES sa={sizeof(sa),NULL,TRUE};
    HANDLE log=CreateFileW(log_path,GENERIC_WRITE,FILE_SHARE_READ,&sa,CREATE_ALWAYS,FILE_ATTRIBUTE_NORMAL,NULL);
    if(log==INVALID_HANDLE_VALUE) { helper_error("Cannot open the private launcher log."); return; }
    STARTUPINFOW start={0}; start.cb=sizeof(start); start.dwFlags=STARTF_USESTDHANDLES;
    start.hStdOutput=log; start.hStdError=log; start.hStdInput=GetStdHandle(STD_INPUT_HANDLE);
    PROCESS_INFORMATION process={0};
    int opened=CreateProcessW(python,command,NULL,NULL,TRUE,CREATE_NO_WINDOW,NULL,root,&start,&process);
    CloseHandle(log);
    if(!opened) { helper_error("Could not start the game launcher."); return; }
    CloseHandle(process.hThread); game=process.hProcess;
    EnableWindow(play_button,FALSE);
    SetWindowTextW(status,L"Game running. Press F1 in the game for pause and display settings.");
    ShowWindow(main_window,SW_MINIMIZE);
    SetTimer(main_window,1,250,NULL);
}

static LRESULT CALLBACK procedure(HWND window,UINT message,WPARAM w,LPARAM l) {
    switch(message) {
    case WM_CTLCOLORSTATIC:
    case WM_CTLCOLORBTN:
        SetBkMode((HDC)w,TRANSPARENT);
        return (LRESULT)GetSysColorBrush(COLOR_WINDOW);
    case WM_COMMAND:
        if(LOWORD(w)==202 && HIWORD(w)==CBN_SELCHANGE)
            EnableWindow(controls[3],SendMessageW(controls[2],CB_GETCURSEL,0,0)==0);
        if(LOWORD(w)==ID_SAVE) save_choices();
        if(LOWORD(w)==ID_PLAY) launch();
        if(LOWORD(w)==ID_ORIGINAL) {
            int values[COUNT]; for(int i=0;i<COUNT;i++) values[i]=defaults[i];
            values[0]=(int)SendMessageW(controls[0],CB_GETCURSEL,0,0);
            set_choices(values); SetWindowTextW(status,L"Original graphics selected. Save or start the game to apply.");
        }
        if(LOWORD(w)==ID_BALANCED) {
            int values[COUNT]; get_choices(values);
            values[1]=1; values[4]=0; values[5]=1; values[7]=0; values[8]=2;
            values[9]=values[10]=values[11]=values[12]=values[13]=0;
            set_choices(values); SetWindowTextW(status,L"Balanced: 2x internal resolution and 4x anisotropic filtering.");
        }
        if(LOWORD(w)==ID_LOG) {
            wchar_t folder[32768]; swprintf(folder,32768,L"%ls\\private",root);
            ShellExecuteW(window,L"open",folder,NULL,NULL,SW_SHOWNORMAL);
        }
        if(LOWORD(w)==ID_QUALITY) {
            int values[COUNT]; get_choices(values);
            values[1]=3; values[7]=1; values[8]=4;
            values[9]=values[10]=values[11]=values[13]=1; values[12]=3;
            set_choices(values); SetWindowTextW(status,L"High Quality selected. Save or start the game to apply.");
        }
        return 0;
    case WM_TIMER:
        if(game && WaitForSingleObject(game,0)==WAIT_OBJECT_0) {
            DWORD exit_code=1; GetExitCodeProcess(game,&exit_code); CloseHandle(game); game=NULL;
            KillTimer(window,1); EnableWindow(play_button,TRUE); ShowWindow(window,SW_RESTORE);
            SetWindowTextW(status,exit_code?L"Game launch failed. Open logs for the recorded error.":L"Game closed. Your graphics settings are saved.");
            if(exit_code) MessageBoxW(window,L"The game could not start or exited with an error. Open logs and inspect settings/launcher.log.",L"Game launch failed",MB_OK|MB_ICONERROR);
        }
        return 0;
    case WM_CLOSE:
        if(game) {
            MessageBoxW(window,L"Close the game before closing this panel. Your game will keep running.",L"Game running",MB_OK|MB_ICONINFORMATION);
            return 0;
        }
        DestroyWindow(window); return 0;
    case WM_DESTROY: PostQuitMessage(0); return 0;
    }
    return DefWindowProcW(window,message,w,l);
}

int WINAPI wWinMain(HINSTANCE instance,HINSTANCE previous,LPWSTR arguments,int show) {
    (void)previous;
    SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2);
    dpi=(int)GetDpiForSystem();
    GetModuleFileNameW(NULL,root,32768);
    for(int i=0;i<3;i++) { wchar_t *slash=wcsrchr(root,L'\\'); if(!slash) return 1; *slash=0; }
    swprintf(python,32768,L"%ls\\private\\tools\\python314\\python.exe",root);
    INITCOMMONCONTROLSEX init={sizeof(init),ICC_STANDARD_CLASSES}; InitCommonControlsEx(&init);
    WNDCLASSW cls={0}; cls.lpfnWndProc=procedure; cls.hInstance=instance;
    cls.hCursor=LoadCursorW(NULL,IDC_ARROW); cls.hIcon=LoadIconW(NULL,IDI_APPLICATION);
    cls.hbrBackground=(HBRUSH)(COLOR_WINDOW+1); cls.lpszClassName=L"LordOfApocalypseGraphicsMenu";
    if(!RegisterClassW(&cls)) return 1;
    RECT rect={0,0,px(760),px(610)};
    DWORD style=WS_OVERLAPPED|WS_CAPTION|WS_SYSMENU|WS_MINIMIZEBOX;
    AdjustWindowRectExForDpi(&rect,style,FALSE,0,(UINT)dpi);
    main_window=CreateWindowExW(0,cls.lpszClassName,L"Lord of Apocalypse - Graphics & Display",style,
                   CW_USEDEFAULT,CW_USEDEFAULT,rect.right-rect.left,rect.bottom-rect.top,NULL,NULL,instance,NULL);
    if(!main_window) return 1;
    font=CreateFontW(-px(14),0,0,0,FW_NORMAL,FALSE,FALSE,FALSE,DEFAULT_CHARSET,0,0,CLEARTYPE_QUALITY,0,L"Segoe UI");
    heading=CreateFontW(-px(25),0,0,0,FW_SEMIBOLD,FALSE,FALSE,FALSE,DEFAULT_CHARSET,0,0,CLEARTYPE_QUALITY,0,L"Segoe UI");
    HWND title=widget(L"STATIC",L"Graphics & Display",0,0,28,18,680,34);
    SendMessageW(title,WM_SETFONT,(WPARAM)heading,TRUE);
    label(L"Lord of Apocalypse",28,54,500,24);
    label(L"Game version",28,94,140,24);
    const wchar_t *versions[]={L"English - expanded translation (WIP)",L"Japanese"};
    combo(0,166,88,290,versions);
    widget(L"BUTTON",L"Original",BS_PUSHBUTTON|WS_TABSTOP,ID_ORIGINAL,465,87,85,29);
    widget(L"BUTTON",L"Balanced",BS_PUSHBUTTON|WS_TABSTOP,ID_BALANCED,555,87,85,29);
    widget(L"BUTTON",L"High Quality",BS_PUSHBUTTON|WS_TABSTOP,ID_QUALITY,645,87,85,29);
    label(L"Display",28,135,360,25); label(L"Advanced graphics",440,135,290,25);
    const wchar_t *scales[]={L"1x - 480 x 272 (PSP)",L"2x - 960 x 544",L"3x - 1440 x 816",L"4x - 1920 x 1088"};
    const wchar_t *modes[]={L"Windowed",L"Borderless fullscreen"};
    const wchar_t *sizes[]={L"960 x 544",L"1280 x 720",L"1600 x 900",L"1920 x 1080",L"2560 x 1440",L"3840 x 2160"};
    const wchar_t *scalings[]={L"Sharp",L"Integer (whole pixels)",L"Smooth (bilinear)"};
    const wchar_t *af[]={L"Off",L"2x",L"4x",L"8x",L"16x"};
    const wchar_t *ssaa[]={L"Off",L"2x supersampling"};
    const wchar_t *textures[]={L"Off",L"2x",L"3x",L"4x",L"5x",L"6x"};
    const wchar_t *fps[]={L"Original 30 FPS",L"60 FPS (experimental)"};
    label(L"Internal resolution",28,178,170,23); combo(1,205,172,205,scales);
    label(L"Display mode",28,224,170,23); combo(2,205,218,205,modes);
    label(L"Window resolution",28,270,170,23); combo(3,205,264,205,sizes);
    label(L"Image scaling",28,316,170,23); combo(4,205,310,205,scalings);
    label(L"Texture filtering",440,178,135,23); combo(8,580,172,150,af);
    label(L"Anti-aliasing",440,224,135,23); combo(11,580,218,150,ssaa);
    check(9,L"Reduce texture shimmer *",440,264,290);
    check(10,L"Reduce colour banding *",440,304,290);
    label(L"Gameplay frame rate",28,358,170,23); combo(14,205,352,205,fps);
    check(5,L"VSync",28,394,150);
    check(7,L"FSR 1 image upscaling",440,356,290);
    check(6,L"Performance HUD",205,394,205);
    label(L"3D smoothing *",440,400,135,23); combo(12,580,394,150,textures);
    check(13,L"HD world / models (English WIP)",28,430,300);
    label(L"Movies retain original timing in both frame-rate modes.\n* Experimental effects; smoothing changes artwork and cannot restore missing detail.",28,462,700,42);
    label(L"F1 opens in-game settings. Frame-rate changes apply after restarting.",28,506,700,24);
    status=widget(L"STATIC",L"Choose your settings, then start the game.",0,0,28,576,704,22);
    widget(L"BUTTON",L"Open logs",BS_PUSHBUTTON|WS_TABSTOP,ID_LOG,28,540,110,30);
    widget(L"BUTTON",L"Save",BS_PUSHBUTTON|WS_TABSTOP,ID_SAVE,470,540,110,30);
    play_button=widget(L"BUTTON",L"Start game",BS_DEFPUSHBUTTON|WS_TABSTOP,ID_PLAY,596,540,135,30);
    set_choices(defaults);
    char output[8192]={0};
    if(helper(L"--menu",output)) {
        int values[COUNT]; char *cursor=output; int valid=1;
        for(int i=0;i<COUNT;i++) {
            char *end=NULL; long value=strtol(cursor,&end,10);
            if(end==cursor || value<0 || value>=lengths[i]) { valid=0; break; }
            values[i]=(int)value; cursor=end;
        }
        if(valid) set_choices(values); else helper_error("Graphics settings helper returned invalid choices.");
    } else helper_error(output);
    ShowWindow(main_window,show); UpdateWindow(main_window);
    /* UI smoke mode creates the real controls without starting a game or writing settings. */
    int smoke=wcsstr(arguments,L"--smoke")!=NULL;
    if(smoke) { int values[COUNT]; get_choices(values); for(int i=0;i<COUNT;i++) if(values[i]<0 || values[i]>=lengths[i]) return 2; DestroyWindow(main_window); }
    MSG message;
    while(GetMessageW(&message,NULL,0,0)>0) {
        if(!IsDialogMessageW(main_window,&message)) { TranslateMessage(&message); DispatchMessageW(&message); }
    }
    DeleteObject(font); DeleteObject(heading);
    return 0;
}
