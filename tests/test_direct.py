"""Tests hors écran du mode en direct : aucune fenêtre, aucun hook, aucune entrée bloquée.

Lancer : python -m unittest discover tests   (depuis la racine du projet)
"""
import ctypes
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import anticroissantage as ac  # noqa: E402
from winapi import *  # noqa: E402,F403

ROSE = 0x00FF00FF  # COLORREF 0x00BBGGRR


def remplir(dc, couleur, rc=None):
    rc = rc or w.RECT(0, 0, ac.W, ac.H)
    user32.FillRect(dc, ctypes.byref(rc), gdi32.CreateSolidBrush(couleur))


class TestDirect(unittest.TestCase):
    def setUp(self):
        ac.s.mem, ac.s.live, ac.s.frame = (memory_dc(ac.W, ac.H) for _ in range(3))
        ac.s.wins, ac.s.panel, ac.s.particles, ac.s.menu = {}, None, [], False
        ac.s.live_on, ac.s.frames = True, 0
        ac.s.arrow = user32.LoadCursorW(None, 32512)

    def test_grab_recopie_le_vrai_bureau(self):
        remplir(ac.s.mem, ROSE)
        ac.grab_desktop()
        screen = user32.GetDC(None)
        points = [(ac.W * i // 6, ac.H * j // 6) for i in range(1, 6) for j in range(1, 6)]
        egaux = sum(gdi32.GetPixel(ac.s.mem, x, y) == gdi32.GetPixel(screen, x + ac.X, y + ac.Y) for x, y in points)
        user32.ReleaseDC(None, screen)
        self.assertGreaterEqual(egaux, len(points) * 0.8)  # le bureau peut bouger entre les deux lectures
        self.assertEqual(ac.s.frames, 1)

    def test_pas_de_recouvrement_donc_pas_de_copie_intermediaire(self):
        self.assertFalse(ac.has_overlay())
        ac.s.particles = [[10, 10, 0, 0]]
        self.assertTrue(ac.has_overlay())

    def test_le_paquet_se_dessine_par_dessus_le_direct(self):
        remplir(ac.s.mem, ROSE)
        ac.show_panel(ac.X + ac.W // 2, ac.Y + ac.H // 2)
        rc = ac.s.panel.rc
        ac.compose(w.RECT(0, 0, ac.W, ac.H))
        self.assertEqual(gdi32.GetPixel(ac.s.frame, 2, 2), ROSE)  # hors du paquet : le bureau
        centre = gdi32.GetPixel(ac.s.frame, (rc.left + rc.right) // 2, (rc.top + rc.bottom) // 2)
        self.assertNotEqual(centre, ROSE)  # dans le paquet : le dessin

    def test_la_fumee_se_dessine_par_dessus_le_direct(self):
        ac.s.puff = clope_bouffee()
        remplir(ac.s.mem, ROSE)
        ac.s.particles = [[ac.W // 2, ac.H // 2, 2, 0]]
        ac.compose(w.RECT(0, 0, ac.W, ac.H))
        self.assertNotEqual(gdi32.GetPixel(ac.s.frame, ac.W // 2, ac.H // 2), ROSE)

    def test_mode_fige_ne_recopie_pas(self):
        # grab_desktop n'est appelé que si s.live_on : le mode figé garde la photo
        ac.s.live_on = False
        remplir(ac.s.mem, ROSE)
        self.assertEqual(gdi32.GetPixel(ac.s.mem, 5, 5), ROSE)
        self.assertEqual(ac.s.frames, 0)

    def test_le_menu_vrai_n_est_pas_recouvert_en_direct(self):
        ac.s.menu = True
        self.assertFalse(ac.has_overlay())  # en direct, le vrai menu est déjà dans l'image
        ac.s.live_on = False
        self.assertTrue(ac.has_overlay())  # figé : on superpose le miroir


class TestEntreesAvalees(unittest.TestCase):
    """Les hooks doivent avaler clics, molette et touches : rien n'atteint les vraies fenêtres."""

    def setUp(self):
        ac.s.wins, ac.s.panel, ac.s.menu, ac.s.altgr = {}, None, False, False
        ac.s.mem, ac.s.live, ac.s.frame = (memory_dc(ac.W, ac.H) for _ in range(3))

    def touche(self, vk, down=True):
        k = KBDLLHOOKSTRUCT(vk, 0, 0, 0, 0)
        return ac.keyboard_hook(0, WM_KEYDOWN if down else 0x101, ctypes.addressof(k))

    def souris(self, msg, x=100, y=100):
        m = MSLLHOOKSTRUCT(w.POINT(x, y), 0, 0, 0, 0)
        return ac.mouse_hook(0, msg, ctypes.addressof(m))

    def test_touches_avalees(self):
        for vk in (0x41, 0x0D, 0x1B, 0x20, 0x70):
            self.assertEqual(self.touche(vk), 1, hex(vk))
            self.touche(vk, False)

    def test_clics_et_molette_avales(self):
        for msg in (WM_LBUTTONDOWN, WM_RBUTTONDOWN, WM_MBUTTONDOWN, 0x202, 0x205, 0x20A):
            self.assertEqual(self.souris(msg), 1, hex(msg))

    def test_altgr_h_deverrouille(self):
        self.touche(0xA5)
        self.assertEqual(self.touche(0x48), 1)
        self.assertTrue(ac.s.unlock_lock)  # demandera le verrouillage de la session


def clope_bouffee():
    import clope
    return clope.bouffee()


if __name__ == "__main__":
    unittest.main()
