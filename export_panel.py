# kupcake.studio – Copyright (C) 2026 Tomáš Kupec
# SPDX-License-Identifier: GPL-3.0-only
"""Panel s možnostmi exportu: ztlumí aplikaci (stejná vrstva jako překrytí s cupcakem) a uprostřed ukáže kartu
„● EXPORT“ – co exportovat, rychlé presety, základní nastavení, soubor a shrnutí.

Je to samostatné průhledné okno přes hlavní okno (jako Prekryti) – nativní okno přehrávače mpv by obyčejný
widget překrylo. Esc nebo klik mimo kartu = Zrušit. Po Exportovat: self.volby, self.vystup, self.rozsah.
"""
from pathlib import Path

from PySide6.QtCore import QEvent, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QComboBox, QDialog, QFileDialog, QFrame, QGridLayout,
                               QHBoxLayout, QLabel, QLineEdit, QPushButton, QRadioButton, QScrollArea, QSizePolicy,
                               QToolButton, QVBoxLayout, QWidget)

import export as ex
import theme
from i18n import t

SIRKA_KARTY = 560
# krátké technické názvy do řádku shrnutí (stejné ve všech jazycích)
KRATCE = {"h264": "MP4 · H.264", "h265": "MP4 · H.265", "mov": "MOV · ProRes", "pruhledne": "MOV · ProRes 4444",
          "srt": "SRT", "vtt": "VTT", "ass": "ASS"}


def fmt_delka(s):
    m, s = divmod(int(round(s)), 60)
    return f"{m}:{s:02d}"


def fmt_velikost(b):
    if b is None:
        return ""
    if b >= 1e9:
        return f"≈ {b / 1e9:.1f} GB"
    return f"≈ {max(b / 1e6, 0.1):.1f} MB" if b < 1e8 else f"≈ {b / 1e6:.0f} MB"


def ikona_dlazdice(druh, velikost=28):
    """Jednoduché čárové ikony dlaždic presetů: v klidu šedé, vybraná modře (výběr)."""
    ikon = QIcon()
    for barva, stav in ((theme.TEXT_2, QIcon.Off), (theme.AKCENT, QIcon.On)):
        pix = QPixmap(velikost * 2, velikost * 2)
        pix.setDevicePixelRatio(2)
        pix.fill(Qt.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.Antialiasing)
        pero = QPen(QColor(barva), 1.6)
        pero.setJoinStyle(Qt.RoundJoin)
        p.setPen(pero)
        s = velikost
        if druh == "original":  # filmové políčko
            p.drawRoundedRect(QRectF(s * 0.16, s * 0.24, s * 0.68, s * 0.52), 3, 3)
            for x in (0.3, 0.5, 0.7):
                p.drawLine(QPointF(s * x, s * 0.24), QPointF(s * x, s * 0.32))
                p.drawLine(QPointF(s * x, s * 0.68), QPointF(s * x, s * 0.76))
        elif druh == "vertikalni":  # telefon na výšku
            p.drawRoundedRect(QRectF(s * 0.33, s * 0.12, s * 0.34, s * 0.76), 4, 4)
            p.drawLine(QPointF(s * 0.45, s * 0.8), QPointF(s * 0.55, s * 0.8))
        elif druh == "youtube":  # obrazovka na šířku s trojúhelníkem
            p.drawRoundedRect(QRectF(s * 0.12, s * 0.26, s * 0.76, s * 0.48), 5, 5)
            trojuhelnik = QPainterPath(QPointF(s * 0.44, s * 0.4))
            trojuhelnik.lineTo(QPointF(s * 0.6, s * 0.5))
            trojuhelnik.lineTo(QPointF(s * 0.44, s * 0.6))
            trojuhelnik.closeSubpath()
            p.drawPath(trojuhelnik)
        else:  # vlastní – posuvníky
            for i, (y, x) in enumerate(((0.3, 0.62), (0.5, 0.36), (0.7, 0.55))):
                p.drawLine(QPointF(s * 0.16, s * y), QPointF(s * 0.84, s * y))
                p.setBrush(QColor(theme.PANEL))
                p.drawEllipse(QPointF(s * x, s * y), s * 0.07, s * 0.07)
        p.end()
        for rezim in (QIcon.Normal, QIcon.Active):
            ikon.addPixmap(pix, rezim, stav)
    return ikon


class ExportPanel(QDialog):
    def __init__(self, okno, video, info, fps, useky, volby):
        """useky = {"smycka": (od, do) | None, "vyber": (od, do) | None}; volby = poslední ex.Volby."""
        super().__init__(okno, Qt.Dialog | Qt.FramelessWindowHint)
        self.okno, self.video, self.info, self.fps = okno, Path(video), info, fps
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowModality(Qt.ApplicationModal)
        self.usek = useky.get("smycka") or useky.get("vyber")
        self.usek_druh = "smycka" if useky.get("smycka") else "vyber"
        self.volby = ex.Volby.z_dict(volby.jako_dict())
        self.vystup = None
        self.rozsah = None
        self._plnim = True
        self._postav()
        self._nastav_ovladani()
        self._plnim = False
        self._obnov()
        self.setGeometry(okno.geometry())
        okno.installEventFilter(self)

    # ---------- stavba ----------
    def _postav(self):
        vnejsi = QVBoxLayout(self)
        vnejsi.setContentsMargins(24, 24, 24, 24)
        self.karta = QFrame()
        self.karta.setObjectName("exportKarta")
        self.karta.setFixedWidth(SIRKA_KARTY)
        vnejsi.addWidget(self.karta, 0, Qt.AlignCenter)
        lay = QVBoxLayout(self.karta)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # záhlaví „● EXPORT“
        hlava = QWidget()
        hlava.setObjectName("exportHlava")
        lh = QHBoxLayout(hlava)
        lh.setContentsMargins(18, 10, 10, 10)
        tecka = QLabel()
        tecka.setPixmap(theme.tecka(theme.AKCENT, 12, 6).pixmap(12, 12))
        nadpis = QLabel(t("exportpanel.nadpis"))
        nadpis.setFont(theme.pismo_zahlavi())
        nadpis.setObjectName("exportNadpis")
        zavrit = QToolButton()
        zavrit.setObjectName("notifikaceZavrit")
        zavrit.setText("✕")
        zavrit.setCursor(Qt.PointingHandCursor)
        zavrit.clicked.connect(self.reject)
        lh.addWidget(tecka)
        lh.addSpacing(6)
        lh.addWidget(nadpis)
        lh.addStretch(1)
        lh.addWidget(zavrit)
        lay.addWidget(hlava)

        # tělo (v malém okně se posouvá)
        self.plocha = QScrollArea()
        self.plocha.setWidgetResizable(True)
        self.plocha.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.plocha.viewport().setAutoFillBackground(False)
        telo = QWidget()
        telo.setObjectName("exportTelo")
        self.plocha.setWidget(telo)
        lt = QVBoxLayout(telo)
        lt.setContentsMargins(18, 14, 18, 8)
        lt.setSpacing(12)
        lay.addWidget(self.plocha, 1)

        # 1. co exportovat – přepínač
        self.co = QButtonGroup(self)
        radek = QHBoxLayout()
        radek.setSpacing(0)
        for i, (klic, popis) in enumerate((("video", "exportpanel.co.video"), ("titulky", "exportpanel.co.titulky"),
                                          ("pruhledne", "exportpanel.co.pruhledne"))):
            b = QPushButton(t(popis))
            b.setObjectName("segment")
            b.setProperty("poloha", "prvni" if i == 0 else "posledni" if i == 2 else "stred")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setFocusPolicy(Qt.NoFocus)
            b.setToolTip(t(popis + ".tip"))
            b.setProperty("klic", klic)
            self.co.addButton(b)
            radek.addWidget(b, 1)
        self.co.buttonClicked.connect(lambda b: self._zmena("co", b.property("klic")))
        lt.addLayout(radek)
        self.popis_co = QLabel()
        self.popis_co.setObjectName("exportPopis")
        self.popis_co.setWordWrap(True)
        lt.addWidget(self.popis_co)

        # 2. rychlé presety – dlaždice
        self.blok_presety = QWidget()
        lp = QHBoxLayout(self.blok_presety)
        lp.setContentsMargins(0, 0, 0, 0)
        lp.setSpacing(8)
        self.presety = QButtonGroup(self)
        for klic in ("original", "vertikalni", "youtube", "vlastni"):
            b = QToolButton()
            b.setObjectName("dlazdice")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setFocusPolicy(Qt.NoFocus)
            b.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            b.setIcon(ikona_dlazdice(klic))
            b.setIconSize(QPixmap(28, 28).size())
            b.setText(t(f"exportpanel.preset.{klic}") + "\n" + t(f"exportpanel.preset.{klic}.pod"))
            b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            b.setProperty("klic", klic)
            self.presety.addButton(b)
            lp.addWidget(b, 1)
        self.presety.buttonClicked.connect(lambda b: self._zmena("preset", b.property("klic")))
        lt.addWidget(self.blok_presety)

        # upozornění: poměr stran neodpovídá presetu
        self.blok_pomer = QFrame()
        self.blok_pomer.setObjectName("exportUpozorneni")
        lu = QVBoxLayout(self.blok_pomer)
        lu.setContentsMargins(12, 9, 12, 9)
        lu.setSpacing(6)
        self.text_pomer = QLabel()
        self.text_pomer.setWordWrap(True)
        self.text_pomer.setObjectName("exportPopis")
        lu.addWidget(self.text_pomer)
        rp = QHBoxLayout()
        self.pomer = QButtonGroup(self)
        for klic in ("okraje", "puvodni"):
            r = QRadioButton(t(f"exportpanel.pomer.{klic}"))
            r.setProperty("klic", klic)
            self.pomer.addButton(r)
            rp.addWidget(r)
        rp.addStretch(1)
        self.pomer.buttonClicked.connect(lambda b: self._zmena("pomer", b.property("klic")))
        lu.addLayout(rp)
        lt.addWidget(self.blok_pomer)

        # 3. základní nastavení
        self.mrizka = QGridLayout()
        self.mrizka.setHorizontalSpacing(12)
        self.mrizka.setVerticalSpacing(8)
        self.mrizka.setColumnStretch(1, 1)
        self.radky = {}

        def radek_formulare(klic, widget):
            popisek = QLabel(t(f"exportpanel.{klic}"))
            popisek.setObjectName("exportPopisek")
            r = self.mrizka.rowCount()
            self.mrizka.addWidget(popisek, r, 0, Qt.AlignRight | Qt.AlignVCenter)
            self.mrizka.addWidget(widget, r, 1)
            self.radky[klic] = (popisek, widget)

        def vyber(klic, polozky):
            c = QComboBox()
            for hodnota, text in polozky:
                c.addItem(text, hodnota)
            c.activated.connect(lambda _i, c=c, k=klic: self._zmena(k, c.currentData()))
            return c

        self.c_format = vyber("format", [(k, t(f"exportpanel.format.{k}")) for k in ("h264", "h265", "mov")])
        radek_formulare("format", self.c_format)
        self.c_format_titulku = vyber("format_titulku", [(k, t(f"exportpanel.titulky.{k}")) for k in ("srt", "vtt", "ass")])
        radek_formulare("format_titulku", self.c_format_titulku)
        self.l_format_pruhledne = QLabel(t("exportpanel.format.prores4444"))
        self.l_format_pruhledne.setObjectName("exportHodnota")
        radek_formulare("format_pruhledne", self.l_format_pruhledne)
        W, H, _ = self.info
        kratsi = min(W, H)
        rozliseni = [("original", t("exportpanel.rozliseni.original", w=W, h=H))]
        rozliseni += [(str(r), t(f"exportpanel.rozliseni.{r}")) for r in ex.ROZLISENI if r < kratsi]
        self.c_rozliseni = vyber("rozliseni", rozliseni)
        self.l_rozliseni = QLabel()
        self.l_rozliseni.setObjectName("exportHodnota")
        bunka = QWidget()
        lb = QHBoxLayout(bunka)
        lb.setContentsMargins(0, 0, 0, 0)
        lb.addWidget(self.c_rozliseni, 1)
        lb.addWidget(self.l_rozliseni, 1)
        radek_formulare("rozliseni", bunka)
        self.c_kvalita = vyber("kvalita", [(k, t(f"exportpanel.kvalita.{k}")) for k in ("vysoka", "standardni", "maly")])
        radek_formulare("kvalita", self.c_kvalita)
        self.c_fps = vyber("fps", [("original", t("exportpanel.fps.original", fps=f"{self.fps:.3g}"))]
                           + [(str(f), f"{f} fps") for f in ex.FPS])
        self.l_fps = QLabel()
        self.l_fps.setObjectName("exportHodnota")
        bunka = QWidget()
        lb = QHBoxLayout(bunka)
        lb.setContentsMargins(0, 0, 0, 0)
        lb.addWidget(self.c_fps, 1)
        lb.addWidget(self.l_fps, 1)
        radek_formulare("fps", bunka)
        self.c_zvuk = vyber("zvuk", [(k, t(f"exportpanel.zvuk.{k}")) for k in ("zachovat", "bez")])
        self.ch_normalizace = QCheckBox(t("exportpanel.normalizace"))
        self.ch_normalizace.setToolTip(t("exportpanel.normalizace.tip"))
        self.ch_normalizace.toggled.connect(lambda v: self._zmena("normalizace", v))
        bunka = QWidget()
        lb = QVBoxLayout(bunka)
        lb.setContentsMargins(0, 0, 0, 0)
        lb.setSpacing(6)
        lb.addWidget(self.c_zvuk)
        lb.addWidget(self.ch_normalizace)
        radek_formulare("zvuk", bunka)
        rozsahy = [("cele", t("exportpanel.rozsah.cele", delka=fmt_delka(self.info[2])))]
        if self.usek:
            od, do = self.usek
            rozsahy.append(("usek", t(f"exportpanel.rozsah.{self.usek_druh}", od=f"{od:.1f}", do=f"{do:.1f}")))
        self.c_rozsah = vyber("rozsah", rozsahy)
        if not self.usek:
            self.c_rozsah.setToolTip(t("exportpanel.rozsah.zadny"))
        radek_formulare("rozsah", self.c_rozsah)
        self.ch_nvenc = QCheckBox(t("exportpanel.nvenc"))
        self.ch_nvenc.toggled.connect(lambda v: self._zmena("nvenc", v))
        self.l_bez_nvenc = QLabel(t("exportpanel.nvenc.nedostupne"))  # jednořádkové oznámení
        self.l_bez_nvenc.setObjectName("exportPopis")
        self.l_bez_nvenc.setWordWrap(True)
        bunka = QWidget()
        lb = QVBoxLayout(bunka)
        lb.setContentsMargins(0, 0, 0, 0)
        lb.setSpacing(4)
        lb.addWidget(self.ch_nvenc)
        lb.addWidget(self.l_bez_nvenc)
        radek_formulare("akcelerace", bunka)
        lt.addLayout(self.mrizka)

        # 4. soubor
        cara = QFrame()
        cara.setObjectName("exportCara")
        cara.setFixedHeight(1)
        lt.addWidget(cara)
        soubor = QGridLayout()
        soubor.setHorizontalSpacing(8)
        soubor.setVerticalSpacing(8)
        soubor.setColumnStretch(1, 1)
        p1 = QLabel(t("exportpanel.nazev"))
        p1.setObjectName("exportPopisek")
        self.e_nazev = QLineEdit(f"{self.video.stem}{t('export.pripona')}")
        self.e_nazev.textChanged.connect(lambda _: self._obnov())
        self.l_pripona = QLabel()
        self.l_pripona.setObjectName("exportHodnota")
        p2 = QLabel(t("exportpanel.slozka"))
        p2.setObjectName("exportPopisek")
        slozka = Path(self.volby.slozka) if self.volby.slozka and Path(self.volby.slozka).is_dir() else self.video.parent
        self.e_slozka = QLineEdit(str(slozka))
        self.e_slozka.textChanged.connect(lambda _: self._obnov())
        prochazet = QPushButton(t("exportpanel.prochazet"))
        prochazet.setObjectName("sekundarni")
        prochazet.setFocusPolicy(Qt.NoFocus)
        prochazet.clicked.connect(self._prochazet)
        soubor.addWidget(p1, 0, 0, Qt.AlignRight | Qt.AlignVCenter)
        soubor.addWidget(self.e_nazev, 0, 1)
        soubor.addWidget(self.l_pripona, 0, 2)
        soubor.addWidget(p2, 1, 0, Qt.AlignRight | Qt.AlignVCenter)
        soubor.addWidget(self.e_slozka, 1, 1)
        soubor.addWidget(prochazet, 1, 2)
        lt.addLayout(soubor)
        self.l_existuje = QLabel()
        self.l_existuje.setObjectName("exportVarovani")
        self.l_existuje.setWordWrap(True)
        lt.addWidget(self.l_existuje)

        # 5. shrnutí a tlačítka (mimo posouvanou plochu – vždy vidět)
        pata = QWidget()
        pata.setObjectName("exportPata")
        lpa = QVBoxLayout(pata)
        lpa.setContentsMargins(18, 10, 18, 16)
        lpa.setSpacing(10)
        self.l_shrnuti = QLabel()
        self.l_shrnuti.setObjectName("exportShrnuti")
        self.l_shrnuti.setFont(theme.pismo_mono(9))
        self.l_shrnuti.setWordWrap(True)
        lpa.addWidget(self.l_shrnuti)
        rt = QHBoxLayout()
        self.ch_otevrit = QCheckBox(t("exportpanel.otevrit"))
        self.ch_otevrit.toggled.connect(lambda v: self._zmena("otevrit_slozku", v))
        rt.addWidget(self.ch_otevrit)
        rt.addStretch(1)
        zrusit = QPushButton(t("btn.zrusit"))
        zrusit.setObjectName("sekundarni")
        zrusit.setFocusPolicy(Qt.NoFocus)
        zrusit.clicked.connect(self.reject)
        self.btn_export = QPushButton(t("exportpanel.exportovat"))
        self.btn_export.setObjectName("primary")
        self.btn_export.setDefault(True)
        self.btn_export.clicked.connect(self._potvrd)
        rt.addWidget(zrusit)
        rt.addWidget(self.btn_export)
        lpa.addLayout(rt)
        lay.addWidget(pata)

    # ---------- stav ----------
    def _nastav_ovladani(self):
        v = self.volby
        if v.rozsah == "usek" and not self.usek:
            v.rozsah = "cele"
        self.nvenc_k_dispozici = ex.nvenc_dostupny("h264_nvenc")
        if not self.nvenc_k_dispozici:
            v.nvenc = False
        for skupina, hodnota in ((self.co, v.co), (self.presety, v.preset), (self.pomer, v.pomer)):
            for b in skupina.buttons():
                b.setChecked(b.property("klic") == hodnota)
        for c, klic in ((self.c_format, "format"), (self.c_format_titulku, "format_titulku"),
                        (self.c_rozliseni, "rozliseni"), (self.c_kvalita, "kvalita"), (self.c_fps, "fps"),
                        (self.c_zvuk, "zvuk"), (self.c_rozsah, "rozsah")):
            i = c.findData(getattr(v, klic))
            if i < 0:  # uložená hodnota tu není (např. rozlišení vyšší než u tohoto videa) → první možnost
                i = 0
                setattr(v, klic, c.itemData(0))
            c.setCurrentIndex(i)
        self.ch_normalizace.setChecked(v.normalizace)
        self.ch_nvenc.setChecked(v.nvenc)
        self.ch_otevrit.setChecked(v.otevrit_slozku)

    def _zmena(self, klic, hodnota):
        if self._plnim:
            return
        setattr(self.volby, klic, hodnota)
        self._obnov()

    def _usek(self):
        return self.usek if self.volby.rozsah == "usek" and self.usek else None

    def _obnov(self):
        """Viditelnost a dostupnost prvků podle voleb, upozornění, shrnutí."""
        if self._plnim:
            return
        v = self.volby
        video, titulky, pruhledne = v.co == "video", v.co == "titulky", v.co == "pruhledne"
        vlastni = v.preset == "vlastni"
        W, H, delka = self.info
        self.popis_co.setText(t(f"exportpanel.co.{v.co}.popis"))
        self.blok_presety.setVisible(not titulky)
        self.blok_pomer.setVisible(not titulky and not ex.pomer_sedi(v, W, H))
        if self.blok_pomer.isVisible():
            bw, bh = ex.PRESETY[v.preset]
            self.text_pomer.setText(t("exportpanel.pomer.text", w=W, h=H, pw=bw, ph=bh))
        viditelne = {
            "format": video, "format_titulku": titulky, "format_pruhledne": pruhledne,
            "rozliseni": not titulky, "kvalita": video, "fps": not titulky, "zvuk": video,
            "rozsah": True, "akcelerace": video,
        }
        for klic, (popisek, widget) in self.radky.items():
            popisek.setVisible(viditelne[klic])
            widget.setVisible(viditelne[klic])
        # ruční nastavení odemkne jen preset Vlastní; jinak ukáže, co preset nastaví
        ow, oh, _, _ = ex.rozmery(v, W, H)
        fps = ex.vystupni_fps(v, self.fps)
        self.c_rozliseni.setVisible(vlastni)
        self.l_rozliseni.setVisible(not vlastni)
        self.l_rozliseni.setText(f"{ow} × {oh}")
        self.c_fps.setVisible(vlastni)
        self.l_fps.setVisible(not vlastni)
        self.l_fps.setText(f"{fps:.3g} fps")
        prores = v.format == "mov"
        self.ch_nvenc.setEnabled(self.nvenc_k_dispozici and not prores)
        self.ch_nvenc.setVisible(self.nvenc_k_dispozici or prores)
        self.l_bez_nvenc.setVisible(not self.nvenc_k_dispozici and not prores)
        if prores:
            self.ch_nvenc.setText(t("exportpanel.nvenc.prores"))
        else:
            self.ch_nvenc.setText(t("exportpanel.nvenc"))
        self.ch_normalizace.setEnabled(v.zvuk == "zachovat")
        self.c_rozsah.setEnabled(bool(self.usek))
        # soubor
        pripona = v.pripona()
        self.l_pripona.setText(pripona)
        cesta = self._cesta()
        zdroj = bool(cesta) and ex.je_stejny_soubor(cesta, self.video)  # zdrojové video se nikdy nepřepisuje
        if zdroj:
            self.l_existuje.setText(t("export.prepis_puvodni"))
            self.l_existuje.show()
        elif cesta and cesta.exists():
            self.l_existuje.setText(t("exportpanel.existuje", nazev=cesta.name))
            self.l_existuje.show()
        else:
            self.l_existuje.hide()
        # shrnutí: formát · rozlišení · délka · velikost
        usek = self._usek()
        delka_vystupu = (usek[1] - usek[0]) if usek else delka
        if titulky:
            casti = [KRATCE[v.format_titulku], fmt_delka(delka_vystupu)]
        else:
            casti = [KRATCE["pruhledne" if pruhledne else v.format], f"{ow}×{oh}", f"{fps:.3g} fps", fmt_delka(delka_vystupu),
                     fmt_velikost(ex.odhad_velikosti(v, W, H, self.fps, delka_vystupu))]
        self.l_shrnuti.setText("  ·  ".join(c for c in casti if c))
        self.btn_export.setEnabled(bool(self.e_nazev.text().strip()) and Path(self.e_slozka.text().strip()).is_dir()
                                   and not zdroj)
        self._vyska()

    def _cesta(self):
        nazev, slozka = self.e_nazev.text().strip(), self.e_slozka.text().strip()
        if not nazev or not slozka:
            return None
        if nazev.lower().endswith(self.volby.pripona()):
            nazev = nazev[: -len(self.volby.pripona())]
        return Path(slozka) / f"{nazev}{self.volby.pripona()}"

    def _prochazet(self):
        slozka = QFileDialog.getExistingDirectory(self, t("exportpanel.slozka"), self.e_slozka.text())
        if slozka:
            self.e_slozka.setText(str(Path(slozka)))

    def _potvrd(self):
        cesta = self._cesta()
        if cesta is None:
            return
        if ex.je_stejny_soubor(cesta, self.video):  # nikdy nepřepsat zdrojové video
            self.l_existuje.setText(t("export.prepis_puvodni"))
            self.l_existuje.show()
            return
        self.volby.slozka = str(cesta.parent)
        self.vystup = cesta
        self.rozsah = self._usek()
        self.accept()

    # ---------- okno ----------
    def _vyska(self):
        """Karta tak vysoká, jak potřebuje obsah, nejvýš do výšky okna (pak se tělo posouvá)."""
        telo = self.plocha.widget()
        lay = telo.layout()
        lay.activate()
        sirka = SIRKA_KARTY - 2
        # výška pro skutečnou šířku – zalamované popisky jsou na užší šířce sizeHint vyšší, než hlásí sizeHint
        potreba = lay.totalHeightForWidth(sirka) if lay.hasHeightForWidth() else lay.totalSizeHint().height()
        telo.setMinimumHeight(potreba)  # když se nevejde, tělo se posouvá místo stlačení řádků přes sebe
        pata = self.l_shrnuti.parentWidget()
        dostupne = self.height() - 48 - 44 - pata.sizeHint().height()
        self.plocha.setFixedHeight(max(min(potreba + 2, dostupne), 160))

    def eventFilter(self, obj, e):
        if obj is self.okno and e.type() in (QEvent.Move, QEvent.Resize):
            self.setGeometry(self.okno.geometry())
        return False

    def resizeEvent(self, e):
        self._vyska()
        super().resizeEvent(e)

    def mousePressEvent(self, e):
        if not self.karta.geometry().contains(e.position().toPoint()):
            self.reject()  # klik mimo kartu = Zrušit
        super().mousePressEvent(e)

    def paintEvent(self, e):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(*theme.ZTLUMENI))  # stejné ztlumení jako překrytí s cupcakem
        p.end()

    def done(self, r):
        self.okno.removeEventFilter(self)
        super().done(r)
