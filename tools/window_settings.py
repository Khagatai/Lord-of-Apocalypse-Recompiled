"""Apply a requested client size to this launch's own Win32 game window."""
import ctypes
from ctypes import wintypes
import time


def apply(pid, size, timeout=10):
    user = ctypes.WinDLL('user32', use_last_error=True)
    user.SetThreadDpiAwarenessContext.argtypes = (wintypes.HANDLE,)
    user.SetThreadDpiAwarenessContext.restype = wintypes.HANDLE
    previous = user.SetThreadDpiAwarenessContext(-4)
    try:
        return _apply(pid, size, timeout)
    finally:
        if previous:
            user.SetThreadDpiAwarenessContext(previous)


def _apply(pid, size, timeout):
    user = ctypes.WinDLL('user32', use_last_error=True)
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user.GetWindowThreadProcessId.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.DWORD))
    user.IsWindowVisible.argtypes = (wintypes.HWND,)
    user.GetWindowLongW.argtypes = (wintypes.HWND, ctypes.c_int)
    user.GetDpiForWindow.argtypes = (wintypes.HWND,)
    user.AdjustWindowRectExForDpi.argtypes = (ctypes.POINTER(wintypes.RECT), wintypes.DWORD, wintypes.BOOL, wintypes.DWORD, wintypes.UINT)
    user.SetWindowPos.argtypes = (wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT)
    user.GetClientRect.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.RECT))
    user.EnumWindows.argtypes = (callback_type, wintypes.LPARAM)
    found = []
    @callback_type
    def visit(window, _):
        owner = wintypes.DWORD()
        user.GetWindowThreadProcessId(window, ctypes.byref(owner))
        if owner.value == pid and user.IsWindowVisible(window):
            found.append(window)
            return False
        return True
    deadline = time.monotonic()+timeout
    while time.monotonic() < deadline:
        user.EnumWindows(visit, 0)
        if found:
            window = found[0]
            rect = wintypes.RECT(0, 0, *size)
            if not user.AdjustWindowRectExForDpi(ctypes.byref(rect), user.GetWindowLongW(window, -16), False,
                                                user.GetWindowLongW(window, -20), user.GetDpiForWindow(window)):
                raise ctypes.WinError(ctypes.get_last_error())
            if not user.SetWindowPos(window, None, 0, 0, rect.right-rect.left, rect.bottom-rect.top, 0x0002 | 0x0004 | 0x0010):
                raise ctypes.WinError(ctypes.get_last_error())
            actual = wintypes.RECT()
            if not user.GetClientRect(window, ctypes.byref(actual)):
                raise ctypes.WinError(ctypes.get_last_error())
            return {'requested': list(size), 'client': [actual.right, actual.bottom], 'applied': (actual.right, actual.bottom) == tuple(size)}
        time.sleep(0.05)
    return {'requested': list(size), 'applied': False, 'error': 'The game window did not appear within 10 seconds'}
