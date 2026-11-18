#define LOA_LAUNCHER_TEST
#include "../tools/windows-launcher.c"
#include <assert.h>
int wmain(void) {
    int settings[LAUNCH_SETTINGS_COUNT];char token[65];const char *controls;
    assert(settings_parse("LOA_SETTINGS 1 missing 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0\r\nLOA_BUILD 16 3 2\r\ncontrols\n",settings,token,&controls));
    assert(settings[LOA_SETTINGS_COUNT]==16&&settings[LOA_SETTINGS_COUNT+1]==3&&settings[LOA_SETTINGS_COUNT+2]==2&&!strcmp(controls,"controls\n"));
    assert(!settings_parse("LOA_SETTINGS 1 missing 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0\nLOA_BUILD 17 3 2\n",settings,token,&controls));
    SetupProgress progress;
    assert(parse_setup_progress("LOA_SETUP_PROGRESS 3 42 111 41",&progress));
    assert(progress.stage==3 && progress.done==42 && progress.total==111 && progress.percent==41);
    assert(parse_setup_progress("LOA_SETUP_PROGRESS 12 1 1 1000",&progress));
    assert(!parse_setup_progress("LOA_SETUP_PROGRESS 10 112 111 500",&progress));
    assert(!parse_setup_progress("LOA_SETUP_PROGRESS 13 1 1 999",&progress));
    assert(!parse_setup_progress("LOA_SETUP_PROGRESS 11 1 1 1000",&progress));
    assert(!parse_setup_progress("LOA_SETUP_PROGRESS 3 1 1 300 garbage",&progress));
    assert(!parse_setup_progress("LOA_SETUP_PROGRESS 3 -1 1 100",&progress));
    assert(!parse_setup_progress("LOA_SETUP_PROGRESS 4294967308 1 1 1000",&progress));
    assert(!parse_setup_progress("LOA_SETUP_PROGRESS 12 0 0 1000",&progress));
    const wchar_t *values[]={L"",L"ordinary",L"C:\\a folder\\",L"a\"quoted\" path",L"$() & path",L"日本語 Ω.iso"};
    wchar_t command[4096]={0};size_t n=0;
    for(unsigned i=0;i<sizeof values/sizeof values[0];i++)assert(argument(command,4096,&n,values[i]));
    int count=0;wchar_t **parsed=CommandLineToArgvW(command,&count);
    assert(parsed && count==6);
    for(int i=0;i<count;i++)assert(!wcscmp(parsed[i],values[i]));
    LocalFree(parsed);n=0;assert(!argument(command,3,&n,L"too long"));
    puts("PASS: Windows Unicode, quotes, trailing backslashes and literal shell metacharacters round trip");
    return 0;
}
