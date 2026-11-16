# kupcake.studio – Copyright (C) 2026 Tomáš Kupec
# SPDX-License-Identifier: GPL-3.0-only
"""Dlaždice sekce Nastavení: každá hodnota stylu titulků má vlastní dlaždici, která ukazuje, co upravuje.

- DlazdiceCislo – číslo s tlačítky − a +; po kliknutí na číslo jde hodnota zapsat, po kliknutí na dlaždici
  ji mění kolečko myši a šipky (pravidlo kolecko.py: bez fokusu kolečko posouvá panel),
- DlazdicePozice – číslo doplněné malou obrazovkou, na které jde titulek táhnout myší (vodorovně / svisle),
- DlazdicePrepinac – zapnuto/vypnuto jedním kliknutím, ukázka podle stylu (stín, pozadí, zvýraznění…),
- DlazdiceBarva – barevný vzorek, kliknutím malá paleta častých barev a „Vlastní barva“,
- DlazdicePismo – „Aa“ ve zvoleném písmu, kliknutím seznam písem s hledáním.

MrizkaDlazdic skládá dlaždice do sloupců podle šířky panelu. Barvy a rozměry jsou v theme.py, záře ani
jiné efekty se nekreslí přes QGraphicsEffect – vše v paintEvent.
"""
import re
from functools import lru_cache

from PySide6.QtCore import QEvent, QLocale, QPoint, QPointF, QRect, QRectF, QSize, Qt, Signal
from PySide6.QtGui import (QColor, QFont, QFontDatabase, QFontMetricsF, QGuiApplication, QPainter, QPainterPath, QPen,
                           QTransform)
from PySide6.QtWidgets import (QAbstractButton, QColorDialog, QFrame, QGridLayout, QLayout, QLineEdit,
                               QListWidget, QListWidgetItem, QPushButton, QStyledItemDelegate, QVBoxLayout,
                               QWidget)

import theme
from i18n import prekladej, t

OKRAJ = 6           # vnitřní okraj dlaždice
POPISEK_V = 20      # výška řádku s popiskem dole
KROK_V = 22         # velikost tlačítek − a +


# ---------- rozložení ----------
class MrizkaDlazdic(QLayout):
    """Dlaždice ve stejně širokých sloupcích; počet sloupců podle šířky (nejméně theme.DLAZDICE_SIRKA na
    dlaždici). Dlaždice s atributem sloupcu = 2 zabere dvě buňky. Skryté dlaždice místo nezabírají."""

    def __init__(self, rodic=None):
        super().__init__(rodic)
        self._polozky = []

    def addItem(self, polozka):
        self._polozky.append(polozka)

    def count(self):
        return len(self._polozky)

    def itemAt(self, i):
        return self._polozky[i] if 0 <= i < len(self._polozky) else None

    def takeAt(self, i):
        return self._polozky.pop(i) if 0 <= i < len(self._polozky) else None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, sirka):
        return self._rozloz(QRect(0, 0, sirka, 0), False)

    def setGeometry(self, r):
        super().setGeometry(r)
        self._rozloz(r, True)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        m = self.contentsMargins()
        return QSize(theme.DLAZDICE_SIRKA + m.left() + m.right(), theme.DLAZDICE_VYSKA + m.top() + m.bottom())

    def sloupcu(self, sirka):
        """Počet sloupců pro danou šířku rozložení (včetně okrajů)."""
        m = self.contentsMargins()
        uvnitr = max(sirka - m.left() - m.right(), 1)
        return max(1, (uvnitr + theme.DLAZDICE_MEZERA) // (theme.DLAZDICE_SIRKA + theme.DLAZDICE_MEZERA))

    def _rozloz(self, r, nastavit):
        m = self.contentsMargins()
        mez, vyska = theme.DLAZDICE_MEZERA, theme.DLAZDICE_VYSKA
        uvnitr = max(r.width() - m.left() - m.right(), 1)
        n = self.sloupcu(r.width())
        bunka = (uvnitr - (n - 1) * mez) / n
        x0, y0 = r.x() + m.left(), r.y() + m.top()
        sloupec = radek = 0
        neco = False
        for polozka in self._polozky:
            if polozka.isEmpty():  # skrytá dlaždice
                continue
            pres = min(getattr(polozka.widget(), "sloupcu", 1), n)
            if sloupec + pres > n:
                sloupec, radek = 0, radek + 1
            if nastavit:
                x = x0 + round(sloupec * (bunka + mez))
                x2 = x0 + round((sloupec + pres) * (bunka + mez) - mez)
                polozka.setGeometry(QRect(x, y0 + radek * (vyska + mez), x2 - x, vyska))
            sloupec += pres
            neco = True
        obsah = (radek + 1) * vyska + radek * mez if neco else 0
        return obsah + m.top() + m.bottom()


# ---------- ukázky (kreslí se podle celého stylu, ať dlaždice ukazuje skutečný vzhled) ----------
def _barva(hex_, alfa=255):
    c = QColor(f"#{hex_}")
    if not c.isValid():
        c = QColor(theme.TEXT)
    c.setAlpha(alfa)
    return c


def _pismo_stylu(styl, px):
    f = QFont(styl.font)
    f.setPixelSize(max(int(px), 6))
    f.setBold(bool(styl.tucne))
    return f


def _slova(styl, texty, r, px):
    """Cesty slov vedle sebe, vystředěné v r (zmenšené, když se nevejdou). Vrací (cesty, skutečná výška
    písma v px)."""
    f = _pismo_stylu(styl, px)
    texty = [s.upper() if styl.velka_pismena else s for s in texty]
    mezera = QFontMetricsF(f).horizontalAdvance(" ")
    cesty, x = [], 0.0
    for s in texty:
        c = QPainterPath()
        c.addText(x, 0, f, s)
        cesty.append(c)
        x += QFontMetricsF(f).horizontalAdvance(s) + mezera
    vse = QPainterPath()
    for c in cesty:
        vse.addPath(c)
    b = vse.boundingRect()
    k = min(1.0, (r.width() - 10) / max(b.width(), 1), (r.height() - 6) / max(b.height(), 1))
    tr = QTransform()
    tr.translate(r.center().x(), r.center().y())
    tr.scale(k, k)
    tr.translate(-b.center().x(), -b.center().y())
    return [tr.map(c) for c in cesty], px * k


def _platno(p, r):
    """„Kousek videa“ pod ukázkou – neutrální šedá, na které je vidět i černý obrys a stín."""
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(theme.DLAZDICE_PLATNO))
    p.drawRoundedRect(r, 4, 4)


def _kresli_stin(p, cesta, styl, px):
    """Stín písma: posun a rozmazání ve stejném poměru k velikosti písma jako ve videu."""
    k = px / max(styl.velikost * 1080, 1)
    posunuta = cesta.translated(styl.stin_x * k, styl.stin_y * k)
    c = _barva(styl.barva_stinu)
    polomer = max(px * 0.06, 1) + styl.stin_rozmazani / 100 * px * 0.22
    if styl.stin_rozmazani <= 0:
        p.strokePath(posunuta, QPen(c, polomer * 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.fillPath(posunuta, c)
        return
    kroky = 7
    c.setAlpha(46)
    for i in range(kroky, 0, -1):
        p.strokePath(posunuta, QPen(c, polomer * 2 * i / kroky, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    c.setAlpha(150)
    p.fillPath(posunuta, c)


def _kresli_text(p, cesty, styl, px, stin=None, barvy=None):
    """Slova se stínem a obrysem podle stylu. barvy = barva každého slova (výchozí barva textu)."""
    if styl.stin if stin is None else stin:
        for c in cesty:
            _kresli_stin(p, c, styl, px)
    for i, c in enumerate(cesty):
        if styl.obrys > 0:
            p.strokePath(c, QPen(_barva(styl.barva_obrysu), 2 * styl.obrys * px, Qt.SolidLine, Qt.RoundCap,
                                 Qt.RoundJoin))
        p.fillPath(c, _barva(barvy[i] if barvy else styl.barva_textu))


def symbol_obrys(p, r, styl, _hodnota):
    _platno(p, r)
    cesty, px = _slova(styl, ["Aa"], r, r.height() * 0.62)
    obrys = max(styl.obrys, 0.0)
    for c in cesty:
        if obrys > 0:
            p.strokePath(c, QPen(_barva(styl.barva_obrysu), 2 * obrys * px, Qt.SolidLine, Qt.RoundCap,
                                 Qt.RoundJoin))
        p.fillPath(c, _barva(styl.barva_textu))


def symbol_stin(p, r, styl, zapnuto):
    _platno(p, r)
    cesty, px = _slova(styl, ["Aa"], r, r.height() * 0.5)
    _kresli_text(p, cesty, styl, px, stin=zapnuto)


def symbol_pozadi(p, r, styl, zapnuto):
    _platno(p, r)
    cesty, px = _slova(styl, ["Abc"], r, r.height() * 0.4)
    if zapnuto:
        vse = QPainterPath()
        for c in cesty:
            vse.addPath(c)
        o = px * styl.odsazeni_pozadi
        box = vse.boundingRect().adjusted(-o, -o, o, o).intersected(r.adjusted(2, 2, -2, -2))
        p.fillRect(box, _barva(styl.barva_pozadi, round(255 * (100 - styl.pruhlednost_pozadi) / 100)))
    _kresli_text(p, cesty, styl, px)


def symbol_zvyrazneni(p, r, styl, zapnuto):
    _platno(p, r)
    cesty, px = _slova(styl, ["Aa", "Bb"], r, r.height() * 0.42)
    _kresli_text(p, cesty, styl, px,
                 barvy=[styl.barva_textu, styl.barva_zvyrazneni if zapnuto else styl.barva_textu])


def symbol_tucne(p, r, _styl, zapnuto):
    f = QFont(theme.PISMO_UI)
    f.setPixelSize(int(r.height() * 0.58))
    f.setWeight(QFont.Black if zapnuto else QFont.Light)
    p.setFont(f)
    p.setPen(QColor(theme.DLAZDICE_HODNOTA if zapnuto else theme.DLAZDICE_POPISEK))
    p.drawText(r, Qt.AlignCenter, "B")


def symbol_velka(p, r, styl, zapnuto):
    f = _pismo_stylu(styl, r.height() * 0.5)
    cesta = QPainterPath()
    cesta.addText(0, 0, f, "AA" if zapnuto else "Aa")
    b = cesta.boundingRect()
    k = min(1.0, (r.width() - 10) / max(b.width(), 1))
    tr = QTransform()
    tr.translate(r.center().x(), r.center().y())
    tr.scale(k, k)
    tr.translate(-b.center().x(), -b.center().y())
    p.fillPath(tr.map(cesta), QColor(theme.DLAZDICE_HODNOTA))


# ---------- dlaždice ----------
class Dlazdice(QWidget):
    """Základ: zaoblená plocha, dole popisek, nad ním obsah (kresli). zmena(hodnota) vysílá hodnotu
    v jednotkách stylu; nastav_hodnotu ji zobrazí bez vyslání."""
    zmena = Signal(object)
    sloupcu = 1

    def __init__(self, zdroj, popisek, napoveda=None):
        super().__init__()
        self.zdroj = zdroj          # panel: .styl (celý styl pro ukázky) a .pomer (šířka / výška videa)
        self._klic_popisku, self._klic_napovedy = popisek, napoveda
        self._popisek = ""
        self.setAttribute(Qt.WA_Hover)
        self.setMinimumSize(theme.DLAZDICE_SIRKA, theme.DLAZDICE_VYSKA)
        prekladej(self._preloz)

    def sizeHint(self):
        return QSize(theme.DLAZDICE_SIRKA, theme.DLAZDICE_VYSKA)

    def _preloz(self):
        self._popisek = t(self._klic_popisku)
        self._obnov_napovedu()
        self.update()

    def _radky_napovedy(self):
        """Nápověda pod myší: celý název (na úzké dlaždici může být zkrácený) a co hodnota dělá."""
        return [t(self._klic_popisku)] + ([t(self._klic_napovedy)] if self._klic_napovedy else [])

    def _obnov_napovedu(self):
        self.setToolTip("\n".join(self._radky_napovedy()))

    # stav pro kreslení
    def zapnuto(self):
        return False

    def ma_fokus(self):
        return self.hasFocus()

    def focusInEvent(self, e):
        super().focusInEvent(e)
        self.update()

    def focusOutEvent(self, e):
        super().focusOutEvent(e)
        self.update()

    def zona(self):
        """Plocha obsahu nad popiskem."""
        return QRectF(OKRAJ, OKRAJ, self.width() - 2 * OKRAJ, self.height() - OKRAJ - POPISEK_V - 2)

    def kresli(self, p, zona):
        pass

    def _tecka(self):
        """Kreslit u popisku tečku zapnuto/vypnuto?"""
        return False

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        if not self.isEnabled():
            p.setOpacity(0.45)
        nad = self.underMouse() and self.isEnabled()
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        ramecek = QColor(theme.DLAZDICE_RAMECEK_HOVER if nad else theme.DLAZDICE_RAMECEK)
        p.setBrush(QColor(theme.DLAZDICE_POZADI_HOVER if nad else theme.DLAZDICE_POZADI))
        p.setPen(QPen(ramecek, 1))
        p.drawRoundedRect(r, theme.RADIUS_PRVEK, theme.RADIUS_PRVEK)
        if self.zapnuto():
            p.setBrush(QColor(*theme.DLAZDICE_ZAPNUTO))
            p.setPen(QPen(QColor(theme.DLAZDICE_FOKUS), 1))
            p.drawRoundedRect(r, theme.RADIUS_PRVEK, theme.RADIUS_PRVEK)
        if self.ma_fokus():
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(QColor(theme.DLAZDICE_FOKUS), 1.5))
            p.drawRoundedRect(r.adjusted(0.25, 0.25, -0.25, -0.25), theme.RADIUS_PRVEK, theme.RADIUS_PRVEK)
        self.kresli(p, self.zona())
        self._kresli_popisek(p, nad)
        p.end()

    def _kresli_popisek(self, p, nad):
        f = QFont(theme.PISMO_UI)
        f.setPointSizeF(8.5)
        p.setFont(f)
        fm = QFontMetricsF(f)
        r = QRectF(OKRAJ, self.height() - POPISEK_V - 1, self.width() - 2 * OKRAJ, POPISEK_V - 2)
        tecka = 11 if self._tecka() else 0
        text = fm.elidedText(self._popisek, Qt.ElideRight, r.width() - tecka)
        sirka = fm.horizontalAdvance(text) + tecka
        x = r.center().x() - sirka / 2
        if tecka:
            stred = QPointF(x + 3.5, r.center().y() + 0.5)
            if self.zapnuto():
                p.setPen(Qt.NoPen)
                p.setBrush(QColor(theme.DLAZDICE_FOKUS))
                p.drawEllipse(stred, 3.5, 3.5)
            else:
                p.setBrush(Qt.NoBrush)
                p.setPen(QPen(QColor(theme.TEXT_3), 1.4))
                p.drawEllipse(stred, 3, 3)
        svetle = nad or self.zapnuto() or self.ma_fokus()
        p.setPen(QColor(theme.DLAZDICE_HODNOTA if svetle else theme.DLAZDICE_POPISEK))
        p.drawText(QRectF(x + tecka, r.top(), sirka - tecka + 1, r.height()), Qt.AlignVCenter | Qt.AlignLeft, text)


class _Krok(QAbstractButton):
    """Tlačítko − nebo + na číselné dlaždici (při držení opakuje)."""

    def __init__(self, rodic, smer):
        super().__init__(rodic)
        self.smer = smer
        self.setFixedSize(KROK_V, KROK_V)
        self.setFocusPolicy(Qt.NoFocus)
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_Hover)
        self.setAutoRepeat(True)
        self.setAutoRepeatDelay(350)
        self.setAutoRepeatInterval(70)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        nad = self.underMouse() and self.isEnabled()
        if nad:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(*theme.SPIN_STISK) if self.isDown() else QColor(theme.DLAZDICE_RAMECEK))
            p.drawRoundedRect(QRectF(self.rect()).adjusted(1, 1, -1, -1), 5, 5)
        barva = theme.SPIN_SIPKA_OFF if not self.isEnabled() else (theme.DLAZDICE_KROK_HOVER if nad
                                                                    else theme.DLAZDICE_KROK)
        pero = QPen(QColor(barva), 1.8)
        pero.setCapStyle(Qt.RoundCap)
        p.setPen(pero)
        s = QPointF(self.width() / 2, self.height() / 2)
        p.drawLine(QPointF(s.x() - 4.5, s.y()), QPointF(s.x() + 4.5, s.y()))
        if self.smer > 0:
            p.drawLine(QPointF(s.x(), s.y() - 4.5), QPointF(s.x(), s.y() + 4.5))
        p.end()


class _Editor(QLineEdit):
    """Pole pro zapsání přesné hodnoty přímo na dlaždici. Esc = zrušit (klávesu jinak sní kolecko.py)."""

    def __init__(self, rodic):
        super().__init__(rodic)
        self.zruseno = False
        self.setObjectName("dlazdiceEditor")
        self.setAlignment(Qt.AlignCenter)
        self.setFrame(False)

    def event(self, e):
        if e.type() in (QEvent.ShortcutOverride, QEvent.KeyPress) and e.key() == Qt.Key_Escape:
            self.zruseno = True
        return super().event(e)

    def keyPressEvent(self, e):
        super().keyPressEvent(e)
        if e.key() in (Qt.Key_Return, Qt.Key_Enter):
            e.accept()  # jinak by Enter doputoval k dlaždici a ta by zápis hned otevřela znovu


class DlazdiceHodnota(Dlazdice):
    """Dlaždice, které po kliknutí (fokus = modrý obrys) mění kolečko myši – kolecko.py je podle názvu
    této třídy řadí mezi „pole“ (bez fokusu kolečko posouvá panel, klik mimo nebo Esc fokus zruší)."""

    def __init__(self, zdroj, popisek, napoveda=None):
        super().__init__(zdroj, popisek, napoveda)
        self.setFocusPolicy(Qt.StrongFocus)


class DlazdiceCislo(DlazdiceHodnota):
    """Číslo s jednotkou a tlačítky − / +. symbol(p, r, styl, hodnota) = volitelná ukázka nad číslem.
    value()/setValue() pracují se zobrazenou hodnotou (jako číselné pole), do stylu jde hodnota / meritko."""

    def __init__(self, zdroj, popisek, od, do, krok=1, *, desetinna=0, meritko=1, jednotka="", symbol=None,
                 specialni=None, znamenko=False, napoveda=None):
        super().__init__(zdroj, popisek, napoveda)
        self.od, self.do, self.krok = float(od), float(do), float(krok)
        self.desetinna, self.meritko, self.jednotka = desetinna, meritko, jednotka
        self.symbol, self.specialni, self.znamenko = symbol, specialni, znamenko
        self._v = float(od)
        self.editor = None
        self._stisk_cisla = False
        self.minus, self.plus = _Krok(self, -1), _Krok(self, +1)
        self.minus.clicked.connect(lambda: self.krokuj(-1))
        self.plus.clicked.connect(lambda: self.krokuj(+1))
        self._obnov_tlacitka()

    def _radky_napovedy(self):
        return super()._radky_napovedy() + [t("dlazdice.tip_cislo")]

    # hodnota
    def value(self):
        return self._v

    def setValue(self, v, vyslat=True):
        v = round(min(max(float(v), self.od), self.do), self.desetinna)
        if abs(v - self._v) < 1e-9:
            return
        self._v = v
        self._obnov_tlacitka()
        self.update()
        if vyslat:
            self.zmena.emit(self.hodnota())

    def hodnota(self):
        """Hodnota v jednotkách stylu."""
        if self.meritko != 1:
            return round(self._v / self.meritko, 4)
        return self._v if self.desetinna else int(round(self._v))

    def nastav_hodnotu(self, h):
        self.setValue(h * self.meritko, vyslat=False)

    def krokuj(self, kolikrat):
        if self.editor is not None:  # − / +, kolečko nebo šipka během zápisu: nejdřív potvrdit zapsané číslo
            self._konec_upravy()
        self.setValue(self._v + kolikrat * self.krok)

    def _obnov_tlacitka(self):
        self.minus.setEnabled(self._v > self.od + 1e-9)
        self.plus.setEnabled(self._v < self.do - 1e-9)

    def text_cisla(self):
        if self.specialni and abs(self._v - self.od) < 1e-9:
            return self.specialni()
        jazyk = QLocale()
        s = jazyk.toString(float(self._v), "f", self.desetinna)
        if self.desetinna and jazyk.decimalPoint() in s:
            s = s.rstrip("0").rstrip(jazyk.decimalPoint())
        return f"+{s}" if self.znamenko and self._v > 0 else s

    def text_jednotky(self):
        return "" if self.specialni and abs(self._v - self.od) < 1e-9 else self.jednotka

    # rozmístění
    def zony(self):
        """(plocha ukázky nebo None, řádek s číslem a tlačítky)."""
        z = self.zona()
        if self.symbol is None:
            return None, z
        return (QRectF(z.left(), z.top(), z.width(), z.height() - KROK_V - 2),
                QRectF(z.left(), z.bottom() - KROK_V, z.width(), KROK_V))

    def _plocha_cisla(self):
        r = self.zony()[1]
        return QRectF(r.left() + KROK_V, r.top(), r.width() - 2 * KROK_V, r.height())

    def _rozmisti(self):
        r = self.zony()[1]
        y = round(r.center().y() - KROK_V / 2)
        self.minus.move(round(r.left()), y)
        self.plus.move(round(r.right() - KROK_V), y)
        self._umisti_editor()

    def _umisti_editor(self):
        """Pole pro zápis hodnoty: nízké, vystředěné v ploše čísla."""
        if self.editor is not None:
            r = self._plocha_cisla()
            vyska = min(r.height(), 26.0)
            self.editor.setGeometry(QRectF(r.left() + 1, r.center().y() - vyska / 2, r.width() - 2,
                                           vyska).toRect())

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._rozmisti()

    def ma_fokus(self):
        return self.hasFocus() or self.editor is not None

    # kreslení
    def kresli(self, p, zona):
        plocha_symbolu, _ = self.zony()
        if plocha_symbolu is not None:
            p.save()
            self.symbol(p, plocha_symbolu, self.zdroj.styl, self._v)
            p.restore()
        if self.editor is not None:
            return
        r = self._plocha_cisla()
        cislo, jednotka = self.text_cisla(), self.text_jednotky()
        velikost = min(17.0, max(12.0, r.height() * 0.5))  # samotné číslo velké, pod ukázkou menší
        while True:  # zmenšit, dokud se číslo s jednotkou nevejde mezi tlačítka
            f = QFont(theme.PISMO_UI)
            f.setPointSizeF(velikost)
            f.setWeight(QFont.DemiBold)
            fj = QFont(theme.PISMO_UI)
            fj.setPointSizeF(max(velikost * 0.62, 8.0))
            sc = QFontMetricsF(f).horizontalAdvance(cislo)
            sj = QFontMetricsF(fj).horizontalAdvance(" " + jednotka) if jednotka else 0
            if sc + sj <= r.width() or velikost <= 9.0:
                break
            velikost -= 1.0
        if sc + sj > r.width():  # ani nejmenší písmo nestačí – jednotka se vynechá
            jednotka, sj = "", 0
        x = r.center().x() - (sc + sj) / 2
        fm = QFontMetricsF(f)
        ucari = r.center().y() + (fm.capHeight()) / 2  # číslice vystředěné svisle, jednotka na stejné účaří
        p.setFont(f)
        p.setPen(QColor(theme.DLAZDICE_HODNOTA))
        p.drawText(QPointF(x, ucari), cislo)
        if jednotka:
            p.setFont(fj)
            p.setPen(QColor(theme.DLAZDICE_JEDNOTKA))
            p.drawText(QPointF(x + sc, ucari), " " + jednotka)

    # ovládání
    def mousePressEvent(self, e):
        self._stisk_cisla = e.button() == Qt.LeftButton and self._plocha_cisla().contains(e.position())
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        if self._stisk_cisla and self._plocha_cisla().contains(e.position()):
            self.uprav()
        self._stisk_cisla = False
        super().mouseReleaseEvent(e)

    def wheelEvent(self, e):
        d = e.angleDelta().y()
        if d:
            self.krokuj(1 if d > 0 else -1)
        e.accept()

    def keyPressEvent(self, e):
        k = e.key()
        if k in (Qt.Key_Up, Qt.Key_Right, Qt.Key_Plus):
            self.krokuj(1)
        elif k in (Qt.Key_Down, Qt.Key_Left, Qt.Key_Minus):
            self.krokuj(-1)
        elif k == Qt.Key_PageUp:
            self.krokuj(10)
        elif k == Qt.Key_PageDown:
            self.krokuj(-10)
        elif k in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_F2):
            self.uprav()
        elif e.text() and e.text() in "0123456789,.":
            self.uprav(e.text())
        else:
            super().keyPressEvent(e)

    def uprav(self, text=None):
        """Zapsání přesné hodnoty: Enter nebo klik jinam potvrdí, Esc zruší."""
        if self.editor is not None:
            return
        ed = self.editor = _Editor(self)
        f = QFont(theme.PISMO_UI)
        f.setPointSizeF(11)
        ed.setFont(f)
        if text is None:
            jazyk = QLocale()
            s = jazyk.toString(float(self._v), "f", self.desetinna)
            if self.desetinna and jazyk.decimalPoint() in s:
                s = s.rstrip("0").rstrip(jazyk.decimalPoint())
            ed.setText(s)
            ed.selectAll()
        else:
            ed.setText(text)
        ed.editingFinished.connect(self._konec_upravy)
        self._rozmisti()
        ed.show()
        ed.setFocus()
        self.update()

    def _konec_upravy(self):
        ed, self.editor = self.editor, None
        if ed is None:
            return
        ed.blockSignals(True)
        mel_fokus = ed.hasFocus()
        if not ed.zruseno:
            # snese i „10,5 %“ nebo „+20 ms“ – bere první číslo v textu
            text = ed.text().replace(",", ".").replace("−", "-").replace(" ", "")
            cislo = re.search(r"[-+]?\d+(?:\.\d+)?", text)
            if cislo:
                self.setValue(float(cislo.group()))
        ed.hide()
        ed.deleteLater()
        if mel_fokus:
            self.setFocus()  # po Enteru zůstane dlaždice aktivní (kolečko, šipky)
        self.update()


class DlazdicePozice(DlazdiceCislo):
    """Pozice titulku v jedné ose (osa „x“ = vodorovně, „y“ = svisle): vlevo malá obrazovka ve tvaru videa
    s titulkem na jeho skutečném místě (jde táhnout myší ve směru osy), vpravo číslo v % a tlačítka − / +."""

    def __init__(self, zdroj, popisek, osa="y", napoveda=None):
        super().__init__(zdroj, popisek, 0, 100, 1, desetinna=1, meritko=100, jednotka="%",
                         symbol=self._obrazovka, napoveda=napoveda)
        self.osa = osa
        self._tah = False

    def zony(self):
        z = self.zona()
        sirka = min(max(z.height() * self.zdroj.pomer, 24.0), z.width() * 0.42)
        return (QRectF(z.left(), z.top(), sirka, z.height()),
                QRectF(z.left() + sirka + 4, z.top(), z.width() - sirka - 4, z.height()))

    def _plocha_cisla(self):
        r = self.zony()[1]
        return QRectF(r.left(), r.top(), r.width(), r.height() - KROK_V)

    def _rozmisti(self):
        r = self.zony()[1]
        y = round(r.bottom() - KROK_V)
        self.minus.move(round(r.center().x() - KROK_V - 3), y)
        self.plus.move(round(r.center().x() + 3), y)
        self._umisti_editor()

    def _plocha_obrazovky(self):
        r = self.zony()[0]
        pomer = self.zdroj.pomer
        w, h = (r.width(), r.width() / pomer) if r.width() / pomer <= r.height() else (r.height() * pomer, r.height())
        return QRectF(r.center().x() - w / 2, r.center().y() - h / 2, w, h)

    def _obrazovka(self, p, _r, styl, hodnota):
        o = self._plocha_obrazovky()
        p.setPen(QPen(QColor(theme.DLAZDICE_RAMECEK_HOVER), 1))
        p.setBrush(QColor(theme.DLAZDICE_PLATNO))
        p.drawRoundedRect(o, 3, 3)
        # proužek = titulek; ve své ose podle hodnoty dlaždice, ve druhé podle stylu
        x = hodnota / 100 if self.osa == "x" else styl.pozice_x
        y = hodnota / 100 if self.osa == "y" else styl.pozice_y
        sirka, vyska = o.width() * 0.5, max(o.height() * 0.09, 3.0)
        stred_y = min(max(o.top() + o.height() * y, o.top() + vyska / 2 + 1), o.bottom() - vyska / 2 - 1)
        titulek = QRectF(o.left() + o.width() * x - sirka / 2, stred_y - vyska / 2, sirka, vyska)
        p.setClipRect(o.adjusted(1, 1, -1, -1))  # titulek u kraje přesahuje z obrazu stejně jako ve videu
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(*theme.DLAZDICE_STIN))
        p.drawRoundedRect(titulek.translated(0, 1), 1.5, 1.5)
        p.setBrush(_barva(styl.barva_textu))
        p.drawRoundedRect(titulek, 1.5, 1.5)

    def prekresli_obrazovku(self):
        """Po změně poměru stran videa (zdroj.pomer): jiná šířka obrazovky posune i číslo s tlačítky."""
        self._rozmisti()
        self.update()

    def _podle_mysi(self, e):
        o = self._plocha_obrazovky()
        podil = ((e.position().x() - o.left()) / max(o.width(), 1) if self.osa == "x"
                 else (e.position().y() - o.top()) / max(o.height(), 1))
        self.setValue(round(podil * 100))

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and self.zony()[0].contains(e.position()):
            self._tah = True
            self._podle_mysi(e)
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._tah:
            self._podle_mysi(e)
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        self._tah = False
        super().mouseReleaseEvent(e)


class DlazdicePrepinac(Dlazdice):
    """Zapnuto / vypnuto jedním kliknutím. symbol(p, r, styl, zapnuto) kreslí ukázku."""

    def __init__(self, zdroj, popisek, symbol, napoveda=None):
        super().__init__(zdroj, popisek, napoveda)
        self.symbol = symbol
        self._v = False
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.TabFocus)

    def isChecked(self):
        return self._v

    def setChecked(self, v, vyslat=True):
        if bool(v) == self._v:
            return
        self._v = bool(v)
        self.update()
        if vyslat:
            self.zmena.emit(self._v)

    def nastav_hodnotu(self, h):
        self.setChecked(h, vyslat=False)

    def zapnuto(self):
        return self._v

    def _tecka(self):
        return True

    def kresli(self, p, zona):
        p.save()
        self.symbol(p, zona, self.zdroj.styl, self._v)
        p.restore()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and self.rect().contains(e.position().toPoint()):
            self.setChecked(not self._v)
        super().mouseReleaseEvent(e)

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_Space, Qt.Key_Return, Qt.Key_Enter):
            self.setChecked(not self._v)
        else:
            super().keyPressEvent(e)


class DlazdiceBarva(Dlazdice):
    """Barevný vzorek; kliknutím malá paleta častých barev a „Vlastní barva“ (plný výběr barvy)."""

    def __init__(self, zdroj, popisek, napoveda=None):
        super().__init__(zdroj, popisek, napoveda)
        self.hex = "FFFFFF"
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.TabFocus)

    def nastav_hodnotu(self, h):
        self.hex = str(h).upper()
        self._obnov_napovedu()
        self.update()

    def _radky_napovedy(self):
        return [f"{t(self._klic_popisku)} · #{getattr(self, 'hex', '')}"]

    def kresli(self, p, zona):
        r = zona.adjusted(8, 5, -8, -3)
        p.setPen(QPen(QColor(theme.DLAZDICE_RAMECEK_HOVER), 1))
        p.setBrush(_barva(self.hex))
        p.drawRoundedRect(r, 5, 5)

    def _zvol(self, hex_):
        if hex_.upper() != self.hex:
            self.nastav_hodnotu(hex_)
            self.zmena.emit(self.hex)

    def otevri(self):
        paleta = PaletaBarev(self, self.hex)
        paleta.vybrano.connect(self._zvol)
        paleta.vlastni.connect(self._vlastni)
        _ukaz_pod(paleta, self)

    def _vlastni(self):
        c = QColorDialog.getColor(_barva(self.hex), self.window(), t(self._klic_popisku))
        if c.isValid():
            self._zvol(c.name()[1:])

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and self.rect().contains(e.position().toPoint()):
            self.otevri()
        super().mouseReleaseEvent(e)

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_Space, Qt.Key_Return, Qt.Key_Enter):
            self.otevri()
        else:
            super().keyPressEvent(e)


class DlazdicePismo(Dlazdice):
    """„Aa“ ve zvoleném písmu a jeho název; kliknutím seznam písem s hledáním."""
    sloupcu = 2

    def __init__(self, zdroj, popisek, pisma, napoveda=None):
        super().__init__(zdroj, popisek, napoveda)
        self.pisma = list(pisma)    # nabídka (vlastní písma aplikace první)
        self.rodina = ""
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.TabFocus)

    def nastav_hodnotu(self, h):
        self.rodina = str(h)
        self.update()

    def kresli(self, p, zona):
        f = QFont(self.rodina)
        f.setPixelSize(int(zona.height() * 0.56))
        f.setBold(bool(self.zdroj.styl.tucne))
        ukazka = "AA" if self.zdroj.styl.velka_pismena else "Aa"
        sirka_ukazky = min(QFontMetricsF(f).horizontalAdvance(ukazka) + 6, zona.width() * 0.4)
        p.setFont(f)
        p.setPen(QColor(theme.DLAZDICE_HODNOTA))
        p.drawText(QRectF(zona.left() + 6, zona.top(), sirka_ukazky, zona.height()),
                   Qt.AlignVCenter | Qt.AlignLeft, ukazka)
        fn = QFont(theme.PISMO_UI)
        fn.setPointSizeF(9.5)
        p.setFont(fn)
        sipka = 14
        r = QRectF(zona.left() + sirka_ukazky + 14, zona.top(), zona.width() - sirka_ukazky - 18 - sipka,
                   zona.height())
        p.drawText(r, Qt.AlignVCenter | Qt.AlignLeft | Qt.TextWordWrap,
                   QFontMetricsF(fn).elidedText(self.rodina, Qt.ElideRight, r.width() * 2 - 12))
        # šipka dolů = otevře seznam
        s = QPointF(zona.right() - 9, zona.center().y())
        pero = QPen(QColor(theme.DLAZDICE_POPISEK), 1.6)
        pero.setCapStyle(Qt.RoundCap)
        pero.setJoinStyle(Qt.RoundJoin)
        p.setPen(pero)
        p.drawPolyline([QPointF(s.x() - 4, s.y() - 2), QPointF(s.x(), s.y() + 2), QPointF(s.x() + 4, s.y() - 2)])

    def _zvol(self, rodina):
        if rodina and rodina != self.rodina:
            self.nastav_hodnotu(rodina)
            self.zmena.emit(rodina)

    def otevri(self):
        vyber = VyberPisma(self, self.pisma, self.rodina)
        vyber.vybrano.connect(self._zvol)
        _ukaz_pod(vyber, self)
        vyber.hledat.setFocus()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and self.rect().contains(e.position().toPoint()):
            self.otevri()
        super().mouseReleaseEvent(e)

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_Space, Qt.Key_Return, Qt.Key_Enter):
            self.otevri()
        else:
            super().keyPressEvent(e)


# ---------- vysouvací prvky ----------
def _ukaz_pod(okno, dlazdice):
    """Ukáže vysouvací okno pod dlaždicí (nad ní, když se dolů nevejde), celé na obrazovce."""
    okno.adjustSize()
    bod = dlazdice.mapToGlobal(QPoint(0, dlazdice.height() + 3))
    obrazovka = QGuiApplication.screenAt(dlazdice.mapToGlobal(dlazdice.rect().center()))
    if obrazovka is not None:
        plocha = obrazovka.availableGeometry()
        if bod.y() + okno.height() > plocha.bottom():
            bod.setY(dlazdice.mapToGlobal(QPoint(0, 0)).y() - okno.height() - 3)
        bod.setX(max(plocha.left() + 4, min(bod.x(), plocha.right() - okno.width() - 4)))
        bod.setY(max(plocha.top() + 4, bod.y()))
    okno.move(bod)
    okno.show()


class _Vzorek(QAbstractButton):
    def __init__(self, hex_, vybrany):
        super().__init__()
        self.hex, self.vybrany = hex_, vybrany
        self.setFixedSize(30, 30)
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_Hover)
        self.setToolTip(f"#{hex_}")

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(3.5, 3.5, -3.5, -3.5)
        p.setPen(QPen(QColor(theme.DLAZDICE_RAMECEK_HOVER), 1))
        p.setBrush(_barva(self.hex))
        p.drawRoundedRect(r, 5, 5)
        if self.vybrany or self.underMouse() or self.hasFocus():  # vybraná barva = modrý rámeček (výběr)
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(QColor(theme.DLAZDICE_FOKUS if self.vybrany else theme.TEXT_2), 1.6))
            p.drawRoundedRect(QRectF(self.rect()).adjusted(1, 1, -1, -1), 7, 7)
        p.end()


class PaletaBarev(QFrame):
    """Malá paleta pod dlaždicí barvy: časté barvy titulků a tlačítko pro plný výběr barvy."""
    vybrano = Signal(str)
    vlastni = Signal()

    def __init__(self, rodic, aktualni):
        super().__init__(rodic, Qt.Popup)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setObjectName("dlazdiceVysuv")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(6)
        mrizka = QGridLayout()
        mrizka.setSpacing(2)
        for i, hex_ in enumerate(theme.PALETA_TITULKU):
            v = _Vzorek(hex_, hex_.upper() == aktualni.upper())
            v.clicked.connect(lambda _=False, h=hex_: self._hotovo(h))
            mrizka.addWidget(v, i // 5, i % 5)
        lay.addLayout(mrizka)
        dalsi = QPushButton(t("dlazdice.vlastni_barva"))
        dalsi.setCursor(Qt.PointingHandCursor)
        dalsi.clicked.connect(self._vlastni)
        lay.addWidget(dalsi)

    def _hotovo(self, hex_):
        self.close()
        self.vybrano.emit(hex_)

    def _vlastni(self):
        self.close()
        self.vlastni.emit()


@lru_cache(maxsize=None)
def _ma_latinku(rodina):
    return QFontDatabase.Latin in QFontDatabase.writingSystems(rodina)


class _DelegatPisma(QStyledItemDelegate):
    """Název písma napsaný tím písmem (symbolová písma bez latinky zůstanou v písmu rozhraní)."""

    def initStyleOption(self, volba, index):
        super().initStyleOption(volba, index)
        rodina = index.data()
        if rodina and _ma_latinku(rodina):
            f = QFont(rodina)
            f.setPointSizeF(11)
            volba.font = f

    def sizeHint(self, volba, index):
        return QSize(220, 30)


class VyberPisma(QFrame):
    """Seznam písem pod dlaždicí: hledání podle názvu, klik nebo Enter písmo použije."""
    vybrano = Signal(str)

    def __init__(self, rodic, pisma, aktualni):
        super().__init__(rodic, Qt.Popup)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setObjectName("dlazdiceVysuv")
        self.pisma = pisma
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(6)
        self.hledat = QLineEdit()
        self.hledat.setPlaceholderText(t("dlazdice.hledat_pismo"))
        self.hledat.setClearButtonEnabled(True)
        self.hledat.textChanged.connect(self._filtruj)
        self.hledat.installEventFilter(self)
        lay.addWidget(self.hledat)
        self.seznam = QListWidget()
        self.seznam.setObjectName("dlazdiceSeznam")
        self.seznam.setUniformItemSizes(True)
        self.seznam.setItemDelegate(_DelegatPisma(self.seznam))
        self.seznam.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.seznam.setFixedSize(max(rodic.width(), 250), 30 * 9 + 4)
        self.seznam.itemClicked.connect(lambda polozka: self._hotovo(polozka.text()))
        self.seznam.itemActivated.connect(lambda polozka: self._hotovo(polozka.text()))
        lay.addWidget(self.seznam)
        self._napln(pisma, aktualni)

    def _napln(self, pisma, vybrat=None):
        self.seznam.clear()
        for rodina in pisma:
            QListWidgetItem(rodina, self.seznam)
        radek = pisma.index(vybrat) if vybrat in pisma else (0 if pisma else -1)
        if radek >= 0:
            self.seznam.setCurrentRow(radek)
            self.seznam.scrollToItem(self.seznam.item(radek), QListWidget.PositionAtCenter)

    def _filtruj(self, text):
        hledane = text.strip().casefold()
        self._napln([r for r in self.pisma if hledane in r.casefold()] if hledane else self.pisma)

    def _hotovo(self, rodina):
        self.close()
        self.vybrano.emit(rodina)

    def eventFilter(self, obj, e):
        if obj is self.hledat and e.type() == QEvent.KeyPress:
            if e.key() in (Qt.Key_Down, Qt.Key_Up, Qt.Key_PageDown, Qt.Key_PageUp):
                self.seznam.keyPressEvent(e)  # šipky v poli hledání procházejí seznam
                return True
            if e.key() in (Qt.Key_Return, Qt.Key_Enter):
                polozka = self.seznam.currentItem()
                if polozka is not None:
                    self._hotovo(polozka.text())
                return True
        return super().eventFilter(obj, e)
