# kupcake.studio – Copyright (C) 2026 Tomáš Kupec
# SPDX-License-Identifier: GPL-3.0-only
"""Vzhled aplikace kupcake.studio na jednom místě: paleta, písma, stylesheet, ikony, záře a animace.

Barvy značky iamtom.kup střídmě, jako akcenty – dvě role, které se nemíchají:
- modrá #00B4FF = výběr a aktivní/fokusované prvky: označená slova a řádky, pole s fokusem, záložky,
  zaškrtávátka, přepínače,
- oranžová #FF6A00 = „teď“ a „akce“: co se právě přehrává a kde jsem v čase (přehrávací hlava, posuvník
  a čas přehrávače, právě přehrávaný titulek, smyčka, značky), hlavní akce (Exportovat, Uložit preset,
  Přehrát), sekce, ve které právě pracuju, běžící zpracování a hotový export. Jinde se nepoužívá.
Vše ostatní klidné a neutrální na téměř černém pozadí.

Kontrast (WCAG): tmavý text #080808 na oranžové #FF6A00 = 7,0 : 1, oranžový text na pozadí #080808
= 7,0 : 1 a na panelu #111214 = 6,5 : 1 (vše nad hranicí AA 4,5 : 1, viz kontrast()).
"""
from string import Template

from PySide6.QtCore import QByteArray, QEvent, QLineF, QObject, QPointF, Qt, QVariantAnimation
from PySide6.QtGui import QColor, QFont, QFontDatabase, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QToolButton, QWidget

from cesty import APP_DIR, DATA_DIR, IKONY_DIR, LOGO

# ---------- paleta ----------
POZADI = "#080808"          # pozadí aplikace – téměř černá značky
PANEL = "#111214"           # karty / panely
PANEL_TMAVY = "#0C0D0E"     # vnořené plochy (tabulka, měřítko, vlna)
RAMECEK = "#1F2226"         # rámečky a oddělovače
POLE = "#17191C"            # vstupní pole, tlačítka
POLE_HOVER = "#1F2125"      # tlačítko pod myší
POLE_RAMECEK = "#2A2E34"
TEXT = "#F2EFEA"            # teplá bílá jako na webu
TEXT_2 = "#8A8F98"          # vedlejší text
TEXT_3 = "#565B63"          # neaktivní
AKCENT = "#00B4FF"          # modrá značky – hlavní akcent
AKCENT_HOVER = "#4DCBFF"
AKCENT_TLUMENY = "#0A7DB3"  # tlumená modrá (průběh, posuvník)
AKCE = "#FF6A00"            # oranžová značky – „teď“ a hlavní akce (viz popis modulu)
AKCE_HOVER = "#FF8533"      # oranžová pod myší
AKCE_ZARE = "#FFA05C"       # světlejší „rozzářená“ oranžová (šipky pod myší, záře)
AKCE_TEXT = POZADI          # text na oranžovém pozadí – vždy tmavý
AKCE_TINT = (255, 106, 0, 28)       # oranžový nádech (pozadí tlačítka v notifikaci pod myší)
AKCE_TLUMENA = (255, 106, 0, 110)   # obrys tlačítka v notifikaci
DOPLNEK = "#C9B48A"         # tlumená písková (dříve smyčka a značky)
# časová osa – oranžová značky pro orientaci (výběr slov zůstává modrý, ať se s přehrávací hlavou nepletou)
OSA_HLAVA = AKCE            # přehrávací hlava: čára 2 px se září, úchyt v měřítku a štítek s časem
OSA_HLAVA_TEXT = AKCE_TEXT  # tmavý text na oranžovém štítku
OSA_ZNACKA = AKCE           # značky (markery)
OSA_SMYCKA = AKCE           # úsek smyčky (poloprůhledně):
OSA_SMYCKA_ALFA = {"meritko": (95, 38), "stopy": (16, 6), "okraj": (200, 80)}  # (zapnutá, vypnutá) krytí 0–255
OSA_PRAVE_HRAJE = AKCE      # tenká linka pod právě přehrávaným slovem
OSA_ZAMEK = AKCE            # ikonka zámku u zamčeného titulku
OSA_MAGNET_ZAP = AKCE       # ikona přichytávání: zapnuto
OSA_MAGNET_VYP = TEXT_3     #                     vypnuto
# přehrávač
PREHRAVAC_PREHRANO = AKCE           # přehraná část posuvníku a úchyt
PREHRAVAC_ZBYTEK = POLE_RAMECEK     # nepřehraná část – tlumená šedá
PREHRAVAC_CAS = AKCE                # aktuální čas (JetBrains Mono); celková délka v TEXT_2
PLAY_ZARE = (255, 106, 0, 150)      # záře tlačítka Přehrát/Pauza pod myší
PLAY_ZARE_POLOMER = 7               # šířka záře kolem kolečka (px) – kreslí se uvnitř plochy tlačítka
# seznam titulků
TITULEK_PROUZEK = AKCE      # svislý proužek vlevo u právě přehrávaného titulku
TITULEK_PROUZEK_SIRKA = 3
TITULEK_CAS = AKCE          # časy právě přehrávaného titulku
TITULEK_PREKRYV = AKCE      # ikonka upozornění při překryvu časů
# nastavení
SKUPINA_ZMENA = AKCE        # tečka v záhlaví skupiny: hodnoty se liší od presetu
# skupiny (kategorie) v Nastavení: pozadí se střídá A, B, A, B… podle pořadí, ať je poznat, co ke které patří
SKUPINA_POZADI_A = PANEL    # = pozadí panelu (#111214)
SKUPINA_POZADI_B = "#1C1F23"  # o ~5 % světlejší tmavě šedá
SKUPINA_PROUZEK = AKCE      # svislý proužek vlevo u rozbalené kategorie
SKUPINA_PROUZEK_SIRKA = 3
SKUPINA_HLAVA_ROZBALENA = "#FFFFFF"  # text hlavičky rozbalené kategorie (sbalené zůstávají TEXT_2)
# sekce (dokovací panely): linka pod záhlavím – sekce, ve které právě pracuju, oranžová, ostatní neutrální
SEKCE_LINKA = RAMECEK
SEKCE_LINKA_AKTIVNI = AKCE
SEKCE_LINKA_SIRKA = 2
# tečka u loga: v klidu modrá, během zpracování pulzuje oranžově
LOGO_TECKA = AKCENT
LOGO_TECKA_PRACE = AKCE
LOGO_PULZ_MS = 1400
# notifikace v rohu okna (hotový export)
NOTIFIKACE_AKCENT = AKCE
NOTIFIKACE_MS = 6000        # po kolika ms sama zmizí (pod myší se odpočet zastaví)
# šipky číselných polí (QSpinBox / QDoubleSpinBox)
SPIN_SIPKA = AKCE                   # v klidu
SPIN_SIPKA_HOVER = AKCE_ZARE        # pod myší – světlejší, „rozzářená“ oranžová
SPIN_SIPKA_OFF = TEXT_3             # pole vypnuté nebo hodnota na minimu/maximu
SPIN_STISK = (255, 106, 0, 55)      # pozadí tlačítka při stisku – oranžová s nízkou krycí schopností
SPIN_TLACITKO = 19                  # šířka tlačítek se šipkami (px)
CHYBA_POZADI, CHYBA_RAMECEK, CHYBA_TEXT = "#2A1418", "#5C2229", "#FFA7A7"
VIDEO_POZADI = "#050505"
# překrytí zpracování: ztlumení rozhraní (#080808, cca 70 % krytí) a tlumená silueta nevyplněného cupcaku
ZTLUMENI = (8, 8, 8, 179)
SILUETA = "#1A1C20"
SILUETA_OBRYS = "#33373E"
VLNA = "#2B5F7D"

# samostatné slovo (titulek z jediného slova) – jedna neutrální barva pro všechna
SLOVO_SAMOSTATNE = "#2A2E35"
# barvy skupin slov (titulků) na časové ose – tlumené, ladí s černou; žádná není modrá ani oranžová,
# ať modrý rámeček výběru vždy jasně vynikne; sousední se vždy liší
SKUPINY = ["#3D6B5C", "#6A4C7D", "#7A4652", "#5F6B3A", "#4F5670"]  # šalvějová, švestková, vínová, olivová, břidlicová

RADIUS_PANEL, RADIUS_PRVEK = 8, 6
ANIMACE_MS = 150

# ---------- písma ----------
FONTY_UI_DIR = APP_DIR / "fonty_ui"
PISMO_UI = "Segoe UI"
PISMO_MONO = "Consolas"


def nacti_pisma():
    """Zaregistruje přibalené Inter a JetBrains Mono; když chybí, použije Segoe UI Variable / Consolas."""
    global PISMO_UI, PISMO_MONO
    for f in sorted(FONTY_UI_DIR.glob("*.ttf")):
        QFontDatabase.addApplicationFont(str(f))
    rodiny = set(QFontDatabase.families())
    PISMO_UI = next((r for r in ("Inter", "Segoe UI Variable Text", "Segoe UI") if r in rodiny), "Segoe UI")
    PISMO_MONO = next((r for r in ("JetBrains Mono", "Cascadia Mono", "Consolas") if r in rodiny), "Consolas")


def pismo_mono(velikost=9, tucne=False):
    f = QFont(PISMO_MONO, velikost)
    f.setWeight(QFont.DemiBold if tucne else QFont.Normal)
    return f


def pismo_nadpisu(velikost=10):
    """Názvy sekcí: malé kapitálky s mírně rozšířenými rozestupy."""
    f = QFont(PISMO_UI)
    f.setPointSizeF(velikost)
    f.setWeight(QFont.DemiBold)
    f.setCapitalization(QFont.SmallCaps)
    f.setLetterSpacing(QFont.PercentageSpacing, 108)
    return f


def pismo_zahlavi(velikost=8.5):
    """Záhlaví panelů v technickém stylu webu: JetBrains Mono, velká písmena, rozšířené rozestupy."""
    f = QFont(PISMO_MONO)
    f.setPointSizeF(velikost)
    f.setWeight(QFont.DemiBold)
    f.setCapitalization(QFont.AllUppercase)
    f.setLetterSpacing(QFont.PercentageSpacing, 116)
    return f


def tecka(barva=AKCENT, velikost=16, prumer=6):
    """Malá kulatá tečka (před názvem panelu, v logu, indikátor stavu) jako ikona."""
    pix = QPixmap(velikost * 2, velikost * 2)
    pix.setDevicePixelRatio(2)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(barva))
    p.drawEllipse(QPointF(velikost / 2, velikost / 2), prumer / 2, prumer / 2)
    p.end()
    return QIcon(pix)


def logo_html(velikost_pt=12, tecka_barva=AKCENT):
    """Logo „• kupcake.studio“: modrá tečka, „kupcake“ tučně v teplé bílé, „.studio“ ve vedlejší šedé
    (stejný princip jako „• iamtom.kup“ na webu). tecka_barva=None = bez tečky (záhlaví aplikace má
    vlastní pulzující tečku, PulzujiciTecka)."""
    hlavni, pripona = LOGO
    tecka_ = (f"<span style='color:{tecka_barva}; font-size:{velikost_pt * 0.6:.1f}pt'>●</span>&nbsp;"
              if tecka_barva else "")
    return (f"<span style='font-size:{velikost_pt}pt'>{tecka_}"
            f"<b style='color:{TEXT}'>{hlavni}</b><span style='color:{TEXT_2}'>{pripona}</span></span>")


def kontrast(a, b):
    """Kontrastní poměr dvou barev podle WCAG 2 (1 až 21)."""
    def jas(c):
        c = QColor(c)
        slozky = []
        for v in (c.redF(), c.greenF(), c.blueF()):
            slozky.append(v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4)
        return 0.2126 * slozky[0] + 0.7152 * slozky[1] + 0.0722 * slozky[2]
    svetla, tmava = sorted((jas(a), jas(b)), reverse=True)
    return (svetla + 0.05) / (tmava + 0.05)


def rgba(barva):
    """(r, g, b, a) → zápis pro stylesheet."""
    return f"rgba({', '.join(map(str, barva))})"


# ---------- ikony ----------
_PREBARVENI = {"#D8CF2A": None, "#1E2026": PANEL}


def ikona(nazev, barva=AKCENT, velikost=16):
    """SVG ikona z ikony/ přebarvená podle palety (v souborech je původní žlutá #D8CF2A)."""
    svg = (IKONY_DIR / nazev).read_text(encoding="utf-8")
    for puvodni, nova in _PREBARVENI.items():
        svg = svg.replace(puvodni, nova or barva)
    pix = QPixmap()
    pix.loadFromData(QByteArray(svg.encode()), "SVG")
    return QIcon(pix) if velikost is None else QIcon(pix.scaled(velikost * 2, velikost * 2, Qt.KeepAspectRatio,
                                                              Qt.SmoothTransformation))


def ikona_magnetu(velikost=16):
    """Přichytávání: zapnuto (zaškrtnutá akce) oranžový magnet, vypnuto šedý."""
    ikon = QIcon()
    for barva, stav in ((OSA_MAGNET_ZAP, QIcon.On), (OSA_MAGNET_VYP, QIcon.Off)):
        pix = ikona("magnet.svg", barva, velikost).pixmap(velikost * 2, velikost * 2)
        pix.setDevicePixelRatio(2)
        for rezim in (QIcon.Normal, QIcon.Active, QIcon.Disabled):
            ikon.addPixmap(pix, rezim, stav)
    return ikon


def _qss_ikony():
    """Ikony, na které odkazuje stylesheet (fajfka), přebarvené do datové složky."""
    cil = DATA_DIR / "tema"
    cil.mkdir(parents=True, exist_ok=True)
    svg = (IKONY_DIR / "fajfka.svg").read_text(encoding="utf-8").replace("#FFFFFF", POZADI)
    (cil / "fajfka.svg").write_text(svg, encoding="utf-8")
    # úchyty mezi sekcemi: v klidu neutrální, pod myší modré
    for nazev in ("uchyt_svisly", "uchyt_vodorovny"):
        svg = (IKONY_DIR / f"{nazev}.svg").read_text(encoding="utf-8")
        (cil / f"{nazev}.svg").write_text(svg.replace("#D8CF2A", POLE_RAMECEK), encoding="utf-8")
        (cil / f"{nazev}_akcent.svg").write_text(svg.replace("#D8CF2A", AKCENT), encoding="utf-8")
    # šipky číselných polí: ostrý trojúhelník; v klidu oranžová, pod myší světlejší, na hranici/vypnuté šedá
    tvary = {"nahoru": "M1.2 7.4 L5 2.6 L8.8 7.4 Z", "dolu": "M1.2 2.6 L5 7.4 L8.8 2.6 Z"}
    for smer, cesta in tvary.items():
        for stav, barva in (("", SPIN_SIPKA), ("_hover", SPIN_SIPKA_HOVER), ("_off", SPIN_SIPKA_OFF)):
            (cil / f"sipka_{smer}{stav}.svg").write_text(
                f'<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" viewBox="0 0 10 10">'
                f'<path d="{cesta}" fill="{barva}"/></svg>', encoding="utf-8")
    return cil.as_posix()


# ---------- dokovací sekce (PySide6-QtAds) ----------
_QSS_DOKY = Template("""
ads--CDockContainerWidget { background: $POZADI; }
ads--CDockSplitter::handle { background: transparent; }
ads--CDockSplitter::handle:horizontal { width: 12px; image: url($IKONY/uchyt_svisly.svg); }
ads--CDockSplitter::handle:vertical { height: 12px; image: url($IKONY/uchyt_vodorovny.svg); }
ads--CDockSplitter::handle:horizontal:hover { image: url($IKONY/uchyt_svisly_akcent.svg); }
ads--CDockSplitter::handle:vertical:hover { image: url($IKONY/uchyt_vodorovny_akcent.svg); }

/* sekce = karta: světlejší panel, jemný rámeček, zaoblené rohy */
ads--CDockAreaWidget { background: $PANEL; border: 1px solid $RAMECEK; border-radius: ${RP}px; }
ads--CDockAreaTitleBar { background: transparent; border: none; border-bottom: ${LS}px solid $LINKA;
                         border-top-left-radius: ${RP}px; border-top-right-radius: ${RP}px;
                         min-height: 34px; padding: 0 4px 0 2px; }
/* sekce, ve které právě pracuju (poslední kliknutí): oranžová linka pod záhlavím místo podtržení záložky */
ads--CDockAreaWidget[posledni="true"] ads--CDockAreaTitleBar { border-bottom-color: $LINKA_AKTIVNI; }
ads--CDockAreaWidget[posledni="true"] ads--CDockWidgetTab[activeTab="true"] { border-bottom-color: transparent; }
ads--CDockAreaTabBar { background: transparent; border: none; }
ads--CDockAreaTabBar > QWidget { background: transparent; }
ads--CDockWidgetTab { background: transparent; border: none; border-bottom: 2px solid transparent;
                      padding: 0 10px 0 8px; qproperty-iconSize: 16px; }
ads--CDockWidgetTab[activeTab="true"] { border-bottom: 2px solid $AKCENT; }
ads--CDockWidgetTab QLabel { color: $TEXT_2; background: transparent; padding-left: 2px; }
ads--CDockWidgetTab[activeTab="true"] QLabel { color: $TEXT; }
ads--CDockWidgetTab:hover QLabel { color: $TEXT; }
ads--CDockWidget { background: $PANEL; border: none; border-bottom-left-radius: ${RP}px;
                   border-bottom-right-radius: ${RP}px; }
ads--CTitleBarButton { background: transparent; border: none; border-radius: 4px; padding: 3px; }
ads--CTitleBarButton:hover { background: $POLE_HOVER; }
ads--CTitleBarButton:pressed { background: $POLE_RAMECEK; }
ads--CFloatingDockContainer { background: $POZADI; }
ads--CFloatingDockContainer ads--CDockContainerWidget { padding: 6px; }

/* náhled ukotvení: plocha je v barvě zvýraznění (modrá), kříž s ikonami v paletě */
ads--CDockOverlayCross { qproperty-iconFrameColor: $AKCENT; qproperty-iconBackgroundColor: $PANEL;
                         qproperty-iconOverlayColor: $AKCENT; qproperty-iconArrowColor: $TEXT;
                         qproperty-iconShadowColor: rgba(0, 0, 0, 150); }
""")


def qss_doku():
    return _QSS_DOKY.substitute(
        POZADI=POZADI, PANEL=PANEL, RAMECEK=RAMECEK, TEXT=TEXT, TEXT_2=TEXT_2, AKCENT=AKCENT,
        POLE_HOVER=POLE_HOVER, POLE_RAMECEK=POLE_RAMECEK, RP=RADIUS_PANEL, IKONY=_qss_ikony(),
        LINKA=SEKCE_LINKA, LINKA_AKTIVNI=SEKCE_LINKA_AKTIVNI, LS=SEKCE_LINKA_SIRKA)


# ---------- stylesheet ----------
_QSS = Template("""
QWidget { color: $TEXT; }
QMainWindow, QDialog { background: $POZADI; }
QToolTip { background: $POLE; color: $TEXT; border: 1px solid $POLE_RAMECEK; padding: 4px 6px; }

/* karty sekcí */
QFrame#karta { background: $PANEL; border: 1px solid $RAMECEK; border-radius: ${RP}px; }
QWidget#kartaHlava { background: transparent; border: none; border-bottom: 1px solid $RAMECEK;
                     border-top-left-radius: ${RP}px; border-top-right-radius: ${RP}px; }
QLabel#kartaNazev { color: $TEXT; }
QFrame#kartaTelo { background: transparent; border: none; }
QPushButton#skupinaHlava { background: transparent; border: none; border-bottom: 1px solid $RAMECEK;
                           border-radius: 0; color: $TEXT_2; text-align: left; padding: 8px 2px 8px 12px; }
QPushButton#skupinaHlava:hover { color: $TEXT; background: transparent; }
QPushButton#skupinaHlava:checked { color: $SKUPINA_HLAVA_ROZBALENA; }
QToolButton#zmenaTecka { background: transparent; border: none; border-radius: 8px; padding: 0; }
QToolButton#zmenaTecka:hover { background: $AKCE_TINT; }

/* menu */
QMenuBar { background: $POZADI; padding: 2px 8px; color: $TEXT_2; }
QMenuBar::item { padding: 5px 10px; border-radius: ${RE}px; background: transparent; }
QMenuBar::item:selected { background: $POLE; color: $TEXT; }
QMenu { background: $PANEL; border: 1px solid $RAMECEK; padding: 4px; }
QMenu::item { padding: 6px 26px 6px 16px; border-radius: ${RE}px; }
QMenu::item:selected { background: $POLE_HOVER; color: $TEXT; }
QMenu::item:disabled { color: $TEXT_3; }
QMenu::separator { height: 1px; background: $RAMECEK; margin: 4px 8px; }

/* tlačítka: plochá, při najetí jemně světlejší (plynulost zajišťuje HoverAnimace) */
QPushButton { background: $POLE; border: 1px solid $POLE_RAMECEK; border-radius: ${RE}px; padding: 7px 16px; }
QPushButton:hover { background: $POLE_HOVER; }
QPushButton:pressed { background: $POLE_RAMECEK; }
QPushButton:disabled { color: $TEXT_3; background: $PANEL; border-color: $RAMECEK; }
/* hlavní tlačítka jako na webu: „pilulka“ – primární oranžové (jen hlavní akce), sekundární s obrysem */
QPushButton#primary, QPushButton#sekundarni { border-radius: 16px; padding: 7px 20px; min-height: 18px; }
QPushButton#primary { background: $AKCE; color: $POZADI; border: 1px solid $AKCE; font-weight: 600; }
QPushButton#primary:hover { background: $AKCE_HOVER; border-color: $AKCE_HOVER; }
QPushButton#primary:disabled { background: #3A2414; border-color: #3A2414; color: #8A6A55; }
QPushButton#sekundarni { background: transparent; color: $TEXT; border: 1px solid #3A3F46; }
QPushButton#sekundarni:hover { border-color: $TEXT_2; background: rgba(242, 239, 234, 10); }
QPushButton#sekundarni:pressed { background: rgba(242, 239, 234, 20); }
QPushButton#sekundarni:disabled { color: $TEXT_3; border-color: $RAMECEK; }
QPushButton#barva { border: 1px solid $POLE_RAMECEK; border-radius: ${RE}px; padding: 0; min-height: 24px; }
QToolButton#nastroj { background: $POLE; border: 1px solid $POLE_RAMECEK; border-radius: ${RE}px; padding: 3px 9px; }
QToolButton#nastroj:hover { background: $POLE_HOVER; }
QToolButton#nastroj:checked { background: $AKCENT_TINT; border-color: $AKCENT; color: $AKCENT; }
QToolButton#nastroj:disabled { color: $TEXT_3; background: $PANEL; border-color: $RAMECEK; }
/* přichytávání: stav ukazuje ikona magnetu (oranžová = zapnuto, šedá = vypnuto), ne modré podbarvení */
QToolButton#nastroj[magnet="true"] { padding: 3px 9px 3px 6px; }
QToolButton#nastroj[magnet="true"]:checked { background: $POLE; border-color: $POLE_RAMECEK; color: $TEXT; }
QToolButton#nastroj[magnet="true"]:!checked { color: $TEXT_2; }
QFrame#oddelovac { color: $RAMECEK; }

/* přehrávač: Přehrát/Pauza oranžové (kreslí PlayTlacitko), posuvník – přehraná část a úchyt oranžové */
QSlider#prubehVidea::groove:horizontal { height: 4px; background: $PREHRAVAC_ZBYTEK; border-radius: 2px; }
QSlider#prubehVidea::sub-page:horizontal { background: $PREHRAVAC_PREHRANO; border-radius: 2px; }
QSlider#prubehVidea::add-page:horizontal { background: $PREHRAVAC_ZBYTEK; border-radius: 2px; }
QSlider#prubehVidea::handle:horizontal { width: 12px; margin: -5px 0; border-radius: 6px;
                                         background: $PREHRAVAC_PREHRANO; border: none; }
QSlider#prubehVidea::handle:horizontal:hover { background: $AKCE_HOVER; }
QSlider#prubehVidea::handle:horizontal:pressed { background: $AKCE_ZARE; }

/* panel s možnostmi exportu (karta uprostřed ztlumené aplikace) */
QFrame#exportKarta { background: $PANEL; border: 1px solid $POLE_RAMECEK; border-radius: ${RP}px; }
QWidget#exportHlava { background: transparent; border-bottom: 1px solid $RAMECEK; }
QLabel#exportNadpis { color: $TEXT; }
QWidget#exportTelo, QWidget#exportPata { background: transparent; }
QWidget#exportPata { border-top: 1px solid $RAMECEK; }
QFrame#exportCara { background: $RAMECEK; border: none; }
QLabel#exportPopis { color: $TEXT_2; }
QLabel#exportPopisek { color: $TEXT_2; }
QLabel#exportHodnota { color: $TEXT; font-family: "$MONO"; padding: 4px 2px; }
QLabel#exportShrnuti { color: $TEXT_2; }
QLabel#exportVarovani { color: $CHYBA_TEXT; }
QFrame#exportUpozorneni { background: $POLE; border: 1px solid $POLE_RAMECEK; border-radius: ${RE}px; }
/* přepínač „co exportovat“ – vybraná část modře (výběr) */
QPushButton#segment { background: transparent; color: $TEXT_2; border: 1px solid $POLE_RAMECEK;
                      border-radius: 0; padding: 7px 10px; }
QPushButton#segment[poloha="prvni"] { border-top-left-radius: ${RE}px; border-bottom-left-radius: ${RE}px; }
QPushButton#segment[poloha="posledni"] { border-top-right-radius: ${RE}px; border-bottom-right-radius: ${RE}px; }
QPushButton#segment:hover { color: $TEXT; background: $POLE_HOVER; }
QPushButton#segment:checked { color: $TEXT; background: $AKCENT_TINT; border-color: $AKCENT; }
/* dlaždice rychlých presetů */
QToolButton#dlazdice { background: $POLE; color: $TEXT_2; border: 1px solid $POLE_RAMECEK; border-radius: ${RE}px;
                       padding: 8px 4px; }
QToolButton#dlazdice:hover { background: $POLE_HOVER; color: $TEXT; }
QToolButton#dlazdice:checked { background: $AKCENT_TINT; border-color: $AKCENT; color: $TEXT; }

/* okno O aplikaci: odkazy-tlačítka (Co je nového, Licence…) a text změn / licencí */
QPushButton#odkazTlacitko { background: transparent; border: none; color: $TEXT_2; padding: 6px 8px;
                            border-radius: ${RE}px; }
QPushButton#odkazTlacitko:hover { color: $TEXT; background: $POLE_HOVER; }
QTextBrowser#oAplikaciText { background: $PANEL_TMAVY; border: 1px solid $RAMECEK; border-radius: ${RE}px;
                             padding: 10px; color: $TEXT; }

/* notifikace v rohu okna */
QPushButton#notifikaceAkce { background: transparent; color: $AKCE; border: 1px solid $AKCE_TLUMENA;
                             border-radius: 13px; padding: 4px 14px; font-weight: 600; }
QPushButton#notifikaceAkce:hover { background: $AKCE_TINT; border-color: $AKCE; }
QPushButton#notifikaceAkce:pressed { background: $AKCE_TINT; }
QToolButton#notifikaceZavrit { background: transparent; border: none; color: $TEXT_3; padding: 0 2px; }
QToolButton#notifikaceZavrit:hover { color: $TEXT; }
QLabel#notifikaceNadpis { color: $TEXT; font-weight: 600; }
QLabel#notifikaceText { color: $TEXT_2; }

/* texty */
QWidget#logo, QWidget#logo QLabel { background: transparent; }
QLabel#betaStitek { color: $TEXT_2; border: 1px solid $POLE_RAMECEK; border-radius: 4px; padding: 0 4px;
                    margin-top: 2px; }
QLabel#stavTecka { background: transparent; }
QLabel#nazev { font-size: 12pt; font-weight: 600; }
QLabel#stav { color: $TEXT_2; }
QLabel#casovyKod { font-family: "$MONO"; color: $TEXT_2; }
QLabel#varovani { background: $CHYBA_POZADI; color: $CHYBA_TEXT; border: 1px solid $CHYBA_RAMECEK;
                  border-radius: ${RE}px; padding: 6px 10px; }
QLabel#nahled { background: $VIDEO_POZADI; border-radius: ${RP}px; color: $TEXT_3; }

/* seznam titulků */
QTableWidget { background: $PANEL_TMAVY; alternate-background-color: #0F1012; gridline-color: $RAMECEK;
               border: 1px solid $RAMECEK; border-radius: ${RE}px; selection-background-color: #0B2533;
               selection-color: $TEXT; }
QHeaderView::section { background: $PANEL; color: $TEXT_2; border: none; border-bottom: 1px solid $RAMECEK;
                       padding: 6px; }
QTableWidget QLineEdit { background: $POLE; border: 1px solid $AKCENT; border-radius: 4px; }
QWidget#cas { background: transparent; }
QWidget#cas QLineEdit { background: transparent; border: 1px solid transparent; border-radius: 4px;
                        color: $TEXT_2; padding: 1px 2px; font-family: "$MONO"; }
QWidget#cas QLineEdit:focus { background: $POLE; border-color: $AKCENT; color: $TEXT; }
QWidget#cas[aktivni="true"] QLineEdit { color: $TITULEK_CAS; }
QWidget#cas QToolButton { background: transparent; border: none; color: $TEXT_3; padding: 0 2px; }
QWidget#cas QToolButton:hover { color: $AKCENT; }

/* pole a ovládací prvky: aktivní = tenký modrý obrys */
QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit { background: $POLE; border: 1px solid $POLE_RAMECEK;
                                                  border-radius: ${RE}px; padding: 4px 6px; }
QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QLineEdit:focus { border-color: $AKCENT; }
QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover { border-color: #3A3F46; }

/* číselná pole: vpravo dvě tlačítka se šipkami, oddělená tenkými linkami */
QSpinBox, QDoubleSpinBox { padding-right: ${SPIN_PRAVY}px; }
QSpinBox::up-button, QDoubleSpinBox::up-button, QSpinBox::down-button, QDoubleSpinBox::down-button {
    subcontrol-origin: border; width: ${SPIN_W}px; background: transparent;
    border: none; border-left: 1px solid $RAMECEK; }
QSpinBox::up-button, QDoubleSpinBox::up-button { subcontrol-position: top right;
    border-bottom: 1px solid $RAMECEK; border-top-right-radius: ${RE}px; }
QSpinBox::down-button, QDoubleSpinBox::down-button { subcontrol-position: bottom right;
    border-bottom-right-radius: ${RE}px; }
QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover { background: $POLE_HOVER; }
QSpinBox::up-button:pressed, QDoubleSpinBox::up-button:pressed,
QSpinBox::down-button:pressed, QDoubleSpinBox::down-button:pressed { background: $SPIN_STISK; }
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow { image: url($IKONY/sipka_nahoru.svg); width: 9px; height: 9px; }
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow { image: url($IKONY/sipka_dolu.svg); width: 9px; height: 9px; }
QSpinBox::up-arrow:hover, QDoubleSpinBox::up-arrow:hover { image: url($IKONY/sipka_nahoru_hover.svg); }
QSpinBox::down-arrow:hover, QDoubleSpinBox::down-arrow:hover { image: url($IKONY/sipka_dolu_hover.svg); }
QSpinBox::up-arrow:disabled, QSpinBox::up-arrow:off,
QDoubleSpinBox::up-arrow:disabled, QDoubleSpinBox::up-arrow:off { image: url($IKONY/sipka_nahoru_off.svg); }
QSpinBox::down-arrow:disabled, QSpinBox::down-arrow:off,
QDoubleSpinBox::down-arrow:disabled, QDoubleSpinBox::down-arrow:off { image: url($IKONY/sipka_dolu_off.svg); }
QComboBox QAbstractItemView { background: $PANEL; border: 1px solid $RAMECEK; selection-background-color: #0B2533; }
QLineEdit#editorSlova { background: $POLE; border: 1px solid $AKCENT; border-radius: 4px; padding: 2px 6px; }
QSlider::groove:horizontal { height: 4px; background: $POLE_RAMECEK; border-radius: 2px; }
QSlider::sub-page:horizontal { background: $AKCENT_TLUMENY; border-radius: 2px; }
QSlider::handle:horizontal { width: 12px; margin: -5px 0; border-radius: 7px; background: $TEXT;
                             border: 1px solid $POLE_RAMECEK; }
QSlider::handle:horizontal:hover { background: #FFFFFF; }
QSlider::handle:horizontal:pressed { background: $POZADI; border: 2px solid $AKCENT; }
QSlider::handle:horizontal:focus { border: 2px solid $AKCENT; }
QProgressBar { background: $RAMECEK; border: none; border-radius: 1px; }
QProgressBar::chunk { background: $AKCENT_TLUMENY; border-radius: 1px; }

/* zaškrtávátka a přepínače */
QCheckBox, QRadioButton { color: $TEXT; spacing: 8px; }
QCheckBox:disabled, QRadioButton:disabled { color: $TEXT_3; }
QCheckBox::indicator, QRadioButton::indicator { width: 18px; height: 18px; }
QCheckBox::indicator { border: 2px solid $TEXT_2; border-radius: 4px; background: $PANEL_TMAVY; }
QRadioButton::indicator { border: 2px solid $TEXT_2; border-radius: 11px; background: $PANEL_TMAVY; }
QCheckBox::indicator:hover, QRadioButton::indicator:hover { border-color: $TEXT; }
QCheckBox::indicator:checked { border-color: $AKCENT; background: $AKCENT; image: url($IKONY/fajfka.svg); }
QCheckBox::indicator:checked:hover { border-color: $AKCENT_HOVER; background: $AKCENT_HOVER; }
QRadioButton::indicator:checked { border: 5px solid $AKCENT; background: $POZADI; border-radius: 11px;
                                  width: 12px; height: 12px; }
QCheckBox::indicator:disabled, QRadioButton::indicator:disabled { border-color: $TEXT_3; background: $PANEL; }
QCheckBox::indicator:checked:disabled { background: #0B4A66; border-color: #0B4A66; }

/* posuvníky: tenké a nenápadné */
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical { background: transparent; width: 8px; margin: 2px; }
QScrollBar:horizontal { background: transparent; height: 8px; margin: 2px; }
QScrollBar::handle:vertical { background: $POLE_RAMECEK; border-radius: 2px; min-height: 28px; }
QScrollBar::handle:horizontal { background: $POLE_RAMECEK; border-radius: 2px; min-width: 28px; }
QScrollBar::handle:hover { background: #3A3F46; }
QScrollBar::handle:pressed { background: $AKCENT_TLUMENY; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }

QGraphicsView { border: 1px solid $RAMECEK; border-radius: ${RE}px; background: $PANEL_TMAVY; }
""")


def qss():
    a = QColor(AKCENT)
    return _QSS.substitute(
        TEXT=TEXT, TEXT_2=TEXT_2, TEXT_3=TEXT_3, POZADI=POZADI, PANEL=PANEL, PANEL_TMAVY=PANEL_TMAVY,
        RAMECEK=RAMECEK, POLE=POLE, POLE_HOVER=POLE_HOVER, POLE_RAMECEK=POLE_RAMECEK, AKCENT=AKCENT,
        AKCENT_HOVER=AKCENT_HOVER, AKCENT_TLUMENY=AKCENT_TLUMENY, VIDEO_POZADI=VIDEO_POZADI,
        AKCE=AKCE, AKCE_HOVER=AKCE_HOVER, SPIN_W=SPIN_TLACITKO, SPIN_PRAVY=SPIN_TLACITKO + 6,
        SPIN_STISK=rgba(SPIN_STISK), AKCE_ZARE=AKCE_ZARE, AKCE_TINT=rgba(AKCE_TINT),
        AKCE_TLUMENA=rgba(AKCE_TLUMENA), PREHRAVAC_PREHRANO=PREHRAVAC_PREHRANO,
        PREHRAVAC_ZBYTEK=PREHRAVAC_ZBYTEK, TITULEK_CAS=TITULEK_CAS, AKCE_TEXT=AKCE_TEXT,
        SKUPINA_HLAVA_ROZBALENA=SKUPINA_HLAVA_ROZBALENA,
        AKCENT_LINKA=f"rgba({a.red()}, {a.green()}, {a.blue()}, 140)",
        AKCENT_TINT=f"rgba({a.red()}, {a.green()}, {a.blue()}, 28)",
        CHYBA_POZADI=CHYBA_POZADI, CHYBA_RAMECEK=CHYBA_RAMECEK, CHYBA_TEXT=CHYBA_TEXT,
        RP=RADIUS_PANEL, RE=RADIUS_PRVEK, MONO=PISMO_MONO, IKONY=_qss_ikony())


def paleta(app):
    from PySide6.QtGui import QPalette
    pal = QPalette()
    for role, barva in [(QPalette.Window, POZADI), (QPalette.WindowText, TEXT), (QPalette.Base, PANEL_TMAVY),
                        (QPalette.AlternateBase, PANEL), (QPalette.Text, TEXT), (QPalette.Button, POLE),
                        (QPalette.ButtonText, TEXT), (QPalette.Highlight, AKCENT),
                        (QPalette.HighlightedText, POZADI), (QPalette.ToolTipBase, POLE),
                        (QPalette.ToolTipText, TEXT), (QPalette.PlaceholderText, TEXT_3)]:
        pal.setColor(role, QColor(barva))
    app.setPalette(pal)


def pouzij(app):
    """Celý vzhled: písma, paleta, stylesheet a plynulé najetí myší na tlačítka."""
    app.setStyle("Fusion")
    nacti_pisma()
    app.setFont(QFont(PISMO_UI, 10))
    paleta(app)
    app.setStyleSheet(qss())
    app._hover = HoverAnimace(app)
    app.installEventFilter(app._hover)


# ---------- záře (kreslí se přímo v paint(), ať časová osa zůstane plynulá) ----------
def zar(p, tvar, barva=AKCENT, sila=1.0, radius=4):
    """Jemná neonová záře kolem obdélníku `tvar` (QRectF): několik průsvitných tahů + ostrý okraj."""
    c = QColor(barva)
    p.save()
    p.setRenderHint(QPainter.Antialiasing)
    p.setBrush(Qt.NoBrush)
    for sirka, alfa in ((7, 22), (4.5, 45), (2.5, 90)):
        c.setAlpha(int(alfa * sila))
        p.setPen(QPen(c, sirka))
        p.drawRoundedRect(tvar, radius, radius)
    c.setAlpha(255)
    p.setPen(QPen(c, 1.5))
    p.drawRoundedRect(tvar, radius, radius)
    p.restore()


def zar_cara(p, x, y1, y2, barva=AKCENT, tloustka=1.5):
    """Svislá svítící čára (přehrávací hlava): jemná záře a ostrá čára dané tloušťky."""
    c = QColor(barva)
    p.save()
    for sirka, alfa in ((tloustka + 7, 22), (tloustka + 3, 55), (tloustka, 255)):
        c.setAlpha(alfa)
        pero = QPen(c, sirka)
        pero.setCapStyle(Qt.FlatCap)
        p.setPen(pero)
        p.drawLine(QLineF(x, y1, x, y2))
    p.restore()


# ---------- animace ----------
def _mix(a, b, t):
    a, b = QColor(a), QColor(b)
    return QColor(round(a.red() + (b.red() - a.red()) * t), round(a.green() + (b.green() - a.green()) * t),
                  round(a.blue() + (b.blue() - a.blue()) * t)).name()


class PulzujiciTecka(QWidget):
    """Tečka u loga v záhlaví: v klidu modrá, během zpracování (přepis, export) jemně pulzuje oranžově –
    tečka mírně dýchá a kolem ní se rozlévá slabá záře."""

    def __init__(self, prumer=7):
        super().__init__()
        self.prumer = prumer
        self.setFixedSize(prumer + 10, prumer + 10)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._faze = 0.0
        self.anim = QVariantAnimation(self)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.setDuration(LOGO_PULZ_MS)
        self.anim.setLoopCount(-1)
        self.anim.valueChanged.connect(self._tik)

    def pulzuj(self, ano):
        if ano and self.anim.state() != QVariantAnimation.Running:
            self.anim.start()
        elif not ano:
            self.anim.stop()
            self._faze = 0.0
        self.update()

    def pulzuje(self):
        return self.anim.state() == QVariantAnimation.Running

    def _tik(self, v):
        self._faze = v
        self.update()

    def paintEvent(self, e):
        import math
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        stred = QPointF(self.width() / 2, self.height() / 2)
        r = self.prumer / 2
        if self.pulzuje():
            s = 0.5 - 0.5 * math.cos(self._faze * 2 * math.pi)  # 0 → 1 → 0, plynule
            zare = QColor(LOGO_TECKA_PRACE)
            zare.setAlpha(int(25 + 70 * s))
            p.setBrush(zare)
            p.drawEllipse(stred, r + 1.5 + 2.5 * s, r + 1.5 + 2.5 * s)
            p.setBrush(QColor(LOGO_TECKA_PRACE))
            p.drawEllipse(stred, r * (0.92 + 0.12 * s), r * (0.92 + 0.12 * s))
        else:
            p.setBrush(QColor(LOGO_TECKA))
            p.drawEllipse(stred, r, r)
        p.end()


class HoverAnimace(QObject):
    """Plynulé (150 ms) zesvětlení tlačítek při najetí myší – stylesheet přechody neumí.
    Během animace dostane tlačítko vlastní barvu pozadí, po odjetí se vrátí čistý stylesheet."""

    def eventFilter(self, obj, e):
        # QObject.inherits("Název") místo isinstance: Leave chodí i widgetům uprostřed mazání (QtAds při
        # přestavbě rozvržení) – jejich Python obal by ještě tvrdil „tlačítko“ a volání metod tlačítka spadne.
        # Ne přes staticMetaObject: jeho Python obal může zneplatnit úklid paměti (filtr pak padá dokola).
        if e.type() not in (QEvent.Enter, QEvent.Leave) or not obj.isWidgetType():
            return False
        if obj.inherits("QPushButton") or obj.inherits("QToolButton"):
            barvy = self._barvy(obj)
            if barvy:
                self._animuj(obj, *barvy, e.type() == QEvent.Enter)
        return False

    @staticmethod
    def _barvy(w):
        if not w.isEnabled() or (w.isCheckable() and w.isChecked()):
            return None
        jmeno = w.objectName()
        if isinstance(w, QToolButton):
            return (POLE, POLE_HOVER) if jmeno == "nastroj" else None
        if jmeno == "primary":
            return AKCE, AKCE_HOVER
        return (POLE, POLE_HOVER) if jmeno == "" else None

    @staticmethod
    def _animuj(w, od, do, dovnitr):
        anim = getattr(w, "_hover_anim", None)
        if anim is None:
            anim = QVariantAnimation(w)
            anim.setDuration(ANIMACE_MS)
            anim.valueChanged.connect(lambda v, w=w, od=od, do=do: w.setStyleSheet(
                f"background-color: {_mix(od, do, v)};" if v > 0.001 else ""))
            w._hover_anim = anim
        stav = anim.currentValue() if anim.state() == QVariantAnimation.Running else (0.0 if dovnitr else 1.0)
        anim.stop()
        anim.setStartValue(float(stav))
        anim.setEndValue(1.0 if dovnitr else 0.0)
        anim.start()

