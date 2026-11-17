"""Exercise the owned native network settings window with an isolated profile."""
import ctypes,hashlib,json,subprocess,sys,time
from ctypes import wintypes as w
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import network_settings as settings,title
def main():
    folder=ROOT/'private/coop-menu';folder.mkdir(exist_ok=True);profile=folder/'network.json'
    value=settings.defaults();settings.save(value,profile)
    protected={p:p.read_bytes() if p.exists() else None for p in (settings.SETTINGS,ROOT/'private/settings/graphics.json')}
    user=ctypes.WinDLL('user32',use_last_error=True);visit=ctypes.WINFUNCTYPE(w.BOOL,w.HWND,w.LPARAM)
    user.GetWindowThreadProcessId.argtypes=(w.HWND,ctypes.POINTER(w.DWORD));user.GetClassNameW.argtypes=(w.HWND,w.LPWSTR,ctypes.c_int)
    user.EnumWindows.argtypes=(visit,w.LPARAM);user.EnumChildWindows.argtypes=(w.HWND,visit,w.LPARAM)
    user.SendMessageW.argtypes=(w.HWND,w.UINT,w.WPARAM,w.LPARAM);user.SendMessageW.restype=ctypes.c_ssize_t
    user.PostMessageW.argtypes=(w.HWND,w.UINT,w.WPARAM,w.LPARAM)
    def name(hwnd):
        buf=ctypes.create_unicode_buffer(256);user.GetClassNameW(hwnd,buf,len(buf));return buf.value
    child=subprocess.Popen([str(title.PYTHON),str(ROOT/'tools/network-settings.py'),'--menu','--profile',str(profile)],creationflags=subprocess.CREATE_NO_WINDOW)
    window=None
    try:
        deadline=time.monotonic()+10
        while not window and time.monotonic()<deadline:
            found=[]
            @visit
            def find(hwnd,lp):
                pid=w.DWORD();user.GetWindowThreadProcessId(hwnd,ctypes.byref(pid))
                if pid.value==child.pid and name(hwnd)=='LOANetworkSettings':found.append(hwnd)
                return True
            user.EnumWindows(find,0);window=found[0] if found else None
            if child.poll() is not None:raise RuntimeError('Network menu exited before opening')
            time.sleep(.05)
        if not window:raise RuntimeError('Owned network settings window not found')
        controls=[]
        @visit
        def collect(hwnd,lp):controls.append((hwnd,name(hwnd)));return True
        user.EnumChildWindows(window,collect,0)
        print('Controls:',[n for h,n in controls],flush=True)
        edits=[h for h,n in controls if n=='Edit'];combo=next(h for h,n in controls if n=='ComboBox')
        if len(edits)!=3:raise ValueError('Network menu control contract differs')
        for handle,text in zip(edits,('203.0.113.10','','Synthetic player')):
            buffer=ctypes.create_unicode_buffer(text);user.SendMessageW(handle,0x000c,0,ctypes.cast(buffer,ctypes.c_void_p).value)
        user.SendMessageW(combo,0x14e,2,0)
        time.sleep(.5)
        capture=folder/'network-menu.png'
        subprocess.run(['powershell','-NoProfile','-File',str(ROOT/'tools/capture-owned-window.ps1'),'-Window',str(window),'-Owner',str(child.pid),'-Output',str(capture)],check=True,capture_output=True)
        user.PostMessageW(window,0x111,100,0);code=child.wait(timeout=5)
        saved=settings.load(profile)
        passed=code==0 and saved==dict(value,mode='join',host='203.0.113.10',nickname='Synthetic player') and all(before==(p.read_bytes() if p.exists() else None) for p,before in protected.items())
        report=dict(scope='owned-network-settings-window-isolated-profile',passed=passed,returncode=code,
                    preferences_protected=True,screenshot_sha256=hashlib.sha256(capture.read_bytes()).hexdigest())
        (folder/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
        if not passed:raise SystemExit(1)
    finally:
        if child.poll() is None:
            if window:user.PostMessageW(window,0x10,0,0)
            try:child.wait(timeout=3)
            except subprocess.TimeoutExpired:child.terminate();child.wait(timeout=3)
if __name__=='__main__':main()
