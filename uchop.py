# kupcake.studio – Copyright (C) 2026 Tomáš Kupec
# SPDX-License-Identifier: GPL-3.0-only
"""Uchopení titulku myší přímo ve videu (sekce Náhled): tažením se titulek přesune kamkoli, tažením za roh
rámečku se změní velikost písma.

Titulky kreslí mpv (libass) do nativního okna, přes které Qt kreslit neumí. Proto:
- kde titulek na obraze leží, se počítá z písma stejně jako v libass (ramecek_titulku),
- výběrový rámeček s úchyty kreslí mpv jako vrstvu nad videem (ass_prekryti → příkaz osd-overlay),
- UchopTitulku převádí pohyb myši na změnu stylu: posun(x, y) a velikost(v) v podílech šířky/výšky videa.

Poloha i velikost jsou hodnoty stylu (pozice_x, pozice_y, velikost) – platí pro všechny titulky a mění se
stejně jako dlaždicemi v sekci Nastavení.
"""
import math
import struct
from functools import lru_cache

from PySide6.QtCore import QObject, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QRawFont

import theme

OKRAJ_PX = 6            # odstup rámečku od textu (px obrazovky)
UCHYT_PX = 9            # strana čtverečku v rohu rámečku
DOSAH_PX = 11           # jak daleko od rohu se úchyt ještě chytne
TAH_PX = 4              # kratší pohyb se stisknutým tlačítkem je kliknutí, ne tah
PRICHYCENI_PX = 6       # vodorovně se titulek přichytí ke středu videa (px obrazovky na každou stranu)
VELIKOST_OD, VELIKOST_DO = 0.02, 0.30   # stejné meze jako dlaždice Velikost
OKRAJ_ZALOMENI = 0.05   # titulky.vytvor_ass: dlouhý text se zalomí 5 % od okrajů
PISMO_PX = 1000         # písmo se měří velké a přepočítává – metriky v pixelech jsou jinak zaokrouhlené


# ---------- kde titulek leží ----------
@lru_cache(maxsize=64)
def _metriky(rodina, tucne):
    """(em na jednotku velikosti ASS, podíl výstupu na výšce řádku). libass bere velikost písma jako výšku
    usWinAscent + usWinDescent z tabulky OS/2, Qt jako em – u některých písem (Montserrat) je rozdíl velký."""
    f = QFont(rodina)
    f.setPixelSize(PISMO_PX)
    f.setBold(tucne)
    try:
        surove = QRawFont.fromFont(f)
        os2, head = surove.fontTable("OS/2").data(), surove.fontTable("head").data()
        vystup, sestup = struct.unpack_from(">hh", os2, 74)   # libass je čte jako short
        em = struct.unpack_from(">H", head, 18)[0]
        if vystup + sestup > 0 and em > 0:
            return em / (vystup + sestup), vystup / (vystup + sestup)
    except (struct.error, AttributeError, RuntimeError):
        pass
    fm = QFontMetricsF(f)
    vyska = max(fm.ascent() + fm.descent(), 1.0)
    return PISMO_PX / vyska, fm.ascent() / vyska


def _zalom(sirky, mezera, nejvic):
    """Rozdělení slov do řádků jako libass (WrapStyle 0): nejdřív co se vejde, pak se řádky vyrovnají
    přesouváním posledního slova na další řádek. Vrací seznam řádků (indexy slov)."""
    radky, sirka = [[]], 0.0
    for i, s in enumerate(sirky):
        nova = sirka + (mezera if radky[-1] else 0.0) + s
        if radky[-1] and nova > nejvic:
            radky.append([i])
            sirka = s
        else:
            radky[-1].append(i)
            sirka = nova

    def delka(radek):
        return sum(sirky[i] for i in radek) + mezera * max(len(radek) - 1, 0)

    for _ in range(len(sirky) + 1):
        zmena = False
        for a, b in zip(radky, radky[1:]):
            while len(a) > 1:
                pred = abs(delka(a) - delka(b))
                po_a, po_b = a[:-1], [a[-1]] + b
                if delka(po_b) > nejvic or abs(delka(po_a) - delka(po_b)) >= pred:
                    break
                b.insert(0, a.pop())
                zmena = True
        if not zmena:
            break
    return radky


def ramecek_titulku(text, styl, W, H):
    """Obdélník (QRectF v pixelech videa), ve kterém je text titulku vidět – těsně kolem písmen. None, když
    není co zobrazit. Počítá stejně jako titulky.vytvor_ass + libass: střed v (pozice_x, pozice_y)."""
    if not text or not text.strip() or W <= 0 or H <= 0:
        return None
    velikost = round(W * styl.velikost)
    em, podil_vystupu = _metriky(styl.font, bool(styl.tucne))
    k = velikost * em / PISMO_PX
    f = QFont(styl.font)
    f.setPixelSize(PISMO_PX)
    f.setBold(bool(styl.tucne))
    fm = QFontMetricsF(f)
    text = text.upper() if styl.velka_pismena else text
    nejvic = W - 2 * round(W * OKRAJ_ZALOMENI)
    radky = []
    for odstavec in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        slova = odstavec.split()
        if not slova:
            continue
        sirky = [fm.horizontalAdvance(s) * k for s in slova]
        for radek in _zalom(sirky, fm.horizontalAdvance(" ") * k, nejvic):
            radky.append(" ".join(slova[i] for i in radek))
    if not radky:
        return None
    x, y = int(W * styl.pozice_x), round(H * styl.pozice_y)
    nahore = y - len(radky) * velikost / 2
    celek = QRectF()
    for i, radek in enumerate(radky):
        ucari = nahore + i * velikost + podil_vystupu * velikost
        inkoust = fm.tightBoundingRect(radek)
        zacatek = x - fm.horizontalAdvance(radek) * k / 2
        celek = celek.united(QRectF(zacatek + inkoust.left() * k, ucari + inkoust.top() * k,
                                    inkoust.width() * k, inkoust.height() * k))
    obrys = velikost * max(styl.obrys, 0.0)
    return celek.adjusted(-obrys, -obrys, obrys, obrys)


# ---------- rámeček nad videem ----------
def _ass_barva(barva, kryti=1.0):
    """„#RRGGBB“ → (barva &HBBGGRR&, průhlednost &HAA& – v ASS je 00 plná a FF neviditelná)."""
    c = QColor(barva)
    return f"&H{c.blue():02X}{c.green():02X}{c.red():02X}&", f"&H{round(255 * (1 - kryti)):02X}&"


def _ctverec(stred, strana):
    p = strana / 2
    return (f"m {stred.x() - p:.1f} {stred.y() - p:.1f} l {stred.x() + p:.1f} {stred.y() - p:.1f} "
            f"{stred.x() + p:.1f} {stred.y() + p:.1f} {stred.x() - p:.1f} {stred.y() + p:.1f}")


def ass_prekryti(ramecek, vybrano, meritko=1.0, voditko=None):
    """Události ASS pro vrstvu nad videem (souřadnice = pixely vrstvy): rámeček kolem titulku, u vybraného
    čtyři úchyty v rozích; voditko = (x, y1, y2) svislá linka středu videa při přichycení."""
    radky = []
    if voditko is not None:
        barva, pruhlednost = _ass_barva(theme.UCHOP_VODITKO, 0.75)
        x, y1, y2 = voditko
        radky.append(f"{{\\an7\\pos(0,0)\\bord0\\shad0\\1c{barva}\\1a{pruhlednost}\\p1}}"
                     f"m {x - 0.5 * meritko:.1f} {y1:.1f} l {x + 0.5 * meritko:.1f} {y1:.1f} "
                     f"{x + 0.5 * meritko:.1f} {y2:.1f} {x - 0.5 * meritko:.1f} {y2:.1f}{{\\p0}}")
    barva, pruhlednost = _ass_barva(theme.UCHOP_RAMECEK, 1.0 if vybrano else 0.55)
    r = ramecek
    radky.append(f"{{\\an7\\pos(0,0)\\bord{(1.0 if vybrano else 0.75) * meritko:.2f}\\shad0\\1a&HFF&"
                 f"\\3c{barva}\\3a{pruhlednost}\\p1}}"
                 f"m {r.left():.1f} {r.top():.1f} l {r.right():.1f} {r.top():.1f} "
                 f"{r.right():.1f} {r.bottom():.1f} {r.left():.1f} {r.bottom():.1f}{{\\p0}}")
    if vybrano:
        vypln, _ = _ass_barva(theme.UCHOP_UCHYT)
        rohy = (r.topLeft(), r.topRight(), r.bottomRight(), r.bottomLeft())
        radky.append(f"{{\\an7\\pos(0,0)\\bord{meritko:.2f}\\shad0\\1c{vypln}\\3c{barva}\\p1}}"
                     + " ".join(_ctverec(roh, UCHYT_PX * meritko) for roh in rohy) + "{\\p0}")
    return "\n".join(radky)


# ---------- ovládání myší ----------
class UchopTitulku(QObject):
    """Převádí myš nad plochou videa na úpravu stylu.

    plocha    – widget s videem (šířka, výška, kurzor),
    rozmery() – vlastnost mpv osd-dimensions: {"w", "h", "ml", "mt", "mr", "mb"} v pixelech vrstvy nad
                videem, nebo None, když video není načtené,
    kresli(ass, w, h) – nakreslí vrstvu nad videem (ass=None ji odstraní).

    Signály: posun(x, y) a velikost(v) při tahu, konec() po puštění tlačítka, když se něco změnilo
    (uložit styl),
    klik_mimo() = kliknutí mimo titulek bez výběru (přehrát / pauza jako dřív)."""
    posun = Signal(float, float)
    velikost = Signal(float)
    konec = Signal()
    klik_mimo = Signal()

    def __init__(self, plocha, rozmery, kresli):
        super().__init__(plocha)
        self.plocha, self._rozmery, self._kresli = plocha, rozmery, kresli
        self.ramecek = None         # v pixelech videa
        self.vybrano = False
        self._klic = None
        self._W = self._H = 0
        self._x = self._y = 0.5     # pozice středu titulku (podíly)
        self._velikost = 0.1
        self._nad = None            # nad čím je myš: None, "titulek" nebo index rohu 0–3
        self._rezim = None          # probíhající tah: "posun" / "velikost"
        self._stisk = None          # bod stisku (pro rozlišení kliknutí a tahu)
        self._mimo = False          # stisk začal mimo titulek
        self._tah = {}
        self._prichyceno = False
        self._zmeneno = False       # tah už něco změnil (jinak šlo jen o kliknutí = výběr)
        self._nakresleno = None

    # --- stav z okna ---
    def nastav_titulek(self, text, styl, W, H):
        """Titulek, který je teď ve videu vidět (text=None = žádný), a styl, kterým je nakreslený."""
        klic = (text, styl.font, bool(styl.tucne), styl.velikost, bool(styl.velka_pismena), styl.obrys,
                styl.pozice_x, styl.pozice_y, W, H)
        if klic == self._klic:
            return
        self._klic = klic
        self._W, self._H = W, H
        self._x, self._y, self._velikost = styl.pozice_x, styl.pozice_y, styl.velikost
        self.ramecek = ramecek_titulku(text, styl, W, H) if text else None
        self.prekresli()

    def zrus_vyber(self):
        self.vybrano, self._rezim, self._nad, self._stisk = False, None, None, None
        self.plocha.unsetCursor()
        self.prekresli()

    def zapomen(self):
        """Nové video: žádný titulek, žádný výběr."""
        self._klic, self.ramecek = None, None
        self.zrus_vyber()

    # --- převody souřadnic ---
    def _zobrazeni(self):
        """(měřítko widget → vrstva ve směru x a y, obdélník videa ve vrstvě) nebo None."""
        d = self._rozmery()
        if not d or not self._W or not self._H or self.plocha.width() <= 0 or self.plocha.height() <= 0:
            return None
        try:
            w, h = float(d["w"]), float(d["h"])
            video = QRectF(float(d["ml"]), float(d["mt"]), w - float(d["ml"]) - float(d["mr"]),
                           h - float(d["mt"]) - float(d["mb"]))
        except (KeyError, TypeError, ValueError):
            return None
        if w <= 0 or h <= 0 or video.width() <= 0 or video.height() <= 0:
            return None
        return w / self.plocha.width(), h / self.plocha.height(), video, w, h

    @staticmethod
    def _do_vrstvy(bod, zobr):
        return QPointF(bod.x() * zobr[0], bod.y() * zobr[1])

    def _do_videa(self, bod_vrstvy, zobr):
        video = zobr[2]
        return QPointF((bod_vrstvy.x() - video.left()) / video.width() * self._W,
                       (bod_vrstvy.y() - video.top()) / video.height() * self._H)

    def _ramecek_ve_vrstve(self, zobr):
        """Rámeček titulku ve vrstvě nad videem, s odstupem od textu."""
        if self.ramecek is None:
            return None
        video = zobr[2]
        kx, ky = video.width() / self._W, video.height() / self._H
        r = QRectF(video.left() + self.ramecek.left() * kx, video.top() + self.ramecek.top() * ky,
                   self.ramecek.width() * kx, self.ramecek.height() * ky)
        o = OKRAJ_PX * zobr[0]
        return r.adjusted(-o, -o, o, o)

    def _co_je_pod(self, bod, zobr):
        r = self._ramecek_ve_vrstve(zobr)
        if r is None:
            return None
        b = self._do_vrstvy(bod, zobr)
        if self.vybrano:
            dosah = DOSAH_PX * zobr[0]
            for i, roh in enumerate((r.topLeft(), r.topRight(), r.bottomRight(), r.bottomLeft())):
                if abs(b.x() - roh.x()) <= dosah and abs(b.y() - roh.y()) <= dosah:
                    return i
        return "titulek" if r.contains(b) else None

    # --- myš ---
    def stisk(self, bod):
        zobr = self._zobrazeni()
        self._stisk, self._mimo, self._rezim, self._zmeneno = QPointF(bod), False, None, False
        pod = self._co_je_pod(bod, zobr) if zobr else None
        if pod is None:
            self._mimo = True
            return
        b = self._do_vrstvy(bod, zobr)
        video = zobr[2]
        stred = QPointF(video.left() + int(self._W * self._x) / self._W * video.width(),
                        video.top() + self._y * video.height())
        if pod == "titulek":
            self.vybrano, self._rezim = True, "posun"
            v = self._do_videa(b, zobr)
            self._tah = {"dx": v.x() - self._x * self._W, "dy": v.y() - self._y * self._H}
        else:
            self._rezim = "velikost"
            self._tah = {"stred": stred, "d0": max(math.hypot(b.x() - stred.x(), b.y() - stred.y()), 1.0),
                         "v0": self._velikost}
        self._nad = pod
        self._nastav_kurzor()
        self.prekresli()

    def pohyb(self, bod, stisknuto):
        zobr = self._zobrazeni()
        if zobr is None:
            return
        if not stisknuto or self._rezim is None:
            if not stisknuto:
                pod = self._co_je_pod(bod, zobr)
                if pod != self._nad:
                    self._nad = pod
                    self._nastav_kurzor()
                    self.prekresli()
            return
        b = self._do_vrstvy(bod, zobr)
        if self._rezim == "posun":
            v = self._do_videa(b, zobr)
            x = min(max((v.x() - self._tah["dx"]) / self._W, 0.0), 1.0)
            y = min(max((v.y() - self._tah["dy"]) / self._H, 0.0), 1.0)
            self._prichyceno = abs(x - 0.5) * zobr[2].width() <= PRICHYCENI_PX * zobr[0]
            if self._prichyceno:
                x = 0.5
            x, y = round(x, 4), round(y, 4)
            if (x, y) != (self._x, self._y):
                self._zmeneno = True
                self.posun.emit(x, y)
            else:
                self.prekresli()
        else:
            stred = self._tah["stred"]
            pomer = math.hypot(b.x() - stred.x(), b.y() - stred.y()) / self._tah["d0"]
            v = round(min(max(self._tah["v0"] * pomer, VELIKOST_OD), VELIKOST_DO), 3)
            if v != self._velikost:
                self._zmeneno = True
                self.velikost.emit(v)

    def uvolneni(self, bod):
        rezim, stisk, mimo = self._rezim, self._stisk, self._mimo
        self._rezim, self._stisk, self._mimo, self._prichyceno = None, None, False, False
        if rezim is not None:
            if self._zmeneno:  # pouhé kliknutí titulek jen vybere – styl se nezměnil, není co ukládat
                self.konec.emit()
            self.prekresli()
        elif mimo and stisk is not None and (abs(bod.x() - stisk.x()) + abs(bod.y() - stisk.y())) <= TAH_PX:
            if self.vybrano:  # klik vedle vybraného titulku jen zruší výběr
                self.vybrano = False
                self.prekresli()
            else:
                self.klik_mimo.emit()

    def opusteno(self):
        if self._rezim is None and self._nad is not None:
            self._nad = None
            self._nastav_kurzor()
            self.prekresli()

    def _nastav_kurzor(self):
        if self._nad is None:
            self.plocha.unsetCursor()
        elif self._nad == "titulek":
            self.plocha.setCursor(Qt.SizeAllCursor)
        else:  # rohy 0 a 2 leží na úhlopříčce zleva nahoře doprava dolů
            self.plocha.setCursor(Qt.SizeFDiagCursor if self._nad in (0, 2) else Qt.SizeBDiagCursor)

    # --- kreslení ---
    def prekresli(self):
        """Rámeček je vidět, když je titulek vybraný, myš je nad ním nebo se právě táhne."""
        zobr = self._zobrazeni()
        r = self._ramecek_ve_vrstve(zobr) if zobr else None
        if r is None or not (self.vybrano or self._nad is not None or self._rezim):
            if self._nakresleno is not None:
                self._nakresleno = None
                self._kresli(None, 0, 0)
            return
        video = zobr[2]
        voditko = None
        if self._rezim == "posun" and self._prichyceno:
            voditko = (video.center().x(), video.top(), video.bottom())
        ass = ass_prekryti(r, self.vybrano or bool(self._rezim), zobr[0], voditko)
        if (ass, zobr[3], zobr[4]) != self._nakresleno:
            self._nakresleno = (ass, zobr[3], zobr[4])
            self._kresli(ass, round(zobr[3]), round(zobr[4]))
