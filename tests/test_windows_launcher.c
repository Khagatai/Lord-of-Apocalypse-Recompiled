#define LOA_LAUNCHER_TEST
#include "../tools/windows-launcher.c"
#include <assert.h>
int wmain(void) {
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
