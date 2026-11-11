# kupcake.studio – Copyright (C) 2026 Tomáš Kupec
# SPDX-License-Identifier: GPL-3.0-only
"""Okno „O aplikaci“: ztlumí aplikaci (jako ostatní překryvná okna) a uprostřed ukáže kartu – animovaný cupcake,
logo, verze a datum sestavení, popis, autor, odkazy (Instagram, TikTok, web, GitHub – adresy v links.py),
Co je nového (CHANGELOG.md), Licence (GPL-3.0 + ADDITIONAL_PERMISSION.md + THIRD_PARTY_LICENSES.md),
Podmínky použití (TERMS.cs.md / TERMS.md) a kopírování informací o systému.
Esc, ✕, Zavřít nebo klik mimo kartu = zavřít.
"""
import re

from PySide6.QtCore import QEvent, Qt, QTimer, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QGuiApplication, QPainter
from PySide6.QtWidgets import (QDialog, QFrame, QHBoxLayout, QLabel, QPushButton, QStackedWidget, QTextBrowser,
                               QToolButton, QVBoxLayout, QWidget)

import kupcake
import links
import theme
from cesty import APP_DIR
from i18n import t
from version import DATUM, VERZE

SIRKA_KARTY = 560


def otevri_odkaz(url):
    """Otevře adresu ve výchozím prohlížeči. Vrátí False, když to nešlo – adresa je pak ve schránce."""
    if not url:
        return False
    import sys
    if sys.platform == "win32":
        # běžící prohlížeč (Firefox, Chrome) by jinak mohl novou záložku otevřít jen na pozadí za aplikací
        import ctypes
        ctypes.windll.user32.AllowSetForegroundWindow(-1)  # ASFW_ANY
    if QDesktopServices.openUrl(QUrl(url)):
        return True
    QGuiApplication.clipboard().setText(url)
    return False


def odkazy():
    """[(klíč, adresa, ikona, hlavní?)] – jen vyplněné adresy (prázdná = tlačítko se neukáže)."""
    vse = [("instagram", links.INSTAGRAM, "znacka_instagram.svg", True),
           ("tiktok", links.TIKTOK, "znacka_tiktok.svg", True),
           ("web", links.WEB, "web.svg", False),
           ("github", links.GITHUB, "znacka_github.svg", False)]
    return [o for o in vse if o[1].strip()]


def tlacitko_odkazu(klic, url, ikona, hlavni, pri_chybe=lambda url: None):
    b = QPushButton(" " + t(f"oaplikaci.odkaz.{klic}"))  # mezera = odstup textu od ikony
    b.setObjectName("primary" if hlavni else "sekundarni")  # Instagram a TikTok oranžově, ostatní s obrysem
    b.setIcon(theme.ikona(ikona, theme.AKCE_TEXT if hlavni else theme.TEXT, 16))
    b.setCursor(Qt.PointingHandCursor)
    b.setFocusPolicy(Qt.NoFocus)
    b.setToolTip(url)
    b.clicked.connect(lambda: otevri_odkaz(url) or pri_chybe(url))
    return b


def _datum(iso):
    try:
        r, m, d = iso.split("-")
        return f"{int(d)}. {int(m)}. {r}"
    except ValueError:
        return iso


def zmeny_verze(verze=VERZE):
    """Část CHANGELOG.md pro danou verzi (Markdown); když chybí, nejnovější zapsaná verze."""
    try:
        text = (APP_DIR / "CHANGELOG.md").read_text(encoding="utf-8")
    except OSError:
        return t("oaplikaci.zmeny_chybi")
    casti = re.split(r"(?m)^## ", text)[1:]
    for c in casti:
        if c.startswith(verze):
            return "## " + c.strip()
    return "## " + casti[0].strip() if casti else t("oaplikaci.zmeny_chybi")


def _dokument(nazev):
    """Přibalený dokument (Markdown) pro zobrazení v aplikaci; odkazy na jiné soubory projektu vedou na GitHub
    (v aplikaci by nikam nevedly), odkazy na oddíly téže stránky zůstanou jako obyčejný text."""
    try:
        text = (APP_DIR / nazev).read_text(encoding="utf-8")
    except OSError:
        return ""
    text = re.sub(r"(?m)^(\*\*English\*\*|\[English\]).*\n+", "", text)  # přepínač jazyka je jen pro GitHub
    text = re.sub(r"\[([^\]]+)\]\(#[^)]*\)", r"\1", text)
    if links.GITHUB:
        return re.sub(r"\]\((?!https?://|mailto:)([^)\s]+)\)", rf"]({links.GITHUB}/blob/main/\1)", text)
    return re.sub(r"\[([^\]]+)\]\((?!https?://|mailto:)[^)\s]+\)", r"\1", text)


def text_licence():
    """Licence: shrnutí v jazyce rozhraní, dodatečné svolení (ADDITIONAL_PERMISSION.md) a seznam knihoven."""
    casti = [t("oaplikaci.licence_text"), _dokument("ADDITIONAL_PERMISSION.md"), _dokument("THIRD_PARTY_LICENSES.md")]
    return "\n\n---\n\n".join(c for c in casti if c)


def text_podminek():
    """Podmínky použití – česky pro češtinu a slovenštinu, jinak anglicky."""
    import i18n
    soubory = ("TERMS.cs.md", "TERMS.md") if i18n.aktualni() in ("cs", "sk") else ("TERMS.md", "TERMS.cs.md")
    return next((text for text in map(_dokument, soubory) if text), "") or t("oaplikaci.podminky_chybi")


class OAplikaci(QDialog):
    def __init__(self, okno):
        super().__init__(okno, Qt.Dialog | Qt.FramelessWindowHint)
        self.okno = okno
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowModality(Qt.ApplicationModal)
        vnejsi = QVBoxLayout(self)
        vnejsi.setContentsMargins(24, 24, 24, 24)
        self.karta = QFrame()
        self.karta.setObjectName("exportKarta")  # stejná karta jako panel exportu
        self.karta.setFixedWidth(SIRKA_KARTY)
        vnejsi.addWidget(self.karta, 0, Qt.AlignCenter)
        lay = QVBoxLayout(self.karta)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # záhlaví „● O APLIKACI“
        hlava = QWidget()
        hlava.setObjectName("exportHlava")
        lh = QHBoxLayout(hlava)
        lh.setContentsMargins(18, 10, 10, 10)
        tecka = QLabel()
        tecka.setPixmap(theme.tecka(theme.AKCENT, 12, 6).pixmap(12, 12))
        self.nadpis = QLabel(t("oaplikaci.nadpis"))
        self.nadpis.setFont(theme.pismo_zahlavi())
        self.nadpis.setObjectName("exportNadpis")
        zavrit = QToolButton()
        zavrit.setObjectName("notifikaceZavrit")
        zavrit.setText("✕")
        zavrit.setCursor(Qt.PointingHandCursor)
        zavrit.setToolTip(t("oaplikaci.zavrit"))
        zavrit.clicked.connect(self.reject)
        lh.addWidget(tecka)
        lh.addSpacing(6)
        lh.addWidget(self.nadpis)
        lh.addStretch(1)
        lh.addWidget(zavrit)
        lay.addWidget(hlava)

        self.stranky = QStackedWidget()
        self.stranky.addWidget(self._hlavni())
        self.stranky.addWidget(self._textova())
        lay.addWidget(self.stranky)
        self.setGeometry(okno.geometry())
        okno.installEventFilter(self)

    # ---------- hlavní stránka ----------
    def _hlavni(self):
        s = QWidget()
        lay = QVBoxLayout(s)
        lay.setContentsMargins(28, 18, 28, 20)
        lay.setSpacing(6)
        self.cupcake = kupcake.CupcakeAnimace(104)  # třešnička jemně poskakuje
        lay.addWidget(self.cupcake, 0, Qt.AlignHCenter)
        logo = QLabel(theme.logo_html(22, tecka_barva=None))
        logo.setTextFormat(Qt.RichText)
        lay.addWidget(logo, 0, Qt.AlignHCenter)
        verze = QLabel(t("oaplikaci.verze", verze=VERZE, datum=_datum(DATUM)))
        verze.setFont(theme.pismo_mono(8.5))
        verze.setObjectName("exportPopis")
        lay.addWidget(verze, 0, Qt.AlignHCenter)
        lay.addSpacing(8)
        popis = QLabel(t("oaplikaci.popis"))
        popis.setWordWrap(True)
        popis.setAlignment(Qt.AlignCenter)
        lay.addWidget(popis)
        autor = QLabel(t("oaplikaci.autor"))
        autor.setObjectName("exportPopis")
        autor.setAlignment(Qt.AlignCenter)
        lay.addWidget(autor)
        soukromi = QLabel(t("oaplikaci.soukromi"))  # vše lokálně, nic se neodesílá
        soukromi.setObjectName("exportPopis")
        soukromi.setWordWrap(True)
        soukromi.setAlignment(Qt.AlignCenter)
        lay.addSpacing(4)
        lay.addWidget(soukromi)
        bez_zaruky = QPushButton(t("oaplikaci.bez_zaruky"))  # „Poskytováno bez záruky · GPL-3.0“ → text licence
        bez_zaruky.setObjectName("odkazTlacitko")
        bez_zaruky.setCursor(Qt.PointingHandCursor)
        bez_zaruky.setFocusPolicy(Qt.NoFocus)
        bez_zaruky.clicked.connect(self.ukaz_licence)
        lay.addWidget(bez_zaruky, 0, Qt.AlignHCenter)
        lay.addSpacing(10)

        radek = QHBoxLayout()
        radek.setSpacing(8)
        radek.addStretch(1)
        for klic, url, ikona, hlavni in odkazy():
            radek.addWidget(tlacitko_odkazu(klic, url, ikona, hlavni, self._odkaz_selhal))
        radek.addStretch(1)
        lay.addLayout(radek)
        lay.addSpacing(12)

        cara = QFrame()
        cara.setObjectName("exportCara")
        cara.setFixedHeight(1)
        lay.addWidget(cara)
        lay.addSpacing(8)
        # dva řádky odkazů: dokumenty (Co je nového · Licence · Podmínky použití) a kopírování informací o systému
        for radek_odkazu in ((("zmeny", self.ukaz_zmeny), ("licence", self.ukaz_licence),
                              ("podminky", self.ukaz_podminky)), (("system", self.kopiruj_info),)):
            dalsi = QHBoxLayout()
            dalsi.setSpacing(4)
            for klic, fn in radek_odkazu:
                b = QPushButton(t(f"oaplikaci.{klic}"))
                b.setObjectName("odkazTlacitko")
                b.setCursor(Qt.PointingHandCursor)
                b.setFocusPolicy(Qt.NoFocus)
                b.clicked.connect(fn)
                dalsi.addWidget(b, 1)
            lay.addLayout(dalsi)
        self.l_stav = QLabel("")
        self.l_stav.setObjectName("exportPopis")
        self.l_stav.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.l_stav)
        lay.addSpacing(4)
        zavrit = QPushButton(t("oaplikaci.zavrit"))
        zavrit.setObjectName("sekundarni")
        zavrit.setFocusPolicy(Qt.NoFocus)
        zavrit.clicked.connect(self.reject)
        lay.addWidget(zavrit, 0, Qt.AlignHCenter)
        return s

    # ---------- stránka s textem (Co je nového, Licence) ----------
    def _textova(self):
        s = QWidget()
        lay = QVBoxLayout(s)
        lay.setContentsMargins(18, 14, 18, 16)
        lay.setSpacing(10)
        self.text = QTextBrowser()
        self.text.setObjectName("oAplikaciText")
        self.text.setOpenExternalLinks(True)
        self.text.setMinimumHeight(420)
        lay.addWidget(self.text, 1)
        zpet = QPushButton(t("oaplikaci.zpet"))
        zpet.setObjectName("sekundarni")
        zpet.setFocusPolicy(Qt.NoFocus)
        zpet.clicked.connect(self.ukaz_hlavni)
        lay.addWidget(zpet, 0, Qt.AlignLeft)
        return s

    def _ukaz_text(self, nadpis, markdown):
        self.nadpis.setText(nadpis)
        self.text.setMarkdown(markdown)
        self.text.verticalScrollBar().setValue(0)
        self.stranky.setCurrentIndex(1)

    def ukaz_zmeny(self):
        self._ukaz_text(t("oaplikaci.zmeny"), zmeny_verze())

    def ukaz_licence(self):
        self._ukaz_text(t("oaplikaci.licence"), text_licence())

    def ukaz_podminky(self):
        self._ukaz_text(t("oaplikaci.podminky"), text_podminek())

    def ukaz_hlavni(self):
        self.nadpis.setText(t("oaplikaci.nadpis"))
        self.stranky.setCurrentIndex(0)

    def _odkaz_selhal(self, url):
        self.l_stav.setText(t("oaplikaci.odkaz_selhal", url=url))

    def kopiruj_info(self):
        import hardware
        QGuiApplication.clipboard().setText(hardware.info_o_systemu())
        self.l_stav.setText(t("oaplikaci.zkopirovano"))
        QTimer.singleShot(4000, self.l_stav, lambda: self.l_stav.setText(""))  # zruší se se zavřením okna

    # ---------- překryv ----------
    def eventFilter(self, obj, e):
        if obj is self.okno and e.type() in (QEvent.Move, QEvent.Resize):
            self.setGeometry(self.okno.geometry())
        return False

    def mousePressEvent(self, e):
        if not self.karta.geometry().contains(e.position().toPoint()):
            self.reject()  # klik mimo kartu = zavřít
        super().mousePressEvent(e)

    def paintEvent(self, e):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(*theme.ZTLUMENI))
        p.end()

    def done(self, r):
        self.okno.removeEventFilter(self)
        super().done(r)
