"""Časová osa: slova jako boxy (QGraphicsScene), zvuková vlna, měřítko, přehrávací hlava s časovým kódem,
smyčka, značky a přichytávání. Úpravy struktury (skupiny, řezy, mazání…) dělá okno přes modul upravy."""
import math

import numpy as np
from PySide6.QtCore import QLineF, QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QFontMetrics, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import (QFrame, QGraphicsItem, QGraphicsLineItem, QGraphicsScene, QGraphicsView,
                               QHBoxLayout, QLineEdit, QSizePolicy, QStyle, QToolButton, QVBoxLayout, QWidget)

import theme
from i18n import t as tr  # `t` je tu často proměnná (titulek)
from titulky import MIN_SLOVO, srovnej

VLNA_RATE = 200          # počet vzorků obálky zvuku za sekundu
H_PRAVITKO = 26
Y_PAS = 30               # pás titulku (skupina slov)
Y_SLOVO = 34
H_VLNA = 78
OKRAJ_PX = 7             # šířka „úchytu“ na okraji boxu
SNAP_PX = 8              # vzdálenost přichycení
MIN_PPS, MAX_PPS = 8, 2500
VYSKY_STOPY = (40, 76)   # normální / vyšší stopa (Ctrl+H)

BARVY = theme.SKUPINY            # barvy skupin slov (titulků) – střídají se, sousední se liší
BARVA_ZNACKY = theme.OSA_ZNACKA   # oranžová značky (markery)
ZAR = 5                           # okraj pro záři kolem označeného slova (px)


def vlna_z_audia(audio, rate=16000):
    """Obálka zvuku: maximum |amplitudy| v okně 1/VLNA_RATE s, normalizovaná na 0–1."""
    krok = rate // VLNA_RATE
    n = len(audio) // krok
    if n == 0:
        return np.zeros(1, dtype=np.float32)
    env = np.abs(audio[: n * krok].reshape(n, krok)).max(axis=1)
    strop = np.percentile(env, 99.5) or 1.0
    return np.clip(env / strop, 0, 1).astype(np.float32)


def fmt_meritko(t, krok):
    m, s = divmod(t, 60)
    if krok < 1:
        return f"{int(m)}:{s:04.1f}"
    return f"{int(m)}:{int(round(s)):02d}"


def casovy_kod(t, fps):
    """HH:MM:SS:snímky."""
    t = max(t, 0.0)
    s = int(t + 1e-9)
    f = min(int((t - s) * fps + 1e-6), max(int(round(fps)) - 1, 0))
    return f"{s // 3600:02d}:{s // 60 % 60:02d}:{s % 60:02d}:{f:02d}"


class Pravitko(QGraphicsItem):
    def __init__(self, osa):
        super().__init__()
        self.osa = osa
        self.setFlag(QGraphicsItem.ItemUsesExtendedStyleOption)
        self.setZValue(5)

    def boundingRect(self):
        return QRectF(0, 0, self.osa.sirka(), H_PRAVITKO)

    def paint(self, p, opt, w=None):
        r = opt.exposedRect
        pps = self.osa.pps
        p.fillRect(QRectF(r.left(), 0, r.width(), H_PRAVITKO), QColor(theme.PANEL))
        if self.osa.smycka:  # úsek smyčky v měřítku – poloprůhledná oranžová (pod čárkami a popisky)
            a, b = self.osa.smycka
            c = QColor(theme.OSA_SMYCKA)
            c.setAlpha(theme.OSA_SMYCKA_ALFA["meritko"][0 if self.osa.smycka_zapnuta else 1])
            p.fillRect(QRectF(a * pps, 0, max((b - a) * pps, 1), H_PRAVITKO), c)
        p.setPen(QColor(theme.RAMECEK))
        p.drawLine(QLineF(r.left(), H_PRAVITKO - 0.5, r.right(), H_PRAVITKO - 0.5))
        # hlavní krok tak, aby popisky byly aspoň ~90 px od sebe
        krok = next((k for k in (0.1, 0.2, 0.5, 1, 2, 5, 10, 15, 30, 60, 120, 300) if k * pps >= 90), 600)
        jemny = krok / (5 if krok in (0.5, 5, 15) else 10 if krok in (1, 10, 60) else 4 if krok == 2 else 5)
        p.setFont(theme.pismo_mono(8))
        # i popisky začínající kousek vlevo od překreslované oblasti – jinak by je výplň useknula
        t0, t1 = max((r.left() - 80) / pps, 0), min(r.right() / pps, self.osa.delka)
        i = math.floor(t0 / jemny)
        while i * jemny <= t1 + 1e-9:
            t = i * jemny
            x = t * pps
            hlavni = abs(t / krok - round(t / krok)) < 1e-6
            p.setPen(QColor(theme.TEXT_2) if hlavni else QColor(theme.POLE_RAMECEK))
            p.drawLine(QLineF(x, H_PRAVITKO - (11 if hlavni else 5), x, H_PRAVITKO))
            if hlavni:
                p.setPen(QColor(theme.TEXT_2))
                p.drawText(QPointF(x + 3, 12), fmt_meritko(t, krok))
            i += 1


class Vlna(QGraphicsItem):
    def __init__(self, osa):
        super().__init__()
        self.osa = osa
        self.setFlag(QGraphicsItem.ItemUsesExtendedStyleOption)

    def boundingRect(self):
        return QRectF(0, self.osa.y_vlna, self.osa.sirka(), H_VLNA)

    def paint(self, p, opt, w=None):
        r = opt.exposedRect
        y = self.osa.y_vlna
        p.fillRect(QRectF(r.left(), y, r.width(), H_VLNA), QColor(theme.POZADI))
        stred = y + H_VLNA / 2
        p.setPen(QColor(theme.RAMECEK))
        p.drawLine(QLineF(r.left(), stred, r.right(), stred))
        env = self.osa.vlna
        if env is None:
            p.setPen(QColor(theme.TEXT_3))
            p.drawText(QRectF(r.left(), y, min(r.width(), 400), H_VLNA), Qt.AlignVCenter,
                       "  " + tr("osa.nacitam_vlnu"))
            return
        pps = self.osa.pps
        x0, x1 = max(int(r.left()), 0), min(int(r.right()) + 1, int(self.osa.sirka()))
        if x1 <= x0:
            return
        # pro každý sloupec pixelů maximum z jeho úseku obálky (při velkém zoomu 1 vzorek)
        xs = np.arange(x0, x1 + 1)
        idx = np.clip((xs / pps * VLNA_RATE).astype(np.int64), 0, len(env) - 1)
        hodnoty = np.maximum.reduceat(env, idx)[:-1]
        pul = H_VLNA / 2 - 3
        p.setPen(QPen(QColor(theme.VLNA), 1))
        p.drawLines([QLineF(x0 + i + 0.5, stred - v * pul, x0 + i + 0.5, stred + v * pul)
                     for i, v in enumerate(hodnoty) if v > 0.004])


class PasItem(QGraphicsItem):
    """Podklad titulku – ukazuje, odkud kam je titulek na obrazovce (včetně dozvuku)."""

    def __init__(self, osa, titulek, barva):
        super().__init__()
        self.osa, self.titulek, self.barva = osa, titulek, QColor(barva)
        self.w = 1.0
        self.setZValue(1)
        self.obnov()

    def obnov(self):
        self.prepareGeometryChange()
        self.w = max((self.titulek.end - self.titulek.start) * self.osa.pps, 1.0)
        self.setPos(self.titulek.start * self.osa.pps, Y_PAS)

    def boundingRect(self):
        return QRectF(0, 0, self.w, self.osa.h_pas)

    def paint(self, p, opt, w=None):
        p.setRenderHint(QPainter.Antialiasing)
        vypln = QColor(self.barva)
        vypln.setAlpha(45)
        okraj = QColor(self.barva)
        okraj.setAlpha(150)
        p.setPen(QPen(okraj, 1, Qt.DashLine if self.titulek.zamceno else Qt.SolidLine))
        p.setBrush(vypln)
        p.drawRoundedRect(QRectF(0.5, 0.5, self.w - 1, self.osa.h_pas - 1), 6, 6)


ZAMEK_PX = 10
_zamek = []


def ikona_zamku():
    """Oranžový zámek (pixmapa se vytvoří jednou, kreslí se v paint() každého zamčeného titulku)."""
    if not _zamek:
        _zamek.append(theme.ikona("zamek.svg", theme.OSA_ZAMEK, ZAMEK_PX).pixmap(ZAMEK_PX * 2, ZAMEK_PX * 2))
    return _zamek[0]


class SlovoItem(QGraphicsItem):
    def __init__(self, osa, slovo, titulek, barva):
        super().__init__()
        self.osa, self.slovo, self.titulek, self.barva = osa, slovo, titulek, QColor(barva)
        self.w = 1.0
        self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.setAcceptHoverEvents(True)
        self.setZValue(2)
        self.obnov()

    def obnov(self):
        self.prepareGeometryChange()
        self.w = max((self.slovo.end - self.slovo.start) * self.osa.pps, 2.0)
        self.setPos(self.slovo.start * self.osa.pps, Y_SLOVO)

    def boundingRect(self):  # s okrajem pro záři označeného slova
        return QRectF(-ZAR, -ZAR, self.w + 2 * ZAR, self.osa.h_slovo + 2 * ZAR)

    def shape(self):  # klikatelný a vybíratelný je jen samotný box
        from PySide6.QtGui import QPainterPath
        cesta = QPainterPath()
        cesta.addRect(QRectF(0, 0, self.w, self.osa.h_slovo))
        return cesta

    def zona(self, x):
        e = min(OKRAJ_PX, self.w / 3)
        if x <= e:
            return "zacatek"
        if x >= self.w - e:
            return "konec"
        return "posun"

    def hoverMoveEvent(self, e):
        if self.titulek.zamceno:
            self.setCursor(Qt.ForbiddenCursor)
            return
        z = self.zona(e.pos().x())
        self.setCursor(Qt.SizeHorCursor if z != "posun" else Qt.OpenHandCursor)

    def paint(self, p, opt, w=None):
        p.setRenderHint(QPainter.Antialiasing)
        h = self.osa.h_slovo
        vybrano = bool(opt.state & QStyle.State_Selected)
        vypln = self.barva.lighter(118) if vybrano else QColor(self.barva)
        if self.titulek.zamceno:
            vypln.setAlpha(150)
        p.setPen(QPen(self.barva.lighter(125), 1))
        p.setBrush(vypln)
        p.drawRoundedRect(QRectF(0.5, 0.5, self.w - 1, h - 1), 4, 4)
        if vybrano:  # označené slovo: modrý rámeček s jemnou září
            theme.zar(p, QRectF(0.5, 0.5, self.w - 1, h - 1), radius=4)
        if self.osa.prave_hraje is self:  # právě přehrávané slovo: tenká oranžová linka pod boxem
            pero = QPen(QColor(theme.OSA_PRAVE_HRAJE), 2)
            pero.setCapStyle(Qt.RoundCap)
            p.setPen(pero)
            p.drawLine(QLineF(2, h + 3, max(self.w - 2, 3), h + 3))
        odsazeni = 4
        if self.titulek.zamceno:  # šrafování = zamčeno
            p.setBrush(QBrush(QColor(0, 0, 0, 70), Qt.BDiagPattern))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(QRectF(1, 1, self.w - 2, h - 2), 4, 4)
            if self.titulek.slova and self.titulek.slova[0] is self.slovo and self.w > 16:
                # malá oranžová ikonka zámku u prvního slova zamčeného titulku
                zamek = ikona_zamku()
                p.drawPixmap(QRectF(3, (h - ZAMEK_PX) / 2, ZAMEK_PX, ZAMEK_PX), zamek, QRectF(zamek.rect()))
                odsazeni = 4 + ZAMEK_PX
        if self.w > 14 + odsazeni - 4:
            p.setPen(QColor(theme.TEXT))
            p.setFont(self.osa.font_slov)
            ramec = QRectF(odsazeni, 2, self.w - odsazeni - 4, h - 4)
            if self.osa.velka_stopa:  # vyšší stopa – dlouhá slova se zalomí na víc řádků
                p.drawText(ramec, Qt.AlignVCenter | Qt.AlignLeft | Qt.TextWrapAnywhere, self.slovo.text)
            else:
                text = QFontMetrics(self.osa.font_slov).elidedText(self.slovo.text, Qt.ElideRight, int(ramec.width()))
                p.drawText(ramec, Qt.AlignVCenter | Qt.AlignLeft, text)


HLAVA_UCHYT = 7          # polovina šířky úchytu přehrávací hlavy v měřítku (px)


class HlavaItem(QGraphicsItem):
    """Přehrávací hlava (oranžová): čára 2 px se září přes celou osu, úchyt v měřítku (za něj jde hlavu
    chytit a táhnout – stejně jako kdekoli v měřítku) a štítek s časovým kódem HH:MM:SS:snímky."""

    def __init__(self, osa):
        super().__init__()
        self.osa = osa
        self.setZValue(100)

    def boundingRect(self):
        return QRectF(-HLAVA_UCHYT - 6, 0, HLAVA_UCHYT + 6 + 112, self.osa.vyska)

    def paint(self, p, opt, w=None):
        p.setRenderHint(QPainter.Antialiasing)
        barva = QColor(theme.OSA_HLAVA)
        theme.zar_cara(p, 0, H_PRAVITKO - 2, self.osa.vyska, barva, tloustka=2)
        # úchyt: štítek se špičkou dolů, sedí v měřítku nad čárou
        p.setPen(Qt.NoPen)
        p.setBrush(barva)
        u = HLAVA_UCHYT
        p.drawPolygon(QPolygonF([QPointF(-u, 6), QPointF(u, 6), QPointF(u, H_PRAVITKO - 9),
                                 QPointF(0, H_PRAVITKO - 1), QPointF(-u, H_PRAVITKO - 9)]))
        # časový kód vpravo od úchytu: oranžové pozadí, tmavý text
        stitek = QRectF(u + 4, 5, 98, 16)
        p.drawRoundedRect(stitek, 3, 3)
        p.setPen(QColor(theme.OSA_HLAVA_TEXT))
        p.setFont(theme.pismo_mono(8, tucne=True))
        p.drawText(stitek, Qt.AlignCenter, casovy_kod(self.osa.playhead_t, self.osa.fps))


class SmyckaItem(QGraphicsItem):
    """Úsek, který se přehrává dokola – výrazně na měřítku, jemně přes stopy."""

    def __init__(self, osa):
        super().__init__()
        self.osa = osa
        self.setZValue(1.5)
        self.hide()

    def boundingRect(self):
        a, b = self.osa.smycka or (0, 0)
        return QRectF(a * self.osa.pps, 0, max((b - a) * self.osa.pps, 1), self.osa.vyska)

    def paint(self, p, opt, w=None):
        r = self.boundingRect()
        stav = 0 if self.osa.smycka_zapnuta else 1
        c = QColor(theme.OSA_SMYCKA)

        def s_alfou(druh):
            x = QColor(c)
            x.setAlpha(theme.OSA_SMYCKA_ALFA[druh][stav])
            return x
        # výplň v měřítku kreslí Pravitko (je nad touto vrstvou); přes stopy jen nádech, výběr zůstane modrý
        p.fillRect(QRectF(r.left(), H_PRAVITKO, r.width(), r.height() - H_PRAVITKO), s_alfou("stopy"))
        p.setPen(QPen(s_alfou("okraj"), 1))
        p.drawLine(QLineF(r.left(), 0, r.left(), r.bottom()))
        p.drawLine(QLineF(r.right(), 0, r.right(), r.bottom()))


class ZnackaItem(QGraphicsItem):
    """Značka (poznámka) – trojúhelník na měřítku a tečkovaná čára přes osu."""

    def __init__(self, osa, znacka):
        super().__init__()
        self.osa, self.znacka = osa, znacka
        self.setZValue(50)
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.PointingHandCursor)
        self.obnov()

    def obnov(self):
        self.prepareGeometryChange()
        self.setPos(self.znacka.t * self.osa.pps, 0)
        self.setToolTip(self.znacka.text or tr("osa.znacka_tip"))

    def boundingRect(self):
        return QRectF(-7, 0, 14, self.osa.vyska)

    def shape(self):  # klikatelný je jen trojúhelník na měřítku
        from PySide6.QtGui import QPainterPath
        cesta = QPainterPath()
        cesta.addRect(QRectF(-7, 0, 14, H_PRAVITKO))
        return cesta

    def paint(self, p, opt, w=None):
        p.setRenderHint(QPainter.Antialiasing)
        barva = QColor(BARVA_ZNACKY)
        p.setPen(Qt.NoPen)
        p.setBrush(barva)
        p.drawPolygon(QPolygonF([QPointF(-6, 2), QPointF(6, 2), QPointF(6, 12), QPointF(0, 18), QPointF(-6, 12)]))
        if self.znacka.text:
            p.setBrush(QColor(theme.TEXT))
            p.drawEllipse(QPointF(0, 8), 2, 2)
        pero = QPen(barva, 1, Qt.DotLine)
        pero.setCosmetic(True)
        p.setPen(pero)
        p.drawLine(QLineF(0, 18, 0, self.osa.vyska))


class OsaView(QGraphicsView):
    def __init__(self, osa):
        super().__init__(osa.scene)
        self.osa = osa
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setRubberBandSelectionMode(Qt.IntersectsItemShape)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.setBackgroundBrush(QColor(theme.PANEL_TMAVY))
        self.setViewportUpdateMode(QGraphicsView.SmartViewportUpdate)
        self.setFocusPolicy(Qt.ClickFocus)
        self.setContextMenuPolicy(Qt.NoContextMenu)  # vlastní menu přes signál kontext
        self.tah = None
        self.scrub = False
        self.smycka_od = None

    def _scena(self, e):
        return self.mapToScene(e.position().toPoint())

    def _polozka(self, e, typ):
        return next((i for i in self.items(e.position().toPoint()) if isinstance(i, typ)), None)

    def mousePressEvent(self, e):
        pos = self._scena(e)
        if e.button() == Qt.RightButton:
            slovo = self._polozka(e, SlovoItem)
            znacka = self._polozka(e, ZnackaItem)
            if slovo and not slovo.isSelected():
                self.osa.scene.clearSelection()
                slovo.setSelected(True)
            druh, obj = ("znacka", znacka.znacka) if znacka else ("slovo", slovo.slovo) if slovo else ("prazdne", None)
            self.osa.kontext.emit(e.globalPosition().toPoint(), druh, obj)
            return
        if e.button() != Qt.LeftButton:
            return super().mousePressEvent(e)
        znacka = self._polozka(e, ZnackaItem)
        if znacka:
            self.osa.seek.emit(znacka.znacka.t)
            return
        if pos.y() < H_PRAVITKO:
            t = min(max(pos.x() / self.osa.pps, 0), self.osa.delka)
            if e.modifiers() & Qt.ShiftModifier:  # Shift + tažení v měřítku = úsek smyčky
                self.smycka_od = t
                self.osa.nastav_smycku(t, t)
            else:
                self.scrub = True
                self.osa.seek.emit(t)
            return
        item = self._polozka(e, SlovoItem)
        if item is None:
            return super().mousePressEvent(e)  # výběrový obdélník
        mod = e.modifiers()
        if mod & (Qt.ControlModifier | Qt.ShiftModifier):
            item.setSelected(not item.isSelected())
            return
        if not item.isSelected():
            self.osa.scene.clearSelection()
            item.setSelected(True)
        zona = item.zona(pos.x() - item.x())
        self.tah = self.osa.zacni_tah(item, zona, pos.x())
        if self.tah and zona == "posun":
            self.viewport().setCursor(Qt.ClosedHandCursor)

    def mouseDoubleClickEvent(self, e):
        if e.button() != Qt.LeftButton:
            return
        znacka = self._polozka(e, ZnackaItem)
        slovo = self._polozka(e, SlovoItem)
        if znacka:
            self.osa.dvojklik_znacka.emit(znacka.znacka)
        elif slovo:
            self.osa.dvojklik_slovo.emit(slovo.slovo)

    def mouseMoveEvent(self, e):
        pos = self._scena(e)
        t = min(max(pos.x() / self.osa.pps, 0), self.osa.delka)
        if self.scrub:
            self.osa.seek.emit(t)
        elif self.smycka_od is not None:
            self.osa.nastav_smycku(min(self.smycka_od, t), max(self.smycka_od, t))
        elif self.tah:
            self.osa.tahni(self.tah, pos.x(), bool(e.modifiers() & Qt.AltModifier))
        else:
            # nad úchytem přehrávací hlavy v měřítku kurzor „táhnout“ (klik a tažení hlavu posouvá)
            nad_uchytem = pos.y() < H_PRAVITKO and abs(pos.x() - self.osa.playhead_t * self.osa.pps) <= HLAVA_UCHYT + 2
            if nad_uchytem:
                self.viewport().setCursor(Qt.SizeHorCursor)
            elif self.viewport().cursor().shape() == Qt.SizeHorCursor and not e.buttons():
                self.viewport().unsetCursor()
            super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if self.scrub:
            self.scrub = False
        elif self.smycka_od is not None:
            self.smycka_od = None
            a, b = self.osa.smycka
            if b - a < 0.05:  # jen klik se Shiftem – úsek nevznikl
                self.osa.nastav_smycku(None)
            self.osa.smycka_vybrana.emit()
        elif self.tah:
            self.osa.dokonci_tah(self.tah)
            self.tah = None
            self.viewport().unsetCursor()
        else:
            super().mouseReleaseEvent(e)

    def wheelEvent(self, e):
        d = e.angleDelta()
        if e.modifiers() & Qt.ControlModifier:
            x = e.position().x()
            t = self.mapToScene(int(x), 0).x() / self.osa.pps
            self.osa.zoom(self.osa.pps * 1.25 ** (d.y() / 120), t, x)
        else:
            krok = d.x() or d.y()
            bar = self.horizontalScrollBar()
            bar.setValue(bar.value() - krok)
        e.accept()


class CasovaOsa(QWidget):
    seek = Signal(float)
    zacatek_upravy = Signal()          # těsně před změnou (pro Undo)
    konec_upravy = Signal(bool)        # True = něco se změnilo
    zmena = Signal()                   # průběžně během tažení
    kontext = Signal(object, str, object)  # globální pozice, "slovo"/"znacka"/"prazdne", objekt
    dvojklik_slovo = Signal(object)
    dvojklik_znacka = Signal(object)
    smycka_vybrana = Signal()          # Shift+tažením v měřítku vznikl úsek smyčky
    varovani = Signal(str)

    def __init__(self):
        super().__init__()
        self.titulky, self.znacky, self.delka, self.pps, self.fps = [], [], 0.0, 100.0, 30.0
        self.vlna = None
        self.playhead_t = 0.0
        self.prichytavat = True
        self.sledovat = True
        self.velka_stopa = False
        self.h_slovo = VYSKY_STOPY[0]
        self.smycka = None             # (od, do) v sekundách
        self.smycka_zapnuta = False
        self.font_slov = QFont("Segoe UI", 9)
        self.slova = []        # všechna slova v časovém pořadí
        self.polozky = []      # SlovoItem ve stejném pořadí
        self.pasy, self.znacky_items = [], []
        self.prave_hraje = None  # SlovoItem pod přehrávací hlavou (oranžová linka)
        self._editor = None

        self.scene = QGraphicsScene(self)
        self.pravitko = Pravitko(self)
        self.vlna_item = Vlna(self)
        self.smycka_item = SmyckaItem(self)
        self.hlava = HlavaItem(self)
        for i in (self.pravitko, self.vlna_item, self.smycka_item, self.hlava):
            self.scene.addItem(i)
        self.snap_cara = QGraphicsLineItem()
        pero = QPen(QColor(theme.AKCENT), 1, Qt.DashLine)
        pero.setCosmetic(True)
        self.snap_cara.setPen(pero)
        self.snap_cara.setZValue(90)
        self.snap_cara.hide()
        self.scene.addItem(self.snap_cara)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        self.lista = QHBoxLayout()
        self.lista.setSpacing(4)
        lay.addLayout(self.lista)
        self.view = OsaView(self)
        lay.addWidget(self.view)
        self._uprav_vysku()

    # ---------- rozměry ----------
    @property
    def h_pas(self):
        return self.h_slovo + 8

    @property
    def y_vlna(self):
        return Y_SLOVO + self.h_slovo + 10

    @property
    def vyska(self):
        return self.y_vlna + H_VLNA + 4

    def sirka(self):
        return max(self.delka * self.pps, 1.0)

    def _uprav_vysku(self):
        self.view.setFixedHeight(self.vyska + 18)

    def nastav_vysku_stopy(self, velka):
        for i in (self.pravitko, self.vlna_item, self.smycka_item, self.hlava):
            i.prepareGeometryChange()
        self.velka_stopa = velka
        self.h_slovo = VYSKY_STOPY[1 if velka else 0]
        self.font_slov = QFont("Segoe UI", 10 if velka else 9)
        for z in self.znacky_items:
            z.prepareGeometryChange()
        self._uprav_vysku()
        self._sceny_rect()
        self.obnov()

    # ---------- lišta nástrojů ----------
    def pridej_listu(self, akce):
        """Tlačítka nad osou z QAction (None = oddělovač, "|" = pružná mezera)."""
        for a in akce:
            if a is None:
                cara = QFrame()
                cara.setFrameShape(QFrame.VLine)
                cara.setObjectName("oddelovac")
                self.lista.addSpacing(4)
                self.lista.addWidget(cara)
                self.lista.addSpacing(4)
            elif a == "|":
                self.lista.addStretch(1)
            else:
                b = QToolButton()
                b.setObjectName("nastroj")
                b.setDefaultAction(a)
                b.setFocusPolicy(Qt.NoFocus)
                b.setToolButtonStyle(Qt.ToolButtonTextOnly)
                if a.property("magnet"):  # přichytávání: stav ukazuje barva magnetu, ne podbarvení
                    b.setProperty("magnet", True)
                    b.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
                    b.setIconSize(QSize(14, 14))
                b.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
                self.lista.addWidget(b)

    # ---------- data ----------
    def nastav(self, titulky, delka, znacky=None):
        """Znovu postaví boxy (po změně struktury titulků). Skupiny (titulky z více slov) mají
        střídající se barvy – sousední skupiny se vždy liší; samostatná slova jednu neutrální barvu."""
        self.zavri_editor(potvrdit=False)
        vybrana = {id(i.slovo) for i in self.polozky if i.isSelected()}
        for i in self.polozky + self.pasy + self.znacky_items:
            self.scene.removeItem(i)
        self._pred_zmenou_sirky()
        self.titulky, self.delka = titulky, delka
        if znacky is not None:
            self.znacky = znacky
        self.slova, self.polozky, self.pasy, self.znacky_items = [], [], [], []
        self.prave_hraje = None
        skupina = 0
        for t in titulky:
            if len(t.slova) >= 2:
                barva = BARVY[skupina % len(BARVY)]
                skupina += 1  # počítají se jen skupiny – i přes samostatná slova mají sousední skupiny jinou barvu
            else:
                barva = theme.SLOVO_SAMOSTATNE
            pas = PasItem(self, t, barva)
            self.scene.addItem(pas)
            self.pasy.append(pas)
            for s in t.slova:
                item = SlovoItem(self, s, t, barva)
                self.scene.addItem(item)
                item.setSelected(id(s) in vybrana)
                self.slova.append(s)
                self.polozky.append(item)
        for z in self.znacky:
            item = ZnackaItem(self, z)
            self.scene.addItem(item)
            self.znacky_items.append(item)
        self._sceny_rect()

    def prelozit(self):
        """Po změně jazyka: texty kreslené přímo na ose (načítání vlny, tipy značek)."""
        for z in self.znacky_items:
            z.obnov()
        self.vlna_item.update()

    def nastav_vlnu(self, env):
        self.vlna = env
        self.vlna_item.update()

    def obnov(self):
        """Přepočítá polohy boxů po změně časů (bez změny struktury)."""
        for i in self.polozky + self.pasy + self.znacky_items:
            i.obnov()
        self.smycka_item.prepareGeometryChange()
        self.smycka_item.update()
        self.nastav_playhead(self.playhead_t)

    def vybrana_slova(self):
        return [i.slovo for i in self.polozky if i.isSelected()]

    def vyber(self, slova):
        ids = {id(s) for s in slova}
        self.scene.clearSelection()
        for i in self.polozky:
            if id(i.slovo) in ids:
                i.setSelected(True)

    def nastav_playhead(self, t, hraje=False):
        self.playhead_t = t
        x = t * self.pps
        self.hlava.setPos(x, 0)
        self.hlava.update()
        self._oznac_prave_hraje(t)
        if hraje and self.sledovat:
            bar = self.view.horizontalScrollBar()
            sirka = self.view.viewport().width()
            if x > bar.value() + sirka - 40 or x < bar.value():
                bar.setValue(int(x - sirka * 0.2))

    def _oznac_prave_hraje(self, t):
        """Slovo pod přehrávací hlavou dostane tenkou oranžovou linku (překreslí se jen staré a nové)."""
        import bisect
        # začátky čte pokaždé znovu – během tažení slov se mění (slova jsou v časovém pořadí)
        i = bisect.bisect_right([s.start for s in self.slova], t) - 1
        nove = self.polozky[i] if 0 <= i < len(self.polozky) and t < self.slova[i].end else None
        if nove is not self.prave_hraje:
            for item in (self.prave_hraje, nove):
                if item is not None and item.scene() is not None:
                    item.update()
            self.prave_hraje = nove

    # ---------- smyčka ----------
    def nastav_smycku(self, od, do=None, zapnuta=None):
        self.smycka_item.prepareGeometryChange()
        self.smycka = None if od is None else (od, do)
        if zapnuta is not None:
            self.smycka_zapnuta = zapnuta
        self.smycka_item.setVisible(self.smycka is not None)
        self.smycka_item.update()
        self.pravitko.update()  # výplň smyčky v měřítku

    # ---------- zoom ----------
    def _pred_zmenou_sirky(self):
        self.pravitko.prepareGeometryChange()
        self.vlna_item.prepareGeometryChange()
        self.smycka_item.prepareGeometryChange()

    def _sceny_rect(self):
        self.scene.setSceneRect(0, 0, self.sirka() + 40, self.vyska)
        self.pravitko.update()
        self.vlna_item.update()

    def zoom(self, pps, kotva_t=None, kotva_x=None):
        if kotva_t is None:
            kotva_x = self.view.viewport().width() / 2
            kotva_t = self.view.mapToScene(int(kotva_x), 0).x() / self.pps
        self.zavri_editor(potvrdit=True)
        self._pred_zmenou_sirky()
        self.pps = min(max(pps, MIN_PPS), MAX_PPS)
        self._sceny_rect()
        self.obnov()
        self.view.horizontalScrollBar().setValue(int(kotva_t * self.pps - kotva_x))

    def zobraz_cele(self):
        if self.delka:
            self.zoom((self.view.viewport().width() - 30) / self.delka, 0, 0)

    def zoom_na(self, od, do):
        """Úsek od–do přes celou šířku (s malým okrajem)."""
        rozsah = max(do - od, 0.2)
        okraj = rozsah * 0.08
        sirka = self.view.viewport().width()
        self.zoom(sirka / (rozsah + 2 * okraj), od - okraj, 0)

    # ---------- úprava textu přímo na ose ----------
    def otevri_editor(self, slovo, potvrzeni):
        """Pole pro úpravu textu přes box slova; Enter / klik jinam = potvrdit, Esc = zrušit."""
        self.zavri_editor(potvrdit=True)
        item = next((i for i in self.polozky if i.slovo is slovo), None)
        if item is None:
            return
        self.view.ensureVisible(item, 40, 0)
        r = self.view.mapFromScene(item.sceneBoundingRect()).boundingRect()
        ed = QLineEdit(slovo.text, self.view.viewport())
        ed.setObjectName("editorSlova")
        ed.setGeometry(r.x(), r.y() + (r.height() - 28) // 2, max(r.width(), 110), 28)
        ed.selectAll()
        ed.show()
        ed.setFocus()
        self._editor = (ed, slovo, potvrzeni)
        ed.returnPressed.connect(lambda: self.zavri_editor(potvrdit=True))
        ed.editingFinished.connect(lambda: self.zavri_editor(potvrdit=True))
        ed.keyPressEvent = self._klavesa_editoru(ed)

    def _klavesa_editoru(self, ed):
        puvodni = ed.keyPressEvent

        def klavesa(e):
            if e.key() == Qt.Key_Escape:
                self.zavri_editor(potvrdit=False)
            else:
                puvodni(e)
        return klavesa

    def zavri_editor(self, potvrdit=True):
        if not self._editor:
            return
        ed, slovo, potvrzeni = self._editor
        self._editor = None
        text = ed.text().strip()
        ed.hide()
        ed.deleteLater()
        if potvrdit and text != slovo.text:
            potvrzeni(slovo, text)
        self.view.setFocus()

    # ---------- tažení ----------
    def zacni_tah(self, item, zona, x):
        slova = self.vybrana_slova() if zona == "posun" else [item.slovo]
        tit = {id(s): t for t in self.titulky for s in t.slova}
        zamcene = next((s for s in slova if tit[id(s)].zamceno), None)
        if zamcene:
            self.varovani.emit(tr("osa.zamceno", slovo=zamcene.text))
            return None
        self.zacatek_upravy.emit()
        return {
            "item": item, "zona": zona, "x0": x, "zmeneno": False,
            "slova": slova, "id": {id(s) for s in slova},
            "puvodni_slova": [(s, s.start, s.end) for s in self.slova],
            "puvodni_tit": [(t, t.start, t.end) for t in self.titulky],
            # dozvuk (konec titulku za posledním slovem) se při tažení zachová
            "dozvuk": {id(t): t.end - t.slova[-1].end for t in self.titulky if t.slova},
            "index": {id(s): i for i, s in enumerate(self.slova)},
        }

    def _cile_snap(self, tah):
        cile = [self.playhead_t]
        for s in self.slova:
            if id(s) not in tah["id"]:
                cile += (s.start, s.end)
        return cile

    def _prichyt(self, hodnoty, cile, bez_snap):
        """(posun, cíl): posun (s), který přichytí nejbližší z `hodnoty` k některému z `cile`."""
        if bez_snap or not self.prichytavat:
            return 0.0, None
        prah = SNAP_PX / self.pps
        nejlepsi = None
        for h in hodnoty:
            for c in cile:
                d = c - h
                if abs(d) <= prah and (nejlepsi is None or abs(d) < abs(nejlepsi[0])):
                    nejlepsi = (d, c)
        return nejlepsi or (0.0, None)

    def _ukaz_snap(self, cil):
        if cil is None:
            self.snap_cara.hide()
        else:
            x = cil * self.pps
            self.snap_cara.setLine(x, 0, x, self.vyska)
            self.snap_cara.show()

    def tahni(self, tah, x, bez_snap=False):
        for s, a, b in tah["puvodni_slova"]:
            s.start, s.end = a, b
        for t, a, b in tah["puvodni_tit"]:
            t.start, t.end = a, b
        dt = (x - tah["x0"]) / self.pps
        idx, sl = tah["index"], self.slova
        cile = self._cile_snap(tah)
        cil = None

        if tah["zona"] == "posun":
            lo, hi = -math.inf, math.inf
            for s in tah["slova"]:
                i = idx[id(s)]
                pred = sl[i - 1] if i > 0 else None
                po = sl[i + 1] if i + 1 < len(sl) else None
                if pred is None:
                    lo = max(lo, -s.start)
                elif id(pred) not in tah["id"]:
                    lo = max(lo, pred.end - s.start)
                if po is None:
                    hi = min(hi, self.delka - s.end)
                elif id(po) not in tah["id"]:
                    hi = min(hi, po.start - s.end)
            s0 = tah["item"].slovo
            d, cil = self._prichyt((s0.start + dt, s0.end + dt), cile, bez_snap)
            dt += d
            dt = min(max(dt, lo), hi) if lo <= hi else 0.0
            for s in tah["slova"]:
                s.start, s.end = round(s.start + dt, 3), round(s.end + dt, 3)
        else:
            s = tah["item"].slovo
            i = idx[id(s)]
            pred = sl[i - 1] if i > 0 else None
            po = sl[i + 1] if i + 1 < len(sl) else None
            if tah["zona"] == "zacatek":
                novy = s.start + dt
                d, cil = self._prichyt((novy,), cile, bez_snap)
                novy = min(max(novy + d, pred.end if pred else 0.0), s.end - MIN_SLOVO)
                s.start = round(novy, 3)
            else:
                novy = s.end + dt
                d, cil = self._prichyt((novy,), cile, bez_snap)
                novy = max(min(novy + d, po.start if po else self.delka), s.start + MIN_SLOVO)
                s.end = round(novy, 3)
        self._ukaz_snap(cil)

        for t in self.titulky:
            if t.slova and id(t) in tah["dozvuk"]:
                t.end = t.slova[-1].end + tah["dozvuk"][id(t)]
        srovnej(self.titulky, self.delka)
        tah["zmeneno"] = any(s.start != a or s.end != b for s, a, b in tah["puvodni_slova"])
        self.obnov()
        self.zmena.emit()

    def dokonci_tah(self, tah):
        self._ukaz_snap(None)
        if not tah["zmeneno"]:
            self.seek.emit(tah["item"].slovo.start)  # obyčejný klik na slovo = skok na něj
        self.konec_upravy.emit(tah["zmeneno"])
