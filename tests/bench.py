"""Mesure hors écran : coût d'une recopie du bureau (BitBlt) et d'un affichage simulé, par image.

Lancer : python tests/bench.py   (aucune fenêtre, aucun hook, aucune entrée bloquée)
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import anticroissantage as ac  # noqa: E402
from winapi import *  # noqa: E402,F403

N = 100
mem, frame, fenetre = (memory_dc(ac.W, ac.H) for _ in range(3))


def mesure(nom, etape):
    t0, c0 = time.perf_counter(), time.process_time()
    for _ in range(N):
        etape()
    dt, cpu = (time.perf_counter() - t0) / N, (time.process_time() - c0) / N
    print(f"{nom:<42} {1000 * dt:6.1f} ms/image  (CPU {1000 * cpu:5.1f} ms)  -> {1 / dt:5.0f} images/s max")


def grab(flags):
    def f():
        screen = user32.GetDC(None)
        gdi32.BitBlt(mem, 0, 0, ac.W, ac.H, screen, ac.X, ac.Y, flags)
        user32.ReleaseDC(None, screen)
    return f


def copie(src, dst):
    return lambda: gdi32.BitBlt(dst, 0, 0, ac.W, ac.H, src, 0, 0, SRCCOPY)


print(f"Bureau virtuel {ac.W}x{ac.H}, {N} images par mesure")
mesure("capture BitBlt (SRCCOPY)", grab(SRCCOPY))
mesure("capture BitBlt (SRCCOPY|CAPTUREBLT)", grab(SRCCOPY | CAPTUREBLT))
mesure("copie mémoire -> fenêtre (sans recouvrement)", copie(mem, fenetre))
mesure("copie mémoire -> frame -> fenêtre (recouvrement)", lambda: (copie(mem, frame)(), copie(frame, fenetre)()))
