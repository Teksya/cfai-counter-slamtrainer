"""Dessin (GDI) du paquet « Ceci n'est pas une clope », de la fumée et du tableau de chasse."""
import ctypes
import random

from winapi import (BITMAPINFOHEADER, SRCCOPY, gdi32, memory_dc, user32, w)

TEXTE = "Ceci n'est pas une clope."
TEXTE_FINI = "Voilà, t'as tout fumé."
BURN_MAX = 5  # nombre de clics pour fumer la clope en entier

PAQUET = 74 | (65 << 8) | (42 << 16)  # kaki des paquets neutres
CENTRE, DROITE = 0x1 | 0x4 | 0x20 | 0x800, 0x2 | 0x4 | 0x20 | 0x800  # flags DrawText
GAUCHE = 0x4 | 0x20 | 0x800


def rgb(r, g, b):
    return r | (g << 8) | (b << 16)


def forme(hdc, fn, coords, fill=None, line=None, width=1):
    """Dessine une forme GDI (Rectangle, Ellipse...) avec remplissage et/ou contour."""
    brush = gdi32.CreateSolidBrush(fill) if fill is not None else gdi32.GetStockObject(5)  # NULL_BRUSH
    pen = gdi32.CreatePen(0, width, line) if line is not None else gdi32.GetStockObject(8)  # NULL_PEN
    old_b, old_p = gdi32.SelectObject(hdc, brush), gdi32.SelectObject(hdc, pen)
    fn(hdc, *[int(c) for c in coords])
    gdi32.SelectObject(hdc, old_b)
    gdi32.SelectObject(hdc, old_p)
    if fill is not None:
        gdi32.DeleteObject(brush)
    if line is not None:
        gdi32.DeleteObject(pen)


def courbe(hdc, points, color, width):
    arr = (w.POINT * len(points))(*[w.POINT(int(x), int(y)) for x, y in points])
    pen = gdi32.CreatePen(0, int(width), color)
    old = gdi32.SelectObject(hdc, pen)
    gdi32.PolyBezier(hdc, arr, len(points))
    gdi32.SelectObject(hdc, old)
    gdi32.DeleteObject(pen)


def texte(hdc, txt, rect, taille, police="Arial Black", flags=CENTRE, color=0):
    font = gdi32.CreateFontW(-int(taille), 0, 0, 0, 400, 0, 0, 0, 1, 0, 0, 4, 0, police)
    old = gdi32.SelectObject(hdc, font)
    gdi32.SetBkMode(hdc, 1)
    gdi32.SetTextColor(hdc, color)
    user32.DrawTextW(hdc, txt, -1, ctypes.byref(rect), flags)
    gdi32.SelectObject(hdc, old)
    gdi32.DeleteObject(font)


def cadre(hdc, W, H):
    """Paquet neutre : fond kaki, encadré blanc à bord noir."""
    u = W / 100.0
    forme(hdc, gdi32.Rectangle, (0, 0, W, H), fill=PAQUET, line=rgb(44, 39, 25), width=max(2, int(u * 0.5)))
    forme(hdc, gdi32.Rectangle, (3 * u, 3 * u, W - 3 * u, H - 10 * u), fill=0)
    forme(hdc, gdi32.Rectangle, (4.1 * u, 4.1 * u, W - 4.1 * u, H - 11.1 * u), fill=rgb(255, 255, 255))


def clope(hdc, x0, y0, L, T, u, burn):
    """La clope : burn = 0 (entière) ... BURN_MAX (il ne reste que le filtre)."""
    x1, y1 = x0 + L, y0 + T
    xf = x0 + L * 0.27                                   # fin du filtre
    r = T * 0.35
    lw = max(1, int(u * 0.2))
    fini = burn >= BURN_MAX
    tip = x1 - (x1 - xf - 2.2 * u) * burn / BURN_MAX     # le bout recule à chaque clic
    xa = max(tip - L * 0.055 * (1 + 0.45 * burn), xf + 2.0 * u)  # début de la cendre

    forme(hdc, gdi32.Ellipse, (x0 + 2 * u, y1 + 0.6 * u, xf + 3 * u if fini else tip + u, y1 + 2.6 * u),
          fill=rgb(226, 226, 222))  # ombre
    rnd = random.Random(11)
    for i in range(burn * 7):                            # cendres tombées au sol
        ax, ay, s = rnd.uniform(tip, x1 + u), y1 + rnd.uniform(1.0, 3.4) * u, rnd.uniform(0.3, 0.9) * u
        forme(hdc, gdi32.Ellipse, (ax, ay, ax + s * 1.8, ay + s), fill=rgb(150, 146, 140) if i % 3 else rgb(108, 104, 100))
    if not fini:
        forme(hdc, gdi32.RoundRect, (xa - r, y0, tip, y1, r * 2, r * 2), fill=rgb(126, 122, 118), line=rgb(90, 86, 82), width=lw)  # cendre
        forme(hdc, gdi32.Rectangle, (xa - 0.9 * u, y0, xa + 0.5 * u, y1), fill=rgb(214, 74, 28))   # braise
        forme(hdc, gdi32.Rectangle, (xa - 0.9 * u, y0, xa - 0.3 * u, y1), fill=rgb(244, 150, 40))
        if xa - 0.8 * u > xf:                            # papier
            forme(hdc, gdi32.Rectangle, (xf, y0, xa - 0.8 * u, y1), fill=rgb(248, 246, 240), line=rgb(170, 164, 150), width=lw)
            forme(hdc, gdi32.Rectangle, (xf, y1 - T * 0.3, xa - 0.9 * u, y1 - u * 0.2), fill=rgb(226, 222, 212))
    # filtre
    forme(hdc, gdi32.RoundRect, (x0, y0, xf + r, y1, r * 2, r * 2), fill=rgb(214, 148, 78), line=rgb(150, 98, 46), width=lw)
    forme(hdc, gdi32.Rectangle, (xf - 0.2 * u, y0, xf + r + 1, y1), fill=rgb(214, 148, 78))
    rnd = random.Random(7)
    for _ in range(90):                                  # grain du liège
        px, py, s = rnd.uniform(x0 + r * 0.6, xf - 0.4 * u), rnd.uniform(y0 + T * 0.12, y1 - T * 0.12), rnd.uniform(0.25, 0.6) * u
        forme(hdc, gdi32.Ellipse, (px, py, px + s * 1.6, py + s), fill=rgb(170, 108, 50) if rnd.random() < 0.6 else rgb(236, 186, 120))
    for bx in (xf - 0.1 * u, xf + 1.1 * u):              # bagues dorées
        forme(hdc, gdi32.Rectangle, (bx, y0, bx + 0.55 * u, y1), fill=rgb(196, 160, 60))
    for by in (y0, y1 - lw):
        forme(hdc, gdi32.Rectangle, (xf - 0.2 * u, by, xf + r + 2, by + lw), fill=rgb(150, 98, 46))
    if fini:                                             # bout écrasé
        forme(hdc, gdi32.Rectangle, (xf + 1.7 * u, y0, xf + r + 2.4 * u, y1), fill=rgb(70, 62, 56), line=rgb(40, 36, 32), width=lw)
    else:                                                # fumée qui part du bout
        sx, sy = tip - 0.5 * u, y0 + T * 0.3
        for dx, col, wd in ((0, rgb(196, 196, 196), 1.1 * u), (1.6 * u, rgb(222, 222, 222), 0.7 * u)):
            courbe(hdc, [(sx + dx, sy), (sx + dx + 5 * u, sy - 4 * u), (sx + dx - 5 * u, sy - 7.5 * u),
                         (sx + dx + u, sy - 11 * u), (sx + dx + 6 * u, sy - 13.5 * u),
                         (sx + dx - 3 * u, sy - 16 * u), (sx + dx + 2 * u, sy - 18.5 * u)], col, wd)


def dessin_paquet(hdc, W, H, message, burn):
    u = W / 100.0
    cadre(hdc, W, H)
    L, T = 62 * u, 5.4 * u
    clope(hdc, (W - L) / 2, H * 0.41 - T / 2, L, T, u, burn)
    message = message.upper().rstrip(".")                # façon « FUMER TUE »
    taille = max(5.4 * min(1.0, 24 / len(message)), 3.2) * u  # rétrécit les phrases longues
    texte(hdc, message, w.RECT(int(5 * u), int(H * 0.56), int(W - 5 * u), int(H - 12 * u)), taille)


def dessin_score(hdc, W, H, lignes):
    """Tableau de chasse : lignes = liste de (libellé, valeur)."""
    u = W / 100.0
    cadre(hdc, W, H)
    texte(hdc, "TABLEAU DE CHASSE", w.RECT(0, int(5.5 * u), int(W), int(15 * u)), 5.4 * u)
    forme(hdc, gdi32.Rectangle, (12 * u, 16 * u, W - 12 * u, 16 * u + max(2, int(u * 0.4))), fill=0)
    y = 18.5 * u
    pas = (H - 18 * u - y) / len(lignes)
    for libelle, valeur in lignes:
        zone = w.RECT(int(12 * u), int(y), int(W - 12 * u), int(y + pas))
        texte(hdc, libelle, zone, min(4.2 * u, pas * 0.6), "Segoe UI", GAUCHE)
        texte(hdc, str(valeur), zone, min(4.6 * u, pas * 0.66), "Segoe UI Semibold", DROITE)
        y += pas
    texte(hdc, "Clique ou appuie sur une touche pour fermer",
          w.RECT(0, int(H - 17 * u), int(W), int(H - 12 * u)), 2.4 * u, "Segoe UI", CENTRE, rgb(120, 120, 120))


def carte(width, height, peintre):
    """Rend peintre(hdc, W, H) en double taille puis réduit (bords lissés). Renvoie un DC mémoire."""
    grand = memory_dc(width * 2, height * 2)
    peintre(grand, width * 2, height * 2)
    out = memory_dc(width, height)
    gdi32.SetStretchBltMode(out, 4)  # HALFTONE
    gdi32.SetBrushOrgEx(out, 0, 0, None)
    gdi32.StretchBlt(out, 0, 0, width, height, grand, 0, 0, width * 2, height * 2, SRCCOPY)
    gdi32.DeleteDC(grand)
    return out


def paquet(width, height, message=TEXTE, burn=0):
    return carte(width, height, lambda dc, W, H: dessin_paquet(dc, W, H, message, burn))


def score(width, height, lignes):
    return carte(width, height, lambda dc, W, H: dessin_score(dc, W, H, lignes))


def bouffee(size=64):
    """Bouffée de fumée : disque gris flou, bitmap 32 bits à alpha prémultiplié (pour AlphaBlend)."""
    bih = BITMAPINFOHEADER(ctypes.sizeof(BITMAPINFOHEADER), size, -size, 1, 32, 0, 0, 0, 0, 0, 0)
    bits = ctypes.c_void_p()
    screen = user32.GetDC(None)
    dc = gdi32.CreateCompatibleDC(screen)
    gdi32.SelectObject(dc, gdi32.CreateDIBSection(screen, ctypes.byref(bih), 0, ctypes.byref(bits), None, 0))
    user32.ReleaseDC(None, screen)
    px = (ctypes.c_ubyte * (size * size * 4)).from_address(bits.value)
    c = (size - 1) / 2
    for y in range(size):
        for x in range(size):
            alpha = int(255 * max(0.0, 1 - ((x - c) ** 2 + (y - c) ** 2) ** 0.5 / c) ** 1.6)
            gris = 236 * alpha // 255
            i = (y * size + x) * 4
            px[i], px[i + 1], px[i + 2], px[i + 3] = gris, gris, min(255, gris + 2), alpha
    return dc
