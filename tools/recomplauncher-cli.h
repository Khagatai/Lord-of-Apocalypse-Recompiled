/* SPDX-License-Identifier: GPL-3.0-or-later
 * Explicit opt-in entry point. Normal no-argument launches keep the GUI. */
static int recomp_launcher_cli(int argc,wchar_t **argv){
    wchar_t python[32768],script[32768],command_line[32768];size_t used=0;
    swprintf(python,32768,L"%ls\\private\\tools\\python314\\python.exe",root);
    swprintf(script,32768,L"%ls\\tools\\recomplauncher.py",root);
    int ok=argument(command_line,32768,&used,python)&&argument(command_line,32768,&used,L"-u")&&argument(command_line,32768,&used,script);
    for(int i=1;i<argc;i++)if(wcscmp(argv[i],L"--recomplauncher"))ok=ok&&argument(command_line,32768,&used,argv[i]);
    if(!ok)return 64;
    STARTUPINFOW si={0};PROCESS_INFORMATION pi={0};si.cb=sizeof si;
    si.dwFlags=STARTF_USESTDHANDLES;si.hStdInput=GetStdHandle(STD_INPUT_HANDLE);
    si.hStdOutput=GetStdHandle(STD_OUTPUT_HANDLE);si.hStdError=GetStdHandle(STD_ERROR_HANDLE);
    if(!CreateProcessW(python,command_line,NULL,NULL,TRUE,CREATE_NO_WINDOW,NULL,root,&si,&pi)){
        const char *error="Cannot start RecompLauncher integration. Extract the complete player ZIP, including its bundled Python and tools.\n";
        DWORD wrote;WriteFile(si.hStdError,error,(DWORD)strlen(error),&wrote,NULL);return 1;
    }
    CloseHandle(pi.hThread);WaitForSingleObject(pi.hProcess,INFINITE);
    DWORD code=1;GetExitCodeProcess(pi.hProcess,&code);CloseHandle(pi.hProcess);return (int)code;
}
