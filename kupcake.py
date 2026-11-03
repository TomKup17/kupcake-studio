"""Cupcake značky kupcake.studio: kresba (SVG) pro ikonu, logo i animaci.

Kreslený styl – zaoblené tvary, výrazné obrysy, plochá barva s jedním jemným odleskem. Poleva modrá
#00B4FF, třešnička oranžová #FF6A00, světlé detaily #F2EFEA. Na košíčku tři svislé proužky.
Vše v plátně 256 × 256; ikona přidá tmavý zaoblený čtverec, animace kreslí bez pozadí.
"""
import math

from PySide6.QtCore import QByteArray, QElapsedTimer, QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QWidget

POZADI = "#080808"
MODRA = "#00B4FF"
ORANZOVA = "#FF6A00"
SVETLA = "#F2EFEA"
TMAVA = "#2A2E35"
MALE = (16, 24)          # u nich jen silueta s třešničkou
VARIANTA = "C"           # vybraná varianta – ikona, logo i animace

KOSICEK = "M60,150 L196,150 L182,212 Q180,222 170,222 L86,222 Q76,222 74,212 Z"
PROUZKY = (100, 128, 156)  # tři svislé proužky na košíčku: střed x (výška 182–212)


def _poleva(varianta):
    """Tvary polevy (sjednotí se překrytím): okraj, tři „obláčky“ a vršek."""
    if varianta == "C":  # vyšší točená poleva ve dvou patrech
        return ('<ellipse cx="128" cy="148" rx="80" ry="20"/><circle cx="78" cy="134" r="27"/>'
                '<circle cx="178" cy="134" r="27"/><ellipse cx="128" cy="122" rx="62" ry="30"/>'
                '<ellipse cx="128" cy="96" rx="44" ry="22"/><ellipse cx="128" cy="78" rx="24" ry="14"/>')
    return ('<ellipse cx="128" cy="148" rx="80" ry="20"/><circle cx="78" cy="132" r="28"/>'
            '<circle cx="178" cy="132" r="28"/><circle cx="128" cy="118" r="40"/>'
            '<ellipse cx="128" cy="100" rx="36" ry="22"/>')


def _tresen_y(varianta):
    return 58 if varianta == "C" else 66


def _barvy(varianta):
    """(obrys, šířka obrysu, výplň košíčku, barva řádků)"""
    return {
        "A": (POZADI, 9, TMAVA, SVETLA),      # tmavé obrysy oddělují tvary, světlé proužky
        "B": (SVETLA, 6, POZADI, SVETLA),     # světlá kresba linkou, košíček průhledný
        "C": (POZADI, 9, SVETLA, TMAVA),      # světlý košíček s tmavými proužky
    }[varianta]


def _obrysene(tvary, vypln, obrys, sirka):
    """Kreslený obrys celé skupiny: nejdřív tvary tlustou čarou, pak stejné tvary výplní."""
    return (f'<g fill="{obrys}" stroke="{obrys}" stroke-width="{sirka * 2}" stroke-linejoin="round">{tvary}</g>'
            f'<g fill="{vypln}">{tvary}</g>')


def telo(varianta=VARIANTA, n=256):
    """Košíček a poleva (bez třešničky)."""
    if n in MALE:  # silueta: světlý košíček, modrá poleva, bez obrysů a řádků
        return (f'<path d="{KOSICEK}" fill="{SVETLA}"/>'
                f'<rect x="38" y="94" width="180" height="68" rx="34" fill="{MODRA}"/>')
    obrys, sirka, vypln_kosicku, barva_radku = _barvy(varianta)
    radky = "".join(f'<rect x="{x - 5}" y="182" width="10" height="30" rx="5"/>' for x in PROUZKY)
    return (_obrysene(f'<path d="{KOSICEK}"/>', vypln_kosicku, obrys, sirka)
            + f'<g fill="{barva_radku}">{radky}</g>'
            + _obrysene(_poleva(varianta), MODRA, obrys, sirka)
            # jediný jemný odlesk na polevě
            + f'<path d="M84,124 Q92,104 112,98" fill="none" stroke="{SVETLA}" stroke-opacity="0.55" '
              f'stroke-width="8" stroke-linecap="round"/>')


def tresen(varianta=VARIANTA, n=256, dy=0.0):
    """Třešnička se stopkou; dy = posun nahoru při poskakování (v jednotkách plátna)."""
    y = _tresen_y(varianta) - dy
    if n in MALE:
        return f'<circle cx="128" cy="{y + 6}" r="28" fill="{ORANZOVA}"/>'
    obrys, sirka, _, _ = _barvy(varianta)
    stopka = f'M128,{y - 14} Q132,{y - 34} 150,{y - 40}'
    # pořadí: obrys stopky, obrys třešně, světlá stopka (napojí se na třešeň), výplň třešně
    return (f'<path d="{stopka}" fill="none" stroke="{obrys}" stroke-width="{6 + sirka * 2}" stroke-linecap="round"/>'
            f'<circle cx="128" cy="{y}" r="{19 + sirka}" fill="{obrys}"/>'
            f'<path d="{stopka}" fill="none" stroke="{SVETLA}" stroke-width="6" stroke-linecap="round"/>'
            f'<circle cx="128" cy="{y}" r="19" fill="{ORANZOVA}"/>'
            f'<circle cx="121" cy="{y - 6}" r="5" fill="{SVETLA}" fill-opacity="0.75"/>')


def svg(varianta=VARIANTA, n=256, pozadi=True, casti=("telo", "tresen"), dy=0.0):
    obsah = ""
    if "telo" in casti:
        obsah += telo(varianta, n)
    if "tresen" in casti:
        obsah += tresen(varianta, n, dy)
    # cupcake je v plátně výš (kvůli třešničce) – posun dolů, ať sedí opticky na střed
    obsah = f'<g transform="translate(0,8)">{obsah}</g>'
    if pozadi:
        obsah = f'<rect width="256" height="256" rx="56" fill="{POZADI}"/>' + obsah
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{n}" height="{n}" viewBox="0 0 256 256">'
            f'{obsah}</svg>')


def vykresli(svg_text, n):
    pix = QPixmap(n, n)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    QSvgRenderer(QByteArray(svg_text.encode())).render(p, QRectF(0, 0, n, n))
    p.end()
    return pix


def pixmapa(velikost, pozadi=False, varianta=VARIANTA):
    """Statický cupcake (logo v záhlaví); ostrý i na displejích s vyšším DPI."""
    pix = vykresli(svg(varianta, 256, pozadi), velikost * 2)
    pix.setDevicePixelRatio(2)
    return pix


# ---------- animace: třešnička poskakuje, kolem probliknou modré jiskřičky ----------
SMYCKA_MS = 1200
JISKRY = ((0.16, 0.30, 0.00), (0.86, 0.22, 0.33), (0.80, 0.62, 0.62), (0.12, 0.66, 0.80))  # (x, y, fáze)


class Kresba:
    """Předkreslené vrstvy (tělo, třešnička) pro danou velikost – snímek animace je jen skládání pixmap."""

    def __init__(self, velikost, varianta=VARIANTA):
        self.n = velikost
        dpr = 2
        self.telo = vykresli(svg(varianta, 256, False, ("telo",)), velikost * dpr)
        self.tresen = vykresli(svg(varianta, 256, False, ("tresen",)), velikost * dpr)
        for pix in (self.telo, self.tresen):
            pix.setDevicePixelRatio(dpr)

    def kresli(self, p, stred, cas_ms):
        """Nakreslí snímek animace se středem v bodě `stred` (QPointF) v čase `cas_ms`."""
        t = (cas_ms % SMYCKA_MS) / SMYCKA_MS
        n = self.n
        x0, y0 = stred.x() - n / 2, stred.y() - n / 2
        # poskok: v první polovině smyčky nahoru a dolů (ease), pak klid
        skok = math.sin(min(t / 0.5, 1.0) * math.pi) ** 2 if t < 0.5 else 0.0
        p.drawPixmap(QPointF(x0, y0), self.telo)
        p.drawPixmap(QPointF(x0, y0 - skok * n * 0.07), self.tresen)
        p.save()
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        for jx, jy, faze in JISKRY:
            f = (t - faze) % 1.0
            if f > 0.3:  # každá jiskra svítí jen krátce
                continue
            sila = math.sin(f / 0.3 * math.pi)
            c = QColor(MODRA)
            c.setAlphaF(sila)
            p.setBrush(c)
            p.drawPath(_jiskra(QPointF(x0 + jx * n, y0 + jy * n), n * 0.07 * (0.6 + 0.4 * sila)))
        p.restore()


def _jiskra(stred, r):
    """Čtyřcípá jiskřička s prohnutými stranami."""
    c, k = stred, r * 0.25
    path = QPainterPath(QPointF(c.x(), c.y() - r))
    for (ax, ay), (bx, by) in (((k, -k), (r, 0)), ((k, k), (0, r)), ((-k, k), (-r, 0)), ((-k, -k), (0, -r))):
        path.quadTo(QPointF(c.x() + ax, c.y() + ay), QPointF(c.x() + bx, c.y() + by))
    return path


class CupcakeAnimace(QWidget):
    """Animovaný cupcake (přepis, export, prázdný náhled, O aplikaci). Běží jen, když je vidět."""

    def __init__(self, velikost=24, parent=None):
        super().__init__(parent)
        self.setFixedSize(velikost, velikost)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.kresba = Kresba(velikost)
        self.hodiny = QElapsedTimer()
        self.casovac = QTimer(self)
        self.casovac.setInterval(16)
        self.casovac.timeout.connect(self.update)

    def showEvent(self, e):
        self.hodiny.start()
        self.casovac.start()
        super().showEvent(e)

    def hideEvent(self, e):
        self.casovac.stop()
        super().hideEvent(e)

    def paintEvent(self, e):
        p = QPainter(self)
        self.kresba.kresli(p, QPointF(self.width() / 2, self.height() / 2),
                           self.hodiny.elapsed() if self.hodiny.isValid() else 0)
        p.end()
