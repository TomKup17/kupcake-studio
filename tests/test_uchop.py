# kupcake.studio – Copyright (C) 2026 Tomáš Kupec
# SPDX-License-Identifier: GPL-3.0-only
"""Uchopení titulku myší ve videu: vodorovná pozice ve stylu a v ASS, výpočet rámečku titulku, vrstva
s rámečkem a převod pohybu myši na změnu stylu. Běží bez obrazovky a bez mpv (rozměry obrazu jsou zadané)."""
import _zaklad  # noqa: F401

import json
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPointF, Qt  # noqa: E402
from PySide6.QtGui import QFontDatabase  # noqa: E402
from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402

app = QApplication.instance() or QApplication([])

import presety  # noqa: E402
import theme  # noqa: E402
import uchop  # noqa: E402
from cesty import FONTY_DIR  # noqa: E402
from titulky import Styl, Titulek, vytvor_ass  # noqa: E402

for soubor in sorted(FONTY_DIR.glob("*.[ot]tf")):
    QFontDatabase.addApplicationFont(str(soubor))

W, H = 1080, 1920


class TestVodorovnaPozice(unittest.TestCase):
    def test_vychozi_styl_je_uprostred_a_jinak_stejny(self):
        s = Styl()
        self.assertEqual(s.pozice_x, 0.5)
        self.assertEqual((s.font, s.velikost, s.pozice_y, s.barva_textu), ("Montserrat ExtraBold", 0.10, 0.475,
                                                                           "F2EC3C"))

    def test_ass_vychozi_pozice_se_nezmenila(self):
        for sirka in (1080, 480, 481, 483, 1921):  # i liché šířky: střed = W // 2 jako před přidáním pozice_x
            ass = vytvor_ass([Titulek(0, 1, "ahoj")], Styl(), sirka, 1000)
            self.assertIn(f"\\pos({sirka // 2},475)", ass)

    def test_ass_vodorovna_pozice_vsech_vrstev(self):
        styl = Styl(pozice_x=0.25, pozice_y=0.8, pozadi=True, stin=True, stin_x=10, stin_y=-5, zvyrazneni=False)
        ass = vytvor_ass([Titulek(0, 1, "ahoj")], styl, W, H)
        udalosti = [r for r in ass.splitlines() if r.startswith("Dialogue:")]
        self.assertEqual(len(udalosti), 3)  # pozadí, stín, text
        self.assertEqual(sum("\\pos(270,1536)" in r for r in udalosti), 2)
        self.assertEqual(sum("\\pos(280,1531)" in r for r in udalosti), 1)  # stín posunutý vůči textu

    def test_stare_soubory_bez_pozice_x(self):
        tmp = Path(tempfile.mkdtemp(prefix="kupcake_styl_"))
        (tmp / "styl.json").write_text(json.dumps({"velikost": 0.12, "pozice_y": 0.7}), encoding="utf-8")
        s = Styl.nacti(tmp / "styl.json")
        self.assertEqual((s.velikost, s.pozice_y, s.pozice_x), (0.12, 0.7, 0.5))
        self.assertEqual(Styl.z_dict({"pozice_x": "vlevo"}).pozice_x, 0.5)   # špatný typ se ignoruje
        self.assertEqual(Styl.z_dict({"pozice_x": 1}).pozice_x, 1.0)        # celé číslo se převede

    def test_presety(self):
        self.assertIn("pozice_x", presety.SKUPINY["pozice"])
        p = presety.Presety(Path(tempfile.mkdtemp(prefix="kupcake_preset_")) / "presety.json")
        styl = Styl(pozice_x=0.2)
        self.assertEqual(p.zmenene_skupiny(styl), {"pozice"})
        self.assertEqual(p.vrat_skupinu(styl, "pozice").pozice_x, 0.5)
        p.uloz("Vlevo", styl)
        self.assertEqual(presety.Presety(p.soubor).styl("Vlevo").pozice_x, 0.2)
        # preset uložený starší verzí (bez pozice_x) zůstane uprostřed
        p.presety["Stary"] = {"velikost": 0.08}
        self.assertEqual(p.styl("Stary").pozice_x, 0.5)


def styl_montserrat(test):
    """Výchozí styl s písmem Montserrat ExtraBold. Bez obrazovky Qt nezná název „Montserrat ExtraBold“
    (Windows ho nabízí jako samostatnou rodinu, FreeType jen jako řez rodiny Montserrat), proto se písmo
    vybere přes rodinu; kdyby Qt sáhlo po jiném řezu, porovnání se změřenými hodnotami se přeskočí."""
    from PySide6.QtGui import QFont, QRawFont
    f = QFont("Montserrat")
    f.setPixelSize(100)
    surove = QRawFont.fromFont(f)
    if (surove.familyName(), surove.styleName()) != ("Montserrat", "ExtraBold"):
        test.skipTest("písmo Montserrat ExtraBold není v tomto prostředí k dispozici")
    return Styl(font="Montserrat")


class TestRamecek(unittest.TestCase):
    def test_bez_textu_neni_ramecek(self):
        for text in (None, "", "   ", "\n"):
            self.assertIsNone(uchop.ramecek_titulku(text, Styl(), W, H))
        self.assertIsNone(uchop.ramecek_titulku("ahoj", Styl(), 0, 0))

    def test_stred_podle_pozice(self):
        for x, y in ((0.5, 0.475), (0.2, 0.1), (0.9, 0.95)):
            r = uchop.ramecek_titulku("AHOJ SVETE", Styl(pozice_x=x, pozice_y=y), W, H)
            self.assertAlmostEqual(r.center().x(), W * x, delta=W * 0.01)
            self.assertAlmostEqual(r.center().y(), H * y, delta=H * 0.015)

    def test_velikost_meni_ramecek_umerne(self):
        maly = uchop.ramecek_titulku("AHOJ", Styl(velikost=0.05), W, H)
        velky = uchop.ramecek_titulku("AHOJ", Styl(velikost=0.10), W, H)
        self.assertAlmostEqual(velky.width() / maly.width(), 2.0, delta=0.03)
        self.assertAlmostEqual(velky.height() / maly.height(), 2.0, delta=0.05)
        self.assertAlmostEqual(velky.center().x(), maly.center().x(), delta=1.5)

    def test_velka_pismena_a_obrys(self):
        mala = uchop.ramecek_titulku("ahoj", Styl(velka_pismena=False), W, H)
        velka = uchop.ramecek_titulku("ahoj", Styl(velka_pismena=True), W, H)
        self.assertGreater(velka.width(), mala.width())
        s_obrysem = uchop.ramecek_titulku("ahoj", Styl(velka_pismena=True, obrys=0.1), W, H)
        self.assertAlmostEqual(s_obrysem.width() - velka.width(), 2 * 0.1 * 108, delta=0.5)

    def test_shoda_s_libass_montserrat(self):
        """Hodnoty změřené na snímku z mpv (libass) pro video 480×854: „AHOJ SVĚTE“ výchozím stylem leží
        v x 137–342, y 388–417. Písmo Montserrat má v libass jiné měřítko než v Qt – výpočet ho musí trefit."""
        r = uchop.ramecek_titulku("AHOJ SVĚTE", styl_montserrat(self), 480, 854)
        for spocitano, zmereno in ((r.left(), 137), (r.right(), 342), (r.top(), 388), (r.bottom(), 417)):
            self.assertAlmostEqual(spocitano, zmereno, delta=2.5)

    def test_dlouhy_text_se_zalomi_a_vejde(self):
        text = "tohle je hodně dlouhý titulek který se zalomí"
        styl = styl_montserrat(self)
        r = uchop.ramecek_titulku(text, styl, 480, 854)
        self.assertLessEqual(r.width(), 480 * 0.9 + 2)
        jeden = uchop.ramecek_titulku("tohle", styl, 480, 854)
        self.assertGreater(r.height(), 2.5 * jeden.height())      # tři řádky (změřeno v mpv: 125 px)
        self.assertAlmostEqual(r.height(), 125, delta=4)
        self.assertAlmostEqual(r.width(), 295, delta=6)
        dva = uchop.ramecek_titulku("jedna\ndva", styl, 480, 854)
        self.assertGreater(dva.height(), 1.8 * jeden.height())    # ruční zalomení řádku

    def test_zalomeni_vyrovna_radky(self):
        # deset stejných slov, vejde se šest na řádek: napřed 6 + 4, po vyrovnání 5 + 5
        radky = uchop._zalom([10.0] * 10, 2.0, 70.0)
        self.assertEqual([len(r) for r in radky], [5, 5])
        self.assertEqual(uchop._zalom([10.0, 10.0], 2.0, 100.0), [[0, 1]])
        self.assertEqual(uchop._zalom([200.0, 10.0], 2.0, 100.0), [[0], [1]])  # příliš dlouhé slovo zůstane samo

    def test_nezname_pismo_nespadne(self):
        r = uchop.ramecek_titulku("ahoj", Styl(font="Tohle Písmo Neexistuje"), W, H)
        self.assertGreater(r.width(), 0)


class Kreslic:
    def __init__(self):
        self.volani = []

    def __call__(self, ass, sirka, vyska):
        self.volani.append((ass, sirka, vyska))

    @property
    def posledni(self):
        return self.volani[-1][0] if self.volani else None


class TestUchop(unittest.TestCase):
    """Plocha 400×800 px, vrstva mpv 800×1600 (obrazovka se 200% měřítkem), video 1080×1920 uprostřed
    s okraji 100 px vlevo a vpravo → obraz ve vrstvě 600 px široký (1 px plochy = 3,6 px videa vodorovně)."""

    def setUp(self):
        self.plocha = QWidget()
        self.plocha.resize(400, 800)
        self.rozmery = {"w": 800, "h": 1600, "ml": 100, "mr": 100, "mt": 266, "mb": 267}
        self.kreslic = Kreslic()
        self.u = uchop.UchopTitulku(self.plocha, lambda: self.rozmery, self.kreslic)
        self.styl = Styl()
        self.udalosti = []
        self.u.posun.connect(self._posun)
        self.u.velikost.connect(self._velikost)
        self.u.konec.connect(lambda: self.udalosti.append("konec"))
        self.u.klik_mimo.connect(lambda: self.udalosti.append("klik_mimo"))
        self.u.nastav_titulek("AHOJ SVĚTE", self.styl, W, H)

    # okno by po signálu změnilo styl a řeklo to zpět – totéž dělá test
    def _posun(self, x, y):
        self.udalosti.append(("posun", x, y))
        self.styl.pozice_x, self.styl.pozice_y = x, y
        self.u.nastav_titulek("AHOJ SVĚTE", self.styl, W, H)

    def _velikost(self, v):
        self.udalosti.append(("velikost", v))
        self.styl.velikost = v
        self.u.nastav_titulek("AHOJ SVĚTE", self.styl, W, H)

    def _stred(self):
        """Střed titulku v souřadnicích plochy."""
        zobr = self.u._zobrazeni()
        r = self.u._ramecek_ve_vrstve(zobr)
        return QPointF(r.center().x() / zobr[0], r.center().y() / zobr[1])

    def _roh(self, i):
        zobr = self.u._zobrazeni()
        r = self.u._ramecek_ve_vrstve(zobr)
        roh = (r.topLeft(), r.topRight(), r.bottomRight(), r.bottomLeft())[i]
        return QPointF(roh.x() / zobr[0], roh.y() / zobr[1])

    def test_bez_videa_se_nic_nedeje(self):
        self.rozmery = None
        self.u.stisk(QPointF(200, 400))
        self.u.pohyb(QPointF(250, 450), True)
        self.u.uvolneni(QPointF(250, 450))
        self.assertEqual(self.udalosti, [])
        self.rozmery = None
        self.u.stisk(QPointF(200, 400))
        self.u.uvolneni(QPointF(200, 400))
        self.assertEqual(self.udalosti, ["klik_mimo"])  # bez videa se kliknutí chová jako dřív

    def test_najeti_ukaze_ramecek_a_kurzor(self):
        self.assertIsNone(self.kreslic.posledni)
        self.u.pohyb(self._stred(), False)
        self.assertEqual(self.plocha.cursor().shape(), Qt.SizeAllCursor)
        self.assertIn("\\p1", self.kreslic.posledni)
        self.assertEqual(self.kreslic.volani[-1][1:], (800, 1600))
        self.assertFalse(self.u.vybrano)
        self.u.pohyb(QPointF(20, 700), False)
        self.assertEqual(self.plocha.cursor().shape(), Qt.ArrowCursor)
        self.assertIsNone(self.kreslic.posledni)  # mimo titulek rámeček zmizí
        self.u.pohyb(self._stred(), False)
        self.u.opusteno()
        self.assertIsNone(self.kreslic.posledni)

    def test_klik_na_titulek_ho_vybere(self):
        stred = self._stred()
        self.u.stisk(stred)
        self.u.uvolneni(stred)
        self.assertTrue(self.u.vybrano)
        self.assertEqual(self.udalosti, [])  # žádný posun, žádné ukládání, žádné přepnutí přehrávání
        najeti_bez_vyberu = uchop.ass_prekryti(self.u._ramecek_ve_vrstve(self.u._zobrazeni()), False, 2.0)
        self.assertGreater(len(self.kreslic.posledni), len(najeti_bez_vyberu))  # navíc úchyty v rozích

    def test_tah_presune_titulek(self):
        stred = self._stred()
        self.u.stisk(stred)
        self.u.pohyb(stred + QPointF(50, 100), True)   # 50 px plochy = 100 px vrstvy z 600 = 1/6 šířky videa
        self.u.uvolneni(stred + QPointF(50, 100))
        self.assertEqual(self.udalosti[-1], "konec")
        _, x, y = self.udalosti[0]
        self.assertAlmostEqual(x, 0.5 + 100 / 600, places=3)
        self.assertAlmostEqual(y, 0.475 + 200 / 1067, places=3)
        self.assertTrue(self.u.vybrano)

    def test_tah_drzi_titulek_za_misto_stisku(self):
        """Stisk mimo střed titulku nesmí titulkem cuknout – první malý pohyb ho posune jen o ten pohyb."""
        bod = self._stred() + QPointF(30, 3)
        self.u.stisk(bod)
        self.u.pohyb(bod + QPointF(0, 6), True)
        _, x, y = self.udalosti[0]
        self.assertAlmostEqual(x, 0.5, places=3)
        self.assertAlmostEqual(y, 0.475 + 12 / 1067, places=3)

    def test_pozice_zustane_ve_videu(self):
        stred = self._stred()
        self.u.stisk(stred)
        self.u.pohyb(stred + QPointF(-5000, -5000), True)
        self.assertEqual(self.udalosti[-1], ("posun", 0.0, 0.0))
        self.u.pohyb(stred + QPointF(5000, 5000), True)
        self.assertEqual(self.udalosti[-1], ("posun", 1.0, 1.0))

    def test_prichyceni_ke_stredu(self):
        self.styl.pozice_x = 0.3
        self.u.nastav_titulek("AHOJ SVĚTE", self.styl, W, H)
        stred = self._stred()
        k_stredu = (0.5 - 0.3) * 600 / 2   # px plochy
        self.u.stisk(stred)
        self.u.pohyb(stred + QPointF(k_stredu + 4, 0), True)     # 4 px vedle středu → přichytí
        self.assertEqual(self.udalosti[-1][1], 0.5)
        self.assertEqual(self.kreslic.posledni.count("\\p1"), 3)  # vodítko, rámeček, úchyty
        self.u.pohyb(stred + QPointF(k_stredu + 12, 0), True)    # 12 px vedle → volně
        self.assertAlmostEqual(self.udalosti[-1][1], 0.5 + 24 / 600, places=3)
        self.assertEqual(self.kreslic.posledni.count("\\p1"), 2)

    def test_tah_za_roh_meni_velikost(self):
        stred = self._stred()
        self.u.stisk(stred)
        self.u.uvolneni(stred)       # vybrat – úchyty jsou jen u vybraného titulku
        self.udalosti.clear()
        roh = self._roh(2)
        self.u.pohyb(roh, False)
        self.assertEqual(self.plocha.cursor().shape(), Qt.SizeFDiagCursor)
        self.u.pohyb(self._roh(1), False)
        self.assertEqual(self.plocha.cursor().shape(), Qt.SizeBDiagCursor)
        roh = self._roh(2)
        self.u.stisk(roh)
        self.u.pohyb(stred + (roh - stred) * 1.5, True)
        self.assertEqual(self.udalosti[-1][0], "velikost")
        self.assertAlmostEqual(self.udalosti[-1][1], 0.15, places=2)
        self.u.pohyb(stred + (roh - stred) * 0.5, True)   # vztaženo k místu stisku, ne k minulému pohybu
        self.assertAlmostEqual(self.udalosti[-1][1], 0.05, places=2)
        self.u.pohyb(stred + (roh - stred) * 50, True)
        self.assertEqual(self.udalosti[-1], ("velikost", uchop.VELIKOST_DO))
        self.u.pohyb(stred, True)
        self.assertEqual(self.udalosti[-1], ("velikost", uchop.VELIKOST_OD))
        self.u.uvolneni(stred)
        self.assertEqual(self.udalosti[-1], "konec")
        self.assertEqual((self.styl.pozice_x, self.styl.pozice_y), (0.5, 0.475))  # střed se nehnul

    def test_rohy_se_chytaji_jen_u_vybraneho(self):
        roh = self._roh(2) + QPointF(4, 4)   # těsně vně rámečku
        self.u.pohyb(roh, False)
        self.assertEqual(self.plocha.cursor().shape(), Qt.ArrowCursor)
        self.u.vybrano = True
        self.u.pohyb(roh, False)
        self.assertEqual(self.plocha.cursor().shape(), Qt.SizeFDiagCursor)

    def test_klik_mimo(self):
        mimo = QPointF(20, 700)
        self.u.stisk(mimo)
        self.u.uvolneni(mimo)
        self.assertEqual(self.udalosti, ["klik_mimo"])           # nic vybraného → přehrát / pauza
        stred = self._stred()
        self.u.stisk(stred)
        self.u.uvolneni(stred)
        self.udalosti.clear()
        self.u.stisk(mimo)
        self.u.uvolneni(mimo)
        self.assertEqual(self.udalosti, [])                      # vybraný titulek → jen zrušit výběr
        self.assertFalse(self.u.vybrano)
        self.u.stisk(mimo)
        self.u.uvolneni(mimo + QPointF(40, 0))                   # tah mimo titulek není kliknutí
        self.assertEqual(self.udalosti, [])

    def test_bez_titulku_neni_co_chytit(self):
        stred = self._stred()
        self.u.nastav_titulek(None, self.styl, W, H)
        self.u.stisk(stred)
        self.u.uvolneni(stred)
        self.assertEqual(self.udalosti, ["klik_mimo"])
        self.assertFalse(self.u.vybrano)

    def test_ramecek_sleduje_zmenu_stylu_a_noveho_videa(self):
        self.u.vybrano = True
        self.u.prekresli()
        pred = self.kreslic.posledni
        self.styl.pozice_y = 0.8
        self.u.nastav_titulek("AHOJ SVĚTE", self.styl, W, H)
        self.assertNotEqual(self.kreslic.posledni, pred)
        pocet = len(self.kreslic.volani)
        self.u.nastav_titulek("AHOJ SVĚTE", self.styl, W, H)     # beze změny se nic nekreslí znovu
        self.assertEqual(len(self.kreslic.volani), pocet)
        self.u.zapomen()
        self.assertIsNone(self.kreslic.posledni)
        self.assertFalse(self.u.vybrano)
        self.assertIsNone(self.u.ramecek)


class TestVrstva(unittest.TestCase):
    def test_barvy_z_theme_ve_tvaru_ass(self):
        from PySide6.QtCore import QRectF
        ass = uchop.ass_prekryti(QRectF(10, 20, 100, 40), True, 1.0, voditko=(60.0, 0.0, 200.0))
        self.assertEqual(len(ass.splitlines()), 3)
        self.assertEqual(theme.UCHOP_RAMECEK, theme.AKCENT)       # výběr = modrá
        self.assertIn("\\3c&HFFB400&", ass)                        # #00B4FF zapsaná jako BGR
        self.assertIn("m 10.0 20.0 l 110.0 20.0 110.0 60.0 10.0 60.0", ass)
        bez = uchop.ass_prekryti(QRectF(10, 20, 100, 40), False)
        self.assertEqual(len(bez.splitlines()), 1)

    def test_barvy_jen_z_theme(self):
        import re
        kod = (_zaklad.KOREN / "uchop.py").read_text(encoding="utf-8")
        self.assertIsNone(re.search(r"#[0-9A-Fa-f]{6}\b", kod))
        self.assertIsNone(re.search(r"QColor\(\s*\d", kod))


if __name__ == "__main__":
    unittest.main()
