# kupcake.studio – Copyright (C) 2026 Tomáš Kupec
# SPDX-License-Identifier: GPL-3.0-only
"""Dlaždice sekce Nastavení: skládání do sloupců, převody hodnot, panel stylu, kolečko myši a vysouvací okna.
Běží bez obrazovky (QT_QPA_PLATFORM=offscreen) a v izolovaném nastavení."""
import _zaklad  # noqa: F401

import os
import re
import unittest
from dataclasses import fields

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, QPoint, QPointF, QRect, Qt  # noqa: E402
from PySide6.QtGui import QKeyEvent, QMouseEvent, QWheelEvent  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget  # noqa: E402

app = QApplication.instance() or QApplication([])

import dlazdice  # noqa: E402
import i18n  # noqa: E402
import kolecko  # noqa: E402
import main  # noqa: E402
import presety  # noqa: E402
import theme  # noqa: E402
from _zaklad import KOREN  # noqa: E402
from titulky import Styl  # noqa: E402

theme.pouzij(app)
kolecko.zapni(app)
i18n.nastav("cs")

# hodnoty stylu, které šly nastavit ve formuláři před dlaždicemi – žádná nesmí chybět
KLICE = ("font", "velikost", "barva_textu", "tucne", "velka_pismena", "barva_obrysu", "obrys", "stin",
         "barva_stinu", "stin_rozmazani", "stin_x", "stin_y", "pozadi", "barva_pozadi", "pruhlednost_pozadi",
         "odsazeni_pozadi", "pozice_y", "max_slov", "max_znaku", "zvyrazneni", "barva_zvyrazneni", "posun_ms",
         "predstih_ms")


class Zdroj:
    """Náhrada panelu: styl a poměr stran pro ukázky na dlaždicích."""

    def __init__(self):
        self.styl = Styl()
        self.pomer = 9 / 16


def kolecko_udalost(widget, nahoru=True):
    bod = QPointF(widget.width() / 2, widget.height() / 2)
    return QWheelEvent(bod, QPointF(widget.mapToGlobal(bod.toPoint())), QPoint(0, 0),
                       QPoint(0, 120 if nahoru else -120), Qt.NoButton, Qt.NoModifier, Qt.NoScrollPhase, False)


class TestMrizka(unittest.TestCase):
    def setUp(self):
        self.w = QWidget()
        self.mrizka = dlazdice.MrizkaDlazdic(self.w)
        self.mrizka.setContentsMargins(10, 8, 8, 10)
        self.dlazdice = []
        for i in range(6):
            d = QWidget()
            d.sloupcu = 2 if i == 0 else 1
            self.mrizka.addWidget(d)
            self.dlazdice.append(d)

    def _sirka(self, sloupcu):
        return 18 + sloupcu * theme.DLAZDICE_SIRKA + (sloupcu - 1) * theme.DLAZDICE_MEZERA

    def test_pocet_sloupcu_podle_sirky(self):
        for n in (1, 2, 3, 4, 6):
            self.assertEqual(self.mrizka.sloupcu(self._sirka(n)), n)
            self.assertEqual(self.mrizka.sloupcu(self._sirka(n) + theme.DLAZDICE_SIRKA - 1), n)
        self.assertEqual(self.mrizka.sloupcu(40), 1)  # ani v příliš úzkém panelu nespadne na nulu

    def test_vyska_podle_sirky(self):
        v, m = theme.DLAZDICE_VYSKA, theme.DLAZDICE_MEZERA
        # 7 buněk (první dlaždice zabírá dvě): 3 sloupce = 3 řádky, 4 sloupce = 2 řádky, 7 sloupců = 1 řádek
        self.assertEqual(self.mrizka.heightForWidth(self._sirka(3)), 18 + 3 * v + 2 * m)
        self.assertEqual(self.mrizka.heightForWidth(self._sirka(4)), 18 + 2 * v + m)
        self.assertEqual(self.mrizka.heightForWidth(self._sirka(7)), 18 + v)
        # v jediném sloupci zabere i široká dlaždice jen jednu buňku
        self.assertEqual(self.mrizka.heightForWidth(self._sirka(1)), 18 + 6 * v + 5 * m)

    def test_skryta_dlazdice_nezabira_misto(self):
        pred = self.mrizka.heightForWidth(self._sirka(3))
        for d in self.dlazdice[3:]:
            d.hide()
        self.assertLess(self.mrizka.heightForWidth(self._sirka(3)), pred)
        for d in self.dlazdice:
            d.hide()
        self.assertEqual(self.mrizka.heightForWidth(self._sirka(3)), 18)

    def test_rozmisteni_bez_prekryvu_a_v_ramci_sirky(self):
        for sirka in (self._sirka(2), 333, self._sirka(4) + 7, 900):
            self.mrizka.setGeometry(QRect(0, 0, sirka, self.mrizka.heightForWidth(sirka)))
            obdelniky = [d.geometry() for d in self.dlazdice]
            for i, a in enumerate(obdelniky):
                self.assertGreaterEqual(a.left(), 10)
                self.assertLessEqual(a.right(), sirka - 8)
                self.assertGreaterEqual(a.width(), theme.DLAZDICE_SIRKA)
                self.assertEqual(a.height(), theme.DLAZDICE_VYSKA)
                for b in obdelniky[i + 1:]:
                    self.assertFalse(a.intersects(b), f"šířka {sirka}")
            self.assertGreater(obdelniky[0].width(), obdelniky[1].width())  # dlaždice přes dva sloupce


class TestCislo(unittest.TestCase):
    def setUp(self):
        i18n.nastav("cs")
        self.zdroj = Zdroj()
        self.d = dlazdice.DlazdiceCislo(self.zdroj, "styl.velikost", 2, 30, 0.5, desetinna=1, meritko=100,
                                        jednotka="%")
        self.d.resize(120, theme.DLAZDICE_VYSKA)
        self.zmeny = []
        self.d.zmena.connect(self.zmeny.append)

    def test_zobrazeni_bez_vyslani(self):
        self.d.nastav_hodnotu(0.10)
        self.assertEqual(self.zmeny, [])
        self.assertAlmostEqual(self.d.value(), 10.0)
        self.assertEqual(self.d.text_cisla(), "10")

    def test_zmena_vysila_hodnotu_stylu(self):
        self.d.nastav_hodnotu(0.10)
        self.d.setValue(self.d.value() + 2.5)
        self.assertEqual(self.zmeny, [0.125])
        self.assertEqual(self.d.text_cisla(), "12,5")
        self.d.setValue(12.5)  # stejná hodnota = žádná další změna
        self.assertEqual(len(self.zmeny), 1)

    def test_meze_a_tlacitka(self):
        self.d.setValue(999)
        self.assertAlmostEqual(self.d.value(), 30.0)
        self.assertFalse(self.d.plus.isEnabled())
        self.assertTrue(self.d.minus.isEnabled())
        self.d.setValue(-5)
        self.assertAlmostEqual(self.d.value(), 2.0)
        self.assertFalse(self.d.minus.isEnabled())
        self.d.plus.click()
        self.assertAlmostEqual(self.d.value(), 2.5)
        self.d.minus.click()
        self.assertAlmostEqual(self.d.value(), 2.0)

    def test_cela_cisla_znamenko_a_auto(self):
        posun = dlazdice.DlazdiceCislo(self.zdroj, "styl.posun", -2000, 2000, 10, jednotka="ms", znamenko=True)
        zmeny = []
        posun.zmena.connect(zmeny.append)
        posun.nastav_hodnotu(0)
        posun.krokuj(1)
        self.assertEqual(zmeny, [10])
        self.assertIs(type(zmeny[0]), int)
        self.assertEqual(posun.text_cisla(), "+10")
        posun.krokuj(-3)
        self.assertEqual(posun.text_cisla(), "-20")
        slov = dlazdice.DlazdiceCislo(self.zdroj, "styl.max_slov", 0, 12, specialni=lambda: i18n.t("styl.auto"))
        slov.nastav_hodnotu(0)
        self.assertEqual((slov.text_cisla(), slov.text_jednotky()), ("Auto", ""))
        slov.krokuj(1)
        self.assertEqual(slov.text_cisla(), "1")

    def test_zapsani_hodnoty(self):
        self.d.nastav_hodnotu(0.10)
        self.d.uprav()
        self.assertIsNotNone(self.d.editor)
        self.assertEqual(self.d.editor.text(), "10")
        self.d.editor.setText("15,5 %")
        self.d.editor.editingFinished.emit()
        self.assertIsNone(self.d.editor)
        self.assertEqual(self.zmeny, [0.155])
        self.d.uprav()
        self.d.editor.setText("nesmysl")
        self.d.editor.editingFinished.emit()
        self.assertAlmostEqual(self.d.value(), 15.5)

    def test_esc_zapis_zrusi(self):
        self.d.nastav_hodnotu(0.10)
        self.d.uprav()
        editor = self.d.editor
        editor.setText("25")
        QApplication.sendEvent(editor, QKeyEvent(QEvent.ShortcutOverride, Qt.Key_Escape, Qt.NoModifier))
        editor.editingFinished.emit()
        self.assertEqual(self.zmeny, [])
        self.assertAlmostEqual(self.d.value(), 10.0)

    def test_sipky(self):
        self.d.nastav_hodnotu(0.10)
        QApplication.sendEvent(self.d, QKeyEvent(QEvent.KeyPress, Qt.Key_Up, Qt.NoModifier))
        QApplication.sendEvent(self.d, QKeyEvent(QEvent.KeyPress, Qt.Key_Up, Qt.NoModifier))
        QApplication.sendEvent(self.d, QKeyEvent(QEvent.KeyPress, Qt.Key_Down, Qt.NoModifier))
        self.assertAlmostEqual(self.d.value(), 10.5)

    def test_pozice_tahem(self):
        pozice = dlazdice.DlazdicePozice(self.zdroj, "styl.pozice")
        pozice.resize(110, theme.DLAZDICE_VYSKA)
        zmeny = []
        pozice.zmena.connect(zmeny.append)
        pozice.nastav_hodnotu(0.475)
        self.assertAlmostEqual(pozice.value(), 48.0)  # jako dřívější posuvník: celá procenta
        o = pozice._plocha_obrazovky()
        for podil in (0.25, 0.9):
            bod = QPointF(o.center().x(), o.top() + o.height() * podil)
            globalni = QPointF(pozice.mapToGlobal(bod.toPoint()))
            typ = QEvent.MouseButtonPress if podil == 0.25 else QEvent.MouseMove
            QApplication.sendEvent(pozice, QMouseEvent(typ, bod, globalni, Qt.LeftButton, Qt.LeftButton,
                                                       Qt.NoModifier))
        self.assertEqual(zmeny, [0.25, 0.9])


class TestPanel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        i18n.nastav("cs")
        cls.panel = main.PanelStylu()
        cls.zmeny = []
        cls.panel.zmena.connect(lambda klic, hodnota: cls.zmeny.append((klic, hodnota)))

    def setUp(self):
        self.panel.nastav(Styl())
        self.zmeny.clear()

    def test_vsechny_hodnoty_maji_dlazdici(self):
        self.assertEqual(set(self.panel.prvky), set(KLICE))
        v_presetech = {k for klice in presety.SKUPINY.values() for k in klice}
        self.assertEqual(v_presetech | set(presety.NEPRENASET), set(KLICE))
        self.assertEqual(list(self.panel.skupiny), ["text", "obrys", "pozadi", "pozice", "efekty", "casovani"])
        self.assertTrue({f.name for f in fields(Styl)} >= set(KLICE))

    def test_nastav_nic_nevysila_a_ukaze_hodnoty(self):
        styl = Styl(font="Arial", velikost=0.07, barva_textu="ff00aa", tucne=True, velka_pismena=False,
                    obrys=0.055, stin=False, pozadi=True, pruhlednost_pozadi=65, pozice_y=0.8, max_slov=3,
                    zvyrazneni=True, posun_ms=-120, predstih_ms=35)
        self.panel.nastav(styl)
        self.assertEqual(self.zmeny, [])
        p = self.panel.prvky
        self.assertEqual(p["font"].rodina, "Arial")
        self.assertAlmostEqual(p["velikost"].value(), 7.0)
        self.assertEqual(p["barva_textu"].hex, "FF00AA")
        self.assertTrue(p["tucne"].isChecked())
        self.assertFalse(p["velka_pismena"].isChecked())
        self.assertAlmostEqual(p["obrys"].value(), 5.5)
        self.assertAlmostEqual(p["pruhlednost_pozadi"].value(), 65)
        self.assertAlmostEqual(p["pozice_y"].value(), 80)
        self.assertEqual(p["max_slov"].text_cisla(), "3")
        self.assertEqual(p["posun_ms"].text_cisla(), "-120")
        self.assertIsNot(self.panel.styl, styl)  # kopie – změna na dlaždici nesmí přepsat styl okna potichu

    def test_zmena_vysila_klic_a_hodnotu_spravneho_typu(self):
        p = self.panel.prvky
        vychozi = Styl()
        for klic in KLICE:
            d = p[klic]
            d.show()  # i dlaždice schované za vypnutým přepínačem
            self.zmeny.clear()
            if isinstance(d, dlazdice.DlazdiceCislo):
                d.krokuj(1 if d.plus.isEnabled() else -1)
            elif isinstance(d, dlazdice.DlazdicePrepinac):
                d.setChecked(not d.isChecked())
            elif isinstance(d, dlazdice.DlazdiceBarva):
                d._zvol("12ab34")
            else:
                d._zvol("Arial")
            self.assertEqual(len(self.zmeny), 1, klic)
            vyslany, hodnota = self.zmeny[0]
            self.assertEqual(vyslany, klic)
            # stejný typ jako ve Stylu – jinak by Styl.z_dict hodnotu při načtení styl.json zahodil
            self.assertIs(type(hodnota), type(getattr(vychozi, klic)), klic)
            self.assertNotEqual(hodnota, getattr(vychozi, klic), klic)
            self.assertEqual(getattr(self.panel.styl, klic), hodnota)
        self.assertEqual(Styl.z_dict({k: v for k, v in self.panel.styl.__dict__.items()}), self.panel.styl)

    def test_dlazdice_vypnutych_prepinacu_jsou_schovane(self):
        p = self.panel.prvky
        zavisle = {"stin": ("barva_stinu", "stin_rozmazani", "stin_x", "stin_y"),
                   "pozadi": ("barva_pozadi", "pruhlednost_pozadi", "odsazeni_pozadi"),
                   "zvyrazneni": ("barva_zvyrazneni",)}
        for prepinac, klice in zavisle.items():
            for zapnuto in (True, False, True):
                p[prepinac].setChecked(zapnuto)
                for klic in klice:
                    self.assertEqual(p[klic].isHidden(), not zapnuto, f"{prepinac}={zapnuto}: {klic}")
        self.panel.nastav(Styl())  # výchozí styl: stín zapnutý, pozadí a zvýraznění vypnuté
        self.assertFalse(p["stin_rozmazani"].isHidden())
        self.assertTrue(p["barva_pozadi"].isHidden())
        self.assertTrue(p["barva_zvyrazneni"].isHidden())

    def test_rozhrani_pro_selftest(self):
        pole = self.panel.prvky["velikost"]
        pole.setValue(pole.value() + 1.5)
        self.assertEqual(self.zmeny, [("velikost", 0.115)])
        tecka = self.panel.skupiny["text"].tecka
        self.assertTrue(tecka.isHidden())
        self.panel.skupiny["text"].nastav_zmenu(True, "x")
        self.assertFalse(tecka.isHidden())
        self.panel.skupiny["text"].nastav_zmenu(False)

    def test_pomer_stran_videa(self):
        self.panel.nastav_pomer(1920, 1080)
        self.assertAlmostEqual(self.panel.pomer, 16 / 9)
        o = self.panel.prvky["pozice_y"]._plocha_obrazovky()
        self.assertGreater(o.width(), o.height())
        self.panel.nastav_pomer(1080, 1920)
        o = self.panel.prvky["pozice_y"]._plocha_obrazovky()
        self.assertLess(o.width(), o.height())
        self.panel.nastav_pomer(100, 0)  # nesmyslné rozměry nesmí shodit kreslení
        self.assertTrue(0.4 <= self.panel.pomer <= 2.4)

    def test_popisky_ve_vsech_jazycich(self):
        try:
            for jazyk in ("cs", "sk", "en", "de", "es"):
                i18n.nastav(jazyk)
                for klic, d in self.panel.prvky.items():
                    self.assertTrue(d._popisek and not d._popisek.startswith("styl."), f"{jazyk}: {klic}")
                    self.assertNotIn("styl.tip.", d.toolTip(), f"{jazyk}: {klic}")
                    self.assertNotIn("dlazdice.", d.toolTip(), f"{jazyk}: {klic}")
                self.assertGreaterEqual(self.panel.minimumWidth(), 240)
        finally:
            i18n.nastav("cs")

    def test_kresleni_ve_vsech_stavech(self):
        """Ukázky se vykreslí bez chyby i s neobvyklým stylem (neznámé písmo, nulové hodnoty, krajní meze)."""
        styly = [Styl(), Styl(font="Tohle Písmo Neexistuje", velikost=0.02, obrys=0.25, stin_rozmazani=0,
                              stin_x=-60, stin_y=60, pozadi=True, pruhlednost_pozadi=100, odsazeni_pozadi=1.0,
                              zvyrazneni=True, pozice_y=0.0, barva_textu="zzzzzz", posun_ms=-2000),
                 Styl(tucne=True, velka_pismena=False, stin=False, pozadi=True, pruhlednost_pozadi=0,
                      pozice_y=1.0, max_slov=12, max_znaku=80, posun_ms=2000, predstih_ms=200)]
        for sirka in (260, 380, 700):
            self.panel.resize(sirka, 600)
            for styl in styly:
                self.panel.nastav(styl)
                self.assertFalse(self.panel.grab().isNull())


class TestKolecko(unittest.TestCase):
    """Pravidlo kolecko.py platí i pro číselné dlaždice: bez fokusu kolečko posouvá panel, s fokusem mění
    hodnotu; Esc nebo klik jinam fokus zruší."""

    @classmethod
    def setUpClass(cls):
        i18n.nastav("cs")
        cls.okno = QWidget()
        lay = QVBoxLayout(cls.okno)
        cls.panel = main.PanelStylu()
        cls.jinde = QLabel("jinde")
        lay.addWidget(cls.panel)
        lay.addWidget(cls.jinde)
        cls.okno.resize(380, 300)  # nízké okno – panel má co posouvat
        cls.okno.show()
        cls.okno.activateWindow()
        app.processEvents()

    @classmethod
    def tearDownClass(cls):
        cls.okno.close()

    def setUp(self):
        self.panel.nastav(Styl())
        self.panel.verticalScrollBar().setValue(0)
        if QApplication.focusWidget() is not None:
            QApplication.focusWidget().clearFocus()
        self.d = self.panel.prvky["velikost"]

    def test_dlazdice_je_pole(self):
        self.assertTrue(kolecko._je_pole(self.d))
        self.assertTrue(kolecko._je_pole(self.panel.prvky["pozice_y"]))
        self.assertFalse(kolecko._je_pole(self.panel.prvky["tucne"]))
        self.assertFalse(kolecko._je_pole(self.panel.prvky["barva_textu"]))

    def test_bez_fokusu_kolecko_posouva_panel(self):
        self.assertGreater(self.panel.verticalScrollBar().maximum(), 0)
        QApplication.sendEvent(self.d, kolecko_udalost(self.d, nahoru=False))
        self.assertAlmostEqual(self.d.value(), 10.0)
        self.assertGreater(self.panel.verticalScrollBar().value(), 0)

    def test_s_fokusem_kolecko_meni_hodnotu(self):
        self.d.setFocus()
        self.assertIs(QApplication.focusWidget(), self.d)
        QApplication.sendEvent(self.d, kolecko_udalost(self.d, nahoru=True))
        QApplication.sendEvent(self.d, kolecko_udalost(self.d, nahoru=True))
        QApplication.sendEvent(self.d, kolecko_udalost(self.d, nahoru=False))
        self.assertAlmostEqual(self.d.value(), 10.5)
        self.assertEqual(self.panel.verticalScrollBar().value(), 0)

    def test_esc_a_klik_jinam_zrusi_fokus(self):
        self.d.setFocus()
        QApplication.sendEvent(self.d, QKeyEvent(QEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier))
        self.assertIsNot(QApplication.focusWidget(), self.d)
        self.d.setFocus()
        bod = QPointF(5, 5)
        QApplication.sendEvent(self.jinde, QMouseEvent(QEvent.MouseButtonPress, bod,
                                                       QPointF(self.jinde.mapToGlobal(bod.toPoint())),
                                                       Qt.LeftButton, Qt.LeftButton, Qt.NoModifier))
        self.assertIsNot(QApplication.focusWidget(), self.d)

    def test_klik_na_tlacitko_dlazdice_fokus_nezrusi(self):
        self.d.setFocus()
        bod = QPointF(5, 5)
        QApplication.sendEvent(self.d.plus, QMouseEvent(QEvent.MouseButtonPress, bod,
                                                        QPointF(self.d.plus.mapToGlobal(bod.toPoint())),
                                                        Qt.LeftButton, Qt.LeftButton, Qt.NoModifier))
        self.assertIs(QApplication.focusWidget(), self.d)


class TestKlikani(unittest.TestCase):
    """Ovládání myší a klávesnicí stejnou cestou jako od uživatele (QTest)."""

    @classmethod
    def setUpClass(cls):
        i18n.nastav("cs")
        cls.panel = main.PanelStylu()
        cls.panel.resize(380, 1300)
        cls.panel.show()
        cls.panel.activateWindow()
        app.processEvents()

    @classmethod
    def tearDownClass(cls):
        cls.panel.close()

    def setUp(self):
        self.panel.nastav(Styl())
        self.zmeny = []
        self.spojeni = self.panel.zmena.connect(lambda klic, hodnota: self.zmeny.append((klic, hodnota)))
        self.panel.activateWindow()  # po zavření vysouvacího okna v předchozím testu není bez obrazovky aktivní nic
        app.processEvents()

    def tearDown(self):
        self.panel.zmena.disconnect(self.spojeni)
        for okno in QApplication.topLevelWidgets():
            if isinstance(okno, (dlazdice.PaletaBarev, dlazdice.VyberPisma)):
                okno.close()

    def _vysuv(self, typ):
        return next((w for w in QApplication.topLevelWidgets() if isinstance(w, typ) and w.isVisible()), None)

    def test_tlacitka_plus_a_minus(self):
        d = self.panel.prvky["max_znaku"]
        QTest.mouseClick(d.plus, Qt.LeftButton)
        QTest.mouseClick(d.plus, Qt.LeftButton)
        QTest.mouseClick(d.minus, Qt.LeftButton)
        self.assertEqual(self.zmeny, [("max_znaku", 16), ("max_znaku", 17), ("max_znaku", 16)])

    def test_klik_na_cislo_a_zapis(self):
        d = self.panel.prvky["predstih_ms"]
        QTest.mouseClick(d, Qt.LeftButton, Qt.NoModifier, d._plocha_cisla().center().toPoint())
        self.assertIsNotNone(d.editor)
        self.assertTrue(d.editor.hasFocus())
        self.assertEqual(d.editor.selectedText(), "40")
        QTest.keyClicks(d.editor, "55")
        QTest.keyClick(d.editor, Qt.Key_Return)
        self.assertIsNone(d.editor)
        self.assertEqual(self.zmeny, [("predstih_ms", 55)])
        self.assertTrue(d.hasFocus())  # po Enteru zůstává dlaždice aktivní pro kolečko a šipky
        QTest.keyClick(d, Qt.Key_Up)
        self.assertEqual(self.zmeny[-1], ("predstih_ms", 60))

    def test_esc_pri_zapisu_nic_nezmeni(self):
        d = self.panel.prvky["predstih_ms"]
        QTest.mouseClick(d, Qt.LeftButton, Qt.NoModifier, d._plocha_cisla().center().toPoint())
        QTest.keyClicks(d.editor, "150")
        QTest.keyClick(d.editor, Qt.Key_Escape)
        self.assertIsNone(d.editor)
        self.assertEqual(self.zmeny, [])
        self.assertAlmostEqual(d.value(), 40)

    def test_krok_behem_zapisu_potvrdi_zapsane_cislo(self):
        d = self.panel.prvky["predstih_ms"]
        QTest.mouseClick(d, Qt.LeftButton, Qt.NoModifier, d._plocha_cisla().center().toPoint())
        QTest.keyClicks(d.editor, "20")
        QTest.mouseClick(d.plus, Qt.LeftButton)
        self.assertIsNone(d.editor)
        self.assertEqual(self.zmeny, [("predstih_ms", 20), ("predstih_ms", 25)])
        QTest.mouseClick(d, Qt.LeftButton, Qt.NoModifier, d._plocha_cisla().center().toPoint())
        QTest.keyClicks(d.editor, "100")
        QTest.keyClick(d.editor, Qt.Key_Down)  # šipka v poli pro zápis = potvrdit a krok dolů
        self.assertIsNone(d.editor)
        self.assertEqual(self.zmeny[-1], ("predstih_ms", 95))

    def test_psani_cislic_zacne_zapis(self):
        d = self.panel.prvky["stin_rozmazani"]
        d.setFocus()
        QTest.keyClick(d, Qt.Key_7)
        self.assertIsNotNone(d.editor)
        QTest.keyClicks(d.editor, "5")
        QTest.keyClick(d.editor, Qt.Key_Enter)
        self.assertEqual(self.zmeny, [("stin_rozmazani", 75)])

    def test_prepinac_jednim_klikem(self):
        d = self.panel.prvky["pozadi"]
        self.assertTrue(self.panel.prvky["barva_pozadi"].isHidden())
        QTest.mouseClick(d, Qt.LeftButton)
        self.assertEqual(self.zmeny, [("pozadi", True)])
        app.processEvents()
        self.assertTrue(self.panel.prvky["barva_pozadi"].isVisible())
        QTest.mouseClick(d, Qt.LeftButton)
        self.assertEqual(self.zmeny[-1], ("pozadi", False))

    def test_klik_na_barvu_otevre_paletu_pod_dlazdici(self):
        d = self.panel.prvky["barva_textu"]
        QTest.mouseClick(d, Qt.LeftButton)
        paleta = self._vysuv(dlazdice.PaletaBarev)
        self.assertIsNotNone(paleta)
        self.assertGreaterEqual(paleta.y(), d.mapToGlobal(QPoint(0, d.height())).y())
        vzorek = next(v for v in paleta.findChildren(dlazdice._Vzorek) if v.hex == "FFFFFF")
        QTest.mouseClick(vzorek, Qt.LeftButton)
        self.assertEqual(self.zmeny, [("barva_textu", "FFFFFF")])
        self.assertIsNone(self._vysuv(dlazdice.PaletaBarev))

    def test_klik_na_pismo_otevre_seznam(self):
        d = self.panel.prvky["font"]
        QTest.mouseClick(d, Qt.LeftButton)
        vyber = self._vysuv(dlazdice.VyberPisma)
        self.assertIsNotNone(vyber)
        self.assertEqual(vyber.seznam.currentItem().text(), "Montserrat ExtraBold")
        QTest.keyClicks(vyber.hledat, "Montserrat Bl")
        QTest.keyClick(vyber.hledat, Qt.Key_Return)
        self.assertEqual(self.zmeny, [("font", "Montserrat Black")])
        self.assertIsNone(self._vysuv(dlazdice.VyberPisma))


class TestVysuvy(unittest.TestCase):
    def setUp(self):
        i18n.nastav("cs")
        self.zdroj = Zdroj()

    def test_paleta_barev(self):
        d = dlazdice.DlazdiceBarva(self.zdroj, "styl.barva_textu")
        d.nastav_hodnotu("f2ec3c")
        zmeny = []
        d.zmena.connect(zmeny.append)
        paleta = dlazdice.PaletaBarev(d, d.hex)
        vzorky = paleta.findChildren(dlazdice._Vzorek)
        self.assertEqual([v.hex for v in vzorky], theme.PALETA_TITULKU)
        self.assertEqual([v.hex for v in vzorky if v.vybrany], ["F2EC3C"])
        paleta.vybrano.connect(d._zvol)
        next(v for v in vzorky if v.hex == "FF3B30").click()
        self.assertEqual(zmeny, ["FF3B30"])
        self.assertEqual(d.hex, "FF3B30")
        self.assertIn("#FF3B30", d.toolTip())
        d._zvol("ff3b30")  # stejná barva = žádná změna
        self.assertEqual(len(zmeny), 1)

    def test_vyber_pisma(self):
        pisma = ["Montserrat ExtraBold", "Montserrat Black", "Arial", "Arial Black", "Verdana"]
        d = dlazdice.DlazdicePismo(self.zdroj, "styl.font", pisma)
        d.nastav_hodnotu("Arial")
        zmeny = []
        d.zmena.connect(zmeny.append)
        vyber = dlazdice.VyberPisma(d, d.pisma, d.rodina)
        vyber.vybrano.connect(d._zvol)
        self.assertEqual(vyber.seznam.count(), 5)
        self.assertEqual(vyber.seznam.currentItem().text(), "Arial")
        vyber.hledat.setText("  BLACK ")
        self.assertEqual([vyber.seznam.item(i).text() for i in range(vyber.seznam.count())],
                         ["Montserrat Black", "Arial Black"])
        QApplication.sendEvent(vyber.hledat, QKeyEvent(QEvent.KeyPress, Qt.Key_Down, Qt.NoModifier))
        QApplication.sendEvent(vyber.hledat, QKeyEvent(QEvent.KeyPress, Qt.Key_Return, Qt.NoModifier))
        self.assertEqual(zmeny, ["Arial Black"])
        self.assertEqual(d.rodina, "Arial Black")

    def test_pismo_mimo_nabidku_zustane_zobrazene(self):
        d = dlazdice.DlazdicePismo(self.zdroj, "styl.font", ["Arial"])
        d.nastav_hodnotu("Písmo Z Jiného Počítače")
        vyber = dlazdice.VyberPisma(d, d.pisma, d.rodina)
        self.assertEqual(d.rodina, "Písmo Z Jiného Počítače")
        self.assertEqual(vyber.seznam.count(), 1)


class TestPravidlaVzhledu(unittest.TestCase):
    def test_barvy_jen_z_theme_a_zadny_graphics_effect(self):
        kod = (KOREN / "dlazdice.py").read_text(encoding="utf-8")
        self.assertIsNone(re.search(r"#[0-9A-Fa-f]{6}\b", kod), "barvy patří do theme.py")
        self.assertIsNone(re.search(r"QColor\(\s*\d", kod), "barvy patří do theme.py")
        for soubor in ("dlazdice.py", "rozvrzeni.py"):  # záře a stíny se kreslí v paintEvent
            kod = (KOREN / soubor).read_text(encoding="utf-8")
            self.assertIsNone(re.search(r"setGraphicsEffect|QGraphics\w*Effect\(", kod), soubor)


if __name__ == "__main__":
    unittest.main()
