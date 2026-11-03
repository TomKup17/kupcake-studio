"""Velká překryvná obrazovka zpracování: cupcake se plní zdola nahoru podle skutečného průběhu.

Překrytí je samostatné průhledné okno nad hlavním oknem (ne jen widget uvnitř): přehrávač mpv kreslí do
nativního okna, přes které by běžný widget nebyl vidět. Okno je modální pro celou aplikaci, takže blokuje
klikání i klávesové zkratky, a drží se velikosti a polohy hlavního okna.

Průběh: nastav_prubeh(p) nastaví cíl (nikdy necouvne), zobrazená náplň se k němu plynule blíží (60 fps).
Konec: dokonci() – náplň dojede na 100 %, dopadne třešnička s odskokem, probliknou jiskřičky a překrytí se
rozplyne. Průběh se zároveň ukazuje na ikoně v hlavním panelu Windows (PrubehNaPanelu).
"""
import math
import time

import numpy as np

from PySide6.QtCore import QEasingCurve, QElapsedTimer, QEvent, QPointF, QPropertyAnimation, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QImage, QPainter, QPainterPath, QPixmap, QRadialGradient
from PySide6.QtWidgets import QMessageBox, QPushButton, QWidget

import kupcake
import theme
from i18n import prekladej, t

DOPAD_S = 0.6       # pád třešničky s odskokem
JISKRY_S = 0.55     # jiskřičky po dopadu
ROZPLYNUTI_MS = 400


class Prekryti(QWidget):
    zrusit = Signal()

    def __init__(self, okno):
        super().__init__(okno, Qt.Tool | Qt.FramelessWindowHint)
        self.okno = okno
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowModality(Qt.ApplicationModal)
        self.setFocusPolicy(Qt.StrongFocus)
        okno.installEventFilter(self)
        self.btn = QPushButton(self)
        self.btn.setObjectName("sekundarni")
        self.btn.setCursor(Qt.PointingHandCursor)
        self.btn.clicked.connect(self._potvrd_zruseni)
        prekladej(lambda: self.btn.setText(t("btn.zrusit")))
        self.panel = PrubehNaPanelu()
        self.casovac = QTimer(self)
        self.casovac.setInterval(16)  # ~60 fps
        self.casovac.timeout.connect(self._tik)
        self.hodiny = QElapsedTimer()
        self.rozplynuti = QPropertyAnimation(self, b"windowOpacity", self)
        self.rozplynuti.setDuration(ROZPLYNUTI_MS)
        self.rozplynuti.setEasingCurve(QEasingCurve.InOutQuad)
        self.rozplynuti.finished.connect(self._skryto)
        self._velikost = 220
        self._priprav_kresbu(self._velikost)
        self._reset()

    # ---------- řízení ----------
    def _reset(self):
        self.cil = self.zobrazeno = 0.0
        self.faze = ""
        self.zbyva = None
        self._start = time.monotonic()
        self._posledni_odhad = 0.0
        self.konec = None          # čas začátku dokončovací animace
        self.po_dokonceni = None
        self.rusim = False

    def spust(self):
        self._reset()
        self.btn.setEnabled(True)
        self.btn.show()
        self.rozplynuti.stop()
        self.setWindowOpacity(1.0)
        self._prizpusob()
        self.show()
        self.raise_()
        self.activateWindow()
        self.hodiny.start()
        self._t_minule = 0.0
        self.casovac.start()
        self.panel.nastav(self.okno, 0.0)

    def nastav_prubeh(self, p):
        """Skutečný celkový průběh 0–1 (z vlákna přes signál). Cíl nikdy necouvne."""
        p = min(max(p, 0.0), 1.0)
        if p > self.cil:
            self.cil = p
            self._odhad()
            self.panel.nastav(self.okno, p)

    def nastav_fazi(self, text):
        if not self.rusim:
            self.faze = text

    def dokonci(self, po_dokonceni=None):
        """Práce doběhla: dojet na 100 %, třešnička, jiskřičky, rozplynutí; pak po_dokonceni()."""
        self.nastav_prubeh(1.0)
        self.po_dokonceni = po_dokonceni
        self.btn.hide()
        if self.konec is None:
            self.konec = -1.0  # čeká, až náplň dojede

    def zavri(self):
        """Okamžitě (chyba, zrušení)."""
        self.casovac.stop()
        self.rozplynuti.stop()
        self.hide()
        self.panel.skryj(self.okno)

    # ---------- zrušení ----------
    def _potvrd_zruseni(self):
        if self.rusim or self.konec is not None:
            return
        if QMessageBox.question(self, t("prekryti.zrusit_titulek"), t("prekryti.zrusit_dotaz")) == QMessageBox.Yes:
            self.rusim = True
            self.btn.setEnabled(False)
            self.faze = t("prekryti.rusim")
            self.zrusit.emit()

    # ---------- čas ----------
    def _odhad(self):
        """Odhad zbývajícího času z rychlosti dosavadního skutečného průběhu (vyhlazený)."""
        ted = time.monotonic()
        uplynulo = ted - self._start
        if self.cil < 0.03 or uplynulo < 3 or ted - self._posledni_odhad < 0.5:
            return
        self._posledni_odhad = ted
        novy = uplynulo * (1 - self.cil) / self.cil
        self.zbyva = novy if self.zbyva is None else 0.8 * self.zbyva + 0.2 * novy

    def _text_zbyva(self):
        if self.konec is not None:
            return t("prekryti.hotovo")
        if self.zbyva is None:
            return t("prekryti.odhaduji")
        zbyva = max(self.zbyva - (time.monotonic() - self._posledni_odhad), 0)
        if zbyva < 5:
            return t("prekryti.temer")
        m, s = divmod(int(round(zbyva)), 60)
        return t("prekryti.zbyva", cas=f"{m}:{s:02d}")

    def _tik(self):
        ted = self.hodiny.elapsed() / 1000
        dt = min(ted - self._t_minule, 0.1)
        self._t_minule = ted
        # plynulé dojíždění k cíli (rychleji, když se dokončuje); nikdy necouvne
        rychlost = 9.0 if self.konec is not None else 3.5
        self.zobrazeno = min(max(self.zobrazeno, self.zobrazeno + (self.cil - self.zobrazeno) * (1 - math.exp(-dt * rychlost))),
                             self.cil)
        if self.konec == -1.0 and self.cil - self.zobrazeno < 0.003:
            self.zobrazeno = 1.0
            self.konec = ted
        if self.konec is not None and self.konec >= 0 and ted - self.konec > DOPAD_S + JISKRY_S \
                and self.rozplynuti.state() != QPropertyAnimation.Running and self.isVisible():
            self.rozplynuti.setStartValue(1.0)
            self.rozplynuti.setEndValue(0.0)
            self.rozplynuti.start()
        self.update()

    def _skryto(self):
        self.casovac.stop()
        self.hide()
        self.setWindowOpacity(1.0)
        self.panel.skryj(self.okno)
        hotovo, self.po_dokonceni = self.po_dokonceni, None
        if hotovo:
            hotovo()

    # ---------- poloha ----------
    def eventFilter(self, obj, e):
        if obj is self.okno and e.type() in (QEvent.Move, QEvent.Resize, QEvent.WindowStateChange) and self.isVisible():
            self._prizpusob()
        return False

    def _prizpusob(self):
        self.setGeometry(self.okno.geometry())

    def resizeEvent(self, e):
        s = int(min(max(min(self.width(), self.height()) * 0.36, 160), 280))  # cupcake 220–280 px, v malém okně menší
        if s != self._velikost:
            self._velikost = s
            self._priprav_kresbu(s)
        self.btn.adjustSize()
        self.btn.move(int(self.width() / 2 - self.btn.width() / 2), int(self._y_textu() + self._vyska_textu() + 18))
        super().resizeEvent(e)

    def _y_textu(self):
        return self.height() / 2 + self._velikost * 0.42

    def _pismo_procent(self):
        f = QFont(theme.PISMO_MONO)
        f.setPointSizeF(max(self._velikost / 8.5, 20))
        f.setWeight(QFont.DemiBold)
        return f

    def _vyska_textu(self):
        """Výška bloku procenta + fáze + zbývající čas (pod ním je tlačítko Zrušit)."""
        return QFontMetricsF(self._pismo_procent()).height() + 4 + 26 + 22

    # ---------- kresba ----------
    def _priprav_kresbu(self, s):
        dpr = self.devicePixelRatioF() or 1.0
        barva = kupcake.vykresli(kupcake.svg(kupcake.VARIANTA, 256, False, ("telo",)), int(s * dpr)).toImage()
        self.barva = QPixmap.fromImage(barva)
        self.tresen = kupcake.vykresli(kupcake.svg(kupcake.VARIANTA, 256, False, ("tresen",)), int(s * dpr))
        for pix in (self.barva, self.tresen):
            pix.setDevicePixelRatio(dpr)
        self.silueta = _silueta(barva, dpr)
        # svislý rozsah těla (kde je něco nakresleno) – náplň jde od jeho spodku po vršek
        img = barva.convertToFormat(QImage.Format_ARGB32)
        data = np.frombuffer(img.constBits(), np.uint8, img.sizeInBytes()).reshape(img.height(), img.bytesPerLine())
        radky = np.nonzero((data[:, 3:img.width() * 4:4] > 20).any(axis=1))[0]
        self.telo_od = (int(radky[0]) if len(radky) else 0) / dpr
        self.telo_do = (int(radky[-1]) if len(radky) else barva.height()) / dpr

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor(*theme.ZTLUMENI))
        s = self._velikost
        # jemné ztmavení kolem středu – text zůstane čitelný i nad rušnou časovou osou
        zaklad = QColor(*theme.ZTLUMENI)
        g = QRadialGradient(QPointF(self.width() / 2, self.height() / 2 + s * 0.15), s * 1.5)
        g.setColorAt(0, QColor(zaklad.red(), zaklad.green(), zaklad.blue(), 170))
        g.setColorAt(1, QColor(zaklad.red(), zaklad.green(), zaklad.blue(), 0))
        p.fillRect(self.rect(), g)
        x0, y0 = self.width() / 2 - s / 2, self.height() / 2 - s * 0.62
        ted = self.hodiny.elapsed() / 1000 if self.hodiny.isValid() else 0.0

        # tlumená silueta celého cupcaku, přes ni náplň v plných barvách ohraničená vlnkou
        p.drawPixmap(QPointF(x0, y0), self.silueta)
        vyska = self.telo_do - self.telo_od
        amplituda = s * 0.014
        hladina = y0 + self.telo_do - self.zobrazeno * (vyska + amplituda * 3)
        if self.zobrazeno > 0:
            vlna = QPainterPath(QPointF(x0, y0 + s + 2))
            vlnova_delka, faze = s / 2.6, ted * 2.2
            krok = max(s / 64, 2)
            x = 0.0
            while x <= s + krok:
                vlna.lineTo(QPointF(x0 + x, hladina + amplituda * math.sin(2 * math.pi * x / vlnova_delka + faze)))
                x += krok
            vlna.lineTo(QPointF(x0 + s + krok, y0 + s + 2))
            vlna.closeSubpath()
            p.save()
            p.setClipPath(vlna)
            p.drawPixmap(QPointF(x0, y0), self.barva)
            p.restore()

        # dokončení: dopad třešničky s odskokem a jiskřičky
        if self.konec is not None and self.konec >= 0:
            k = ted - self.konec
            u = min(k / DOPAD_S, 1.0)
            pad = 1 - QEasingCurve(QEasingCurve.OutBounce).valueForProgress(u)
            p.setOpacity(min(u * 4, 1.0))
            p.drawPixmap(QPointF(x0, y0 - pad * s * 0.55), self.tresen)
            p.setOpacity(1.0)
            j = (k - DOPAD_S * 0.55) / JISKRY_S
            if 0 < j < 1:
                p.setPen(Qt.NoPen)
                for jx, jy, faze_j in kupcake.JISKRY:
                    f = min(max((j - faze_j * 0.5) / 0.5, 0), 1)
                    sila = math.sin(f * math.pi)
                    if sila <= 0:
                        continue
                    c = QColor(theme.AKCENT)
                    c.setAlphaF(sila)
                    p.setBrush(c)
                    p.drawPath(kupcake._jiskra(QPointF(x0 + (jx - 0.5) * 1.3 * s + s / 2,
                                                       y0 + (jy - 0.5) * 1.2 * s + s / 2), s * 0.05 * (0.6 + 0.4 * sila)))

        # procenta, fáze, zbývající čas
        y = self._y_textu()
        procenta = self._pismo_procent()
        p.setFont(procenta)
        p.setPen(QColor(theme.TEXT))
        fm = QFontMetricsF(procenta)
        p.drawText(QRectF(0, y, self.width(), fm.height()), Qt.AlignCenter, f"{int(self.zobrazeno * 100)}%")
        y += fm.height() + 4
        faze = QFont(theme.PISMO_UI)
        faze.setPointSizeF(11.5)
        p.setFont(faze)
        p.setPen(QColor(theme.TEXT_2))
        p.drawText(QRectF(0, y, self.width(), 24), Qt.AlignCenter, "" if self.konec is not None else self.faze)
        y += 26
        maly = QFont(theme.PISMO_UI)
        maly.setPointSizeF(9.5)
        p.setFont(maly)
        p.setPen(QColor(theme.TEXT_2))
        p.drawText(QRectF(0, y, self.width(), 20), Qt.AlignCenter, self._text_zbyva())
        p.end()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self._potvrd_zruseni()
        # ostatní klávesy (zkratky hlavního okna) během zpracování nic nedělají


def _silueta(barva, dpr):
    """Tlumená silueta: tvar cupcaku v tmavé šedi s jemným světlejším obrysem."""
    w, h = barva.width(), barva.height()
    maska = QImage(barva)

    def obarvi(barva_hex):
        img = QImage(maska)
        q = QPainter(img)
        q.setCompositionMode(QPainter.CompositionMode_SourceIn)
        q.fillRect(img.rect(), QColor(barva_hex))
        q.end()
        return img

    obrys, vypln = obarvi(theme.SILUETA_OBRYS), obarvi(theme.SILUETA)
    vysledek = QImage(w, h, QImage.Format_ARGB32_Premultiplied)
    vysledek.fill(Qt.transparent)
    q = QPainter(vysledek)
    d = 1.5 * dpr
    for dx, dy in ((-d, 0), (d, 0), (0, -d), (0, d), (-d, -d), (d, d), (-d, d), (d, -d)):
        q.drawImage(QPointF(dx, dy), obrys)
    q.drawImage(0, 0, vypln)
    q.end()
    pix = QPixmap.fromImage(vysledek)
    pix.setDevicePixelRatio(dpr)
    return pix


class PrubehNaPanelu:
    """Zelený pruh průběhu na ikoně aplikace v hlavním panelu Windows (ITaskbarList3). Jinde nic nedělá."""
    NORMAL, ZADNY = 2, 0

    def __init__(self):
        self.rozhrani = None
        try:
            import ctypes
            import uuid
            from ctypes import POINTER, byref, c_void_p

            class GUID(ctypes.Structure):
                _fields_ = [("data", ctypes.c_ubyte * 16)]

            def guid(text):
                g = GUID()
                ctypes.memmove(g.data, uuid.UUID(text).bytes_le, 16)
                return g
            ole32 = ctypes.windll.ole32
            ole32.CoInitialize(None)
            ukazatel = c_void_p()
            clsid, iid = guid("56FDF344-FD6D-11d0-958A-006097C9A090"), guid("EA1AFB91-9E28-4B86-90E9-9E9F8A5EEFAF")
            if ole32.CoCreateInstance(byref(clsid), None, 1, byref(iid), byref(ukazatel)) != 0:
                return
            self._vtbl = ctypes.cast(ukazatel, POINTER(POINTER(c_void_p))).contents
            self._ukazatel = ukazatel
            self._typy = ctypes
            self._volej(3)  # HrInit
            self.rozhrani = ukazatel
        except Exception:
            self.rozhrani = None

    def _volej(self, index, *argumenty):
        c = self._typy
        typy = {9: (c.c_void_p, c.c_ulonglong, c.c_ulonglong), 10: (c.c_void_p, c.c_int)}.get(index, ())
        funkce = c.WINFUNCTYPE(c.c_long, c.c_void_p, *typy)(self._vtbl[index])
        return funkce(self._ukazatel, *argumenty)

    def nastav(self, okno, p):
        if self.rozhrani:
            try:
                hwnd = int(okno.winId())
                self._volej(10, hwnd, self.NORMAL)
                self._volej(9, hwnd, int(p * 1000), 1000)
            except Exception:
                pass

    def skryj(self, okno):
        if self.rozhrani:
            try:
                self._volej(10, int(okno.winId()), self.ZADNY)
            except Exception:
                pass
