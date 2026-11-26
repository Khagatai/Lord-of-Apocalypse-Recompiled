/* SPDX-License-Identifier: GPL-3.0-or-later
 * Temporary diagnostic front end. No game code/assets or networking identities.
 * Environment changes apply only to this launcher and its child processes.
 */
#define UNICODE
#define _UNICODE
#include <windows.h>
#include <wchar.h>
#include <stdio.h>

static int directory(const wchar_t *path) {
    if(CreateDirectoryW(path,NULL))return 1;
    return GetLastError()==ERROR_ALREADY_EXISTS &&
        (GetFileAttributesW(path)&FILE_ATTRIBUTE_DIRECTORY)!=0;
}

#ifndef LOA_COOP_DIAGNOSTIC_TEST
int WINAPI wWinMain(HINSTANCE instance,HINSTANCE previous,LPWSTR args,int show) {
    (void)instance;(void)previous;(void)args;(void)show;
    static wchar_t root[32768],exe[32768],folder[32768],flight[32768],command[32768];
    DWORD length=GetModuleFileNameW(NULL,root,32768);
    if(!length||length>=32768)return 1;
    wchar_t *slash=wcsrchr(root,L'\\');if(!slash)return 1;*slash=0;
    if(wcslen(root)>32000)return 1;
    swprintf(exe,32768,L"%ls\\LordOfApocalypse.exe",root);
    if(GetFileAttributesW(exe)==INVALID_FILE_ATTRIBUTES){
        MessageBoxW(NULL,L"Extract this diagnostic update into your existing game folder, beside LordOfApocalypse.exe.",L"Lord of Apocalypse diagnostics",MB_OK|MB_ICONERROR);return 1;
    }
    swprintf(folder,32768,L"%ls\\private",root);if(!directory(folder))return 1;
    swprintf(folder,32768,L"%ls\\private\\diagnostics",root);if(!directory(folder))return 1;
    swprintf(flight,32768,L"%ls\\coop-flight.json",folder);
    /* The report's last live guest pc at the terminal module import, measured
     * on NPJH50503 and framework 8704fba. Capture before that caller exits.
     * A recorder trigger freezes evidence only; it does not pause the game,
     * replace the import result or change module/exception semantics. */
    if(!SetEnvironmentVariableW(L"SR_FLIGHT",L"hle,sched,unsupported,fault;4096")||
       !SetEnvironmentVariableW(L"SR_FLIGHT_TRIGGER",L"pc:0x08c94284")||
       !SetEnvironmentVariableW(L"SR_FLIGHT_OUTPUT",flight)||
       !SetEnvironmentVariableW(L"SR_HLELOG",L"1"))return 1;
    swprintf(command,32768,L"\"%ls\"",exe);
    STARTUPINFOW start={0};start.cb=sizeof start;PROCESS_INFORMATION process={0};
    if(!CreateProcessW(exe,command,NULL,NULL,FALSE,0,NULL,root,&start,&process)){
        MessageBoxW(NULL,L"Could not start the existing game launcher. Check that the complete installation is extracted.",L"Lord of Apocalypse diagnostics",MB_OK|MB_ICONERROR);return 1;
    }
    CloseHandle(process.hThread);CloseHandle(process.hProcess);return 0;
}
#endif
