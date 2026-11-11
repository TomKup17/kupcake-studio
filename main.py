# kupcake.studio – Copyright (C) 2026 Tomáš Kupec
# SPDX-License-Identifier: GPL-3.0-only
"""kupcake.studio – automatické titulky (přepis, editor, přehrávač s živými titulky, styly, export)."""
import json
import logging
import sys
import traceback
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import QByteArray, QEvent, QLocale, QObject, QRectF, QSettings, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QAction, QColor, QFontDatabase, QIcon, QImage, QKeySequence, QPainter, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QCheckBox, QColorDialog, QComboBox, QDialog, QDialogButtonBox,
    QDoubleSpinBox, QFileDialog, QHBoxLayout, QHeaderView, QInputDialog, QLabel, QLineEdit,
    QMainWindow, QMenu, QMessageBox, QProgressBar, QPushButton, QScrollArea, QSizePolicy, QSlider, QSpinBox,
    QStackedWidget, QTableWidget, QTableWidgetItem, QToolButton, QVBoxLayout, QWidget,
)

import cesty
import i18n
import kolecko
import kupcake
import theme
from i18n import prekladej, t
from cesty import APP_ID, FONTY_DIR, IKONA, MUTEX, NASTAVENI_DIR, NAZEV, STYL_SOUBOR, VERZE
import upravy
from titulky import (MIN_SLOVO, Styl, Titulek, Znacka, nastav_text, prepocitej_text, rozdel_slova, seskup,
                     srovnej, video_fps, video_info, vyrez, vytvor_ass, vytvor_srt, vytvor_vtt)

ROZLOZENI_VERZE = 2  # formát rozlozeni.ini (1 = verze 1.0 se splittery, 2 = dokovací sekce QtAds)
VIDEO_PRIPONY = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v", ".mts"}
VLASTNI_FONTY = ["Montserrat ExtraBold", "Montserrat Black"]  # ze složky fonts/
MIN_DELKA = 0.1      # nejkratší povolený titulek (s)
KROK, KROK_SHIFT = 0.1, 0.5



def fmt_cas(t):
    m, s = divmod(max(t, 0), 60)
    return f"{int(m)}:{s:05.2f}"


def parse_cas(text):
    text = text.strip().replace(",", ".")
    casti = text.split(":")
    if not 1 <= len(casti) <= 3:
        raise ValueError
    sec = 0.0
    for c in casti:
        sec = sec * 60 + float(c)
    if sec < 0:
        raise ValueError
    return sec


def krok():
    return KROK_SHIFT if QApplication.keyboardModifiers() & Qt.ShiftModifier else KROK


def otevri_slozku(soubor):
    """Průzkumník se složkou souboru a souborem označeným."""
    import subprocess
    soubor = Path(soubor)
    if sys.platform == "win32" and soubor.exists():
        # seznam argumentů, bez shellu – „/select,“ a cesta zvlášť (Průzkumník je takto přijme i s mezerami)
        subprocess.Popen(["explorer", "/select,", str(soubor.resolve())])
    else:
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(soubor.parent)))


class Uloha(QThread):
    """Dlouhá práce ve vlákně. fn(progress, log): progress(podíl, fáze=None) hlásí celkový průběh a případně
    novou fázi (prubeh.Faze); po zrus() vyhodí nejbližší hlášení průběhu prubeh.Zruseno."""
    progress = Signal(float)
    faze = Signal(str)
    log = Signal(str)
    hotovo = Signal(object)
    chyba = Signal(str)
    zruseno = Signal()

    def __init__(self, fn):
        super().__init__()
        self.fn = fn
        self._zrusit = False

    def zrus(self):
        self._zrusit = True

    def _progress(self, p, faze=None):
        from prubeh import Zruseno
        if self._zrusit:
            raise Zruseno()
        self.progress.emit(float(p))
        if faze:
            self.faze.emit(faze)

    def run(self):
        from prubeh import Zruseno
        from stahovani import Odmitnuto
        try:
            self.hotovo.emit(self.fn(self._progress, self.log.emit))
        except Exception as e:
            # i export: zabité FFmpeg skončí vlastní chybou; odmítnuté stažení modelu = zrušení
            if self._zrusit or isinstance(e, (Zruseno, Odmitnuto)):
                self.zruseno.emit()
                return
            import logy
            self.detail = traceback.format_exc()
            logging.getLogger("kupcake").error("Úloha selhala:\n%s", self.detail)
            stderr = getattr(e, "stderr", None)
            text = stderr.decode("utf-8", "replace").strip() if isinstance(stderr, bytes) else str(stderr or e)
            self.chyba.emit(logy.srozumitelne(e, text))


class SouhlasSeStazenim(QObject):
    """Dotaz „Stáhnout model?“ před každým stahováním (stahovani.zeptej_se). Stahuje se ve vlákně úlohy –
    dotaz se proto ukáže v hlavním vlákně a vlákno počká na odpověď (BlockingQueuedConnection)."""
    dotaz = Signal(object)

    def __init__(self, okno):
        super().__init__(okno)
        self.okno = okno
        self.dotaz.connect(self._zeptej, Qt.BlockingQueuedConnection)

    def __call__(self, popis, velikost, zdroj):
        odpoved = {}
        if QThread.currentThread() is self.thread():
            self._zeptej((popis, velikost, zdroj, odpoved))
        else:
            self.dotaz.emit((popis, velikost, zdroj, odpoved))
        return odpoved.get("ano", False)

    def _zeptej(self, data):
        popis, velikost, zdroj, odpoved = data
        prekryti = getattr(self.okno, "prekryti", None)
        rodic = prekryti if prekryti is not None and prekryti.isVisible() else self.okno
        velikost = f"{velikost / 1e9:.2f} GB" if velikost >= 1e8 else f"{velikost / 1e6:.0f} MB"
        odpoved["ano"] = QMessageBox.question(
            rodic, t("stahovani.titulek"), t("stahovani.dotaz", co=popis, velikost=velikost, zdroj=zdroj),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes) == QMessageBox.Yes


class DropZona(QWidget):
    """Prázdný náhled před nahráním videa: tmavý přechod s nádechem modré/fialové a pár nenápadných
    hvězdiček (jako pozadí webu iamtom.kup), uprostřed animovaný cupcake, výzva a „CREATIVE AI · VIDEO · SUBTITLES“."""
    HESLO = (("CREATIVE ", None), ("AI", "akce"), (" · VIDEO · SUBTITLES", None))

    def __init__(self):
        super().__init__()
        self.setObjectName("drop")
        self.setCursor(Qt.PointingHandCursor)
        self.kliknuto = None
        self.aktivni = False
        import random
        nahoda = random.Random(7)  # pevné rozmístění – hvězdičky při změně velikosti neposkakují
        self.hvezdy = [(nahoda.random(), nahoda.random(), nahoda.uniform(0.5, 1.3), nahoda.randint(35, 120))
                       for _ in range(70)]
        prekladej(self.update)
        # animovaný cupcake nad výzvou (vlastní malý widget – překresluje se jen jeho plocha)
        self.cupcake = kupcake.CupcakeAnimace(96, self)
        self.cupcake.setAttribute(Qt.WA_TransparentForMouseEvents)  # klik projde na plochu

    def resizeEvent(self, e):
        s = self.cupcake.width()
        self.cupcake.move(int(self.width() / 2 - s / 2), int(self.height() / 2 - 70 - s))
        super().resizeEvent(e)

    def nastav_aktivni(self, ano):
        self.aktivni = ano
        self.update()

    def mousePressEvent(self, e):
        if self.kliknuto:
            self.kliknuto()

    def paintEvent(self, e):
        from PySide6.QtCore import QPointF
        from PySide6.QtGui import QFont, QFontMetricsF, QPen, QRadialGradient
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        p.setClipRect(r)
        p.fillRect(r, QColor(theme.POZADI))
        # dva velmi tmavé „mlhoviny“ – modrá vlevo nahoře, fialová vpravo dole
        for cx, cy, barva in ((0.3, 0.25, QColor(14, 34, 66, 150)), (0.78, 0.85, QColor(40, 20, 62, 120))):
            g = QRadialGradient(QPointF(r.width() * cx, r.height() * cy), max(r.width(), r.height()) * 0.6)
            g.setColorAt(0, barva)
            g.setColorAt(1, QColor(8, 8, 8, 0))
            p.fillRect(r, g)
        p.setPen(Qt.NoPen)
        for x, y, velikost, alfa in self.hvezdy:
            p.setBrush(QColor(242, 239, 234, alfa))
            p.drawEllipse(QPointF(r.width() * x, r.height() * y), velikost / 2 + 0.2, velikost / 2 + 0.2)
        # rámeček: jemný přerušovaný, při přetahování videa modrý
        p.setBrush(Qt.NoBrush)
        pero = QPen(QColor(theme.AKCENT if self.aktivni else theme.RAMECEK), 1.5 if self.aktivni else 1, Qt.DashLine)
        p.setPen(pero)
        p.drawRoundedRect(r.adjusted(1, 1, -1, -1), 14, 14)

        stred = r.center()
        hlavni = QFont(theme.PISMO_UI)
        hlavni.setPointSizeF(18)
        hlavni.setWeight(QFont.DemiBold)
        heslo = theme.pismo_zahlavi(8.5)
        heslo.setCapitalization(QFont.MixedCase)
        heslo.setLetterSpacing(QFont.PercentageSpacing, 125)
        maly = QFont(theme.PISMO_UI)
        maly.setPointSizeF(9.5)
        fm_h, fm_s, fm_m = QFontMetricsF(hlavni), QFontMetricsF(heslo), QFontMetricsF(maly)

        y = stred.y() - 34
        p.setFont(hlavni)
        p.setPen(QColor(theme.TEXT))
        p.drawText(QRectF(r.left(), y - fm_h.height(), r.width(), fm_h.height()), Qt.AlignCenter, t("drop"))
        y += 14 + fm_s.ascent()
        sirka = sum(fm_s.horizontalAdvance(text) for text, _ in self.HESLO)
        x = stred.x() - sirka / 2
        p.setFont(heslo)
        for text, druh in self.HESLO:
            p.setPen(QColor(theme.AKCE if druh == "akce" else theme.TEXT_2))
            p.drawText(QPointF(x, y), text)
            x += fm_s.horizontalAdvance(text)
        y += 30
        p.setFont(maly)
        p.setPen(QColor(theme.TEXT_3))
        p.drawText(QRectF(r.left(), y, r.width(), fm_m.height()), Qt.AlignCenter, t("drop.klik"))
        p.end()


class Nahled(QLabel):
    """Statický náhled (záloha, když není k dispozici libmpv)."""

    def __init__(self):
        super().__init__()
        prekladej(lambda: self.setText(t("nahled.popisek")))
        self.setObjectName("nahled")
        self.setAlignment(Qt.AlignCenter)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.setMinimumWidth(220)
        self.pix = None

    def nastav(self, data):
        img = QImage.fromData(data)
        self.pix = QPixmap.fromImage(img) if not img.isNull() else None
        self._prekresli()

    def _prekresli(self):
        if self.pix:
            self.setPixmap(self.pix.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def resizeEvent(self, e):
        self._prekresli()
        super().resizeEvent(e)


class TabulkaTitulku(QTableWidget):
    """Seznam titulků. Právě přehrávaný titulek má vlevo oranžový svislý proužek („teď“), označený řádek
    zůstává modrý (výběr). Titulek, jehož čas se překrývá se sousedním, má vpravo oranžovou ikonku
    upozornění s popiskem."""
    IKONA_PREKRYVU = 14

    def __init__(self, *a):
        super().__init__(*a)
        self.aktivni = -1
        self.prekryvy = {}  # řádek → text popisku
        self._ikona_prekryvu = theme.ikona("varovani.svg", theme.TITULEK_PREKRYV, self.IKONA_PREKRYVU)

    def nastav_prekryvy(self, prekryvy):
        if prekryvy != self.prekryvy:
            self.prekryvy = prekryvy
            self.viewport().update()

    def _ramec_ikony(self, r):
        bunka = self.visualRect(self.model().index(r, self.columnCount() - 1))
        s = self.IKONA_PREKRYVU
        return QRectF(bunka.right() - s - 8, bunka.center().y() - s / 2 + 0.5, s, s)

    def paintEvent(self, e):
        super().paintEvent(e)
        p = QPainter(self.viewport())
        p.setRenderHint(QPainter.Antialiasing)
        if 0 <= self.aktivni < self.rowCount():
            r = self.visualRect(self.model().index(self.aktivni, 0))
            if r.isValid():
                p.setPen(Qt.NoPen)
                p.setBrush(QColor(theme.TITULEK_PROUZEK))
                p.drawRoundedRect(QRectF(1, r.top() + 3, theme.TITULEK_PROUZEK_SIRKA, r.height() - 6), 1.5, 1.5)
        for r in self.prekryvy:
            if r < self.rowCount():
                self._ikona_prekryvu.paint(p, self._ramec_ikony(r).toRect())
        p.end()

    def viewportEvent(self, e):
        if e.type() == QEvent.ToolTip:
            from PySide6.QtWidgets import QToolTip
            for r, text in self.prekryvy.items():
                if r < self.rowCount() and self._ramec_ikony(r).adjusted(-3, -3, 3, 3).contains(e.pos()):
                    QToolTip.showText(e.globalPos(), text, self.viewport())
                    return True
        return super().viewportEvent(e)


class CasPole(QWidget):
    """Čas začátku/konce jednoho titulku: ◀ [0:01.25] ▶ (Shift = větší krok)."""

    def __init__(self, okno, titulek, klic):
        super().__init__()
        self.setObjectName("cas")
        self.okno, self.titulek, self.klic = okno, titulek, klic
        lay = QHBoxLayout(self)
        lay.setContentsMargins(2, 0, 2, 0)
        lay.setSpacing(0)
        for znak, smer in (("◀", -1), (None, 0), ("▶", 1)):
            if znak is None:
                self.edit = QLineEdit()
                self.edit.setAlignment(Qt.AlignCenter)
                self.edit.setFixedWidth(70)
                self.edit.editingFinished.connect(self._zapsano)
                self.edit.installEventFilter(self)
                lay.addWidget(self.edit)
                continue
            b = QToolButton()
            b.setText(znak)
            b.setAutoRepeat(True)
            b.setAutoRepeatDelay(400)
            b.setAutoRepeatInterval(90)
            b.setFocusPolicy(Qt.NoFocus)
            b.setToolTip(t("cas.ubrat" if smer < 0 else "cas.pridat"))
            b.clicked.connect(lambda _=False, s=smer: self._posun(s))
            lay.addWidget(b)
        self.obnov()

    def obnov(self):
        self.edit.setText(fmt_cas(getattr(self.titulek, self.klic)))

    def nastav_aktivni(self, ano):
        self.setProperty("aktivni", ano)
        self.style().unpolish(self)
        self.style().polish(self)
        self.edit.style().unpolish(self.edit)
        self.edit.style().polish(self.edit)

    def _posun(self, smer):
        self.okno.vyber_titulek(self.titulek)
        self.okno.zmen_cas(self.titulek, self.klic, getattr(self.titulek, self.klic) + smer * krok())

    def _zapsano(self):
        try:
            val = parse_cas(self.edit.text())
        except ValueError:
            self.okno.varuj(t("cas.neplatny"))
            self.obnov()
            return
        if not self.okno.zmen_cas(self.titulek, self.klic, val):
            self.obnov()

    def eventFilter(self, obj, e):
        if e.type() == QEvent.FocusIn:
            self.okno.vyber_titulek(self.titulek)
        return False


class BarvaTlacitko(QPushButton):
    zmena = Signal(str)

    def __init__(self, titulek):
        super().__init__()
        self.setObjectName("barva")
        self.setCursor(Qt.PointingHandCursor)
        self.titulek = titulek
        self.hex = "FFFFFF"
        self.clicked.connect(self._vyber)

    def nastav(self, hex_):
        self.hex = hex_.upper()
        # selektor jen na tlačítko samotné – bez něj by barvu zdědily i dialogy a další potomci
        self.setStyleSheet(f"QPushButton#barva {{ background: #{self.hex}; }}")
        self.setToolTip(f"#{self.hex}")

    def _vyber(self):
        c = QColorDialog.getColor(QColor(f"#{self.hex}"), self.window(), t(self.titulek))
        if c.isValid():
            self.nastav(c.name()[1:])
            self.zmena.emit(self.hex)


class PanelStylu(QScrollArea):
    """Ovládací prvky stylu. Vysílá zmena(klic, hodnota) – styl samotný mění okno. Nahoře výběr presetu
    a „Uložit preset“ (hlavní akce sekce – oranžová)."""
    zmena = Signal(str, object)
    preset_vybran = Signal(str)
    ulozit_preset = Signal()
    smazat_preset = Signal()

    def __init__(self):
        super().__init__()
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setMinimumWidth(300)
        self.viewport().setAutoFillBackground(False)  # průhledné – pod ním je karta
        obsah = QWidget()
        lay = QVBoxLayout(obsah)
        lay.setContentsMargins(0, 0, 0, 0)  # kategorie s vlastním pozadím přes celou šířku
        lay.setSpacing(4)
        self.prvky = {}
        self.skupiny = {}

        radek = QHBoxLayout()
        radek.setContentsMargins(0, 2, 0, 8)
        radek.setSpacing(6)
        self.preset = QComboBox()
        self.preset.setMinimumContentsLength(8)
        self.preset.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.preset.activated.connect(lambda i: self.preset_vybran.emit(self.preset.itemData(i)))
        prekladej(lambda: self.preset.setToolTip(t("preset.vyber")))
        radek.addWidget(self.preset, 1)
        self.btn_smazat_preset = QToolButton()
        self.btn_smazat_preset.setObjectName("nastroj")
        self.btn_smazat_preset.setText("✕")
        self.btn_smazat_preset.setFocusPolicy(Qt.NoFocus)
        prekladej(lambda: self.btn_smazat_preset.setToolTip(t("preset.smazat")))
        self.btn_smazat_preset.clicked.connect(self.smazat_preset)
        radek.addWidget(self.btn_smazat_preset)
        self.btn_ulozit_preset = QPushButton()
        self.btn_ulozit_preset.setObjectName("primary")
        self.btn_ulozit_preset.setFocusPolicy(Qt.NoFocus)
        prekladej(lambda: self.btn_ulozit_preset.setText(t("preset.ulozit")))
        self.btn_ulozit_preset.clicked.connect(self.ulozit_preset)
        radek.addWidget(self.btn_ulozit_preset)
        lay.addLayout(radek)

        g = self._skupina(lay, "text")
        font = QComboBox()
        font.setEditable(True)
        font.setMinimumContentsLength(12)
        font.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        font.setInsertPolicy(QComboBox.NoInsert)
        # písma rozhraní (Inter, JetBrains Mono) nejsou pro FFmpeg dostupná – do nabídky pro titulky nepatří
        rodiny = [f for f in QFontDatabase.families()
                  if not f.startswith(("@", "Inter", "JetBrains Mono"))]
        font.addItems(VLASTNI_FONTY + [f for f in rodiny if f not in VLASTNI_FONTY])
        font.currentTextChanged.connect(lambda v: self._posli("font", v.strip()) if v.strip() else None)
        self.prvky["font"] = font
        g.addRow(self._popisek("styl.font"), font)
        self._cislo(g, "velikost", "styl.velikost", 2, 30, 0.5, "styl.pripona_sirky", meritko=100)
        self._barva(g, "barva_textu", "styl.barva_textu")
        self._zaskrt(g, "tucne", "styl.tucne")
        self._zaskrt(g, "velka_pismena", "styl.velka_pismena")

        g = self._skupina(lay, "obrys")
        self._barva(g, "barva_obrysu", "styl.barva_obrysu")
        self._cislo(g, "obrys", "styl.obrys", 0, 25, 0.5, "styl.pripona_pisma", meritko=100)
        self._zaskrt(g, "stin", "styl.stin")
        self._barva(g, "barva_stinu", "styl.barva_stinu")
        self._cele(g, "stin_rozmazani", "styl.rozmazani", 0, 100)
        self._cele(g, "stin_x", "styl.posun_x", -60, 60, " px")
        self._cele(g, "stin_y", "styl.posun_y", -60, 60, " px")

        self.form_pozadi = g = self._skupina(lay, "pozadi")
        self._zaskrt(g, "pozadi", "styl.pozadi")
        self._barva(g, "barva_pozadi", "styl.barva_pozadi")
        self._cele(g, "pruhlednost_pozadi", "styl.pruhlednost", 0, 100, " %")
        self._cislo(g, "odsazeni_pozadi", "styl.odsazeni", 0, 100, 1, "styl.pripona_pisma", meritko=100)
        self.prvky["pozadi"].toggled.connect(self._viditelnost_pozadi)

        g = self._skupina(lay, "pozice")
        pozice = QSlider(Qt.Horizontal)
        pozice.setRange(0, 100)
        popis = QLabel()
        popis.setMinimumWidth(40)
        pozice.valueChanged.connect(lambda v: popis.setText(f"{v} %"))
        pozice.valueChanged.connect(lambda v: self._posli("pozice_y", v / 100))
        radek = QHBoxLayout()
        radek.addWidget(pozice, 1)
        radek.addWidget(popis)
        self.prvky["pozice_y"] = pozice
        g.addRow(self._popisek("styl.pozice"), radek)
        slova = self._cele(g, "max_slov", "styl.max_slov", 0, 12)
        prekladej(lambda: slova.setSpecialValueText(t("styl.auto")))
        self._cele(g, "max_znaku", "styl.max_znaku", 5, 80)
        tip = QLabel()
        prekladej(lambda: tip.setText(t("styl.tip_pozice")))
        tip.setObjectName("stav")
        tip.setWordWrap(True)
        g.addRow(tip)

        self.form_zvyrazneni = g = self._skupina(lay, "efekty")
        self._zaskrt(g, "zvyrazneni", "styl.zvyrazneni")
        self._barva(g, "barva_zvyrazneni", "styl.barva_zvyrazneni")
        self.prvky["zvyrazneni"].toggled.connect(
            lambda v: self.form_zvyrazneni.setRowVisible(self.prvky["barva_zvyrazneni"], v))

        g = self._skupina(lay, "casovani")
        posun = self._cele(g, "posun_ms", "styl.posun", -2000, 2000, " ms")
        posun.setSingleStep(10)
        predstih = self._cele(g, "predstih_ms", "styl.predstih", 0, 200, " ms")
        predstih.setSingleStep(5)
        tip = QLabel()
        prekladej(lambda: tip.setText(t("styl.tip_casovani")))
        tip.setObjectName("stav")
        tip.setWordWrap(True)
        g.addRow(tip)

        lay.addSpacing(8)
        self.btn_vychozi = QPushButton()
        prekladej(lambda: self.btn_vychozi.setText(t("styl.vychozi")))
        self.btn_vychozi.setFocusPolicy(Qt.NoFocus)
        lay.addWidget(self.btn_vychozi)
        lay.addStretch(1)
        self.setWidget(obsah)
        from rozvrzeni import obnov_stridani
        obnov_stridani(lay)  # pozadí kategorií A, B, A, B… podle pořadí

    def _skupina(self, lay, klic):
        """klic = stálé jméno skupiny (ukládá se stav sbalení), nadpis se překládá."""
        from rozvrzeni import Skupina
        skupina = Skupina("")
        prekladej(lambda: skupina.nastav_nazev(t(f"styl.skupina.{klic}")))
        self.skupiny[klic] = skupina
        lay.addWidget(skupina)
        return skupina.form

    @staticmethod
    def _popisek(klic):
        lbl = QLabel()
        prekladej(lambda: lbl.setText(t(klic)))
        return lbl

    def _posli(self, klic, hodnota):
        if not self.signalsBlocked():
            self.zmena.emit(klic, hodnota)

    def _cislo(self, form, klic, popis, od, do, krok_, pripona, meritko):
        w = QDoubleSpinBox()
        w.setRange(od, do)
        w.setSingleStep(krok_)
        w.setDecimals(1)

        def preloz():  # přípona i formát čísla (10,0 / 10.0) podle jazyka
            w.setLocale(QLocale())
            w.setSuffix(t(pripona))
        prekladej(preloz)
        w.valueChanged.connect(lambda v: self._posli(klic, round(v / meritko, 4)))
        w.meritko = meritko
        self.prvky[klic] = w
        form.addRow(self._popisek(popis), w)
        return w

    def _cele(self, form, klic, popis, od, do, pripona=""):
        w = QSpinBox()
        w.setRange(od, do)
        w.setSuffix(pripona)
        w.valueChanged.connect(lambda v: self._posli(klic, v))
        self.prvky[klic] = w
        form.addRow(self._popisek(popis), w)
        return w

    def _zaskrt(self, form, klic, popis):
        w = QCheckBox()
        prekladej(lambda: w.setText(t(popis)))
        w.toggled.connect(lambda v: self._posli(klic, v))
        self.prvky[klic] = w
        form.addRow("", w)

    def _barva(self, form, klic, popis):
        w = BarvaTlacitko(popis)
        w.zmena.connect(lambda v: self._posli(klic, v))
        self.prvky[klic] = w
        form.addRow(self._popisek(popis), w)

    def nastav_presety(self, nazvy, aktualni):
        """nazvy: klíče presetů (presety.VYCHOZI = vestavěný, zobrazí se přeložený název)."""
        from presety import VYCHOZI
        self.preset.blockSignals(True)
        self.preset.clear()
        for nazev in nazvy:
            self.preset.addItem(t("preset.vychozi") if nazev == VYCHOZI else nazev, nazev)
        self.preset.setCurrentIndex(max(self.preset.findData(aktualni), 0))
        self.preset.blockSignals(False)
        self.btn_smazat_preset.setEnabled(aktualni != VYCHOZI)

    def _viditelnost_pozadi(self, zapnuto):
        for k in ("barva_pozadi", "pruhlednost_pozadi", "odsazeni_pozadi"):
            self.form_pozadi.setRowVisible(self.prvky[k], zapnuto)

    def nastav(self, styl):
        """Zobrazí hodnoty stylu bez vyslání změn."""
        self.blockSignals(True)
        for klic, w in self.prvky.items():
            v = getattr(styl, klic)
            if isinstance(w, QComboBox):
                w.setCurrentText(v)
            elif isinstance(w, QDoubleSpinBox):
                w.setValue(v * w.meritko)
            elif isinstance(w, QSlider):
                w.setValue(round(v * 100))
            elif isinstance(w, QSpinBox):
                w.setValue(v)
            elif isinstance(w, QCheckBox):
                w.setChecked(v)
            elif isinstance(w, BarvaTlacitko):
                w.nastav(v)
        self._viditelnost_pozadi(styl.pozadi)
        self.form_zvyrazneni.setRowVisible(self.prvky["barva_zvyrazneni"], styl.zvyrazneni)
        self.blockSignals(False)


class Okno(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(NAZEV)
        self.resize(1480, 900)
        self.setAcceptDrops(True)

        self.video = None
        self.info = None  # (W, H, délka)
        self.slova = []
        self.titulky = []
        self.pole = []    # [(CasPole začátek, CasPole konec)] po řádcích
        self.aktivni = -1  # řádek právě přehrávaného titulku
        self.upraveno = False  # ruční úpravy, které by přerozdělení zahodilo
        self.historie, self.budoucnost = [], []  # Undo/Redo – snímky (titulky, značky)
        self._pred_tahem = None
        self.znacky = []         # značky (poznámky) na časové ose
        self.schranka = []       # zkopírovaná slova (Ctrl+C / Ctrl+X)
        self._konec_vyberu = None  # „Přehrát výběr“ zastaví v tomto čase
        self._panely_obnoveny = False  # rozvržení sekcí se obnovuje až s prvním zobrazením editoru
        self._vychozi_stav = None
        self.fps = 30.0
        self.vlna_uloha = None
        self.styl = Styl.nacti(STYL_SOUBOR)
        self.projekt_cesta = None  # uložený projekt .kupcake (None = zatím neuložený)
        self.neulozeno = False     # změny od posledního uložení
        self.uloha = None
        self.export = None
        self.nahled_uloha = None
        self.nahled_ceka = False
        self._plnim = False

        self.nahled_timer = QTimer(self)
        self.nahled_timer.setSingleShot(True)
        self.nahled_timer.setInterval(60)
        self.nahled_timer.timeout.connect(self._vykresli_nahled)
        self.varovani_timer = QTimer(self)
        self.varovani_timer.setSingleShot(True)
        self.varovani_timer.setInterval(5000)
        import projekt
        self.autosave_timer = QTimer(self)  # automatické uložení rozpracovaného projektu (obnova po pádu)
        self.autosave_timer.setInterval(projekt.AUTOSAVE_MS)
        self.autosave_timer.timeout.connect(self._autosave)
        self.autosave_timer.start()

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        # --- stránka 1: přetažení videa ---
        p1 = QWidget()
        l1 = QVBoxLayout(p1)
        l1.setContentsMargins(40, 40, 40, 40)
        self.drop = DropZona()
        self.drop.kliknuto = self.vyber_video
        l1.addWidget(self.drop)
        self.stack.addWidget(p1)

        # --- stránka 2: editor ---
        p2 = QWidget()
        l2 = QVBoxLayout(p2)
        l2.setContentsMargins(16, 10, 16, 16)
        l2.setSpacing(8)

        hlava = QHBoxLayout()
        self.nazev = QLabel()
        self.nazev.setObjectName("nazev")
        hlava.addWidget(self.nazev, 1)
        self.btn_jine = QPushButton()
        prekladej(lambda: self.btn_jine.setText(t("btn.jine_video")))
        self.btn_jine.setObjectName("sekundarni")
        self.btn_jine.setFocusPolicy(Qt.NoFocus)
        self.btn_jine.clicked.connect(self.vyber_video)
        hlava.addWidget(self.btn_jine)
        self.btn_zrusit = QPushButton()
        prekladej(lambda: self.btn_zrusit.setText(t("btn.zrusit")))
        self.btn_zrusit.setObjectName("sekundarni")
        self.btn_zrusit.setFocusPolicy(Qt.NoFocus)
        self.btn_zrusit.clicked.connect(self.zrusit_export)
        self.btn_zrusit.hide()
        hlava.addWidget(self.btn_zrusit)
        self.btn_export = QPushButton()
        prekladej(lambda: self.btn_export.setText(t("btn.export")))
        self.btn_export.setObjectName("primary")
        self.btn_export.setFocusPolicy(Qt.NoFocus)
        self.btn_export.clicked.connect(self.exportovat)  # hlavní akce – oranžová „pilulka“
        hlava.addWidget(self.btn_export)
        l2.addLayout(hlava)

        radek_stavu = QHBoxLayout()
        radek_stavu.setSpacing(6)
        self.nacitani = kupcake.CupcakeAnimace(26)  # animovaný cupcake = právě probíhá přepis / export
        self.nacitani.hide()
        radek_stavu.addWidget(self.nacitani)
        self.stav = QLabel()
        self.stav.setObjectName("stav")
        radek_stavu.addWidget(self.stav, 1)
        l2.addLayout(radek_stavu)
        self.bar = QProgressBar()
        self.bar.setRange(0, 1000)
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(3)  # tenká linka průběhu – svítí jen během přepisu/exportu
        l2.addWidget(self.bar)
        self.varovani = QLabel()
        self.varovani.setObjectName("varovani")
        self.varovani.setWordWrap(True)
        self.varovani.hide()
        self.varovani_timer.timeout.connect(self.varovani.hide)
        l2.addWidget(self.varovani)

        # editor titulků
        editor = QWidget()
        le = QVBoxLayout(editor)
        le.setContentsMargins(0, 0, 0, 0)
        self.tab = TabulkaTitulku(0, 3)
        prekladej(lambda: self.tab.setHorizontalHeaderLabels([t("tab.zacatek"), t("tab.konec"), t("tab.text")]))
        hh = self.tab.horizontalHeader()
        for c in (0, 1):
            hh.setSectionResizeMode(c, QHeaderView.Fixed)
            self.tab.setColumnWidth(c, 132)
        hh.setSectionResizeMode(2, QHeaderView.Stretch)
        self.tab.verticalHeader().setVisible(False)
        self.tab.verticalHeader().setDefaultSectionSize(36)
        self.tab.setAlternatingRowColors(True)
        self.tab.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tab.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed
                                 | QAbstractItemView.AnyKeyPressed)
        self.tab.itemChanged.connect(self.zmena_bunky)
        self.tab.cellClicked.connect(self.klik_na_radek)
        le.addWidget(self.tab, 1)
        tl = QHBoxLayout()
        self.btn_pridat = QPushButton()
        prekladej(lambda: self.btn_pridat.setText(t("btn.pridat")))
        self.btn_pridat.clicked.connect(self.pridat)
        self.btn_smazat = QPushButton()
        prekladej(lambda: self.btn_smazat.setText(t("btn.smazat")))
        self.btn_smazat.clicked.connect(self.smazat)
        self.btn_sloucit = QPushButton()
        prekladej(lambda: self.btn_sloucit.setText(t("btn.sloucit")))
        self.btn_sloucit.clicked.connect(self.sloucit)
        for b in (self.btn_pridat, self.btn_smazat, self.btn_sloucit):
            b.setFocusPolicy(Qt.NoFocus)
            tl.addWidget(b)
        tl.addStretch(1)
        le.addLayout(tl)

        # přehrávač (nebo statický náhled, když chybí libmpv)
        stred = QWidget()
        ls = QVBoxLayout(stred)
        ls.setContentsMargins(0, 0, 0, 0)
        try:
            from prehravac import ASS_SOUBOR, Prehravac
            self.prehravac = Prehravac()
            self.ass_soubor = ASS_SOUBOR
            self.prehravac.cas.connect(self.cas_videa)
            ls.addWidget(self.prehravac, 1)
            radek = QHBoxLayout()
            self.btn_zac_ted = QPushButton()
            prekladej(lambda: self.btn_zac_ted.setText(t("btn.zacatek_ted")))
            self.btn_zac_ted.clicked.connect(lambda: self.nastav_aktualni("start"))
            self.btn_kon_ted = QPushButton()
            prekladej(lambda: self.btn_kon_ted.setText(t("btn.konec_ted")))
            self.btn_kon_ted.clicked.connect(lambda: self.nastav_aktualni("end"))
            for b in (self.btn_zac_ted, self.btn_kon_ted):
                b.setFocusPolicy(Qt.NoFocus)
                radek.addWidget(b)
            ls.addLayout(radek)
            tip = QLabel()
            prekladej(lambda: tip.setText(t("tip.prehravac")))
            tip.setObjectName("stav")
            tip.setWordWrap(True)
            ls.addWidget(tip)
        except Exception as e:
            logging.getLogger("kupcake").exception("chyba")
            self.prehravac = None
            self.btn_zac_ted = self.btn_kon_ted = None
            self.nahled = Nahled()
            ls.addWidget(self.nahled, 1)
            chyba = QLabel()
            prekladej(lambda e=str(e): chyba.setText(t("chyba.prehravac", chyba=e)))
            chyba.setObjectName("stav")
            chyba.setWordWrap(True)
            ls.addWidget(chyba)

        from presety import Presety
        self.presety = Presety(NASTAVENI_DIR / "presety.json")
        self.panel = PanelStylu()
        self.panel.nastav(self.styl)
        self.panel.zmena.connect(self.zmena_stylu)
        self.panel.btn_vychozi.clicked.connect(self.vychozi_styl)
        self.panel.preset_vybran.connect(self.pouzij_preset)
        self.panel.ulozit_preset.connect(self.uloz_preset)
        self.panel.smazat_preset.connect(self.smaz_preset)
        for klic, skupina in self.panel.skupiny.items():
            skupina.vratit.connect(lambda k=klic: self.vrat_skupinu(k))
        prekladej(self._obnov_presety)

        from osa import CasovaOsa
        self.osa = CasovaOsa()
        self.osa.seek.connect(self.skoc_osa)
        self.osa.zacatek_upravy.connect(lambda: setattr(self, "_pred_tahem", self.snimek_stavu()))
        self.osa.konec_upravy.connect(self.konec_tahu)
        self.osa.zmena.connect(self.casy_zmeneny)
        self.osa.kontext.connect(self.kontextove_menu)
        self.osa.dvojklik_slovo.connect(self.uprav_text_slova)
        self.osa.dvojklik_znacka.connect(self.uprav_znacku)
        self.osa.smycka_vybrana.connect(self._smycka_z_meritka)
        self.osa.varovani.connect(self.varuj)

        # sekce jako dokovací panely: přesun za záhlaví, záložky, plovoucí okna, dvojklik = přes celé okno
        from doky import Dokovani
        self.dok = Dokovani(p2)
        self.dok.zprava.connect(self.stav.setText)
        for klic, obsah in (("titulky", editor), ("nahled", stred), ("nastaveni", self.panel), ("osa", self.osa)):
            self.dok.pridej(klic, f"karta.{klic}", obsah)
        self.dok.vychozi_rozmisteni()
        l2.addWidget(self.dok.m, 1)
        self.stack.addWidget(p2)

        self._vytvor_akce()
        self.akce["snap"].setIcon(theme.ikona_magnetu())  # oranžový = zapnuto, šedý = vypnuto
        self.akce["snap"].setProperty("magnet", True)
        self.akce["snap"].setIconVisibleInMenu(False)  # v menu stačí zaškrtnutí
        self.dok.sdilej_akce(self.akce.values())
        self._vytvor_menu()
        self.osa.pridej_listu([self.akce[k] if k not in (None, "|") else k for k in (
            "zpet", "znovu", None, "rozriznout", "seskupit", "rozdelit", "zarovnat_vyber", None,
            "snap", "smycka", "sledovat", "znacka", "|", "oddalit", "priblizit", "na_sirku", "na_vyber", "vyssi")])
        self._obnov_undo_tlacitka()
        from prekryti import Prekryti
        self.prekryti = Prekryti(self)  # velká obrazovka zpracování s plnícím se cupcakem
        self.prekryti.zrusit.connect(self.zrus_ulohu)
        from notifikace import Notifikace
        self.notifikace = Notifikace(self)  # „Export dokončen“ v rohu okna
        import stahovani
        self.souhlas = SouhlasSeStazenim(self)  # nic se nestáhne bez potvrzení uživatele
        stahovani.nastav_souhlas(self.souhlas)
        self._obnov_rozlozeni()

    # ---------- akce, menu a rozložení ----------
    # (klíč, zkratky oddělené |, metoda, zaškrtávací/výchozí stav)
    # Texty jsou v locales: akce.<klíč> (menu) a akce.<klíč>.kratce (lišta nad časovou osou).
    AKCE = {
        "soubor": [
            ("otevrit", "Ctrl+O", "otevri_soubor"),
            ("otevrit_video", "", "vyber_video"),
            ("ulozit", "Ctrl+S", "uloz_projekt"),
            ("ulozit_jako", "Ctrl+Shift+S", "uloz_projekt_jako"),
            None,
            ("export", "Ctrl+E", "exportovat"),
            None,
            ("konec", "", "close"),
        ],
        "upravy": [
            ("zpet", "Ctrl+Z", "zpet"),
            ("znovu", "Ctrl+Y|Ctrl+Shift+Z", "znovu"),
            None,
            ("kopirovat", "Ctrl+C", "kopirovat"),
            ("vyjmout", "Ctrl+X", "vyjmout"),
            ("vlozit", "Ctrl+V", "vlozit"),
            ("smazat", "Delete", "smazat_klavesa"),
            ("smazat_posun", "Shift+Delete", "smazat_s_posunem"),
            None,
            ("upravit", "F2", "uprav_vybrane_slovo"),
            ("nove_slovo", "Insert", "vlozit_slovo"),
            ("spojit", "Ctrl+J", "spojit_slova"),
            ("zarovnat_vyber", "Ctrl+Shift+A", "zarovnat_vyber"),
            None,
            ("rozriznout", "Ctrl+B", "rozriznout"),
            ("seskupit", "Ctrl+G", "seskupit"),
            ("rozdelit", "Ctrl+Shift+G", "rozdelit_skupinu"),
            ("rozdelit_u", "Ctrl+K", "rozdelit_u_slova"),
            None,
            ("zamek", "Ctrl+Shift+L", "prepni_zamek"),
            ("znacka", "M", "pridat_znacku"),
        ],
        "prehravani": [
            ("prehrat", "Space", "prehrat"),
            ("prehrat_vyber", "Shift+Space", "prehrat_vyber"),
            ("j", "J", "jkl_j"),
            ("k", "K", "jkl_k"),
            ("l", "L", "jkl_l"),
            None,
            ("snimek_zpet", "Left", "snimek_zpet"),
            ("snimek_vpred", "Right", "snimek_vpred"),
            ("sekunda_zpet", "Shift+Left", "sekunda_zpet"),
            ("sekunda_vpred", "Shift+Right", "sekunda_vpred"),
            ("na_zacatek", "Home", "na_zacatek"),
            ("na_konec", "End", "na_konec"),
            ("predchozi", "Up", "predchozi_titulek"),
            ("dalsi", "Down", "dalsi_titulek"),
            None,
            ("smycka", "Ctrl+L", "prepni_smycku", False),
        ],
        "zobrazeni": [
            ("na_sirku", "Shift+Z", "na_sirku"),
            ("na_vyber", "Z", "na_vyber"),  # Alt+Z otevírá menu Zobrazení
            ("priblizit", "Ctrl+=|Ctrl++", "priblizit"),
            ("oddalit", "Ctrl+-", "oddalit"),
            ("vyssi", "Ctrl+H", "prepni_vysku", False),
            ("sledovat", "", "prepni_sledovani", True),
            ("snap", "N", "prepni_prichytavani", True),
            None,
            ("rozlozeni", "", "vychozi_rozlozeni"),
            ("zamknout_rozvrzeni", "", "prepni_zamek_rozvrzeni", False),
        ],
        "napoveda": [
            ("zkratky", "F1", "ukaz_zkratky"),
            ("zpetna_vazba", "", "zpetna_vazba"),
            ("o_aplikaci", "", "o_aplikaci"),
        ],
    }
    UPRAVY = ("kopirovat", "vyjmout", "vlozit", "smazat", "smazat_posun", "upravit", "nove_slovo", "spojit",
              "zarovnat_vyber",
              "rozriznout", "seskupit", "rozdelit", "rozdelit_u", "zamek", "znacka", "export", "ulozit", "ulozit_jako")

    def _vytvor_akce(self):
        self.akce = {}
        for polozky in self.AKCE.values():
            for p in polozky:
                if p is None:
                    continue
                klic, klavesy, metoda, *zaskrt = p
                a = QAction(self)
                if klavesy:
                    a.setShortcuts([QKeySequence(k) for k in klavesy.split("|")])
                prekladej(lambda a=a, klic=klic: self._preloz_akci(a, klic))
                fn = getattr(self, metoda)
                if zaskrt:
                    a.setCheckable(True)
                    a.setChecked(zaskrt[0])
                    a.toggled.connect(fn)
                else:
                    a.triggered.connect(lambda _=False, fn=fn: fn())
                self.addAction(a)  # zkratky fungují v celém okně
                self.akce[klic] = a
        for k in ("export", "ulozit", "ulozit_jako"):
            self.akce[k].setEnabled(False)

    @staticmethod
    def _preloz_akci(a, klic):
        text = t(f"akce.{klic}", nazev=NAZEV)
        a.setText(text)
        a.setIconText(t(f"akce.{klic}.kratce") if i18n.ma(f"akce.{klic}.kratce") else text)
        zkratka = a.shortcut().toString(QKeySequence.NativeText)
        a.setToolTip(f"{text}  ({zkratka})" if zkratka else text)

    def _vytvor_menu(self):
        mb = self.menuBar()
        # „• kupcake.studio“ + malý cupcake v záhlaví, stejný princip jako logo webu; odkaz drží okno –
        # setCornerWidget v PySide vlastnictví nepřebírá a lokální proměnná by logo hned smazala
        self.logo = QWidget()
        self.logo.setObjectName("logo")
        lay = QHBoxLayout(self.logo)
        lay.setContentsMargins(2, 0, 14, 0)
        lay.setSpacing(3)
        # tečka: v klidu modrá, během zpracování (přepis, export) jemně pulzuje oranžově
        self.tecka_loga = theme.PulzujiciTecka()
        text = QLabel(theme.logo_html(11, tecka_barva=None))
        text.setTextFormat(Qt.RichText)
        cupcake = QLabel()
        cupcake.setPixmap(kupcake.pixmapa(18))
        lay.addWidget(self.tecka_loga)
        lay.addWidget(text)
        if "-" in VERZE:  # předběžná verze (1.0.0-beta.1) – nenápadný štítek BETA vedle loga
            beta = QLabel("BETA")
            beta.setObjectName("betaStitek")
            beta.setFont(theme.pismo_mono(7))
            beta.setToolTip(VERZE)
            lay.addWidget(beta)
        self.logo.setCursor(Qt.PointingHandCursor)  # klik na logo = O aplikaci
        self.logo.installEventFilter(self)
        prekladej(lambda: self.logo.setToolTip(t("akce.o_aplikaci", nazev=NAZEV)))
        lay.addSpacing(3)
        lay.addWidget(cupcake)
        mb.setCornerWidget(self.logo, Qt.TopLeftCorner)
        for nazev, polozky in self.AKCE.items():
            m = mb.addMenu("")
            prekladej(lambda m=m, nazev=nazev: m.setTitle(t(f"menu.{nazev}")))
            for p in polozky:
                if p is None:
                    m.addSeparator()
                else:
                    if p[0] == "konec":  # Soubor → Nedávné projekty (před Konec)
                        self.menu_nedavne = m.addMenu("")
                        prekladej(lambda: self.menu_nedavne.setTitle(t("projekt.nedavne")))
                        self.menu_nedavne.aboutToShow.connect(self._naplnit_nedavne)
                        m.addSeparator()
                    m.addAction(self.akce[p[0]])
            if nazev == "zobrazeni":
                self._vytvor_menu_rozvrzeni(m)
                self._vytvor_menu_jazyka(mb)  # Nastavení → Jazyk vložit před Nápovědu

    def _vytvor_menu_rozvrzeni(self, m):
        """Zobrazení: sekce zapnout/vypnout a uložená (pojmenovaná) rozvržení."""
        m.addSeparator()
        sekce = m.addMenu("")
        prekladej(lambda: sekce.setTitle(t("menu.sekce")))
        for dw in self.dok.sekce.values():
            sekce.addAction(dw.toggleViewAction())
        self.menu_rozvrzeni = m.addMenu("")
        prekladej(lambda: self.menu_rozvrzeni.setTitle(t("menu.rozvrzeni")))
        self.menu_rozvrzeni.aboutToShow.connect(self._naplnit_menu_rozvrzeni)
        self._naplnit_menu_rozvrzeni()

    def _naplnit_menu_rozvrzeni(self):
        m = self.menu_rozvrzeni
        m.clear()
        nazvy = self.dok.nazvy_rozvrzeni()
        for nazev in nazvy:
            m.addAction(nazev).triggered.connect(lambda _=False, n=nazev: self.otevri_rozvrzeni(n))
        if not nazvy:
            m.addAction(t("rozvrzeni.zadna")).setEnabled(False)
        m.addSeparator()
        m.addAction(t("rozvrzeni.ulozit")).triggered.connect(self.uloz_vlastni_rozvrzeni)
        smazat = m.addMenu(t("rozvrzeni.smazat"))
        smazat.setEnabled(bool(nazvy))
        for nazev in nazvy:
            smazat.addAction(nazev).triggered.connect(lambda _=False, n=nazev: self.smaz_vlastni_rozvrzeni(n))
        for a in m.actions():  # rozvržení dává smysl až nad zobrazeným editorem
            a.setEnabled(a.isEnabled() and self._panely_obnoveny)

    def _soubor_rozvrzeni(self):
        return NASTAVENI_DIR / "rozvrzeni_vlastni.ini"

    def uloz_vlastni_rozvrzeni(self):
        nazev, ok = QInputDialog.getText(self, t("rozvrzeni.dialog_titulek"), t("rozvrzeni.dialog_popis"))
        nazev = nazev.strip()
        if ok and nazev:
            self.dok.pridej_rozvrzeni(nazev)
            self.dok.uloz_rozvrzeni(self._soubor_rozvrzeni())
            self.stav.setText(t("rozvrzeni.ulozeno", nazev=nazev))

    def otevri_rozvrzeni(self, nazev):
        self.dok.otevri_rozvrzeni(nazev)
        self.stav.setText(t("rozvrzeni.otevreno", nazev=nazev))

    def smaz_vlastni_rozvrzeni(self, nazev):
        self.dok.smaz_rozvrzeni(nazev)
        self.dok.uloz_rozvrzeni(self._soubor_rozvrzeni())
        self.stav.setText(t("rozvrzeni.smazano", nazev=nazev))

    def prepni_zamek_rozvrzeni(self, zamknout):
        self.dok.zamkni(zamknout)
        self.stav.setText(t("rozvrzeni.zamceno" if zamknout else "rozvrzeni.odemceno"))

    def _vytvor_menu_jazyka(self, mb):
        from PySide6.QtGui import QActionGroup
        m = mb.addMenu("")
        prekladej(lambda: m.setTitle(t("menu.nastaveni")))
        podmenu = m.addMenu("")
        prekladej(lambda: podmenu.setTitle(t("menu.jazyk")))
        skupina = QActionGroup(self)
        self.akce_jazyku = {}
        for kod, nazev in i18n.dostupne():  # názvy jazyků v jejich vlastní podobě
            a = podmenu.addAction(nazev)
            a.setCheckable(True)
            a.setChecked(kod == i18n.aktualni())
            a.triggered.connect(lambda _=False, kod=kod: self.zmen_jazyk(kod))
            skupina.addAction(a)
            self.akce_jazyku[kod] = a
        self._vytvor_menu_prepisu(m)

    def _vytvor_menu_prepisu(self, m):
        """Nastavení → Přesnost přepisu, Přepis počítat na, informace „Přepis běží na: …“."""
        from PySide6.QtGui import QActionGroup
        from dialogy import PRESNOSTI, REZIMY, presnost_prepisu, rezim_prepisu
        m.addSeparator()
        presnost = m.addMenu("")
        presnost.setToolTipsVisible(True)
        prekladej(lambda: presnost.setTitle(t("presnost.nadpis")))
        skupina = QActionGroup(self)
        self.akce_presnosti = {}
        for klic in PRESNOSTI:
            a = presnost.addAction("")
            a.setCheckable(True)
            prekladej(lambda a=a, klic=klic: (a.setText(t(f"presnost.{klic}")),
                                              a.setToolTip(t(f"presnost.{klic}.popis"))))
            a.triggered.connect(lambda _=False, klic=klic: self.zmen_presnost(klic))
            skupina.addAction(a)
            self.akce_presnosti[klic] = a
        self.akce_presnosti[presnost_prepisu()].setChecked(True)
        rezim = m.addMenu("")
        prekladej(lambda: rezim.setTitle(t("rezim.nadpis")))
        skupina = QActionGroup(self)
        self.akce_rezimu = {}
        for klic in REZIMY:
            a = rezim.addAction("")
            a.setCheckable(True)
            prekladej(lambda a=a, klic=klic: a.setText(t(f"rezim.{klic}")))
            a.triggered.connect(lambda _=False, klic=klic: self.zmen_rezim(klic))
            skupina.addAction(a)
            self.akce_rezimu[klic] = a
        self.akce_rezimu[rezim_prepisu()].setChecked(True)
        self.akce_bezi_na = m.addAction("")
        self.akce_bezi_na.setEnabled(False)  # jen informace
        # vícejazyčný model MMS pro přesné časování – jen nekomerční použití, proto výchozí vypnuto
        import zarovnani
        self.akce_mms = m.addAction("")
        self.akce_mms.setCheckable(True)
        self.akce_mms.setChecked(zarovnani.mms_zapnuto())
        prekladej(lambda: self.akce_mms.setText(t("mms.nastaveni")))
        self.akce_mms.toggled.connect(self.prepni_mms)
        m.addSeparator()
        self.akce_pripominky = m.addAction("")
        self.akce_pripominky.setCheckable(True)
        self.akce_pripominky.setChecked(self._pripominka_zapnuta())
        prekladej(lambda: self.akce_pripominky.setText(t("pripominka.nastaveni")))
        self.akce_pripominky.toggled.connect(self.prepni_pripominku)
        self.akce_aktualizaci = m.addAction("")
        self.akce_aktualizaci.setCheckable(True)
        self.akce_aktualizaci.setChecked(str(i18n.nastaveni().value("aktualizace/zapnuto", "true")).lower() == "true")
        prekladej(lambda: self.akce_aktualizaci.setText(t("aktualizace.nastaveni")))
        self.akce_aktualizaci.toggled.connect(self.prepni_aktualizace)
        m.aboutToShow.connect(self._obnov_bezi_na)
        self._obnov_bezi_na()

    def _obnov_bezi_na(self):
        import hardware
        from dialogy import presnost_prepisu, rezim_prepisu
        hw = hardware.zjisti()
        zarizeni, compute = hardware.volba(presnost_prepisu(), rezim_prepisu(), hw)
        self.akce_bezi_na.setText(t("prepis.bezi_na", zarizeni=hardware.popis(zarizeni, hw)) + f"  ({compute})")

    def zmen_rezim(self, klic):
        from dialogy import uloz_prepis
        uloz_prepis("prepis/zarizeni", klic)
        self._obnov_bezi_na()
        self.stav.setText(self.akce_bezi_na.text())

    def zmen_presnost(self, klic):
        """Volba přesnosti přepisu; model, který ještě není stažený, se stáhne hned (se souhlasem a průběhem)."""
        import model as modely
        from dialogy import uloz_prepis
        uloz_prepis("prepis/model", klic)
        self.stav.setText(t("presnost.zvolena", nazev=t(f"presnost.{klic}")))
        if modely.je_pripraven(klic) or self.zaneprazdneno():
            return

        def prace(progress, log):
            modely.priprav_model(klic, lambda p: progress(p, "model"), log)
            return klic

        self.spust(prace, lambda k: self.nastav_stav(t("presnost.stazena", nazev=t(f"presnost.{k}")), 1.0),
                   "stazeni", prekryti=True, zruseno=lambda: self.nastav_stav(t("presnost.nestazena"), 1.0))

    def zmen_jazyk(self, kod):
        """Přepne jazyk rozhraní hned, bez restartu."""
        i18n.nastav(kod, ulozit=True)
        self.akce_jazyku[kod].setChecked(True)
        if self.video:
            self.naplnit_tabulku()  # popisky ◀ ▶ u časů
            if not self.titulky:
                self.obnov_nahled()  # ukázkový titulek v novém jazyce
        self.osa.prelozit()
        self.stav.setText(t("jazyk.zmenen", jazyk=dict(i18n.dostupne())[kod]))

    def ukaz_zkratky(self):
        dlg = QDialog(self)
        dlg.setWindowTitle(t("zkratky.titulek"))
        dlg.resize(560, 680)
        lay = QVBoxLayout(dlg)
        tab = QTableWidget(0, 2)
        tab.setHorizontalHeaderLabels([t("zkratky.akce"), t("zkratky.zkratka")])
        tab.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        tab.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        tab.verticalHeader().setVisible(False)
        tab.setEditTriggers(QAbstractItemView.NoEditTriggers)
        tab.setSelectionMode(QAbstractItemView.NoSelection)
        mys = [(t("zkratky.mys"), None)] + [(t(f"zkratky.mys.{k}"), t(f"zkratky.gesto.{g}")) for k, g in (
            ("okraj", "tazeni"), ("stred", "tazeni"), ("klik", "klik"), ("pridat", "shift_klik"),
            ("obdelnik", "prazdne"), ("upravit", "dvojklik"), ("kontext", "prave"), ("smycka", "shift_meritko"),
            ("bez_snap", "alt"), ("zoom", "kolecko"), ("sekce", "zahlavi"), ("maximalizace", "dvojklik_zahlavi"))]
        radky = []
        for nazev, polozky in self.AKCE.items():
            radky.append((t(f"menu.{nazev}").replace("&", ""), None))
            for p in polozky:
                if p and p[1]:
                    radky.append((self.akce[p[0]].text(), self.akce[p[0]].shortcut().toString(QKeySequence.NativeText)))
        for text, zkratka in radky + mys:
            r = tab.rowCount()
            tab.insertRow(r)
            bunka = QTableWidgetItem(text)
            if zkratka is None:  # nadpis sekce
                f = bunka.font()
                f.setBold(True)
                bunka.setFont(f)
                bunka.setForeground(QColor(theme.AKCENT))
            tab.setItem(r, 0, bunka)
            tab.setItem(r, 1, QTableWidgetItem(zkratka or ""))
        lay.addWidget(tab)
        tl = QDialogButtonBox(QDialogButtonBox.Close)
        tl.rejected.connect(dlg.reject)
        lay.addWidget(tl)
        dlg.exec()

    def _ulozene_rozlozeni(self):
        return QSettings(str(NASTAVENI_DIR / "rozlozeni.ini"), QSettings.IniFormat)

    def vychozi_rozlozeni(self):
        for skupina in self.panel.skupiny.values():
            skupina.rozbal(True)
        if self._panely_obnoveny:
            self.dok.obnov(self._vychozi_stav)
            self.dok.vychozi_velikosti()
            self.stav.setText(t("rozvrzeni.vychozi"))
        else:  # editor ještě není vidět – použije se výchozí, až se zobrazí
            self._ulozene_rozlozeni().remove("dok")

    def _obnov_rozlozeni(self):
        """Při startu: stav skupin, zámek a uložená rozvržení. Sekce až s prvním zobrazením editoru."""
        self._panely_obnoveny = False
        self._vychozi_stav = None
        s = self._ulozene_rozlozeni()
        if s.value("verze") != str(ROZLOZENI_VERZE):
            # rozložení ze starší verze (1.0 = pevné splittery) – ponechá se jen okno a skupiny,
            # sekce začnou ve výchozím rozvržení
            for klic in s.childGroups() + s.childKeys():
                if klic not in ("okno", "skupiny"):
                    s.remove(klic)
            s.setValue("verze", str(ROZLOZENI_VERZE))
        for nazev, skupina in self.panel.skupiny.items():
            rozbalena = s.value(f"skupiny/{nazev}")
            if rozbalena is not None:
                skupina.rozbal(rozbalena in (True, "true"))
        try:
            self.dok.nacti_rozvrzeni(self._soubor_rozvrzeni())
        except Exception:  # poškozený soubor s uloženými rozvrženími – aplikace kvůli němu nesmí spadnout
            logging.getLogger("kupcake").exception("chyba")
        if s.value("dok/zamceno") in (True, "true"):
            self.akce["zamknout_rozvrzeni"].setChecked(True)

    def _obnov_panely(self):
        # skryté sekce nemají skutečné rozměry a plovoucí okna nemají vyskočit už nad úvodní stránkou,
        # proto se rozvržení obnovuje až nad zobrazeným editorem
        if self._panely_obnoveny:
            return
        self._panely_obnoveny = True
        self.dok.vychozi_velikosti()
        self._vychozi_stav = self.dok.m.saveState()
        stav = self._ulozene_rozlozeni().value("dok/stav")
        if isinstance(stav, QByteArray) and not stav.isEmpty():
            if not self.dok.platny_stav(stav):
                stav = self._vychozi_stav
            try:
                ok = self.dok.obnov(stav)  # včetně plovoucích oken na jejich monitorech
            except Exception:
                logging.getLogger("kupcake").exception("chyba")
                ok = False
            if not ok or not self.dok.neco_videt():  # nečitelné nebo prázdné rozvržení → výchozí
                self.dok.obnov(self._vychozi_stav)
                self.dok.vychozi_velikosti()
            self.dok.okna_na_obrazovku(self)

    def uloz_rozlozeni(self):
        s = self._ulozene_rozlozeni()
        s.setValue("okno/geometrie", self.saveGeometry())
        if self._panely_obnoveny:  # editor byl vidět – rozvržení je skutečné
            s.setValue("dok/stav", self.dok.stav())
        s.setValue("dok/zamceno", self.dok.zamceno)
        for nazev, skupina in self.panel.skupiny.items():
            s.setValue(f"skupiny/{nazev}", skupina.je_rozbalena())
        s.sync()
        self.dok.uloz_rozvrzeni(self._soubor_rozvrzeni())

    def zobraz(self):
        """Otevře okno v uložené velikosti a poloze, poprvé maximalizované."""
        geometrie = self._ulozene_rozlozeni().value("okno/geometrie")
        if geometrie and self.restoreGeometry(geometrie):
            self.show()
        else:
            self.showMaximized()

    # ---------- drag & drop ----------
    def _video_z_mime(self, mime):
        """Přetažené video nebo projekt .kupcake."""
        for url in mime.urls():
            p = Path(url.toLocalFile())
            if p.suffix.lower() in VIDEO_PRIPONY or p.suffix.lower() == ".kupcake":
                return p
        return None

    def dragEnterEvent(self, e):
        if not self.zaneprazdneno() and self._video_z_mime(e.mimeData()):
            e.acceptProposedAction()
            self.drop.nastav_aktivni(True)

    def dragLeaveEvent(self, e):
        self.drop.nastav_aktivni(False)

    def dropEvent(self, e):
        self.drop.nastav_aktivni(False)
        p = self._video_z_mime(e.mimeData())
        if p:
            self.otevri_cestu(p)

    def vyber_video(self):
        if self.zaneprazdneno() or not self._neulozene_ok():
            return
        cesta, _ = QFileDialog.getOpenFileName(
            self, t("dialog.vyber_video"), str(Path.home() / "Desktop"),
            t("dialog.videa") + " (" + " ".join(f"*{x}" for x in sorted(VIDEO_PRIPONY)) + ")")
        if cesta:
            self.otevri(Path(cesta))

    # ---------- kontrola aktualizací (GitHub Releases) ----------
    def zkontroluj_aktualizace(self):
        """Po startu na pozadí (nejvýš 1× za den); výsledek přijde signálem do hlavního vlákna."""
        import aktualizace
        if not hasattr(self, "_most_aktualizace"):
            class Most(QObject):
                nova = Signal(str, str)
            self._most_aktualizace = Most(self)
            self._most_aktualizace.nova.connect(self._nabidni_aktualizaci)
        aktualizace.zkontroluj_na_pozadi(i18n.nastaveni(), lambda v, u: self._most_aktualizace.nova.emit(v, u))

    def _nabidni_aktualizaci(self, verze, url, pokus=0):
        if self.zaneprazdneno() or self.notifikace.isVisible() or QApplication.activeModalWidget() is not None:
            if pokus < 30:  # během práce ne – zkusit znovu za minutu
                QTimer.singleShot(60_000, lambda: self._nabidni_aktualizaci(verze, url, pokus + 1))
            return
        from o_aplikaci import otevri_odkaz

        def preskocit():
            s = i18n.nastaveni()
            s.setValue("aktualizace/preskocit", verze)
            s.sync()
        self.notifikace.ukaz_tlacitka(t("aktualizace.nadpis", verze=verze), t("aktualizace.text"),
                                      [(t("aktualizace.stahnout"), lambda: otevri_odkaz(url), True),
                                       (t("aktualizace.preskocit"), preskocit, False)])

    def prepni_aktualizace(self, zapnuto):
        s = i18n.nastaveni()
        s.setValue("aktualizace/zapnuto", "true" if zapnuto else "false")
        s.sync()

    def prepni_mms(self, zapnout):
        """Nastavení → přesné časování i pro jazyky bez vlastního modelu (vícejazyčný model MMS). Model je pod
        licencí CC BY-NC 4.0 (jen nekomerční použití) – zapne se až po potvrzení upozornění."""
        import zarovnani
        if zapnout and QMessageBox.question(self, NAZEV, t("mms.upozorneni"), QMessageBox.Yes | QMessageBox.No,
                                            QMessageBox.No) != QMessageBox.Yes:
            self.akce_mms.blockSignals(True)
            self.akce_mms.setChecked(False)
            self.akce_mms.blockSignals(False)
            return
        zarovnani.nastav_mms(zapnout)

    def uvitani(self):
        """Při prvním spuštění (nové hlavní verze) právní upozornění bety se souhlasem. Vrátí False = ukončit."""
        import uvitani
        if not uvitani.je_potreba():
            return True
        dlg = uvitani.Uvitani(self)
        prijato = dlg.exec() == QDialog.Accepted
        dlg.deleteLater()
        return prijato

    def zpetna_vazba(self):
        """Nápověda → Nahlásit chybu / Zpětná vazba: odkaz z links.py ve výchozím prohlížeči."""
        import links
        from o_aplikaci import otevri_odkaz
        if not otevri_odkaz(links.ZPETNA_VAZBA):
            self.stav.setText(t("oaplikaci.odkaz_selhal", url=links.ZPETNA_VAZBA))

    def o_aplikaci(self):
        """Okno O aplikaci – překryvná karta (o_aplikaci.py); z menu Nápověda i kliknutím na logo."""
        if self.zaneprazdneno():
            return
        from o_aplikaci import OAplikaci
        dlg = OAplikaci(self)
        dlg.exec()
        dlg.deleteLater()

    # ---------- připomínka „Sleduj mě“ po 5. exportu ----------
    PRIPOMINKA_PO = 5

    def _pripominka_zapnuta(self):
        return str(i18n.nastaveni().value("pripominka/zapnuta", "true")).lower() == "true"

    def prepni_pripominku(self, zapnuto):
        s = i18n.nastaveni()
        s.setValue("pripominka/zapnuta", "true" if zapnuto else "false")
        s.sync()

    def _po_exportu(self):
        """Počítá úspěšné exporty; po 5. jednou (nikdy během práce) nenápadně připomene sledování autora."""
        s = i18n.nastaveni()
        pocet = int(s.value("pripominka/exportu", 0) or 0) + 1
        s.setValue("pripominka/exportu", pocet)
        s.sync()
        if pocet >= self.PRIPOMINKA_PO and self._pripominka_zapnuta() \
                and str(s.value("pripominka/zobrazena", "false")).lower() != "true":
            QTimer.singleShot(theme.NOTIFIKACE_MS + 1500, self._ukaz_pripominku)  # až zmizí „Export dokončen“

    def _ukaz_pripominku(self):
        if self.zaneprazdneno() or self.notifikace.isVisible() or self.prekryti.isVisible() \
                or QApplication.activeModalWidget() is not None:
            return  # během práce ne – zkusí se po dalším exportu
        import links
        from o_aplikaci import otevri_odkaz
        s = i18n.nastaveni()
        s.setValue("pripominka/zobrazena", "true")  # nejvýš jednou
        s.sync()
        tlacitka = [(t("oaplikaci.odkaz.instagram"), lambda: otevri_odkaz(links.INSTAGRAM), True),
                    (t("oaplikaci.odkaz.tiktok"), lambda: otevri_odkaz(links.TIKTOK), True),
                    (t("pripominka.nezobrazovat"), lambda: self.akce_pripominky.setChecked(False), False)]
        tlacitka = [b for b, url in zip(tlacitka, (links.INSTAGRAM, links.TIKTOK, "x")) if url.strip()]
        self.notifikace.ukaz_tlacitka(t("pripominka.nadpis"), t("pripominka.text"), tlacitka)

    def eventFilter(self, obj, e):
        if obj is getattr(self, "logo", None) and e.type() == QEvent.MouseButtonRelease \
                and e.button() == Qt.LeftButton:
            QTimer.singleShot(0, self.o_aplikaci)  # klik na logo v záhlaví
            return True
        return False

    def zaneprazdneno(self):
        return self.uloha is not None and self.uloha.isRunning()

    # ---------- projekty (.kupcake) ----------
    NEDAVNYCH = 8

    def _nastav_neulozeno(self, ano=True):
        self.neulozeno = bool(ano and self.video)
        nazev = Path(self.projekt_cesta).stem if self.projekt_cesta else (self.video.name if self.video else "")
        self.setWindowTitle(f"{'• ' if self.neulozeno else ''}{nazev} – {NAZEV}" if nazev else NAZEV)

    def _stav_projektu(self):
        import projekt
        return projekt.sestav(self.video, self.info, self.titulky, self.znacky, self.styl, self.slova,
                              self.jazyk_prepisu, self.posun_zvuku, self.zarovnano,
                              self.osa.smycka if self.osa.smycka_zapnuta else None,
                              self.dok.stav() if self._panely_obnoveny else None, self.projekt_cesta, VERZE)

    def uloz_projekt_jako(self):
        return self.uloz_projekt(jako=True)

    def uloz_projekt(self, jako=False):
        """Ctrl+S (Ctrl+Shift+S = jako). Vrátí True, když se uložilo."""
        import projekt
        if not self.video or self.zaneprazdneno():
            return False
        cesta = None if jako else self.projekt_cesta
        if not cesta:
            vychozi = (Path(self.projekt_cesta).parent if self.projekt_cesta else self.video.parent) / \
                (self.video.stem + projekt.PRIPONA)
            cesta, _ = QFileDialog.getSaveFileName(self, t("projekt.ulozit_titulek"), str(vychozi),
                                                   f"{t('projekt.filtr')} (*{projekt.PRIPONA})")
            if not cesta:
                return False
            cesta = str(Path(cesta).with_suffix(projekt.PRIPONA))
        self.projekt_cesta = cesta
        try:
            projekt.uloz(cesta, self._stav_projektu())
        except OSError as e:
            QMessageBox.critical(self, NAZEV, t("projekt.chyba_ulozeni", chyba=e))
            return False
        projekt.AUTOSAVE.unlink(missing_ok=True)  # uloženo – obnova po pádu už není potřeba
        self._pridej_nedavny(cesta)
        self._nastav_neulozeno(False)
        self.stav.setText(t("projekt.ulozen", nazev=Path(cesta).name))
        return True

    def _neulozene_ok(self):
        """Před zavřením / otevřením jiného: uložit, zahodit, nebo zrušit. True = pokračovat."""
        if not getattr(self, "neulozeno", False) or not self.video:
            return True
        odpoved = QMessageBox.question(
            self, NAZEV, t("projekt.neulozene", nazev=Path(self.projekt_cesta).name if self.projekt_cesta
                           else self.video.name),
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel, QMessageBox.Save)
        if odpoved == QMessageBox.Save:
            return self.uloz_projekt()
        return odpoved == QMessageBox.Discard

    def otevri_soubor(self):
        """Ctrl+O: projekt (.kupcake) nebo video."""
        import projekt
        if self.zaneprazdneno() or not self._neulozene_ok():
            return
        videa = " ".join(f"*{x}" for x in sorted(VIDEO_PRIPONY))
        cesta, _ = QFileDialog.getOpenFileName(
            self, t("projekt.otevrit_titulek"), str(Path.home() / "Desktop"),
            f"{t('projekt.filtr_vse')} (*{projekt.PRIPONA} {videa});;{t('projekt.filtr')} (*{projekt.PRIPONA});;"
            f"{t('dialog.videa')} ({videa})")
        if cesta:
            self.otevri_cestu(Path(cesta), zeptat=False)

    def otevri_cestu(self, cesta, zeptat=True):
        """Projekt nebo video podle přípony (z dialogu, přetažení, příkazové řádky, nedávných)."""
        import projekt
        if zeptat and (self.zaneprazdneno() or not self._neulozene_ok()):
            return
        if cesta.suffix.lower() == projekt.PRIPONA:
            self.otevri_projekt(cesta)
        else:
            self.otevri(cesta)

    def otevri_projekt(self, cesta, data=None, obnova=False):
        import projekt
        try:
            data = data or projekt.nacti(cesta)
        except projekt.ChybaProjektu as e:
            QMessageBox.warning(self, NAZEV, t("projekt.chyba_nacteni", nazev=Path(cesta).name, chyba=e))
            return False
        video = projekt.najdi_video(data, None if obnova else cesta)
        if video is None:  # video se přesunulo – nechat uživatele ho najít
            QMessageBox.information(self, NAZEV, t("projekt.video_chybi", video=data["video"]))
            nove, _ = QFileDialog.getOpenFileName(
                self, t("dialog.vyber_video"), str(Path(cesta).parent),
                t("dialog.videa") + " (" + " ".join(f"*{x}" for x in sorted(VIDEO_PRIPONY)) + ")")
            if not nove:
                return False
            video = Path(nove)
        try:
            info = video_info(video)
        except Exception as e:
            QMessageBox.warning(self, NAZEV, t("chyba.video_necitelne", chyba=e))
            return False
        self.styl = data["styl"]
        self.panel.nastav(self.styl)
        self._obnov_tecky()
        self._nacti_video(video, info, data["titulky"], data["znacky"])
        self.slova = data["slova"]
        self.jazyk_prepisu, self.posun_zvuku, self.zarovnano = data["jazyk"], data["posun_zvuku"], data["zarovnano"]
        self.upraveno = True  # ruční úpravy z projektu nesmí přepsat nové rozdělení
        if data["smycka"]:
            QTimer.singleShot(0, lambda od=data["smycka"][0], do=data["smycka"][1]: self._zapni_smycku(od, do))
        if data["rozvrzeni"]:
            stav = QByteArray(data["rozvrzeni"])
            QTimer.singleShot(50, lambda: self.dok.platny_stav(stav) and self.dok.obnov(stav))
        self.nastav_ovladani(True)
        self.obnov_nahled()
        self.projekt_cesta = None if obnova else str(cesta)
        self._nastav_neulozeno(obnova)  # obnovený projekt je neuložený, dokud ho uživatel neuloží
        if not obnova:
            self._pridej_nedavny(str(cesta))
            self.stav.setText(t("projekt.otevren", nazev=Path(cesta).name))
        return True

    # nedávné projekty
    def _nedavne(self):
        hodnota = i18n.nastaveni().value("projekty/nedavne", [])
        seznam = [hodnota] if isinstance(hodnota, str) else list(hodnota or [])
        return [p for p in seznam if p]

    def _pridej_nedavny(self, cesta):
        seznam = [cesta] + [p for p in self._nedavne() if Path(p) != Path(cesta)]
        s = i18n.nastaveni()
        s.setValue("projekty/nedavne", seznam[:self.NEDAVNYCH])
        s.sync()

    def _naplnit_nedavne(self):
        m = self.menu_nedavne
        m.clear()
        seznam = self._nedavne()
        for cesta in seznam:
            a = m.addAction(Path(cesta).name)
            a.setToolTip(cesta)
            a.setEnabled(Path(cesta).is_file())
            a.triggered.connect(lambda _=False, c=cesta: self.otevri_cestu(Path(c)))
        if not seznam:
            m.addAction(t("projekt.zadne_nedavne")).setEnabled(False)
        else:
            m.addSeparator()
            m.addAction(t("projekt.vymazat_nedavne")).triggered.connect(
                lambda: (i18n.nastaveni().remove("projekty/nedavne"), i18n.nastaveni().sync()))

    # automatické ukládání a obnova po pádu
    def _autosave(self):
        import projekt
        if getattr(self, "neulozeno", False) and self.video and not self.zaneprazdneno():
            try:
                data = self._stav_projektu()
                data["obnova"] = {"projekt": self.projekt_cesta}
                projekt.uloz(projekt.AUTOSAVE, data)
            except OSError:
                logging.getLogger("kupcake").exception("automatické uložení selhalo")

    def nabidni_obnovu(self):
        """Po spuštění: leží-li tu automaticky uložený projekt, aplikace minule nedoběhla – nabídnout obnovu."""
        import projekt
        if not projekt.AUTOSAVE.is_file():
            return
        import datetime
        kdy = datetime.datetime.fromtimestamp(projekt.AUTOSAVE.stat().st_mtime).strftime("%d. %m. %H:%M")
        try:
            data = projekt.nacti(projekt.AUTOSAVE)
        except projekt.ChybaProjektu:
            projekt.AUTOSAVE.unlink(missing_ok=True)
            return
        if QMessageBox.question(self, NAZEV, t("projekt.obnovit", video=data["video"].name, kdy=kdy),
                                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes) == QMessageBox.Yes:
            try:
                puvodni = json.loads(projekt.AUTOSAVE.read_text(encoding="utf-8")).get("obnova", {}).get("projekt")
            except (OSError, ValueError):
                puvodni = None
            if self.otevri_projekt(projekt.AUTOSAVE, data, obnova=True):
                self.projekt_cesta = puvodni
                self._nastav_neulozeno(True)
                self.stav.setText(t("projekt.obnoven"))
                return
        projekt.AUTOSAVE.unlink(missing_ok=True)

    # ---------- přepis ----------
    def otevri(self, video, jazyk_reci=False):
        """jazyk_reci: False = zeptat se dialogem, None = rozpoznat automaticky, jinak kód (např. "cs")."""
        try:
            info = video_info(video)
        except Exception as e:
            QMessageBox.warning(self, NAZEV, t("chyba.video_necitelne", chyba=e))
            return
        from titulky import ma_zvuk
        if not ma_zvuk(video):  # bez zvuku není co přepsat – editor pro ruční titulky
            QMessageBox.information(self, NAZEV, t("chyba.bez_zvuku"))
            self._nacti_video(video, info)
            self.projekt_cesta = None
            self._nastav_neulozeno(False)
            self.nastav_ovladani(True)
            return
        if jazyk_reci is False:
            from dialogy import vyber_jazyk_reci
            jazyk_reci = vyber_jazyk_reci(self, video.name, info[2])
            if jazyk_reci is False:  # zrušeno
                return
        self._nacti_video(video, info)
        self.jazyk_prepisu = jazyk_reci
        self.projekt_cesta = None
        self._nastav_neulozeno(False)

        from dialogy import moznosti_prepisu, presnost_prepisu, rezim_prepisu
        presne, oddelit_hlas = moznosti_prepisu()
        model_prepisu, rezim = presnost_prepisu(), rezim_prepisu()

        def prace(progress, log):
            from prepis import prepis
            return prepis(video, jazyk_reci, progress, log, presne=presne, oddelit_hlas=oddelit_hlas,
                          model=model_prepisu, rezim=rezim)

        self.spust(prace, self.prepis_hotov, "prepis", prekryti=True, zruseno=self.prepis_zrusen)

    def _nacti_video(self, video, info, titulky=None, znacky=None):
        """Video do editoru (přehrávač, vlna, časová osa) – bez přepisu; volá ho otevri() i otevření projektu."""
        self.video, self.info = video, info
        self.zvuk, self.jazyk_prepisu, self.posun_zvuku, self.zarovnano = None, None, 0.0, False
        self.slova, self.titulky, self.upraveno = [], list(titulky or []), False
        self.historie, self.budoucnost = [], []
        self.znacky, self._konec_vyberu = list(znacky or []), None
        self.fps = video_fps(video)
        self.osa.fps = self.fps
        self.osa.nastav_smycku(None, zapnuta=False)
        self.akce["smycka"].blockSignals(True)
        self.akce["smycka"].setChecked(False)
        self.akce["smycka"].blockSignals(False)
        self._obnov_undo_tlacitka()
        self.osa.nastav_vlnu(None)
        self.naplnit_tabulku()
        QTimer.singleShot(0, self.osa.zobraz_cele)  # až bude stránka editoru vidět a známá její šířka

        def vlna(progress, log):
            from osa import vlna_z_audia
            from prepis import nacti_zvuk
            from titulky import ma_zvuk
            return vlna_z_audia(nacti_zvuk(video)) if ma_zvuk(video) else None

        self.vlna_uloha = Uloha(vlna)
        self.vlna_uloha.hotovo.connect(lambda env, v=video: self.osa.nastav_vlnu(env) if v == self.video else None)
        self.vlna_uloha.start()
        W, H, delka = info
        self.nazev.setText(f"{video.name}   ·   {W}×{H}   ·   {fmt_cas(delka)}")
        self.stack.setCurrentIndex(1)
        QTimer.singleShot(0, self._obnov_panely)
        self.nastav_ovladani(bool(self.titulky))
        if self.prehravac:
            self._zapis_ass()  # titulky musí existovat dřív, než mpv načte video
            self.prehravac.nacti(video)
        else:
            self.obnov_nahled()

    def prepis_zrusen(self):
        """Zrušený přepis: editor zůstane s videem bez titulků, jde otevřít znovu nebo vybrat jiné video."""
        self.nastav_ovladani(False)
        self.btn_jine.setEnabled(True)
        self.akce["otevrit"].setEnabled(True)
        self.nastav_stav(t("stav.prepis_zrusen"), 1.0)

    def prepis_hotov(self, vysledek):
        from jazyky_reci import nazev
        self.slova = vysledek["slova"]
        # pro „Znovu zarovnat výběr“: zvuk 16 kHz (případně jen oddělený hlas), jazyk a posun zvukové stopy
        self.zvuk = vysledek.get("audio")
        self.jazyk_prepisu = vysledek.get("jazyk")
        self.posun_zvuku = vysledek.get("posun_zvuku", 0.0)
        self.zarovnano = vysledek.get("zarovnano", False)
        self.preskupit()
        zprava = t("stav.hotovo", n=len(self.titulky))
        if vysledek.get("rozpoznano"):
            zprava = t("reci.rozpoznano", jazyk=nazev(vysledek["jazyk"])) + " " + zprava
        self.zarizeni_prepisu = vysledek.get("zarizeni", "")
        if self.zarizeni_prepisu:
            zprava += " " + t("stav.prepsano_na", zarizeni=self.zarizeni_prepisu)
        self.nastav_stav(zprava, 1.0)
        self._nastav_neulozeno(True)  # nový přepis = rozpracovaný (zatím neuložený) projekt
        if vysledek.get("varovani"):  # GPU došla paměť → dokončeno na procesoru: upozornění, ne chyba
            self.varuj(vysledek["varovani"])
            self.varovani_timer.start(12000)
        self.nastav_ovladani(True)
        if self.titulky:
            self.tab.selectRow(0)
        self.osa.zobraz_cele()

    def preskupit(self, zapamatovat=False):
        if zapamatovat and self.titulky:
            self.zapamatuj()
        self.titulky = seskup(self.slova, self.styl)
        srovnej(self.titulky, self.info[2])
        self.upraveno = False
        self.naplnit_tabulku()
        self.obnov_nahled()

    # ---------- styl a náhled ----------
    def zmena_stylu(self, klic, hodnota):
        if klic in ("max_slov", "max_znaku") and self.slova:
            if self.upraveno and QMessageBox.question(
                    self, NAZEV, t("dotaz.preskupit")) != QMessageBox.Yes:
                self.panel.nastav(self.styl)
                return
            setattr(self.styl, klic, hodnota)
            self.preskupit(zapamatovat=True)
        else:
            setattr(self.styl, klic, hodnota)
            self.obnov_nahled()
        self.styl.uloz(STYL_SOUBOR)
        self._obnov_tecky()
        self._nastav_neulozeno(True)

    def _nastav_styl(self, novy):
        """Celý nový styl (preset, výchozí, vrácená skupina). Když se mění rozdělení na titulky a jsou
        ruční úpravy, nejdřív se zeptá. Vrátí False, když uživatel odmítl."""
        preskupit = (novy.max_slov, novy.max_znaku) != (self.styl.max_slov, self.styl.max_znaku)
        if preskupit and self.slova and self.upraveno and QMessageBox.question(
                self, NAZEV, t("dotaz.zmena_stylu")) != QMessageBox.Yes:
            return False
        self.styl = novy
        self.panel.nastav(self.styl)
        self.styl.uloz(STYL_SOUBOR)
        if preskupit and self.slova:
            self.preskupit(zapamatovat=True)
        else:
            self.obnov_nahled()
        self._obnov_tecky()
        self._nastav_neulozeno(True)
        return True

    def vychozi_styl(self):
        from presety import VYCHOZI
        if self._nastav_styl(Styl()):
            self.presety.nastav_aktualni(VYCHOZI)
            self._obnov_presety()

    # ---------- presety ----------
    def _nazev_presetu(self, nazev):
        from presety import VYCHOZI
        return t("preset.vychozi") if nazev == VYCHOZI else nazev

    def _obnov_presety(self):
        self.panel.nastav_presety(self.presety.nazvy(), self.presety.aktualni)
        self._obnov_tecky()

    def _obnov_tecky(self):
        """Oranžová tečka v záhlaví skupin, jejichž hodnoty se liší od aktuálního presetu."""
        zmenene = self.presety.zmenene_skupiny(self.styl)
        popisek = t("preset.zmeneno", preset=self._nazev_presetu(self.presety.aktualni))
        for klic, skupina in self.panel.skupiny.items():
            skupina.nastav_zmenu(klic in zmenene, popisek)

    def pouzij_preset(self, nazev):
        if self._nastav_styl(self.presety.pouzij(nazev, self.styl)):
            self.presety.nastav_aktualni(nazev)
            self.stav.setText(t("preset.pouzit", preset=self._nazev_presetu(nazev)))
        self._obnov_presety()  # i po odmítnutí – výběr se vrátí na dosavadní preset

    def uloz_preset(self):
        from presety import VYCHOZI
        aktualni = self.presety.aktualni
        nazev, ok = QInputDialog.getText(self, t("preset.ulozit_titulek"), t("preset.ulozit_popis"),
                                         text="" if aktualni == VYCHOZI else aktualni)
        nazev = nazev.strip()
        if not ok or not nazev:
            return
        if nazev == t("preset.vychozi"):
            self.varuj(t("preset.vychozi_nelze"))
            return
        if nazev != aktualni and self.presety.existuje(nazev) and QMessageBox.question(
                self, NAZEV, t("preset.prepsat", preset=nazev)) != QMessageBox.Yes:
            return
        self.presety.uloz(nazev, self.styl)
        self._obnov_presety()
        self.stav.setText(t("preset.ulozen", preset=nazev))

    def smaz_preset(self):
        from presety import VYCHOZI
        nazev = self.presety.aktualni
        if nazev == VYCHOZI or QMessageBox.question(
                self, NAZEV, t("preset.smazat_dotaz", preset=nazev)) != QMessageBox.Yes:
            return
        self.presety.smaz(nazev)
        self._obnov_presety()
        self.stav.setText(t("preset.smazan", preset=nazev))

    def vrat_skupinu(self, klic):
        """Klik na oranžovou tečku: hodnoty skupiny zpět na aktuální preset (po potvrzení)."""
        preset = self._nazev_presetu(self.presety.aktualni)
        skupina = t(f"styl.skupina.{klic}")
        if QMessageBox.question(self, NAZEV, t("preset.vratit_dotaz", skupina=skupina, preset=preset)) \
                != QMessageBox.Yes:
            return
        if self._nastav_styl(self.presety.vrat_skupinu(self.styl, klic)):
            self.stav.setText(t("preset.vraceno", skupina=skupina, preset=preset))

    # ---------- Undo / Redo ----------
    def snimek_stavu(self):
        """Kopie všeho, co jde vrátit: titulky (se slovy a zámky) a značky."""
        return deepcopy((self.titulky, self.znacky))

    def zapamatuj(self, snimek=None):
        """Uloží stav před úpravou (snimek = stav pořízený dřív, např. na začátku tažení)."""
        self.historie.append(snimek if snimek is not None else self.snimek_stavu())
        del self.historie[:-300]
        self.budoucnost.clear()
        self._obnov_undo_tlacitka()
        self._nastav_neulozeno(True)  # každá vratná úprava = neuložená změna projektu

    def _obnov_undo_tlacitka(self):
        self.akce["zpet"].setEnabled(bool(self.historie))
        self.akce["znovu"].setEnabled(bool(self.budoucnost))

    def zpet(self):
        if self.historie and not self.zaneprazdneno():
            self.budoucnost.append(self.snimek_stavu())
            self._obnov_stav(self.historie.pop())

    def znovu(self):
        if self.budoucnost and not self.zaneprazdneno():
            self.historie.append(self.snimek_stavu())
            self._obnov_stav(self.budoucnost.pop())

    def _obnov_stav(self, stav):
        self.titulky, self.znacky = stav
        self.upraveno = True
        self.naplnit_tabulku()
        self.obnov_nahled()
        self._obnov_undo_tlacitka()
        self._nastav_neulozeno(True)

    def _uprav(self, fn, zprava=None):
        """Jedna vratná úprava: fn() vrátí nový seznam titulků (nebo None, když mění na místě).
        upravy.Chyba = srozumitelné upozornění a nic se nezmění."""
        if not self.video or self.zaneprazdneno():
            return False
        pred = self.snimek_stavu()
        try:
            vysledek = fn()
        except upravy.Chyba as e:
            self.varuj(str(e))
            return False
        if vysledek is not None:
            self.titulky = vysledek
        srovnej(self.titulky, self.info[2])
        self.zapamatuj(pred)
        self.upraveno = True
        self.varovani.hide()
        self.naplnit_tabulku()
        self.obnov_nahled()
        if zprava:
            self.stav.setText(zprava)
        return True

    # ---------- úpravy na časové ose ----------
    def _vybrana(self):
        return self.osa.vybrana_slova()

    def _hlava(self):
        return self.prehravac.t if self.prehravac else self.osa.playhead_t

    def seskupit(self):
        self._uprav(lambda: upravy.seskup(self.titulky, self._vybrana()), t("stav.seskupeno"))

    def rozdelit_skupinu(self):
        self._uprav(lambda: upravy.rozdel_skupinu(self.titulky, self._vybrana()),
                    t("stav.rozdeleno"))

    def rozdelit_u_slova(self):
        vybrana = self._vybrana()
        if len(vybrana) != 1:
            self.varuj(t("varovani.oznac_jedno_rozdelit"))
            return
        self._uprav(lambda: upravy.rozdel_u_slova(self.titulky, vybrana[0]),
                    t("stav.rozdeleno_u", slovo=vybrana[0].text))

    def rozriznout(self):
        self._uprav(lambda: upravy.rozriznout(self.titulky, self._hlava()), t("stav.rozriznuto"))

    def spojit_slova(self):
        self._uprav(lambda: upravy.spoj_slova(self.titulky, self._vybrana()), t("stav.spojeno"))

    def zarovnat_vyber(self):
        """Znovu zarovná označená slova ke zvuku (např. po ruční opravě textu). Běží na pozadí jako přepis;
        výsledek je jedna vratná úprava. Slova zamčených titulků se nemění."""
        if not self.video or self.zaneprazdneno():
            return
        vsechna = sorted((s for tit in self.titulky for s in tit.slova), key=lambda s: s.start)
        zamcena = {id(s) for tit in self.titulky if tit.zamceno for s in tit.slova}
        vybrana = sorted((s for s in self._vybrana() if id(s) not in zamcena), key=lambda s: s.start)
        if not vybrana:
            self.varuj(t("varovani.zarovnat_nic"))
            return
        import zarovnani
        if not zarovnani.ma_model(self.jazyk_prepisu):  # jazyk bez vlastního modelu a MMS není zapnutý
            self.varuj(t("varovani.zarovnat_bez_modelu"))
            return
        pred = self.snimek_stavu()
        posun, video, jazyk, zvuk = self.posun_zvuku, self.video, self.jazyk_prepisu, self.zvuk
        data = [{"text": s.text, "start": s.start - posun, "end": s.end - posun} for s in vybrana]
        # hranice: sousední nevybraná slova se nesmí překrýt
        i0, i1 = vsechna.index(vybrana[0]), vsechna.index(vybrana[-1])
        dno = vsechna[i0 - 1].end if i0 > 0 else 0.0
        strop = vsechna[i1 + 1].start if i1 + 1 < len(vsechna) else self.info[2]

        def prace(progress, log):
            import zarovnani
            from prepis import nacti_zvuk, normalizuj
            audio = zvuk if zvuk is not None else normalizuj(nacti_zvuk(video))
            return zarovnani.zarovnej_vyber(data, audio, jazyk, log)

        def hotovo(vysledek):
            for s, v in zip(vybrana, vysledek):
                s.start = round(min(max(v["start"] + posun, dno), strop - MIN_SLOVO), 3)
                s.end = round(min(max(v["end"] + posun, s.start + MIN_SLOVO), strop), 3)
            for tit in self.titulky:
                if any(s in vybrana for s in tit.slova):
                    tit.slova.sort(key=lambda s: s.start)
            srovnej(self.titulky, self.info[2])
            self.zapamatuj(pred)
            self.upraveno = True
            self.nastav_ovladani(True)
            self.naplnit_tabulku()
            self.osa.vyber(vybrana)
            self.obnov_nahled()
            self.nastav_stav(t("stav.zarovnano", n=len(vybrana)), 1.0)

        self.nastav_ovladani(False)
        self.spust(prace, hotovo, "zarovnani")

    def smazat_slova(self, s_posunem=False):
        vybrana = self._vybrana()
        self._uprav(lambda: upravy.smaz(self.titulky, vybrana, s_posunem),
                    t("stav.smazano_posun" if s_posunem else "stav.smazano", n=len(vybrana)))

    def smazat_s_posunem(self):
        self.smazat_slova(True)

    def smazat_klavesa(self):
        """Delete: v seznamu titulků maže řádky, jinak označená slova na časové ose."""
        if self.tab.hasFocus() and self.vybrane_radky():
            self.smazat()
        elif self._vybrana():
            self.smazat_slova()
        else:
            self.varuj(t("varovani.oznac_smazat"))

    def kopirovat(self):
        try:
            self.schranka = upravy.kopiruj(self.titulky, self._vybrana())
        except upravy.Chyba as e:
            self.varuj(str(e))
            return False
        self.stav.setText(t("stav.zkopirovano", n=sum(len(s) for s in self.schranka)))
        return True

    def vyjmout(self):
        if self.kopirovat():
            self.smazat_slova()

    def vlozit(self):
        vlozena = []

        def proved():
            nove, vl = upravy.vloz(self.titulky, self.schranka, self._hlava(), self.info[2])
            vlozena.extend(vl)
            return nove
        if self._uprav(proved, t("stav.vlozeno", n=sum(len(s) for s in self.schranka))):
            self.osa.vyber(vlozena)

    def vlozit_slovo(self):
        vlozena = []

        def proved():
            delka = upravy.volne_misto(self.titulky, self._hlava(), self.info[2])
            nove, vl = upravy.vloz(self.titulky, [[(t("text.nove_slovo"), 0.0, delka)]], self._hlava(), self.info[2])
            vlozena.extend(vl)
            return nove
        if self._uprav(proved, t("stav.nove_slovo")):
            self.osa.vyber(vlozena)
            self.osa.otevri_editor(vlozena[0], self._potvrd_text)

    def uprav_vybrane_slovo(self):
        vybrana = self._vybrana()
        if len(vybrana) != 1:
            self.varuj(t("varovani.oznac_jedno_upravit"))
            return
        self.uprav_text_slova(vybrana[0])

    def uprav_text_slova(self, slovo):
        if upravy.titulek_slova(self.titulky, slovo).zamceno:
            self.varuj(t("varovani.zamceno"))
            return
        self.osa.otevri_editor(slovo, self._potvrd_text)

    def _potvrd_text(self, slovo, text):
        if not text:  # prázdný text = smazat slovo
            self._uprav(lambda: upravy.smaz(self.titulky, [slovo]), t("stav.slovo_smazano"))
            return

        def proved():
            slovo.text = text
            prepocitej_text(upravy.titulek_slova(self.titulky, slovo))
        self._uprav(proved, t("stav.text_zmenen", text=text))

    def prepni_zamek(self):
        vysledek = []
        self._uprav(lambda: vysledek.append(upravy.prepni_zamek(self.titulky, self._vybrana())))
        if vysledek:
            zamceno, n = vysledek[0]
            self.stav.setText(t("stav.zamceno" if zamceno else "stav.odemceno", n=n))

    # ---------- značky ----------
    def pridat_znacku(self):
        cas = round(self._hlava(), 3)

        def proved():
            self.znacky.append(Znacka(cas))
            self.znacky.sort(key=lambda z: z.t)
        self._uprav(proved, t("stav.znacka_pridana"))

    def uprav_znacku(self, znacka):
        text, ok = QInputDialog.getText(self, t("znacka.titulek"), t("znacka.poznamka", cas=fmt_cas(znacka.t)),
                                        text=znacka.text)
        if ok:
            def proved():
                next(z for z in self.znacky if z.t == znacka.t).text = text.strip()
            self._uprav(proved, t("stav.znacka_ulozena"))

    def smazat_znacku(self, znacka):
        def proved():
            self.znacky = [z for z in self.znacky if z.t != znacka.t]
        self._uprav(proved, t("stav.znacka_smazana"))

    # ---------- kontextové menu ----------
    def kontextove_menu(self, pozice, druh, obj):
        m = QMenu(self)
        if druh == "znacka":
            m.addAction(t("kontext.skocit_na_znacku")).triggered.connect(lambda: self.skoc_osa(obj.t))
            m.addAction(t("kontext.upravit_poznamku")).triggered.connect(lambda: self.uprav_znacku(obj))
            m.addAction(t("kontext.smazat_znacku")).triggered.connect(lambda: self.smazat_znacku(obj))
        elif druh == "slovo":
            a = self.akce
            zamceno = upravy.titulek_slova(self.titulky, obj).zamceno
            for k in ("seskupit", "rozdelit", "rozdelit_u", None, "rozriznout", "spojit", "upravit", "zarovnat_vyber", None,
                      "kopirovat", "vyjmout", "vlozit", "smazat", "smazat_posun", None, "prehrat_vyber"):
                m.addSeparator() if k is None else m.addAction(a[k])
            m.addAction(t("kontext.smycka_z_vyberu")).triggered.connect(self.smycka_z_vyberu)
            m.addAction(a["na_vyber"])
            m.addSeparator()
            z = m.addAction(t("kontext.odemknout" if zamceno else "kontext.zamknout"))
            z.setShortcut(a["zamek"].shortcut())
            z.triggered.connect(self.prepni_zamek)
            m.addAction(a["znacka"])
        else:
            for k in ("vlozit", "nove_slovo", "znacka", None, "na_sirku"):
                m.addSeparator() if k is None else m.addAction(self.akce[k])
        m.exec(pozice)

    # ---------- přehrávání ----------
    def _hrac(self):
        if not self.prehravac or not self.video:
            return None
        return self.prehravac

    def prehrat(self):
        if self._hrac():
            self._konec_vyberu = None
            self.prehravac.prepni()

    def jkl_j(self):
        if self._hrac():
            self.prehravac.jkl("J")

    def jkl_k(self):
        if self._hrac():
            self._konec_vyberu = None
            self.prehravac.jkl("K")

    def jkl_l(self):
        if self._hrac():
            self.prehravac.jkl("L")

    def snimek_zpet(self):
        if self._hrac():
            self.prehravac.snimek(-1)

    def snimek_vpred(self):
        if self._hrac():
            self.prehravac.snimek(1)

    def sekunda_zpet(self):
        if self._hrac():
            self.prehravac.posun(-1)

    def sekunda_vpred(self):
        if self._hrac():
            self.prehravac.posun(1)

    def na_zacatek(self):
        if self._hrac():
            self.prehravac.skoc(0)

    def na_konec(self):
        if self._hrac():
            self.prehravac.skoc(self.prehravac.delka)

    def _skoc_na_titulek(self, i):
        self.tab.selectRow(i)
        self.skoc_osa(self.titulky[i].start)

    def predchozi_titulek(self):
        t = self._hlava()
        i = next((i for i in range(len(self.titulky) - 1, -1, -1) if self.titulky[i].start < t - 0.02), None)
        if i is not None:
            self._skoc_na_titulek(i)

    def dalsi_titulek(self):
        t = self._hlava()
        i = next((i for i, x in enumerate(self.titulky) if x.start > t + 0.02), None)
        if i is not None:
            self._skoc_na_titulek(i)

    def _rozsah_vyberu(self):
        """(od, do) označených slov na ose, jinak označených řádků v seznamu, jinak None."""
        vybrana = self._vybrana()
        if vybrana:
            return min(s.start for s in vybrana), max(s.end for s in vybrana)
        radky = self.vybrane_radky()
        if radky:
            return self.titulky[radky[0]].start, self.titulky[radky[-1]].end
        return None

    def prehrat_vyber(self):
        rozsah = self._rozsah_vyberu()
        if not self._hrac() or not rozsah:
            self.varuj(t("varovani.oznac_prehrat"))
            return
        self.prehravac._zastav_jkl()
        self.prehravac.skoc(rozsah[0])
        self._konec_vyberu = rozsah[1]
        self.prehravac.mpv.pause = False

    # ---------- smyčka ----------
    def _zapni_smycku(self, od, do):
        self.osa.nastav_smycku(od, do, True)
        if self.prehravac:
            self.prehravac.nastav_smycku(od, do)
            if not od <= self.prehravac.t <= do:
                self.prehravac.skoc(od)
        self.akce["smycka"].blockSignals(True)
        self.akce["smycka"].setChecked(True)
        self.akce["smycka"].blockSignals(False)
        self.stav.setText(t("stav.smycka", od=fmt_cas(od), do=fmt_cas(do)))

    def prepni_smycku(self, zapnout):
        if not zapnout:
            if self.osa.smycka:
                self.osa.nastav_smycku(*self.osa.smycka, zapnuta=False)
            if self.prehravac:
                self.prehravac.nastav_smycku(None)
            return
        rozsah = self.osa.smycka or self._rozsah_vyberu()
        if not rozsah:
            hlava = self._hlava()
            tit = next((x for x in self.titulky if x.start <= hlava < x.end), None)
            rozsah = (tit.start, tit.end) if tit else None
        if not rozsah:
            self.varuj(t("varovani.smycka"))
            self.akce["smycka"].blockSignals(True)
            self.akce["smycka"].setChecked(False)
            self.akce["smycka"].blockSignals(False)
            return
        self._zapni_smycku(*rozsah)

    def smycka_z_vyberu(self):
        rozsah = self._rozsah_vyberu()
        if rozsah:
            self._zapni_smycku(*rozsah)

    def _smycka_z_meritka(self):
        if self.osa.smycka:
            self._zapni_smycku(*self.osa.smycka)
        else:
            self.prepni_smycku(False)
            self.akce["smycka"].blockSignals(True)
            self.akce["smycka"].setChecked(False)
            self.akce["smycka"].blockSignals(False)

    # ---------- zobrazení ----------
    def na_sirku(self):
        self.osa.zobraz_cele()

    def na_vyber(self):
        rozsah = self._rozsah_vyberu()
        if rozsah:
            self.osa.zoom_na(*rozsah)
        else:
            self.varuj(t("varovani.oznac_zoom"))

    def priblizit(self):
        self.osa.zoom(self.osa.pps * 1.5)

    def oddalit(self):
        self.osa.zoom(self.osa.pps / 1.5)

    def prepni_vysku(self, velka):
        self.osa.nastav_vysku_stopy(velka)  # sekce časové osy se sama přizpůsobí výšce stopy

    def prepni_sledovani(self, zapnuto):
        self.osa.sledovat = zapnuto

    def prepni_prichytavani(self, zapnuto):
        self.osa.prichytavat = zapnuto
        self.stav.setText(t("stav.prichytavani_zap" if zapnuto else "stav.prichytavani_vyp"))

    # ---------- časová osa ----------
    def skoc_osa(self, t):
        if self.prehravac:
            self.prehravac.skoc(t)
        else:
            self.osa.nastav_playhead(t)

    def konec_tahu(self, zmeneno):
        if zmeneno and self._pred_tahem is not None:
            self.zapamatuj(self._pred_tahem)
            self.upraveno = True
        self._pred_tahem = None

    def casy_zmeneny(self):
        """Časy se změnily na ose – obnoví seznam a náhled."""
        for zac, kon in self.pole:
            zac.obnov()
            kon.obnov()
        self._obnov_prekryvy()
        self.obnov_nahled()

    def obnov_nahled(self):
        """Každá změna textu, času nebo stylu – překreslí titulky v přehrávači/náhledu."""
        if self.video:
            self.nahled_timer.start()

    def _zapis_ass(self):
        W, H, delka = self.info
        titulky = self.titulky or [Titulek(0, max(delka, 1), t("text.ukazka"))]
        self.ass_soubor.parent.mkdir(exist_ok=True)
        self.ass_soubor.write_text(vytvor_ass(titulky, self.styl, W, H), encoding="utf-8-sig")

    def _vykresli_nahled(self):
        if self.prehravac:
            self._zapis_ass()
            self.prehravac.obnov_titulky()
            return
        # záloha bez libmpv: statický snímek přes ffmpeg
        if self.nahled_uloha is not None and self.nahled_uloha.isRunning():
            self.nahled_ceka = True
            return
        from nahled import vykresli
        r = self.tab.currentRow() if 0 <= self.tab.currentRow() < len(self.titulky) else 0
        cas, text = ((self.titulky[r].start + self.titulky[r].end) / 2, self.titulky[r].text) \
            if self.titulky else (self.info[2] / 2, t("text.ukazka"))
        video, styl = self.video, replace(self.styl)
        W, H, delka = self.info
        self.nahled_uloha = Uloha(lambda p, l: vykresli(video, cas, text, styl, W, H, delka))
        self.nahled_uloha.hotovo.connect(self.nahled.nastav)
        self.nahled_uloha.chyba.connect(lambda msg: self.stav.setText(t("stav.nahled_selhal", zprava=msg[-300:])))
        self.nahled_uloha.finished.connect(self._nahled_dokoncen)
        self.nahled_uloha.start()

    def _nahled_dokoncen(self):
        if self.nahled_ceka:
            self.nahled_ceka = False
            self._vykresli_nahled()

    # ---------- přehrávač a časování ----------
    def cas_videa(self, t):
        hraje = bool(self.prehravac and self.prehravac.hraje())
        self.osa.nastav_playhead(t, hraje=hraje)
        if self._konec_vyberu is not None and t >= self._konec_vyberu - 0.02:  # „Přehrát výběr“ došlo na konec
            self._konec_vyberu = None
            if self.prehravac:
                self.prehravac.mpv.pause = True
        idx = next((i for i, x in enumerate(self.titulky) if x.start <= t < x.end), -1)
        if idx != self.aktivni:
            self._zvyrazni(self.aktivni, False)
            self._zvyrazni(idx, True)
            self.aktivni = idx
            if idx >= 0 and not self.prehravac.mpv.pause:
                self.tab.scrollToItem(self.tab.item(idx, 2))

    def _zvyrazni(self, r, ano):
        if not 0 <= r < len(self.titulky):
            return
        item = self.tab.item(r, 2)
        self._plnim = True
        if ano:  # oranžový proužek vlevo a oranžové časy; modrá zůstává jen výběru
            self.tab.aktivni = r
        elif self.tab.aktivni == r:
            self.tab.aktivni = -1
        self.tab.viewport().update()
        f = item.font()
        f.setBold(ano)
        item.setFont(f)
        self._plnim = False
        for p in self.pole[r]:
            p.nastav_aktivni(ano)

    def klik_na_radek(self, r, c):
        if self.prehravac and 0 <= r < len(self.titulky):
            t = self.titulky[r]
            # na samém začátku je titulek kvůli prolínání ještě neviditelný – skočíme za náběh
            self.prehravac.skoc(t.start + min(self.styl.fade_in / 1000, (t.end - t.start) / 2))
        elif not self.prehravac:
            self.obnov_nahled()

    def vyber_titulek(self, t):
        i = self._index(t)
        if i >= 0 and self.tab.currentRow() != i:
            self.tab.selectRow(i)

    def _index(self, t):
        return next((i for i, x in enumerate(self.titulky) if x is t), -1)

    def varuj(self, text):
        self.varovani.setText("⚠  " + text)
        self.varovani.show()
        self.varovani_timer.start()

    def zmen_cas(self, tit, klic, val):
        """Nastaví začátek/konec titulku. Při kolizi zobrazí upozornění a vrátí False."""
        i = self._index(tit)
        if i < 0:
            return False
        if tit.zamceno:
            return self._kolize(t("kolize.zamceno", i=i + 1))
        val = round(max(val, 0.0), 2)
        if val == round(getattr(tit, klic), 2):
            return True
        delka = self.info[2] if self.info else 0
        pred = self.titulky[i - 1] if i > 0 else None
        po = self.titulky[i + 1] if i + 1 < len(self.titulky) else None
        prvni = tit.slova[0] if tit.slova else None
        posledni = tit.slova[-1] if tit.slova else None
        if klic == "start":
            if val > tit.end - MIN_DELKA:
                return self._kolize(t("kolize.zacatek", i=i + 1, cas=fmt_cas(tit.end)))
            if pred and val < pred.end - 1e-6:
                return self._kolize(t("kolize.predchozi", i=i + 1, cas=fmt_cas(pred.end)))
            if prvni and val > prvni.end - MIN_SLOVO:
                return self._kolize(t("kolize.prvni_slovo", slovo=prvni.text, cas=fmt_cas(prvni.end)))
        else:
            if posledni and val < posledni.start + MIN_SLOVO:
                return self._kolize(t("kolize.posledni_slovo", slovo=posledni.text, cas=fmt_cas(posledni.start)))
            if val < tit.start + MIN_DELKA:
                return self._kolize(t("kolize.konec", i=i + 1, cas=fmt_cas(tit.start)))
            if po and val > po.start + 1e-6:
                return self._kolize(t("kolize.nasledujici", i=i + 1, cas=fmt_cas(po.start)))
            if delka and val > delka + 0.05:
                return self._kolize(t("kolize.konec_videa", cas=fmt_cas(delka)))
        self.zapamatuj()
        setattr(tit, klic, val)
        # okraj titulku táhne i okraj krajního slova (na ose se posune box)
        if klic == "start" and prvni:
            prvni.start = val
        elif klic == "end" and posledni and val < posledni.end:
            posledni.end = val
        self.upraveno = True
        self.varovani.hide()
        self.pole[i][0 if klic == "start" else 1].obnov()
        self._obnov_prekryvy()
        self.osa.obnov()
        self.obnov_nahled()
        return True

    def _kolize(self, text):
        self.varuj(text)
        return False

    def nastav_aktualni(self, klic):
        r = self.tab.currentRow()
        if not 0 <= r < len(self.titulky):
            self.varuj(t("varovani.vyber_titulek"))
            return
        self.zmen_cas(self.titulky[r], klic, self.prehravac.t)

    # ---------- export ----------
    def exportovat(self):
        chyby = [i + 1 for i, t in enumerate(self.titulky) if t.end <= t.start]
        prekryvy = [i + 1 for i in range(len(self.titulky) - 1)
                    if self.titulky[i].end > self.titulky[i + 1].start + 1e-6]
        if chyby or prekryvy:
            zprava = []
            if chyby:
                zprava.append(t("export.konec_pred_zacatkem", seznam=", ".join(map(str, chyby[:10]))))
            if prekryvy:
                zprava.append(t("export.prekryv", seznam=", ".join(map(str, prekryvy[:10]))))
            QMessageBox.warning(self, NAZEV, t("export.oprav") + "\n\n" + "\n".join(zprava))
            return
        import export as ex
        from export_panel import ExportPanel
        if self.prehravac:
            self.prehravac.mpv.pause = True
        self.notifikace.skryj()
        # panel s možnostmi exportu; úsek = smyčka, jinak výběr na časové ose
        vybrana = self._vybrana()
        useky = {"smycka": self.osa.smycka if self.osa.smycka_zapnuta and self.osa.smycka else None,
                 "vyber": (min(s.start for s in vybrana), max(s.end for s in vybrana)) if vybrana else None}
        panel = ExportPanel(self, self.video, self.info, self.fps, useky, self._volby_exportu())
        prijato = panel.exec() == QDialog.Accepted
        panel.deleteLater()
        if not prijato:
            return
        volby, vystup, rozsah = panel.volby, panel.vystup, panel.rozsah
        if ex.je_stejny_soubor(vystup, self.video):  # zdrojové video se nikdy nepřepisuje
            QMessageBox.warning(self, NAZEV, t("export.prepis_puvodni"))
            return
        self._uloz_volby_exportu(volby)
        self._otevrit_po_exportu = volby.otevrit_slozku
        W, H, delka = self.info
        od, do = rozsah or (0.0, delka)
        titulky = vyrez(self.titulky, od, do) if rozsah else self.titulky

        if volby.co == "titulky":  # jen soubor s titulky – hotovo hned, bez překrytí
            try:
                if volby.format_titulku == "srt":
                    obsah = vytvor_srt(titulky, self.styl)
                elif volby.format_titulku == "vtt":
                    obsah = vytvor_vtt(titulky, self.styl)
                else:
                    obsah = vytvor_ass(titulky, self.styl, W, H)
                vystup.write_text(obsah, encoding="utf-8-sig" if volby.format_titulku == "ass" else "utf-8")
            except OSError as e:
                self.selhalo("export", str(e))
                return
            self.export_hotov(vystup)
            return

        # místo na disku: odhad velikosti + 15 % + 100 MB – raději varovat předem než skončit s půlkou souboru
        import shutil
        potreba = (ex.odhad_velikosti(volby, W, H, self.fps, do - od) or 0) * 1.15 + 100 * 2**20
        volno = shutil.disk_usage(vystup.parent).free
        if volno < potreba:
            QMessageBox.warning(self, NAZEV, t("chyba.misto_export", potreba=f"{potreba / 1e9:.1f}",
                                                volno=f"{volno / 1e9:.1f}", slozka=str(vystup.parent)))
            return
        ow, oh, _, _ = ex.rozmery(volby, W, H)
        ass = vytvor_ass(titulky, self.styl, ow, oh)  # titulky v rozlišení výstupu – ostré i po zmenšení
        self.export = ex.Export()
        exp, video, info, fps = self.export, self.video, self.info, self.fps

        def prace(progress, log):
            progress(0.0, "export")
            log(t("export.vypaluji_kodek", kodek=ex.kodek(volby)))
            exp.vypal(video, ass, vystup, do - od, progress, volby=volby, info=info, fps_zdroj=fps, rozsah=rozsah)
            return vystup

        self.nastav_ovladani(False)
        self.spust(prace, self.export_hotov, "export", prekryti=True, hotovo_po_animaci=True,
                   zruseno=self.export_zrusen)

    def _volby_exportu(self):
        """Poslední použité volby exportu (aplikace si je pamatuje)."""
        import json
        from export import Volby
        try:
            return Volby.z_dict(json.loads(i18n.nastaveni().value("export/volby", "{}")))
        except (TypeError, ValueError):
            return Volby()

    def _uloz_volby_exportu(self, volby):
        import json
        s = i18n.nastaveni()
        s.setValue("export/volby", json.dumps(volby.jako_dict(), ensure_ascii=False))
        s.sync()

    def export_hotov(self, vystup):
        self.nastav_ovladani(True)
        self.nastav_stav(t("export.ulozeno", cesta=vystup), 1.0)
        self.notifikace.ukaz(t("notifikace.export"), vystup.name, t("notifikace.otevrit_slozku"),
                             lambda: otevri_slozku(vystup))
        if getattr(self, "_otevrit_po_exportu", False):
            otevri_slozku(vystup)
        self._po_exportu()

    def export_zrusen(self):
        self.nastav_ovladani(True)
        self.nastav_stav(t("stav.export_zrusen"), 1.0)

    def zrusit_export(self):
        if self.export:
            self.export.zrus()

    def zrus_ulohu(self):
        """Tlačítko Zrušit v překrytí (po potvrzení) nebo zavření okna: ukončí běžící práci co nejdřív."""
        if self.uloha is not None:
            self.uloha.zrus()
        self.zrusit_export()

    # ---------- společné ----------
    def spust(self, fn, hotovo, nazev, prekryti=False, hotovo_po_animaci=False, zruseno=None):
        """Spustí fn ve vlákně. prekryti=True = velká obrazovka zpracování s cupcakem (přepis, export),
        jinak jen malý cupcake a tenká linka průběhu u stavového řádku. hotovo_po_animaci = hotovo() až po
        rozplynutí překrytí (export ukazuje zprávu); jinak hned, ať se pod překrytím připraví editor."""
        self.uloha = Uloha(fn)
        self.uloha.progress.connect(lambda p: self.bar.setValue(int(p * 1000)))
        self.uloha.log.connect(lambda t: self.stav.setText(t))
        self.uloha.log.connect(logging.getLogger("kupcake").info)  # průběh práce i do logu
        self.uloha.chyba.connect(lambda msg: (self.prekryti.zavri(), self.bar.show(), self.selhalo(nazev, msg)))
        self.uloha.zruseno.connect(lambda: (self.prekryti.zavri(), self.bar.show(),
                                            zruseno() if zruseno else self.selhalo(nazev, t("prekryti.rusim"))))
        self.uloha.finished.connect(self.nacitani.hide)
        self.uloha.finished.connect(lambda: self.tecka_loga.pulzuj(False))
        self.tecka_loga.pulzuj(True)
        self.bar.setValue(0)
        if prekryti:
            self.bar.hide()  # záložní ukazatel – během překrytí ho nahrazuje cupcake
            self.uloha.progress.connect(self.prekryti.nastav_prubeh)
            self.uloha.faze.connect(lambda k: self.prekryti.nastav_fazi(t(f"faze.{k}")))

            def dokonceno(vysledek):
                self.bar.show()
                if hotovo_po_animaci:
                    self.prekryti.dokonci(lambda: hotovo(vysledek))
                else:
                    hotovo(vysledek)
                    self.prekryti.dokonci()
            self.uloha.hotovo.connect(dokonceno)
            self.prekryti.spust()
        else:
            self.uloha.hotovo.connect(hotovo)
            self.nacitani.show()
        self.uloha.start()

    def selhalo(self, nazev, msg):
        self.btn_zrusit.hide()
        self.nastav_ovladani(bool(self.titulky))
        self.btn_jine.setEnabled(True)
        self.nastav_stav(t(f"stav.{nazev}_selhal"), 0)
        import logy
        detail = getattr(self.uloha, "detail", "") if self.uloha is not None else ""
        logy.ukaz_chybu(self, msg, detail, uvod=t(f"stav.{nazev}_selhal") + " " + t("chyba.bezi_dal"))

    def nastav_stav(self, text, p):
        self.stav.setText(text)
        # hotovo = linka zůstane neutrální (žlutá jen během práce, ať nesvítí přes celé okno)
        self.bar.setValue(0 if p >= 1 else int(p * 1000))

    def nastav_ovladani(self, ano):
        for b in (self.btn_pridat, self.btn_smazat, self.btn_sloucit, self.btn_export, self.btn_jine,
                  self.btn_zac_ted, self.btn_kon_ted):
            if b:
                b.setEnabled(ano)
        for k in self.UPRAVY:  # během přepisu/exportu jen přehrávání a zobrazení
            self.akce[k].setEnabled(ano)
        self.tab.setEnabled(ano)

    # ---------- editor ----------
    def naplnit_tabulku(self):
        self._plnim = True
        self.aktivni = -1
        self.tab.setRowCount(len(self.titulky))
        self.pole = []
        for r, tit in enumerate(self.titulky):
            dvojice = (CasPole(self, tit, "start"), CasPole(self, tit, "end"))
            for c, p in enumerate(dvojice):
                self.tab.setItem(r, c, QTableWidgetItem())
                self.tab.item(r, c).setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                self.tab.setCellWidget(r, c, p)
            self.pole.append(dvojice)
            bunka = QTableWidgetItem(tit.text)
            if tit.zamceno:
                bunka.setIcon(theme.ikona("zamek.svg", theme.TEXT_2))
                bunka.setToolTip(t("tooltip.zamceny"))
            self.tab.setItem(r, 2, bunka)
        self._plnim = False
        self.osa.nastav(self.titulky, self.info[2] if self.info else 0.0, self.znacky)
        self._obnov_prekryvy()
        if self.prehravac:
            self.cas_videa(self.prehravac.t)

    def _obnov_prekryvy(self):
        """Titulky, jejichž čas zasahuje do sousedního – oranžová ikonka upozornění v seznamu."""
        prekryvy = {}
        for i in range(len(self.titulky) - 1):
            a, b = self.titulky[i], self.titulky[i + 1]
            if a.end > b.start + 1e-6:
                prekryvy.setdefault(i, []).append(t("tooltip.prekryv_dalsi", i=i + 2, cas=fmt_cas(b.start)))
                prekryvy.setdefault(i + 1, []).append(t("tooltip.prekryv_predchozi", i=i + 1, cas=fmt_cas(a.end)))
        self.tab.nastav_prekryvy({r: "\n".join(texty) for r, texty in prekryvy.items()})

    def zmena_bunky(self, item):
        if self._plnim or item.column() != 2:
            return
        tit = self.titulky[item.row()]
        if item.text() != tit.text and tit.zamceno:
            self._plnim = True
            item.setText(tit.text)
            self._plnim = False
            self.varuj(t("kolize.zamceno", i=item.row() + 1))
            return
        if item.text() != tit.text:
            self.zapamatuj()
            nastav_text(tit, item.text())
            self.upraveno = True
            self.osa.nastav(self.titulky, self.info[2])
            self.obnov_nahled()

    def vybrane_radky(self):
        return sorted({i.row() for i in self.tab.selectedIndexes()})

    def pridat(self):
        radky = self.vybrane_radky()
        i = radky[-1] if radky else len(self.titulky) - 1
        start = self.titulky[i].end if i >= 0 else 0.0
        konec = start + 1.0
        if i + 1 < len(self.titulky):
            konec = min(konec, self.titulky[i + 1].start)
        if self.info:
            konec = min(konec, self.info[2])
        if konec - start < MIN_DELKA:
            self.varuj(t("varovani.neni_misto"))
            return
        self.zapamatuj()
        konec = round(konec, 2)
        novy = t("text.novy_titulek")
        self.titulky.insert(i + 1, Titulek(start, konec, novy, rozdel_slova(novy, start, konec)))
        self.upraveno = True
        self.naplnit_tabulku()
        self.tab.selectRow(i + 1)
        self.tab.editItem(self.tab.item(i + 1, 2))
        self.obnov_nahled()

    def _zamcene_radky(self, radky):
        zamcene = [r + 1 for r in radky if self.titulky[r].zamceno]
        if zamcene:
            self.varuj(t("varovani.zamcene_radky", seznam=", ".join(map(str, zamcene))))
        return bool(zamcene)

    def smazat(self):
        radky = self.vybrane_radky()
        if self._zamcene_radky(radky):
            return
        if radky:
            self.zapamatuj()
            self.upraveno = True
        for r in reversed(radky):
            del self.titulky[r]
        self.naplnit_tabulku()
        self.obnov_nahled()

    def sloucit(self):
        radky = self.vybrane_radky()
        if not radky or radky[0] + 1 >= len(self.titulky):
            return
        i = radky[0]
        if self._zamcene_radky([i, i + 1]):
            return
        self.zapamatuj()
        a, b = self.titulky[i], self.titulky.pop(i + 1)
        a.text = f"{a.text} {b.text}"
        a.slova += b.slova
        a.end = max(a.end, b.end)
        self.upraveno = True
        self.naplnit_tabulku()
        self.tab.selectRow(i)
        self.obnov_nahled()

    def closeEvent(self, e):
        if self.zaneprazdneno():
            if QMessageBox.question(self, NAZEV, t("dotaz.zavrit")) != QMessageBox.Yes:
                e.ignore()
                return
            self.zrus_ulohu()
            self.uloha.wait(3000)
            self.prekryti.zavri()
        elif not self._neulozene_ok():  # neuložené změny: uložit / zahodit / zůstat
            e.ignore()
            return
        import projekt
        projekt.AUTOSAVE.unlink(missing_ok=True)  # řádné zavření – obnova po pádu není potřeba
        for u in (self.nahled_uloha, self.vlna_uloha):
            if u is not None:
                u.wait(5000)
        if self.prehravac:
            self.prehravac.ukonci()
        self.uloz_rozlozeni()
        e.accept()


def tmavy_motiv(app):
    theme.pouzij(app)  # paleta, písma, stylesheet a animace – vše v theme.py
    kolecko.zapni(app)  # kolečko mění hodnotu pole až po kliknutí do něj, jinak posouvá panel
    i18n.nacti_ulozeny()  # jazyk rozhraní (poprvé podle Windows) + překlady dialogů Qt
    for f in sorted(FONTY_DIR.glob("*.[ot]tf")):
        QFontDatabase.addApplicationFont(str(f))


def main():
    # vlastní AppUserModelID – jinak Windows seskupí okno pod python.exe a ukáže jeho ikonu
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
        # mutex po dobu běhu – instalátor/odinstalátor podle něj pozná, že má aplikaci nejdřív zavřít
        _mutex = ctypes.windll.kernel32.CreateMutexW(None, False, MUTEX)  # noqa: F841
    cesty.priprav()
    import logy
    logy.nastav()  # log do %LOCALAPPDATA%\KupcakeStudio\logs + zachytávání nečekaných chyb
    app = QApplication(sys.argv)
    app.setApplicationName(NAZEV)
    app.setApplicationVersion(VERZE)
    app.setWindowIcon(QIcon(str(IKONA)))
    if len(sys.argv) == 4 and sys.argv[1] == "--selftest":  # kontrola sestaveného exe, viz selftest.py
        import selftest
        test = selftest.spust(sys.modules[__name__], sys.argv[2], sys.argv[3])  # noqa: F841
        theme.pouzij(app)
        for f in sorted(FONTY_DIR.glob("*.[ot]tf")):
            QFontDatabase.addApplicationFont(str(f))
        sys.exit(app.exec())
    tmavy_motiv(app)
    # úvodní splash hned po spuštění; hlavní okno se mezitím postaví (až doběhne fade-in, ať animace nezadrhne)
    # a těžké knihovny pro přepis (faster-whisper, CUDA) se načtou na pozadí – po splashi se už na nic nečeká
    import threading
    from splash import PROLINANI_MS, Splash
    threading.Thread(target=lambda: __import__("prepis"), daemon=True).start()
    stav = {"okno": None}

    def postav():
        if stav["okno"] is None:
            stav["okno"] = Okno()
            logy.zapni_dialogy(stav["okno"])  # nečekaná chyba = srozumitelná hláška, aplikace běží dál

    def otevri_okno():
        postav()
        okno = stav["okno"]
        okno.zobraz()
        okno.raise_()
        okno.activateWindow()
        QTimer.singleShot(200, lambda: po_zobrazeni(okno))

    def po_zobrazeni(okno):
        if not okno.uvitani():  # první spuštění bety: upozornění a souhlas; bez souhlasu konec
            okno.close()
            return
        if len(sys.argv) > 1 and Path(sys.argv[1]).is_file():
            okno.otevri_cestu(Path(sys.argv[1]), zeptat=False)  # video nebo projekt (dvojklik na .kupcake)
        else:
            okno.nabidni_obnovu()  # minule spadla? nabídnout obnovu projektu
        QTimer.singleShot(5000, okno.zkontroluj_aktualizace)  # na pozadí, nejvýš 1× za den

    splash = Splash()
    splash.hotovo.connect(otevri_okno)
    splash.spust()
    QTimer.singleShot(PROLINANI_MS + 60, postav)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
