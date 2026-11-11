# kupcake.studio – Copyright (C) 2026 Tomáš Kupec
# SPDX-License-Identifier: GPL-3.0-only
"""Úvodní splash screen: cupcake (assets/splash/cupcake.png), pod ním „kupcake.studio“ a „by iamtom.kup“.

Okno bez rámečku a titulkové lišty (Qt.SplashScreen – bez vlastní položky na hlavním panelu), vycentrované
na obrazovce. Plynulý fade-in, zobrazení, fade-out; pak vyšle hotovo. Klik nebo Esc ho přeskočí.
Hlavní okno se mezitím staví na pozadí (main.py), takže po splashi se nečeká na nic dalšího.
Když obrázek chybí, ukáže se jen text.
"""
from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QGuiApplication, QPainter, QPixmap
from PySide6.QtWidgets import QWidget

import theme
from cesty import APP_DIR, LOGO

DELKA_S = 3.0         # jak dlouho je splash vidět celkem (včetně prolínání) – změň tady
PROLINANI_MS = 400     # fade-in i fade-out
OBRAZEK = APP_DIR / "assets" / "splash" / "cupcake.png"
VYSKA_OBRAZKU = 230    # px (logické), obrázek se zmenší / zvětší se zachováním poměru stran
MEZERA = 16            # mezi obrázkem a textem
OKRAJ = 44             # vnitřní okraj karty


class Splash(QWidget):
    hotovo = Signal()

    def __init__(self):
        super().__init__(None, Qt.SplashScreen | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setCursor(Qt.PointingHandCursor)
        self._skonceno = False
        self.obrazek = self._nacti_obrazek()
        self.pismo_nazvu = QFont(theme.PISMO_UI)
        self.pismo_nazvu.setPointSizeF(24)
        self.pismo_nazvu.setWeight(QFont.Bold)
        self.pismo_podpisu = QFont(theme.PISMO_UI)
        self.pismo_podpisu.setPointSizeF(10.5)
        self.nazev = LOGO  # ("kupcake", ".studio")
        self._rozmer()
        self.pruhlednost = QPropertyAnimation(self, b"windowOpacity", self)
        self.pruhlednost.setEasingCurve(QEasingCurve.InOutQuad)
        self.pruhlednost.finished.connect(lambda: self._konec() if self.pruhlednost.endValue() == 0.0 else None)
        self.casovac = QTimer(self)
        self.casovac.setSingleShot(True)
        self.casovac.timeout.connect(self._zmiz)

    # ---------- obsah ----------
    def _nacti_obrazek(self):
        if not OBRAZEK.is_file():
            return None
        pix = QPixmap(str(OBRAZEK))
        if pix.isNull():
            return None
        dpr = QGuiApplication.primaryScreen().devicePixelRatio() if QGuiApplication.primaryScreen() else 1.0
        pix = pix.scaledToHeight(int(VYSKA_OBRAZKU * dpr), Qt.SmoothTransformation)
        pix.setDevicePixelRatio(dpr)
        return pix

    def _rozmer(self):
        fm_n, fm_p = QFontMetricsF(self.pismo_nazvu), QFontMetricsF(self.pismo_podpisu)
        sirka_textu = fm_n.horizontalAdvance("".join(self.nazev))
        vyska = fm_n.height() + 4 + fm_p.height()
        if self.obrazek is not None:
            w_obr = self.obrazek.width() / self.obrazek.devicePixelRatio()
            vyska += VYSKA_OBRAZKU + MEZERA
        else:
            w_obr = 0
        self.setFixedSize(int(max(sirka_textu, w_obr, 300) + 2 * OKRAJ), int(vyska + 2 * OKRAJ))

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        # karta v barvách aplikace: tmavé pozadí, jemný okraj
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        p.setPen(QColor(theme.RAMECEK))
        p.setBrush(QColor(theme.POZADI))
        p.drawRoundedRect(r, 18, 18)
        y = OKRAJ
        if self.obrazek is not None:
            w_obr = self.obrazek.width() / self.obrazek.devicePixelRatio()
            p.drawPixmap(int((self.width() - w_obr) / 2), y, self.obrazek)
            y += VYSKA_OBRAZKU + MEZERA
        # „kupcake.studio“ – jako logo: první část teplá bílá, „.studio“ vedlejší šedá
        fm_n = QFontMetricsF(self.pismo_nazvu)
        hlavni, pripona = self.nazev
        x = (self.width() - fm_n.horizontalAdvance(hlavni + pripona)) / 2
        p.setFont(self.pismo_nazvu)
        p.setPen(QColor(theme.TEXT))
        p.drawText(QRectF(x, y, self.width(), fm_n.height()), Qt.AlignLeft | Qt.AlignTop, hlavni)
        p.setPen(QColor(theme.TEXT_2))
        p.drawText(QRectF(x + fm_n.horizontalAdvance(hlavni), y, self.width(), fm_n.height()),
                   Qt.AlignLeft | Qt.AlignTop, pripona)
        y += fm_n.height() + 4
        p.setFont(self.pismo_podpisu)
        p.setPen(QColor(theme.TEXT_2))
        p.drawText(QRectF(0, y, self.width(), QFontMetricsF(self.pismo_podpisu).height()),
                   Qt.AlignHCenter | Qt.AlignTop, "by iamtom.kup")
        p.end()

    # ---------- průběh ----------
    def spust(self):
        obrazovka = QGuiApplication.primaryScreen().availableGeometry()
        self.move(obrazovka.center() - self.rect().center())
        self.setWindowOpacity(0.0)
        self.show()
        self.raise_()
        self.activateWindow()
        self.setFocus()
        self._prolni(1.0)
        self.casovac.start(int(max(DELKA_S * 1000 - PROLINANI_MS, PROLINANI_MS)))

    def _prolni(self, cil, ms=PROLINANI_MS):
        self.pruhlednost.stop()
        self.pruhlednost.setDuration(ms)
        self.pruhlednost.setStartValue(self.windowOpacity())
        self.pruhlednost.setEndValue(cil)
        self.pruhlednost.start()

    def _zmiz(self):
        self._prolni(0.0)  # po doběhnutí do 0 zavolá _konec (viz __init__)

    def preskoc(self):
        """Klik / Esc: hned pryč a rovnou hlavní okno."""
        self.casovac.stop()
        self.pruhlednost.stop()
        self._konec()

    def _konec(self):
        if self._skonceno:
            return
        self._skonceno = True
        self.hotovo.emit()  # nejdřív hlavní okno, pak skrýt – aplikace nesmí zůstat bez okna (ukončila by se)
        self.hide()
        self.deleteLater()

    def mousePressEvent(self, e):
        self.preskoc()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.preskoc()
        else:
            super().keyPressEvent(e)
