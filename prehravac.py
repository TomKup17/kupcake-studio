# kupcake.studio – Copyright (C) 2026 Tomáš Kupec
# SPDX-License-Identifier: GPL-3.0-only
"""Přehrávač videa (libmpv) s živými ASS titulky – vykresluje je libass stejně jako export."""
import ctypes
import os
from ctypes import wintypes
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, QVariantAnimation, Signal
from PySide6.QtGui import QColor, QPainter, QPolygonF, QRadialGradient
from PySide6.QtWidgets import QApplication, QHBoxLayout, QLabel, QPushButton, QSlider, QVBoxLayout, QWidget

import theme
from cesty import FONTY_DIR, MPV_DIR, TMP_DIR

if MPV_DIR.is_dir():
    os.add_dll_directory(str(MPV_DIR))
    os.environ["PATH"] = str(MPV_DIR) + os.pathsep + os.environ.get("PATH", "")
import mpv  # noqa: E402

ASS_SOUBOR = TMP_DIR / "prehravac.ass"


def fmt_cas10(t):
    m, s = divmod(max(t, 0), 60)
    return f"{int(m)}:{s:04.1f}"


def _vypni_vstup_mpv(hwnd):
    """Okno mpv nesmí brát myš ani klávesnici – jinak by přestaly fungovat zkratky aplikace.
    Zakázané podokno propouští kliknutí do rodiče (naší plochy)."""
    user32 = ctypes.windll.user32
    proc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def cb(child, _):
        user32.EnableWindow(child, False)
        return True

    user32.EnumChildWindows(wintypes.HWND(hwnd), proc(cb), 0)


class VideoPlocha(QWidget):
    kliknuto = Signal()

    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WA_NativeWindow)
        self.setAttribute(Qt.WA_DontCreateNativeAncestors)
        self.setObjectName("videoPlocha")
        self.setStyleSheet(f"QWidget#videoPlocha {{ background: {theme.VIDEO_POZADI}; border-radius: 6px; }}")
        self.setMinimumSize(200, 200)

    def mousePressEvent(self, e):
        self.kliknuto.emit()


class PlayTlacitko(QPushButton):
    """Přehrát/Pauza: oranžové kulaté tlačítko s tmavým symbolem; pod myší se jemně rozzáří
    (zesvětlí a rozlije se kolem něj oranžová záře).

    Záře se kreslí v paintEvent uvnitř vlastní plochy tlačítka (kolem kolečka je na ni rezerva), ne přes
    QGraphicsDropShadowEffect – efekt kreslí mimo widget do rodiče, a to se vedle nativní plochy videa
    a v dokovacích sekcích QtAds nepřekresluje spolehlivě."""
    PRUMER = 34

    def __init__(self):
        super().__init__()
        self.okraj = theme.PLAY_ZARE_POLOMER  # rezerva pro záři na každé straně kolečka
        self.setFixedSize(self.PRUMER + 2 * self.okraj, self.PRUMER + 2 * self.okraj)
        self.setCursor(Qt.PointingHandCursor)
        self.setObjectName("play")
        self.hraje = False
        self._zare = 0.0
        self.anim = QVariantAnimation(self)
        self.anim.setDuration(theme.ANIMACE_MS + 70)
        self.anim.valueChanged.connect(self._nastav_zari)

    def nastav_hraje(self, hraje):
        if hraje != self.hraje:
            self.hraje = hraje
            self.update()

    def _nastav_zari(self, v):
        self._zare = float(v)
        self.update()

    def _kolecko(self):
        o = self.okraj
        return QRectF(o, o, self.PRUMER, self.PRUMER).adjusted(0.5, 0.5, -0.5, -0.5)

    def hitButton(self, pos):  # klikatelné je jen kolečko, ne rezerva pro záři
        c = self._kolecko().center()
        return (pos.x() - c.x()) ** 2 + (pos.y() - c.y()) ** 2 <= (self.PRUMER / 2 + 1) ** 2

    def sizeHint(self):
        return self.size()

    def _animuj(self, cil):
        self.anim.stop()
        self.anim.setStartValue(self._zare)
        self.anim.setEndValue(cil)
        self.anim.start()

    def enterEvent(self, e):
        self._animuj(1.0)
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._animuj(0.0)
        super().leaveEvent(e)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        if not self.isEnabled():
            pozadi = QColor(theme.POLE_RAMECEK)
        elif self.isDown():
            pozadi = QColor(theme.AKCE)
        else:  # plynule z AKCE do AKCE_HOVER podle záře
            a, b = QColor(theme.AKCE), QColor(theme.AKCE_HOVER)
            z = self._zare
            pozadi = QColor(round(a.red() + (b.red() - a.red()) * z), round(a.green() + (b.green() - a.green()) * z),
                            round(a.blue() + (b.blue() - a.blue()) * z))
        r = self._kolecko()
        if self._zare > 0.01 and self.isEnabled():  # záře: měkký oranžový prstenec kolem kolečka
            zare = QColor(*theme.PLAY_ZARE)
            vnejsi = self.PRUMER / 2 + self.okraj
            g = QRadialGradient(r.center(), vnejsi)
            konec = QColor(zare)
            konec.setAlpha(0)
            g.setColorAt(0, zare)
            g.setColorAt((self.PRUMER / 2) / vnejsi, zare)
            g.setColorAt(1, konec)
            p.setOpacity(self._zare)
            p.setBrush(g)
            p.drawEllipse(r.center(), vnejsi, vnejsi)
            p.setOpacity(1.0)
        p.setBrush(pozadi)
        p.drawEllipse(r)
        p.setBrush(QColor(theme.AKCE_TEXT if self.isEnabled() else theme.TEXT_3))
        c = r.center()
        if self.hraje:  # pauza: dva svislé pruhy
            for dx in (-4.2, 1.4):
                p.drawRoundedRect(QRectF(c.x() + dx, c.y() - 5.5, 2.8, 11), 1, 1)
        else:  # přehrát: trojúhelník, opticky posunutý doprava
            p.drawPolygon(QPolygonF([QPointF(c.x() - 3.6, c.y() - 6), QPointF(c.x() + 6, c.y()),
                                     QPointF(c.x() - 3.6, c.y() + 6)]))
        p.end()


class Prehravac(QWidget):
    cas = Signal(float)  # aktuální čas videa (s), vysílá se při každé změně

    def __init__(self):
        super().__init__()
        # Plocha videa musí být nativní okno (mpv do ní kreslí). Qt by jinak udělalo nativními i její
        # sourozence (Přehrát, posuvník, čas) – a nativní okno, jehož poloha v rodiči se nezmění, se při
        # přesunu sekce v QtAds nepřesune s ní: tlačítko Přehrát pak zůstávalo viset na starém místě.
        QApplication.setAttribute(Qt.AA_DontCreateNativeWidgetSiblings)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        self.plocha = VideoPlocha()
        self.plocha.kliknuto.connect(self.prepni)
        lay.addWidget(self.plocha, 1)

        ovl = QHBoxLayout()
        ovl.setSpacing(10 - theme.PLAY_ZARE_POLOMER // 2)  # část mezery tvoří rezerva pro záři tlačítka
        self.btn_play = PlayTlacitko()
        self.btn_play.setFocusPolicy(Qt.NoFocus)
        self.btn_play.clicked.connect(self.prepni)
        ovl.addWidget(self.btn_play)
        self.posuvnik = QSlider(Qt.Horizontal)
        self.posuvnik.setObjectName("prubehVidea")  # přehraná část a úchyt oranžové (theme.py)
        self.posuvnik.setFocusPolicy(Qt.NoFocus)
        self.posuvnik.sliderMoved.connect(lambda v: self.skoc(v / 1000))
        self.posuvnik.sliderPressed.connect(lambda: self.skoc(self.posuvnik.value() / 1000))
        ovl.addWidget(self.posuvnik, 1)
        self.lbl_cas = QLabel()
        self.lbl_cas.setObjectName("casovyKod")  # neproporcionální písmo – čísla neposkakují
        self.lbl_cas.setTextFormat(Qt.RichText)
        self.lbl_cas.setMinimumWidth(170)
        self.lbl_cas.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        ovl.addWidget(self.lbl_cas)
        lay.addLayout(ovl)

        self.mpv = mpv.MPV(
            wid=str(int(self.plocha.winId())),
            vo="gpu", hwdec="auto-safe", keep_open="yes", idle="yes", pause=True,
            hr_seek="yes", osc=False, osd_level=0, input_default_bindings=False,
            input_vo_keyboard=False, input_cursor=False, cursor_autohide="no",
            sub_auto="no", sub_ass_override="no", blend_subtitles="video",
            sub_fonts_dir=str(FONTY_DIR), sub_files=str(ASS_SOUBOR),
            # bezpečnost: žádné konfigurace a skripty mpv z profilu uživatele, žádné youtube-dl,
            # playlisty uvnitř videa jen na místní soubory (nic se nestáhne ze sítě)
            config="no", load_scripts="no", ytdl="no", load_unsafe_playlists="no",
            demuxer_lavf_o="protocol_whitelist=[file]",
        )
        self.delka = 0.0
        self.t = 0.0
        self.smer, self.rychlost = 0, 1   # J/K/L: -1 pozpátku, 0 stojí, 1 dopředu; násobek rychlosti
        self.lbl_cas.setText(self._text_casu(0.0))
        self.timer = QTimer(self)
        self.timer.setInterval(40)
        self.timer.timeout.connect(self._tik)
        self.timer.start()
        # mpv neumí plynule přehrávat pozpátku bez velké cache – J proto krokuje přesnými skoky
        self.zpet_timer = QTimer(self)
        self.zpet_timer.setInterval(50)
        self.zpet_timer.timeout.connect(self._krok_zpet)

    def nacti(self, video):
        self.delka, self.t = 0.0, 0.0
        self._zastav_jkl()
        self.nastav_smycku(None)
        self.mpv.pause = True
        self.mpv.loadfile(str(Path(video).resolve()))

    # ---------- J / K / L, snímky, smyčka ----------
    def _zastav_jkl(self):
        self.zpet_timer.stop()
        self.smer, self.rychlost = 0, 1
        self.mpv.speed = 1.0

    def jkl(self, klavesa):
        """L = dopředu, J = pozpátku (opakovaně = 2×, 4×, 8×), K = pauza."""
        if not self.delka:
            return
        if klavesa == "K":
            self._zastav_jkl()
            self.mpv.pause = True
            return
        smer = 1 if klavesa == "L" else -1
        self.rychlost = min(self.rychlost * 2, 8) if self.smer == smer else 1
        self.smer = smer
        if smer == 1:
            self.zpet_timer.stop()
            self.mpv.speed = float(self.rychlost)
            self.mpv.pause = False
        else:
            self.mpv.pause = True
            self.zpet_timer.start()
        self._zobraz(self.t)

    def _krok_zpet(self):
        novy = self.t - 0.05 * self.rychlost
        if novy <= 0:
            self.skoc(0)
            self._zastav_jkl()
        else:
            self.skoc(novy)

    def snimek(self, smer):
        """Posun o jeden snímek (mpv frame-step / frame-back-step)."""
        if not self.delka:
            return
        self._zastav_jkl()
        try:
            self.mpv.command("frame-step" if smer > 0 else "frame-back-step")
        except Exception:
            pass

    def nastav_smycku(self, od, do=None):
        """A-B smyčka přímo v mpv (od=None = vypnout)."""
        try:
            if od is None:
                self.mpv.ab_loop_a, self.mpv.ab_loop_b = "no", "no"
            else:
                self.mpv.ab_loop_a, self.mpv.ab_loop_b = float(od), float(do)
        except Exception:
            pass

    def obnov_titulky(self):
        try:
            self.mpv.command("sub-reload")
        except Exception:
            pass  # video ještě není načtené – titulky se načtou s ním

    def prepni(self):
        if self.delka:
            hraje = not self.mpv.pause or self.zpet_timer.isActive()
            self._zastav_jkl()
            if hraje:
                self.mpv.pause = True
            else:
                if self.t >= self.delka - 0.05:
                    self.skoc(0)
                self.mpv.pause = False

    def hraje(self):
        return (not self.mpv.pause) or self.zpet_timer.isActive()

    def skoc(self, t):
        if not self.delka:
            return
        t = min(max(t, 0.0), self.delka)
        try:
            self.mpv.seek(t, reference="absolute", precision="exact")
        except Exception:
            pass
        self._zobraz(t)

    def posun(self, o):
        self.skoc(self.t + o)

    def _text_casu(self, t):
        """Aktuální čas oranžově (kde jsem v čase), celková délka a režim J/L šedě."""
        rezim = ""
        if self.smer and (self.rychlost != 1 or self.smer < 0):
            rezim = f"&nbsp;&nbsp;&nbsp;{'◀◀' if self.smer < 0 else '▶▶'} {self.rychlost}×"
        return (f"<span style='color:{theme.PREHRAVAC_CAS}'>{fmt_cas10(t)}</span>"
                f"<span style='color:{theme.TEXT_2}'> / {fmt_cas10(self.delka)}{rezim}</span>")

    def _zobraz(self, t):
        self.t = t
        self.lbl_cas.setText(self._text_casu(t))
        if not self.posuvnik.isSliderDown():
            self.posuvnik.setValue(int(t * 1000))
        self.cas.emit(t)

    def _tik(self):
        try:
            delka, t, pauza = self.mpv.duration, self.mpv.time_pos, self.mpv.pause
        except Exception:
            return
        if delka and delka != self.delka:
            self.delka = delka
            self.posuvnik.setRange(0, int(delka * 1000))
            self.lbl_cas.setText(self._text_casu(self.t))  # celková délka hned po načtení videa
        if delka:
            _vypni_vstup_mpv(int(self.plocha.winId()))  # levné; mpv může okno vytvořit znovu
        self.btn_play.nastav_hraje(not pauza or self.zpet_timer.isActive())
        if pauza and self.smer == 1:  # došlo na konec / zastaveno jinak
            self._zastav_jkl()
        if t is not None and abs(t - self.t) > 1e-4:
            self._zobraz(t)

    def ukonci(self):
        self.timer.stop()
        self.mpv.terminate()
