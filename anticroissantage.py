"""AntiCroissantage : un faux bureau verrouillé pour piéger les collègues.

Lancer       : pythonw anticroissantage.py
Test sûr     : python anticroissantage.py --timeout 20 --nolock
Déverrouiller: AltGr + H (verrouille ensuite vraiment la session Windows)

Le script affiche le vrai bureau en direct (recopié ~20 fois par seconde) en plein écran,
et avale clavier et clics : vidéo, horloge et fenêtres continuent de bouger, mais rien ne répond.
Le curseur bouge, le menu Démarrer est un miroir du vrai. Un clic affiche un paquet
« Ceci n'est pas une clope ».

Options : --fige (photo figée au lieu du direct, seules la barre des tâches et le menu bougent),
          --fps N (images par seconde en direct, 20 par défaut), --mesure (affiche images/s et CPU à la fin),
          --timeout N (déverrouille seul après N s), --nolock (ne verrouille pas la session).
"""
import base64
import ctypes
import random
import subprocess
import sys
import threading
import time
from types import SimpleNamespace

import clope
from winapi import *  # noqa: F403  (constantes, structures et fonctions Windows)

user32.SetProcessDPIAware()
X, Y = user32.GetSystemMetrics(76), user32.GetSystemMetrics(77)  # coin haut-gauche du bureau virtuel
W, H = user32.GetSystemMetrics(78), user32.GetSystemMetrics(79)  # sa taille (tous les écrans)

VK_H, VK_RMENU, VK_LWIN, VK_RWIN, VK_ESCAPE, VK_RETURN = 0x48, 0xA5, 0x5B, 0x5C, 0x1B, 0x0D
VK_CTRL_GAUCHE = 0xA2  # AltGr envoie un Ctrl fantôme juste avant
# Touches jamais transmises au vrai menu Démarrer : Entrée, Ctrl, Alt, Tab, F1-F24
BLOQUEES = {VK_RETURN, 0x11, 0xA2, 0xA3, 0x12, 0xA4, 0xA5, 0x09, *range(0x70, 0x88)}

PANEL_MS = 6000    # le paquet disparaît après ce délai sans clic
SMOKE_LIFE = 28    # durée de vie d'une bouffée de fumée (en images)
MESSAGES = ["Ça sert à rien de cliquer.", "Elle arrivera pas, ta clope.", "Toujours pas une clope.",
            "Tu peux cliquer toute la journée.", "Va plutôt chercher des croissants.", "Bon, t'as fini ?"]

# État du verrouillage (une seule instance du programme)
s = SimpleNamespace(
    wins={},            # fenêtre -> (décalage x, y) de son écran dans l'image
    mem=None,           # image du bureau : photo figée, ou recopie en direct du vrai bureau
    live=None,          # copie en direct du vrai menu Démarrer
    frame=None,         # image composée avant affichage (évite le scintillement)
    taskbars=[],        # rectangles des barres des tâches
    panel=None,         # le paquet affiché : SimpleNamespace(rc, message, burn, dc)
    panel_until=0, msg_i=0, particles=[], puff=None, tick=0,
    menu=False, menu_t=0, start_rect=None, mirror_ok=True,
    live_on=False, fps=20, next_grab=0, frames=0, grab_s=0.0,   # mode en direct et mesures
    altgr=False, keys_down=set(), unlock_lock=True, deadline=0, arrow=None, hinst=None)
stats = SimpleNamespace(clicks=0, keys=0, menus=0, smoked=0, first=None, last=None)


def now():
    return kernel32.GetTickCount64()


def note_attempt():
    stats.last = time.time()
    stats.first = stats.first or stats.last


# --- Écrans, photo, barres des tâches ------------------------------------------------------------

def monitors():
    found = []

    @MONITORENUMPROC
    def callback(hmon, hdc, rect, lparam):
        r = rect.contents
        found.append((r.left, r.top, r.right - r.left, r.bottom - r.top))
        return True

    user32.EnumDisplayMonitors(None, None, callback, 0)
    return found or [(X, Y, W, H)]


def find_taskbars():
    """Rectangles (dans l'image) de la barre principale et des barres des autres écrans."""
    handles, prev = [user32.FindWindowW("Shell_TrayWnd", None)], None
    while True:
        prev = user32.FindWindowExW(None, prev, "Shell_SecondaryTrayWnd", None)
        if not prev:
            break
        handles.append(prev)
    rects = []
    for hwnd in filter(None, handles):
        r = w.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(r))
        if r.bottom - r.top >= 20 and Y <= r.top and r.bottom <= Y + H:  # ignore une barre masquée
            rects.append(w.RECT(r.left - X, r.top - Y, r.right - X, r.bottom - Y))
    return rects


def capture():
    s.mem, s.live, s.frame = memory_dc(W, H), memory_dc(W, H), memory_dc(W, H)
    screen = user32.GetDC(None)
    gdi32.BitBlt(s.mem, 0, 0, W, H, screen, X, Y, SRCCOPY | CAPTUREBLT)
    user32.ReleaseDC(None, screen)


def grab_desktop():
    """Mode en direct : recopie le vrai bureau (sous nos fenêtres, exclues des captures) dans s.mem."""
    t0 = time.perf_counter()
    screen = user32.GetDC(None)
    gdi32.BitBlt(s.mem, 0, 0, W, H, screen, X, Y, SRCCOPY)  # sans CAPTUREBLT : plus rapide, sans scintillement du curseur
    user32.ReleaseDC(None, screen)
    s.frames += 1
    s.grab_s += time.perf_counter() - t0
    for hwnd in list(s.wins):
        user32.InvalidateRect(hwnd, None, False)


def refresh_taskbars():
    """Recopie la vraie barre des tâches dans la photo : l'horloge reste à l'heure."""
    screen = user32.GetDC(None)
    for rc in s.taskbars:
        gdi32.BitBlt(s.mem, rc.left, rc.top, rc.right - rc.left, rc.bottom - rc.top,
                     screen, rc.left + X, rc.top + Y, SRCCOPY)
        invalidate(rc)
    user32.ReleaseDC(None, screen)


def invalidate(rc):
    """Demande le redessin de la zone rc (coordonnées de l'image) dans chaque fenêtre."""
    for hwnd, (ox, oy) in list(s.wins.items()):
        r = w.RECT(rc.left - ox, rc.top - oy, rc.right - ox, rc.bottom - oy)
        user32.InvalidateRect(hwnd, ctypes.byref(r), False)


# --- Menu Démarrer miroir -----------------------------------------------------------------------
# Le vrai menu s'ouvre sous le faux bureau (nos fenêtres sont exclues des captures d'écran).
# On en affiche une copie en direct ; les clics et Entrée sont bloqués, donc rien ne se lance.

def menu_rect():
    """Zone où le menu peut apparaître : au-dessus de la barre des tâches principale."""
    t = s.taskbars[0] if s.taskbars else None
    return w.RECT(max(t.left, 0), max(t.bottom - 950, 0), t.right, t.bottom) if t else None


def tap(vk):
    keys = (INPUT * 2)()
    for k, flags in zip(keys, (0, 2)):  # appui puis relâchement
        k.type, k.u.ki = 1, KEYBDINPUT(vk, 0, flags, 0, 0)
    user32.SendInput(2, keys, ctypes.sizeof(INPUT))


def open_menu():
    if s.menu or not s.mirror_ok or not s.taskbars or now() - s.menu_t < 500:
        return
    s.menu, s.menu_t = True, now()
    stats.menus += 1
    hide_panel()
    tap(VK_LWIN)


def close_menu():
    if s.menu:
        s.menu, s.menu_t = False, now()
        tap(VK_ESCAPE)
        invalidate(menu_rect())


def menu_has_focus():
    name = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(user32.GetForegroundWindow(), name, 256)
    return any(part in name.value for part in ("CoreWindow", "Xaml", "Shell", "Start", "Search"))


def find_start_button():
    """Cherche le bouton Démarrer avec UI Automation (PowerShell, en tâche de fond)."""
    script = (
        "Add-Type -AssemblyName UIAutomationClient,UIAutomationTypes;"
        "Add-Type 'using System.Runtime.InteropServices; public class D{[DllImport(\"user32.dll\")] public static extern bool SetProcessDPIAware();}';"
        "[D]::SetProcessDPIAware()|Out-Null;"
        "$A=[Windows.Automation.AutomationElement];"
        "$t=$A::RootElement.FindFirst('Children',(New-Object Windows.Automation.PropertyCondition($A::ClassNameProperty,'Shell_TrayWnd')));"
        "$e=$t.FindFirst('Descendants',(New-Object Windows.Automation.PropertyCondition($A::AutomationIdProperty,'StartButton')));"
        "$r=$e.Current.BoundingRectangle;\"$([int]$r.Left),$([int]$r.Top),$([int]$r.Right),$([int]$r.Bottom)\""
    )
    encoded = base64.b64encode(script.encode("utf-16-le")).decode()
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-EncodedCommand", encoded], capture_output=True,
                             text=True, timeout=20, creationflags=0x08000000, stdin=subprocess.DEVNULL).stdout
        s.start_rect = tuple(int(v) for v in out.strip().split(","))
    except Exception:  # bouton introuvable : seule la touche Windows ouvrira le menu
        pass


# --- Paquet « Ceci n'est pas une clope » et fumée -------------------------------------------------

def show_panel(px, py):
    """Affiche le paquet au centre de l'écran où l'on a cliqué."""
    screens = monitors()
    mx, my, mw, mh = next((m for m in screens if m[0] <= px < m[0] + m[2] and m[1] <= py < m[1] + m[3]), screens[0])
    pw = int(mw * 0.40)
    ph = int(pw * 0.62)
    left, top = mx - X + (mw - pw) // 2, my - Y + (mh - ph) // 2
    s.panel = SimpleNamespace(rc=w.RECT(left, top, left + pw, top + ph), message=clope.TEXTE, burn=0,
                              dc=clope.paquet(pw, ph))
    invalidate(s.panel.rc)


def burn_panel():
    """Un clic sur le paquet : la clope se consume un peu plus, avec un nouveau message."""
    p = s.panel
    p.burn += 1
    if p.burn >= clope.BURN_MAX:
        p.message = clope.TEXTE_FINI
        stats.smoked += 1
    else:
        p.message = MESSAGES[s.msg_i % len(MESSAGES)]
        s.msg_i += 1
    p.dc = clope.paquet(p.rc.right - p.rc.left, p.rc.bottom - p.rc.top, p.message, p.burn)
    invalidate(p.rc)


def hide_panel():
    if s.panel:
        invalidate(s.panel.rc)
        s.panel = None


def on_click(px, py):
    """Clic sur le faux bureau (px, py : coordonnées écran)."""
    s.panel_until = now() + PANEL_MS
    p = s.panel
    if not p:
        show_panel(px, py)
    elif p.burn < clope.BURN_MAX and p.rc.left <= px - X < p.rc.right and p.rc.top <= py - Y < p.rc.bottom:
        burn_panel()


def scale():
    return max(user32.GetSystemMetrics(1) / 1080, 0.6)  # la fumée grossit avec la définition de l'écran


def smoke_step():
    """Fait monter les bouffées de fumée ; le paquet affiché en fait naître sous le curseur."""
    k = scale()
    parts = s.particles
    zone = (20 + SMOKE_LIFE * 2.4) * k

    def bbox():
        return w.RECT(int(min(p[0] for p in parts) - zone), int(min(p[1] for p in parts) - zone),
                      int(max(p[0] for p in parts) + zone), int(max(p[1] for p in parts) + zone)) if parts else None

    before = bbox()
    for p in parts:
        p[0] += p[3] * k
        p[1] -= 2.4 * k
        p[2] += 1
    parts[:] = [p for p in parts if p[2] < SMOKE_LIFE]
    if s.panel:
        pt = w.POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        parts.append([pt.x - X + random.uniform(-3, 3) * k, pt.y - Y - 6 * k, 0, random.uniform(-0.9, 0.9)])
    for rc in (before, bbox()):
        if rc:
            invalidate(rc)


def has_overlay():
    return bool(s.panel or s.particles or (s.menu and not s.live_on))


def compose(zone):
    """Compose la zone (coordonnées de l'image) dans s.frame : photo, menu, paquet, fumée."""
    f = s.frame
    saved = gdi32.SaveDC(f)
    gdi32.IntersectClipRect(f, zone.left, zone.top, zone.right, zone.bottom)
    gdi32.BitBlt(f, 0, 0, W, H, s.mem, 0, 0, SRCCOPY)
    if s.menu and not s.live_on:  # en direct, le vrai menu est déjà dans s.mem
        mr = menu_rect()
        gdi32.BitBlt(f, mr.left, mr.top, mr.right - mr.left, mr.bottom - mr.top, s.live, 0, 0, SRCCOPY)
    if s.panel:
        rc = s.panel.rc
        gdi32.BitBlt(f, rc.left, rc.top, rc.right - rc.left, rc.bottom - rc.top, s.panel.dc, 0, 0, SRCCOPY)
    for x, y, age, _ in s.particles:
        size = int((20 + age * 2.4) * scale())
        alpha = int(150 * (1 - age / SMOKE_LIFE))
        msimg32.AlphaBlend(f, int(x - size / 2), int(y - size / 2), size, size, s.puff, 0, 0, 64, 64,
                           BLENDFUNCTION(0, 0, alpha, 1))
    gdi32.RestoreDC(f, saved)


# --- Clavier et souris ----------------------------------------------------------------------------

def unlock(lock_session=True):
    s.unlock_lock = lock_session
    close_menu()
    for hwnd in list(s.wins):
        user32.DestroyWindow(hwnd)


@HOOKPROC
def keyboard_hook(n, wp, lp):
    if n < 0:
        return user32.CallNextHookEx(None, n, wp, lp)
    key = ctypes.cast(lp, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
    if key.flags & 0x10:  # touche que nous avons nous-mêmes envoyée : on laisse passer
        return user32.CallNextHookEx(None, n, wp, lp)
    vk, down = key.vkCode, wp in (WM_KEYDOWN, WM_SYSKEYDOWN)
    if vk == VK_RMENU:
        s.altgr = down
        return 1
    if down and vk == VK_H and s.altgr:
        unlock("--nolock" not in sys.argv)
        return 1
    if vk != VK_CTRL_GAUCHE:  # on compte les tentatives, sans la répétition automatique
        if not down:
            s.keys_down.discard(vk)
        elif vk not in s.keys_down:
            s.keys_down.add(vk)
            stats.keys += 1
            note_attempt()
    if vk in (VK_LWIN, VK_RWIN):
        if down:
            close_menu() if s.menu else open_menu()
    elif s.menu and vk == VK_ESCAPE:
        if down:
            close_menu()
    elif s.menu and vk not in BLOQUEES and menu_has_focus():
        return user32.CallNextHookEx(None, n, wp, lp)  # la frappe va au vrai menu
    return 1  # tout le reste est avalé


@HOOKPROC
def mouse_hook(n, wp, lp):
    if n < 0 or wp == WM_MOUSEMOVE:  # le curseur bouge normalement
        return user32.CallNextHookEx(None, n, wp, lp)
    if wp in (WM_LBUTTONDOWN, WM_RBUTTONDOWN, WM_MBUTTONDOWN):
        stats.clicks += 1
        note_attempt()
        pt = ctypes.cast(lp, ctypes.POINTER(MSLLHOOKSTRUCT)).contents.pt
        if s.menu:
            close_menu()
        elif wp == WM_LBUTTONDOWN and s.start_rect and s.start_rect[0] <= pt.x <= s.start_rect[2] \
                and s.start_rect[1] <= pt.y <= s.start_rect[3]:
            open_menu()
        else:
            on_click(pt.x, pt.y)
    return 1  # clics et molette avalés


# --- Fenêtres -------------------------------------------------------------------------------------

def slow_step():
    """Toutes les 100 ms : fenêtres au premier plan, menu en direct, expiration, barre des tâches."""
    for hwnd in list(s.wins):
        user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x2 | 0x1 | 0x10)  # HWND_TOPMOST, sans bouger
    user32.SetCursor(s.arrow)
    if s.live_on:
        pass  # le bureau entier est déjà recopié en direct
    elif s.menu:
        mr = menu_rect()
        screen = user32.GetDC(None)
        gdi32.BitBlt(s.live, 0, 0, mr.right - mr.left, mr.bottom - mr.top, screen, mr.left + X, mr.top + Y, SRCCOPY)
        user32.ReleaseDC(None, screen)
        invalidate(mr)
    elif s.tick % 10 == 0:
        refresh_taskbars()
    if s.panel and now() > s.panel_until:
        hide_panel()
    if s.deadline and now() > s.deadline:
        unlock(False)


@WNDPROC
def window_proc(hwnd, msg, wp, lp):
    if msg == WM_PAINT:
        ps = PAINTSTRUCT()
        hdc = user32.BeginPaint(hwnd, ctypes.byref(ps))
        ox, oy = s.wins.get(hwnd, (0, 0))
        r = ps.rcPaint
        zone = w.RECT(r.left + ox, r.top + oy, r.right + ox, r.bottom + oy)
        source = s.mem
        if has_overlay():  # sinon on évite une copie : s.mem va directement à l'écran
            compose(zone)
            source = s.frame
        gdi32.BitBlt(hdc, r.left, r.top, r.right - r.left, r.bottom - r.top, source, zone.left, zone.top, SRCCOPY)
        user32.EndPaint(hwnd, ctypes.byref(ps))
        return 0
    if msg == WM_ERASEBKGND:
        return 1
    if msg == WM_SETCURSOR:  # toujours la flèche normale
        user32.SetCursor(s.arrow)
        return 1
    if msg == WM_TIMER:  # ~30 fois/s
        s.tick += 1
        if s.live_on and time.perf_counter() >= s.next_grab:
            s.next_grab = time.perf_counter() + 1 / s.fps
            grab_desktop()
        smoke_step()
        if s.tick % 3 == 0:
            slow_step()
        return 0
    if msg == WM_DESTROY:
        user32.PostQuitMessage(0)
        return 0
    return user32.DefWindowProcW(hwnd, msg, wp, lp)


def create_window(proc, name, x, y, width, height, topmost_flags):
    cls = WNDCLASS()
    cls.lpfnWndProc, cls.hInstance, cls.hCursor, cls.lpszClassName = proc, s.hinst, s.arrow, name
    user32.RegisterClassW(ctypes.byref(cls))
    return user32.CreateWindowExW(topmost_flags, name, name, 0x80000000 | 0x10000000,  # WS_POPUP | WS_VISIBLE
                                  x, y, width, height, None, None, s.hinst, None)


def message_loop():
    msg = w.MSG()
    while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
        user32.TranslateMessage(ctypes.byref(msg))
        user32.DispatchMessageW(ctypes.byref(msg))


# --- Retour de l'utilisateur ------------------------------------------------------------------------

def session_locked():
    desktop = user32.OpenDesktopW("Default", 0, False, 0x0100)  # DESKTOP_SWITCHDESKTOP
    if not desktop:
        return True
    switched = user32.SwitchDesktop(desktop)
    user32.CloseDesktop(desktop)
    return not switched


def wait_for_unlock():
    """Attend que le mot de passe soit tapé (le verrouillage met un instant à s'installer)."""
    start = time.time()
    while not session_locked() and time.time() - start < 8:
        time.sleep(0.2)
    while session_locked():
        time.sleep(0.5)
    time.sleep(0.8)


def show_scoreboard():
    """Tableau de chasse : ce qui s'est passé pendant ton absence."""
    def hhmm(t):
        return time.strftime("%H:%M", time.localtime(t))

    rows = [("Clics", stats.clicks), ("Touches", stats.keys)]
    if stats.menus:
        rows.append(("Menu Démarrer ouvert", f"{stats.menus} fois"))
    if stats.smoked:
        rows.append(("Clopes fumées", stats.smoked))
    rows += [("Première tentative", hhmm(stats.first)), ("Dernière tentative", hhmm(stats.last))]

    sw, sh = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
    cw = int(sw * 0.36)
    ch = int(cw * 0.62)
    card = clope.score(cw, ch, rows)

    @WNDPROC
    def proc(hwnd, msg, wp, lp):
        if msg == WM_PAINT:
            ps = PAINTSTRUCT()
            hdc = user32.BeginPaint(hwnd, ctypes.byref(ps))
            gdi32.BitBlt(hdc, 0, 0, cw, ch, card, 0, 0, SRCCOPY)
            user32.EndPaint(hwnd, ctypes.byref(ps))
        elif msg in (WM_LBUTTONDOWN, WM_RBUTTONDOWN, WM_KEYDOWN):
            user32.DestroyWindow(hwnd)
        elif msg == WM_DESTROY:
            user32.PostQuitMessage(0)
        else:
            return user32.DefWindowProcW(hwnd, msg, wp, lp)
        return 0

    hwnd = create_window(proc, "TableauDeChasse", (sw - cw) // 2, (sh - ch) // 2, cw, ch, 0x8)
    user32.SetForegroundWindow(hwnd)
    message_loop()


# --- Programme ----------------------------------------------------------------------------------------

def option(name, default):
    """Valeur numérique qui suit --name dans la ligne de commande."""
    return int(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else default


def main():
    s.live_on = "--fige" not in sys.argv
    s.fps = max(option("--fps", 20), 1)
    t_start, cpu_start = time.perf_counter(), time.process_time()
    if "--timeout" in sys.argv:  # filet de sécurité pour tester : déverrouille tout seul
        s.deadline = now() + option("--timeout", 15) * 1000
    s.hinst = kernel32.GetModuleHandleW(None)
    s.arrow = user32.LoadCursorW(None, 32512)  # IDC_ARROW
    s.puff = clope.bouffee()

    capture()
    s.taskbars = find_taskbars()
    for i, (x, y, width, height) in enumerate(monitors()):  # une fenêtre par écran
        hwnd = create_window(window_proc, "AntiCroissantage", x, y, width, height, 0x8 | 0x80)  # TOPMOST | TOOLWINDOW
        s.wins[hwnd] = (x - X, y - Y)
        if not user32.SetWindowDisplayAffinity(hwnd, 0x11):  # nos fenêtres invisibles aux captures
            s.mirror_ok = False
        if i == 0:
            user32.SetTimer(hwnd, 1, 33, None)
    threading.Thread(target=find_start_button, daemon=True).start()

    hooks = [user32.SetWindowsHookExW(13, keyboard_hook, s.hinst, 0),  # WH_KEYBOARD_LL
             user32.SetWindowsHookExW(14, mouse_hook, s.hinst, 0)]     # WH_MOUSE_LL
    message_loop()
    for hook in hooks:
        user32.UnhookWindowsHookEx(hook)

    if "--mesure" in sys.argv:
        secs = time.perf_counter() - t_start
        print(f"{s.frames} images en {secs:.1f} s = {s.frames / secs:.1f} images/s, "
              f"CPU {100 * (time.process_time() - cpu_start) / secs:.1f} % d'un coeur, "
              f"capture {1000 * s.grab_s / max(s.frames, 1):.1f} ms/image")
    if s.unlock_lock:
        user32.LockWorkStation()
        wait_for_unlock()
    if stats.first:
        show_scoreboard()


if __name__ == "__main__":
    main()
