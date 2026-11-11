# kupcake.studio – Copyright (C) 2026 Tomáš Kupec
# SPDX-License-Identifier: GPL-3.0-only
"""Nenápadná notifikace v pravém dolním rohu okna (hotový export): oranžový proužek vlevo, nadpis, název
souboru, tlačítko akce („Otevřít složku“) a samovolné zmizení po pár sekundách.

Je to samostatné okno (Qt.Tool) nad hlavním oknem – nativní okno přehrávače mpv by obyčejný widget
překrylo. Fokus si nebere, takže nepřeruší psaní ani klávesové zkratky.
"""
from PySide6.QtCore import QEvent, QPropertyAnimation, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QToolButton, QVBoxLayout, QWidget

import theme

OKRAJ = 20      # odstup od okraje okna (px)
SIRKA = 340


class Notifikace(QWidget):
    def __init__(self, okno):
        super().__init__(okno, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowDoesNotAcceptFocus)
        self.okno = okno
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFixedWidth(SIRKA)
        self._akce = None

        lay = QHBoxLayout(self)
        lay.setContentsMargins(18, 12, 10, 12)
        lay.setSpacing(10)
        texty = QVBoxLayout()
        texty.setSpacing(2)
        self.nadpis = QLabel()
        self.nadpis.setObjectName("notifikaceNadpis")
        self.text = QLabel()
        self.text.setObjectName("notifikaceText")
        texty.addWidget(self.nadpis)
        texty.addWidget(self.text)
        self.radek = QHBoxLayout()  # víc tlačítek pod textem (ukaz_tlacitka)
        self.radek.setContentsMargins(0, 8, 0, 0)
        self.radek.setSpacing(6)
        texty.addLayout(self.radek)
        lay.addLayout(texty, 1)
        self.tlacitko = QPushButton()
        self.tlacitko.setObjectName("notifikaceAkce")
        self.tlacitko.setCursor(Qt.PointingHandCursor)
        self.tlacitko.setFocusPolicy(Qt.NoFocus)
        self.tlacitko.clicked.connect(self._klik)
        lay.addWidget(self.tlacitko, 0, Qt.AlignVCenter)
        zavrit = QToolButton()
        zavrit.setObjectName("notifikaceZavrit")
        zavrit.setText("✕")
        zavrit.setCursor(Qt.PointingHandCursor)
        zavrit.setFocusPolicy(Qt.NoFocus)
        zavrit.clicked.connect(self.skryj)
        lay.addWidget(zavrit, 0, Qt.AlignTop)

        self.odpocet = QTimer(self)
        self.odpocet.setSingleShot(True)
        self.odpocet.setInterval(theme.NOTIFIKACE_MS)
        self.odpocet.timeout.connect(self.skryj)
        self.pruhlednost = QPropertyAnimation(self, b"windowOpacity", self)
        self.pruhlednost.finished.connect(self._po_animaci)
        okno.installEventFilter(self)

    def _vycisti_radek(self):
        while self.radek.count():
            w = self.radek.takeAt(0).widget()
            if w is not None:
                w.deleteLater()

    def ukaz(self, nadpis, text, text_akce, akce):
        self._vycisti_radek()
        self.setFixedWidth(SIRKA)
        self.nadpis.setText(nadpis)
        self.text.setWordWrap(False)
        self.text.setText(self.text.fontMetrics().elidedText(text, Qt.ElideMiddle, SIRKA - 160))
        self.text.setToolTip(text)
        self.tlacitko.setText(text_akce)
        self.tlacitko.show()
        self._akce = akce
        self._zobraz()

    def ukaz_tlacitka(self, nadpis, text, tlacitka):
        """Notifikace s víc tlačítky pod textem: tlacitka = [(text, akce, hlavní?)]. Klik provede akci a zavře."""
        self._vycisti_radek()
        self.nadpis.setText(nadpis)
        self.text.setWordWrap(True)
        self.text.setText(text)
        self.text.setToolTip("")
        self.tlacitko.hide()
        for popis, akce, hlavni in tlacitka:
            b = QPushButton(popis)
            b.setObjectName("notifikaceAkce" if hlavni else "odkazTlacitko")
            b.setCursor(Qt.PointingHandCursor)
            b.setFocusPolicy(Qt.NoFocus)
            b.clicked.connect(lambda _=False, akce=akce: (akce(), self.skryj()))
            self.radek.addWidget(b)
        self.radek.addStretch(1)
        self.setMinimumWidth(0)
        self.setMaximumWidth(16777215)
        self.layout().activate()
        self.setFixedWidth(max(SIRKA, self.layout().sizeHint().width()))  # ať se tlačítka neuseknou
        self._zobraz()

    def _zobraz(self):
        self.layout().activate()
        self.adjustSize()
        self._umisti()
        if not self.isVisible():
            self.setWindowOpacity(0.0)
            self.show()
        self._prolni(1.0, 200)
        self.odpocet.start()

    def skryj(self):
        self.odpocet.stop()
        if self.isVisible():
            self._prolni(0.0, 300)

    def _prolni(self, cil, ms):
        self.pruhlednost.stop()
        self.pruhlednost.setDuration(ms)
        self.pruhlednost.setStartValue(self.windowOpacity())
        self.pruhlednost.setEndValue(cil)
        self.pruhlednost.start()

    def _po_animaci(self):
        if self.pruhlednost.endValue() == 0.0:
            self.hide()

    def _klik(self):
        if self._akce:
            self._akce()
        self.skryj()

    def _umisti(self):
        g = self.okno.geometry()  # klientská plocha okna v souřadnicích obrazovky
        self.move(g.right() - self.width() - OKRAJ, g.bottom() - self.height() - OKRAJ)

    # pod myší se odpočet zastaví, po odjetí běží znovu
    def enterEvent(self, e):
        self.odpocet.stop()
        self._prolni(1.0, 120)
        super().enterEvent(e)

    def leaveEvent(self, e):
        if self.isVisible():
            self.odpocet.start(max(theme.NOTIFIKACE_MS // 2, 2000))
        super().leaveEvent(e)

    def eventFilter(self, obj, e):
        if obj is self.okno and self.isVisible():
            if e.type() in (QEvent.Move, QEvent.Resize):
                self._umisti()
            elif e.type() == QEvent.WindowStateChange and self.okno.isMinimized():
                self.hide()
        return False

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        p.setPen(QColor(theme.POLE_RAMECEK))
        p.setBrush(QColor(theme.PANEL))
        p.drawRoundedRect(r, theme.RADIUS_PANEL, theme.RADIUS_PANEL)
        # oranžový akcent: svislý proužek vlevo
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(theme.NOTIFIKACE_AKCENT))
        p.drawRoundedRect(QRectF(6, 10, 3, r.height() - 20), 1.5, 1.5)
        p.end()
