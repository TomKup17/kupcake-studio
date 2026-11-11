# kupcake.studio – Copyright (C) 2026 Tomáš Kupec
# SPDX-License-Identifier: GPL-3.0-only
"""Úvodní okno při prvním spuštění (beta): upozornění, odkazy na licenci a podmínky použití a souhlas „Rozumím“.

Překryvná karta ve stylu aplikace (ztlumené pozadí, cupcake, štítek BETA). Tlačítko Začít se aktivuje až po
zaškrtnutí „Rozumím“; potvrzení se uloží do nastavení. Znovu se okno ukáže jen při první spuštění nové hlavní
verze – klíč je hlavní číslo verze a příznak předběžné verze (1.0.0-beta.1 a beta.2 → „1-beta“, 1.0.0 → „1“).
Zavření bez potvrzení (Alt+F4) aplikaci ukončí – bez souhlasu se nepokračuje.
"""
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (QCheckBox, QDialog, QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy,
                               QStackedWidget, QTextBrowser, QVBoxLayout, QWidget)

import i18n
import kupcake
import links
import theme
from i18n import t
from version import VERZE

KLIC = "souhlas/verze"


def klic_verze(verze=VERZE):
    hlavni = verze.split(".")[0]
    return f"{hlavni}-beta" if "-" in verze else hlavni


def je_potreba(nastaveni=None):
    s = nastaveni or i18n.nastaveni()
    return str(s.value(KLIC, "") or "") != klic_verze()


def uloz_souhlas(nastaveni=None):
    s = nastaveni or i18n.nastaveni()
    s.setValue(KLIC, klic_verze())
    s.setValue("souhlas/plna_verze", VERZE)
    s.sync()


class Uvitani(QDialog):
    def __init__(self, okno):
        super().__init__(okno, Qt.Dialog | Qt.FramelessWindowHint)
        self.okno = okno
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowModality(Qt.ApplicationModal)
        vnejsi = QVBoxLayout(self)
        vnejsi.setContentsMargins(24, 24, 24, 24)
        self.karta = QFrame()
        self.karta.setObjectName("exportKarta")
        self.karta.setFixedWidth(560)
        vnejsi.addWidget(self.karta, 0, Qt.AlignCenter)
        lay = QVBoxLayout(self.karta)
        lay.setContentsMargins(0, 0, 0, 0)
        self.stranky = QStackedWidget()
        self.stranky.addWidget(self._hlavni())
        self.stranky.addWidget(self._licence())
        self.stranky.currentChanged.connect(self._stranka)
        lay.addWidget(self.stranky)
        self._stranka(0)
        self.setGeometry(okno.geometry())
        okno.installEventFilter(self)

    def _hlavni(self):
        s = QWidget()
        lay = QVBoxLayout(s)
        lay.setContentsMargins(32, 24, 32, 22)
        lay.setSpacing(8)
        lay.addWidget(kupcake.CupcakeAnimace(96), 0, Qt.AlignHCenter)
        radek = QHBoxLayout()
        radek.addStretch(1)
        logo = QLabel(theme.logo_html(20, tecka_barva=None))
        logo.setTextFormat(Qt.RichText)
        radek.addWidget(logo)
        if "-" in VERZE:
            beta = QLabel("BETA")
            beta.setObjectName("betaStitek")
            beta.setFont(theme.pismo_mono(7.5))
            radek.addWidget(beta, 0, Qt.AlignVCenter)
        radek.addStretch(1)
        lay.addLayout(radek)
        lay.addSpacing(6)
        nadpis = QLabel(t("uvitani.nadpis"))
        nadpis.setObjectName("notifikaceNadpis")
        nadpis.setAlignment(Qt.AlignCenter)
        lay.addWidget(nadpis)
        text = QLabel(t("uvitani.text"))
        text.setWordWrap(True)
        text.setAlignment(Qt.AlignCenter)
        lay.addWidget(text)
        lay.addSpacing(4)
        odkazy = QHBoxLayout()
        odkazy.addStretch(1)
        for klic, fn in (("uvitani.licence", self._ukaz_licenci), ("oaplikaci.podminky", self._ukaz_podminky),
                         ("uvitani.chyba", self._nahlasit)):
            b = QPushButton(t(klic))
            b.setObjectName("odkazTlacitko")
            b.setCursor(Qt.PointingHandCursor)
            b.setFocusPolicy(Qt.NoFocus)
            b.clicked.connect(fn)
            odkazy.addWidget(b)
        odkazy.addStretch(1)
        lay.addLayout(odkazy)
        cara = QFrame()
        cara.setObjectName("exportCara")
        cara.setFixedHeight(1)
        lay.addWidget(cara)
        lay.addSpacing(6)
        dole = QHBoxLayout()
        self.rozumim = QCheckBox(t("uvitani.rozumim"))
        dole.addWidget(self.rozumim)
        dole.addStretch(1)
        self.zacit = QPushButton(t("uvitani.zacit"))
        self.zacit.setObjectName("primary")  # oranžové – hlavní akce
        self.zacit.setEnabled(False)
        self.zacit.clicked.connect(self._zacit)
        self.rozumim.toggled.connect(self.zacit.setEnabled)
        dole.addWidget(self.zacit)
        lay.addLayout(dole)
        return s

    def _licence(self):
        """Stránka s textem – Licence nebo Podmínky použití (obsah se doplní až při zobrazení)."""
        s = QWidget()
        lay = QVBoxLayout(s)
        lay.setContentsMargins(18, 16, 18, 16)
        self.prohlizec = prohlizec = QTextBrowser()
        prohlizec.setObjectName("oAplikaciText")
        prohlizec.setOpenExternalLinks(True)
        prohlizec.setMinimumHeight(420)
        lay.addWidget(prohlizec)
        zpet = QPushButton(t("oaplikaci.zpet"))
        zpet.setObjectName("sekundarni")
        zpet.clicked.connect(lambda: self.stranky.setCurrentIndex(0))
        lay.addWidget(zpet, 0, Qt.AlignLeft)
        return s

    def _stranka(self, index):
        """Karta tak vysoká jako aktuální stránka (skrytá stránka s licencí ji jinak natáhne)."""
        for i in range(self.stranky.count()):
            self.stranky.widget(i).setSizePolicy(QSizePolicy.Preferred,
                                                 QSizePolicy.Preferred if i == index else QSizePolicy.Ignored)
        self.stranky.adjustSize()
        self.karta.adjustSize()

    def _ukaz_text(self, markdown):
        self.prohlizec.setMarkdown(markdown)
        self.prohlizec.verticalScrollBar().setValue(0)
        self.stranky.setCurrentIndex(1)

    def _ukaz_licenci(self):
        from o_aplikaci import text_licence
        self._ukaz_text(text_licence())

    def _ukaz_podminky(self):
        from o_aplikaci import text_podminek
        self._ukaz_text(text_podminek())

    def _nahlasit(self):
        from o_aplikaci import otevri_odkaz
        otevri_odkaz(links.ZPETNA_VAZBA)

    def _zacit(self):
        if self.rozumim.isChecked():
            uloz_souhlas()
            self.accept()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            if self.stranky.currentIndex() == 1:
                self.stranky.setCurrentIndex(0)
            return  # bez potvrzení se okno nezavírá
        super().keyPressEvent(e)

    def eventFilter(self, obj, e):
        if obj is self.okno and e.type() in (QEvent.Move, QEvent.Resize):
            self.setGeometry(self.okno.geometry())
        return False

    def paintEvent(self, e):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(*theme.ZTLUMENI))
        p.end()

    def done(self, r):
        self.okno.removeEventFilter(self)
        super().done(r)
