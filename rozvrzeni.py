"""Sbalitelné skupiny v sekci Nastavení. (Rozvržení sekcí samotných řeší doky.py.)"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QFormLayout, QHBoxLayout, QPushButton, QSizePolicy, QToolButton, QVBoxLayout, QWidget

import theme


def obnov_stridani(rozlozeni):
    """Střídání pozadí A, B, A, B… podle pořadí skupin v rozložení (ne napevno u skupiny) – funguje i po
    přidání nebo přeházení kategorií. Volá se po sestavení panelu."""
    poradi = 0
    for i in range(rozlozeni.count()):
        w = rozlozeni.itemAt(i).widget()
        if isinstance(w, Skupina):
            w.nastav_poradi(poradi)
            poradi += 1


class Skupina(QWidget):
    """Sbalitelná skupina nastavení: klikací nadpis se šipkou a pod ním formulář. V nadpisu vpravo může
    svítit malá oranžová tečka – hodnoty skupiny se liší od presetu; klik na ni vyšle vratit.
    Celá skupina (hlavička i obsah) má vlastní pozadí – střídá se A/B podle pořadí (obnov_stridani);
    rozbalená má vlevo oranžový proužek přes celou výšku."""
    prepnuto = Signal(bool)
    vratit = Signal()

    def __init__(self, nazev):
        super().__init__()
        self.nazev = nazev
        self.poradi = 0
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        self.hlava = QPushButton()
        self.hlava.setObjectName("skupinaHlava")
        self.hlava.setCheckable(True)
        self.hlava.setChecked(True)
        self.hlava.setCursor(Qt.PointingHandCursor)
        self.hlava.setFocusPolicy(Qt.NoFocus)
        self.hlava.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.hlava.setFont(theme.pismo_nadpisu(9.5))
        self.hlava.toggled.connect(self.rozbal)
        lay.addWidget(self.hlava)
        uvnitr = QHBoxLayout(self.hlava)
        uvnitr.setContentsMargins(0, 0, 4, 0)
        uvnitr.addStretch(1)
        self.tecka = QToolButton()
        self.tecka.setObjectName("zmenaTecka")
        self.tecka.setIcon(theme.tecka(theme.SKUPINA_ZMENA, 16, 7))
        self.tecka.setFixedSize(18, 18)
        self.tecka.setCursor(Qt.PointingHandCursor)
        self.tecka.setFocusPolicy(Qt.NoFocus)
        self.tecka.clicked.connect(self.vratit)
        self.tecka.hide()
        uvnitr.addWidget(self.tecka)
        self.telo = QWidget()
        self.form = QFormLayout(self.telo)
        self.form.setContentsMargins(10, 10, 8, 14)  # vlevo místo pro proužek, vpravo pro okraj pozadí
        self.form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.form.setHorizontalSpacing(10)
        self.form.setVerticalSpacing(8)
        lay.addWidget(self.telo)
        self._popisek()

    def _popisek(self):
        # && = obyčejný znak & (jinak by ho tlačítko bralo jako zkratku Alt+písmeno)
        self.hlava.setText(("▾  " if self.hlava.isChecked() else "▸  ") + self.nazev.replace("&", "&&"))

    def nastav_nazev(self, nazev):
        self.nazev = nazev
        self._popisek()

    def nastav_zmenu(self, zmeneno, popisek=""):
        self.tecka.setVisible(zmeneno)
        self.tecka.setToolTip(popisek)

    def nastav_poradi(self, poradi):
        self.poradi = poradi
        self.update()

    def rozbal(self, ano=True):
        if self.hlava.isChecked() != ano:
            self.hlava.setChecked(ano)  # zavolá rozbal znovu přes toggled
            return
        self.telo.setVisible(ano)
        self._popisek()
        self.update()
        self.prepnuto.emit(ano)

    def paintEvent(self, e):
        p = QPainter(self)
        barva = theme.SKUPINA_POZADI_A if self.poradi % 2 == 0 else theme.SKUPINA_POZADI_B
        p.fillRect(self.rect(), QColor(barva))
        if self.je_rozbalena():
            p.fillRect(0, 0, theme.SKUPINA_PROUZEK_SIRKA, self.height(), QColor(theme.SKUPINA_PROUZEK))
        p.end()

    def je_rozbalena(self):
        return self.hlava.isChecked()
