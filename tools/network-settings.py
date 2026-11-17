"""Developer-only direct-IP prototype settings; not the player-facing F1 menu."""
import argparse,ctypes,json,sys
from ctypes import wintypes as w
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import network_settings as settings

def menu(profile):
    value=settings.load(profile);user=ctypes.WinDLL('user32',use_last_error=True);kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    CALLBACK=ctypes.WINFUNCTYPE(ctypes.c_ssize_t,w.HWND,w.UINT,w.WPARAM,w.LPARAM)
    class WNDCLASS(ctypes.Structure):
        _fields_=[('style',w.UINT),('lpfnWndProc',CALLBACK),('cbClsExtra',ctypes.c_int),('cbWndExtra',ctypes.c_int),('hInstance',w.HINSTANCE),('hIcon',w.HICON),('hCursor',w.HANDLE),('hbrBackground',w.HBRUSH),('lpszMenuName',w.LPCWSTR),('lpszClassName',w.LPCWSTR)]
    user.DefWindowProcW.argtypes=(w.HWND,w.UINT,w.WPARAM,w.LPARAM);user.DefWindowProcW.restype=ctypes.c_ssize_t
    user.CreateWindowExW.argtypes=(w.DWORD,w.LPCWSTR,w.LPCWSTR,w.DWORD,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,w.HWND,w.HMENU,w.HINSTANCE,w.LPVOID);user.CreateWindowExW.restype=w.HWND
    user.SendMessageW.argtypes=(w.HWND,w.UINT,w.WPARAM,w.LPARAM);user.SendMessageW.restype=ctypes.c_ssize_t
    user.GetWindowTextW.argtypes=(w.HWND,w.LPWSTR,ctypes.c_int)
    user.DestroyWindow.argtypes=(w.HWND,);user.MessageBoxW.argtypes=(w.HWND,w.LPCWSTR,w.LPCWSTR,w.UINT)
    user.RegisterClassW.argtypes=(ctypes.POINTER(WNDCLASS),);kernel.GetModuleHandleW.argtypes=(w.LPCWSTR,);kernel.GetModuleHandleW.restype=w.HMODULE
    controls={};instance=kernel.GetModuleHandleW(None)
    def text(handle):
        buf=ctypes.create_unicode_buffer(256);user.GetWindowTextW(handle,buf,len(buf));return buf.value
    @CALLBACK
    def procedure(window,message,wp,lp):
        if message==0x111 and (wp&65535)==100:
            try:
                updated=dict(value)
                updated['mode']=('off','host','join')[user.SendMessageW(controls['mode'],0x147,0,0)]
                for name in ('host','public_host','nickname'):updated[name]=text(controls[name]).strip()
                settings.save(updated,profile);user.DestroyWindow(window)
            except Exception as error:user.MessageBoxW(window,str(error),'Co-op settings',0x10)
            return 0
        if message==0x111 and (wp&65535)==101:user.DestroyWindow(window);return 0
        if message==2:user.PostQuitMessage(0);return 0
        return user.DefWindowProcW(window,message,wp,lp)
    cls=WNDCLASS();cls.lpfnWndProc=procedure;cls.hInstance=instance;cls.hbrBackground=6;cls.lpszClassName='LOANetworkSettings'
    if not user.RegisterClassW(ctypes.byref(cls)):raise ctypes.WinError(ctypes.get_last_error())
    window=user.CreateWindowExW(0,cls.lpszClassName,'Lord of Apocalypse — Co-op settings',0x00ca0000,180,180,600,430,None,None,instance,None)
    if not window:raise ctypes.WinError(ctypes.get_last_error())
    def widget(kind,label,style,x,y,width,height,ident=0):
        control=user.CreateWindowExW(0,kind,label,0x50010000|style,x,y,width,height,window,ident,instance,None)
        if not control:raise ctypes.WinError(ctypes.get_last_error())
        return control
    widget('STATIC','Experimental internet peer-to-peer co-op',0,20,18,550,24)
    widget('STATIC','Room and mission play are still under validation.',0,20,44,550,24)
    widget('STATIC','Mode',0,20,88,180,24)
    controls['mode']=widget('COMBOBOX','',0x0003|0x200000,210,84,340,180)
    for choice in ('Off','Host a room','Join a host'):
        data=ctypes.create_unicode_buffer(choice);user.SendMessageW(controls['mode'],0x143,0,ctypes.cast(data,ctypes.c_void_p).value)
    user.SendMessageW(controls['mode'],0x14e,('off','host','join').index(value['mode']),0)
    for i,(name,label) in enumerate([('host',"Host's public IPv4"),('public_host','Your public IPv4 (hosting)'),('nickname','Player nickname')]):
        y=126+i*42;widget('STATIC',label,0,20,y+4,190,24);controls[name]=widget('EDIT',value[name],0x00800000|0x80,210,y,340,27)
    widget('STATIC','Changes apply after restarting the game. Save your progress first.',0,20,264,550,30)
    widget('STATIC','Direct internet play currently needs manual router port forwarding.\nNo public servers, automatic router changes or game-file uploads.',0,20,298,550,42)
    widget('BUTTON','Save',0x0001,338,352,100,30,100);widget('BUTTON','Cancel',0,450,352,100,30,101)
    user.ShowWindow.argtypes=(w.HWND,ctypes.c_int);user.UpdateWindow.argtypes=(w.HWND,)
    user.ShowWindow(window,5);user.UpdateWindow(window);message=w.MSG()
    user.GetMessageW.argtypes=(ctypes.POINTER(w.MSG),w.HWND,w.UINT,w.UINT)
    user.TranslateMessage.argtypes=(ctypes.POINTER(w.MSG),);user.DispatchMessageW.argtypes=(ctypes.POINTER(w.MSG),);user.DispatchMessageW.restype=ctypes.c_ssize_t
    while user.GetMessageW(ctypes.byref(message),None,0,0)>0:user.TranslateMessage(ctypes.byref(message));user.DispatchMessageW(ctypes.byref(message))

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--profile',type=Path,default=settings.SETTINGS)
    parser.add_argument('--menu',action='store_true');parser.add_argument('--mode',choices=('off','host','join'))
    parser.add_argument('--host');parser.add_argument('--public-host');parser.add_argument('--bind');parser.add_argument('--nickname');parser.add_argument('--port',type=int)
    args=parser.parse_args();profile=settings.profile_path(args.profile)
    if args.menu:menu(profile);return
    value=settings.load(profile)
    for name in ('mode','host','public_host','bind','nickname','port'):
        if getattr(args,name) is not None:value[name]=getattr(args,name)
    if any(getattr(args,k) is not None for k in ('mode','host','public_host','bind','nickname','port')):settings.save(value,profile)
    print(json.dumps(value,indent=2))
if __name__=='__main__':
    try:main()
    except Exception as error:
        if '--menu' in sys.argv:ctypes.WinDLL('user32').MessageBoxW(None,str(error),'Co-op settings',0x10)
        else:raise
