"""Déclarations ctypes de l'API Windows utilisée par le projet (aucune dépendance externe)."""
import ctypes
from ctypes import wintypes as w

user32 = ctypes.WinDLL("user32")
gdi32 = ctypes.WinDLL("gdi32")
kernel32 = ctypes.WinDLL("kernel32")
msimg32 = ctypes.WinDLL("msimg32")

LRESULT = ctypes.c_ssize_t
WNDPROC = ctypes.WINFUNCTYPE(LRESULT, w.HWND, ctypes.c_uint, w.WPARAM, w.LPARAM)
HOOKPROC = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, w.WPARAM, w.LPARAM)
MONITORENUMPROC = ctypes.WINFUNCTYPE(w.BOOL, w.HANDLE, w.HDC, ctypes.POINTER(w.RECT), w.LPARAM)

SRCCOPY, CAPTUREBLT = 0x00CC0020, 0x40000000
WM_DESTROY, WM_PAINT, WM_ERASEBKGND, WM_SETCURSOR, WM_TIMER = 0x2, 0xF, 0x14, 0x20, 0x113
WM_KEYDOWN, WM_SYSKEYDOWN = 0x100, 0x104
WM_MOUSEMOVE, WM_LBUTTONDOWN, WM_RBUTTONDOWN, WM_MBUTTONDOWN = 0x200, 0x201, 0x204, 0x207


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [("vkCode", w.DWORD), ("scanCode", w.DWORD), ("flags", w.DWORD),
                ("time", w.DWORD), ("dwExtraInfo", ctypes.c_size_t)]


class MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [("pt", w.POINT), ("mouseData", w.DWORD), ("flags", w.DWORD),
                ("time", w.DWORD), ("dwExtraInfo", ctypes.c_size_t)]


class WNDCLASS(ctypes.Structure):
    _fields_ = [("style", ctypes.c_uint), ("lpfnWndProc", WNDPROC),
                ("cbClsExtra", ctypes.c_int), ("cbWndExtra", ctypes.c_int),
                ("hInstance", w.HINSTANCE), ("hIcon", w.HANDLE),
                ("hCursor", w.HANDLE), ("hbrBackground", w.HANDLE),
                ("lpszMenuName", w.LPCWSTR), ("lpszClassName", w.LPCWSTR)]


class PAINTSTRUCT(ctypes.Structure):
    _fields_ = [("hdc", w.HDC), ("fErase", w.BOOL), ("rcPaint", w.RECT),
                ("fRestore", w.BOOL), ("fIncUpdate", w.BOOL),
                ("rgbReserved", ctypes.c_byte * 32)]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", w.WORD), ("wScan", w.WORD), ("dwFlags", w.DWORD),
                ("time", w.DWORD), ("dwExtraInfo", ctypes.c_size_t)]


class MOUSEINPUT(ctypes.Structure):  # sert uniquement à donner à INPUT sa bonne taille
    _fields_ = [("dx", w.LONG), ("dy", w.LONG), ("mouseData", w.DWORD),
                ("dwFlags", w.DWORD), ("time", w.DWORD), ("dwExtraInfo", ctypes.c_size_t)]


class _InputUnion(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", w.DWORD), ("u", _InputUnion)]


class BLENDFUNCTION(ctypes.Structure):
    _fields_ = [("BlendOp", ctypes.c_ubyte), ("BlendFlags", ctypes.c_ubyte),
                ("SourceConstantAlpha", ctypes.c_ubyte), ("AlphaFormat", ctypes.c_ubyte)]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [("biSize", w.DWORD), ("biWidth", w.LONG), ("biHeight", w.LONG),
                ("biPlanes", w.WORD), ("biBitCount", w.WORD), ("biCompression", w.DWORD),
                ("biSizeImage", w.DWORD), ("biXPelsPerMeter", w.LONG),
                ("biYPelsPerMeter", w.LONG), ("biClrUsed", w.DWORD), ("biClrImportant", w.DWORD)]


def _sig(lib, name, restype, *argtypes):
    fn = getattr(lib, name)
    fn.restype, fn.argtypes = restype, list(argtypes)


i, u = ctypes.c_int, ctypes.c_uint
P = ctypes.POINTER

# --- user32 ---
_sig(user32, "DefWindowProcW", LRESULT, w.HWND, u, w.WPARAM, w.LPARAM)
_sig(user32, "CallNextHookEx", LRESULT, w.HANDLE, i, w.WPARAM, w.LPARAM)
_sig(user32, "SetWindowsHookExW", w.HANDLE, i, HOOKPROC, w.HINSTANCE, w.DWORD)
_sig(user32, "UnhookWindowsHookEx", w.BOOL, w.HANDLE)
_sig(user32, "CreateWindowExW", w.HWND, w.DWORD, w.LPCWSTR, w.LPCWSTR, w.DWORD, i, i, i, i,
     w.HWND, w.HANDLE, w.HINSTANCE, w.LPVOID)
_sig(user32, "RegisterClassW", w.WORD, P(WNDCLASS))
_sig(user32, "DestroyWindow", w.BOOL, w.HWND)
_sig(user32, "PostQuitMessage", None, i)
_sig(user32, "GetMessageW", i, P(w.MSG), w.HWND, u, u)
_sig(user32, "TranslateMessage", w.BOOL, P(w.MSG))
_sig(user32, "DispatchMessageW", LRESULT, P(w.MSG))
_sig(user32, "SetTimer", ctypes.c_size_t, w.HWND, ctypes.c_size_t, u, w.LPVOID)
_sig(user32, "SetWindowPos", w.BOOL, w.HWND, w.HWND, i, i, i, i, u)
_sig(user32, "SetWindowDisplayAffinity", w.BOOL, w.HWND, w.DWORD)
_sig(user32, "SetForegroundWindow", w.BOOL, w.HWND)
_sig(user32, "InvalidateRect", w.BOOL, w.HWND, P(w.RECT), w.BOOL)
_sig(user32, "BeginPaint", w.HDC, w.HWND, P(PAINTSTRUCT))
_sig(user32, "EndPaint", w.BOOL, w.HWND, P(PAINTSTRUCT))
_sig(user32, "GetDC", w.HDC, w.HWND)
_sig(user32, "ReleaseDC", i, w.HWND, w.HDC)
_sig(user32, "DrawTextW", i, w.HDC, w.LPCWSTR, i, P(w.RECT), u)
_sig(user32, "FindWindowW", w.HWND, w.LPCWSTR, w.LPCWSTR)
_sig(user32, "FindWindowExW", w.HWND, w.HWND, w.HWND, w.LPCWSTR, w.LPCWSTR)
_sig(user32, "GetWindowRect", w.BOOL, w.HWND, P(w.RECT))
_sig(user32, "EnumDisplayMonitors", w.BOOL, w.HDC, P(w.RECT), MONITORENUMPROC, w.LPARAM)
_sig(user32, "SendInput", u, u, P(INPUT), i)
_sig(user32, "GetForegroundWindow", w.HWND)
_sig(user32, "GetClassNameW", i, w.HWND, w.LPWSTR, i)
_sig(user32, "GetCursorPos", w.BOOL, P(w.POINT))
_sig(user32, "LoadCursorW", w.HANDLE, w.HINSTANCE, w.LPVOID)
_sig(user32, "SetCursor", w.HANDLE, w.HANDLE)
_sig(user32, "GetSystemMetrics", i, i)
_sig(user32, "LockWorkStation", w.BOOL)
_sig(user32, "OpenDesktopW", w.HANDLE, w.LPCWSTR, w.DWORD, w.BOOL, w.DWORD)
_sig(user32, "SwitchDesktop", w.BOOL, w.HANDLE)
_sig(user32, "CloseDesktop", w.BOOL, w.HANDLE)

# --- gdi32 ---
_sig(gdi32, "CreateCompatibleDC", w.HDC, w.HDC)
_sig(gdi32, "CreateCompatibleBitmap", w.HANDLE, w.HDC, i, i)
_sig(gdi32, "CreateDIBSection", w.HANDLE, w.HDC, P(BITMAPINFOHEADER), u, P(ctypes.c_void_p), w.HANDLE, w.DWORD)
_sig(gdi32, "SelectObject", w.HANDLE, w.HDC, w.HANDLE)
_sig(gdi32, "DeleteObject", w.BOOL, w.HANDLE)
_sig(gdi32, "DeleteDC", w.BOOL, w.HDC)
_sig(gdi32, "BitBlt", w.BOOL, w.HDC, i, i, i, i, w.HDC, i, i, w.DWORD)
_sig(gdi32, "StretchBlt", w.BOOL, w.HDC, i, i, i, i, w.HDC, i, i, i, i, w.DWORD)
_sig(gdi32, "SetStretchBltMode", i, w.HDC, i)
_sig(gdi32, "SetBrushOrgEx", w.BOOL, w.HDC, i, i, w.LPVOID)
_sig(gdi32, "SaveDC", i, w.HDC)
_sig(gdi32, "RestoreDC", w.BOOL, w.HDC, i)
_sig(gdi32, "IntersectClipRect", i, w.HDC, i, i, i, i)
_sig(gdi32, "CreatePen", w.HANDLE, i, i, w.DWORD)
_sig(gdi32, "CreateSolidBrush", w.HANDLE, w.DWORD)
_sig(gdi32, "GetStockObject", w.HANDLE, i)
_sig(gdi32, "Rectangle", w.BOOL, w.HDC, i, i, i, i)
_sig(gdi32, "Ellipse", w.BOOL, w.HDC, i, i, i, i)
_sig(gdi32, "RoundRect", w.BOOL, w.HDC, i, i, i, i, i, i)
_sig(gdi32, "PolyBezier", w.BOOL, w.HDC, P(w.POINT), w.DWORD)
_sig(gdi32, "SetBkMode", i, w.HDC, i)
_sig(gdi32, "SetTextColor", w.DWORD, w.HDC, w.DWORD)
_sig(gdi32, "CreateFontW", w.HANDLE, i, i, i, i, i, w.DWORD, w.DWORD, w.DWORD, w.DWORD,
     w.DWORD, w.DWORD, w.DWORD, w.DWORD, w.LPCWSTR)

# --- msimg32 / kernel32 ---
_sig(msimg32, "AlphaBlend", w.BOOL, w.HDC, i, i, i, i, w.HDC, i, i, i, i, BLENDFUNCTION)
_sig(kernel32, "GetModuleHandleW", w.HINSTANCE, w.LPCWSTR)
_sig(kernel32, "GetTickCount64", ctypes.c_ulonglong)


del i, u, P  # raccourcis de déclaration, inutiles ailleurs


def memory_dc(width, height):
    """Contexte graphique en mémoire de width x height pixels."""
    screen = user32.GetDC(None)
    dc = gdi32.CreateCompatibleDC(screen)
    gdi32.SelectObject(dc, gdi32.CreateCompatibleBitmap(screen, width, height))
    user32.ReleaseDC(None, screen)
    return dc
