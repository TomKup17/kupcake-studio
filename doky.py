# kupcake.studio – Copyright (C) 2026 Tomáš Kupec
# SPDX-License-Identifier: GPL-3.0-only
"""Volně přesouvatelné sekce (PySide6-QtAds, Advanced Docking System, LGPL 2.1).

Sekce (Titulky, Náhled, Nastavení, Časová osa) jde chytit za záhlaví a ukotvit jinam, vložit jako záložku,
vytáhnout do samostatného okna, dvojklikem na záhlaví maximalizovat. Rozvržení se ukládá a jde si
pojmenovat (perspektivy QtAds).
"""
from xml.etree import ElementTree

import PySide6QtAds as ads
from PySide6.QtCore import QByteArray, QCoreApplication, QEvent, QObject, QSettings, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QAbstractButton, QFrame, QLabel, QVBoxLayout

import theme
from i18n import prekladej, t

M = ads.CDockManager
F = ads.CDockWidget.DockWidgetFeature

# chování dokování; dvojklik NEodpojuje sekci – používáme ho pro maximalizaci
KONFIGURACE = {
    M.eConfigFlag.OpaqueSplitterResize: True,
    M.eConfigFlag.AlwaysShowTabs: True,                 # záhlaví se jménem sekce i u jediné sekce
    M.eConfigFlag.DockAreaHasCloseButton: True,
    M.eConfigFlag.DockAreaCloseButtonClosesTab: True,
    M.eConfigFlag.DockAreaHasUndockButton: True,
    M.eConfigFlag.DockAreaHasTabsMenuButton: True,
    M.eConfigFlag.DockAreaDynamicTabsMenuButtonVisibility: True,
    M.eConfigFlag.DockAreaHideDisabledButtons: True,
    M.eConfigFlag.FloatingContainerHasWidgetTitle: True,
    M.eConfigFlag.FloatingContainerHasWidgetIcon: True,
    M.eConfigFlag.EqualSplitOnInsertion: True,
    M.eConfigFlag.DragPreviewIsDynamic: True,
    M.eConfigFlag.DragPreviewShowsContentPixmap: True,
    M.eConfigFlag.DragPreviewHasWindowFrame: False,
    M.eConfigFlag.FocusHighlighting: False,
    M.eConfigFlag.DoubleClickUndocksWidget: False,
    M.eConfigFlag.ActiveTabHasCloseButton: False,
    M.eConfigFlag.AllTabsHaveCloseButton: False,
    M.eConfigFlag.MiddleMouseButtonClosesTab: False,
    M.eConfigFlag.XmlCompressionEnabled: False,
}
ZAMYKATELNE = F.DockWidgetMovable | F.DockWidgetFloatable | F.DockWidgetClosable


class PosledniSekce(QObject):
    """Sekce, ve které uživatel naposledy klikl (= právě v ní pracuje), dostane vlastnost posledni=true –
    stylesheet jí pod záhlavím nakreslí oranžovou linku. Filtr je na celé aplikaci, aby zachytil kliknutí
    do kteréhokoli prvku sekce (i do plochy videa nebo časové osy)."""

    def __init__(self, rodic):
        super().__init__(rodic)
        self.oblast = None
        QCoreApplication.instance().installEventFilter(self)

    def eventFilter(self, obj, e):
        if e.type() != QEvent.MouseButtonPress or not obj.isWidgetType():
            return False
        w = obj
        while w is not None and not w.inherits("ads::CDockAreaWidget"):
            w = w.parentWidget()
        if w is not None and w is not self.oblast:
            self.oznac(w)
        return False

    def oznac(self, oblast):
        for o, ano in ((self.oblast, False), (oblast, True)):
            if o is None:
                continue
            try:
                o.setProperty("posledni", ano)
                for w in [o.titleBar()] + o.titleBar().findChildren(ads.CDockWidgetTab):
                    w.style().unpolish(w)
                    w.style().polish(w)
            except RuntimeError:  # oblast mezitím smazaná (přestavba rozvržení)
                pass
        self.oblast = oblast


class Dokovani(QObject):
    """Správce sekcí. Vysílá zprava(text) pro stavový řádek."""
    zprava = Signal(str)

    def __init__(self, rodic):
        super().__init__(rodic)
        for priznak, zapnuto in KONFIGURACE.items():
            M.setConfigFlag(priznak, zapnuto)
        self.m = M(rodic)
        self.m.setStyleSheet(theme.qss_doku())
        ikony = M.iconProvider()
        for druh, soubor in ((ads.TabCloseIcon, "ads_zavrit.svg"), (ads.DockAreaCloseIcon, "ads_zavrit.svg"),
                             (ads.DockAreaUndockIcon, "ads_odpojit.svg"), (ads.DockAreaMenuIcon, "ads_menu.svg")):
            ikony.registerCustomIcon(druh, theme.ikona(soubor, theme.TEXT_2))
        self.sekce = {}        # klíč → CDockWidget
        self._maximalizace = None
        self.zamceno = False
        self._akce = []        # klávesové zkratky hlavního okna, platí i v samostatných oknech sekcí
        self.posledni = PosledniSekce(self)
        self.m.dockAreaCreated.connect(self._nova_oblast)
        self.m.floatingWidgetCreated.connect(lambda okno: okno.addActions(self._akce))
        prekladej(self._preloz_oblasti)

    # ---------- sekce ----------
    def pridej(self, klic, klic_nazvu, obsah):
        """Sekce = karta: záhlaví (záložka QtAds: modrá tečka a název) a tělo s odsazením 12 px."""
        telo = QFrame()
        telo.setObjectName("kartaTelo")
        lay = QVBoxLayout(telo)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.addWidget(obsah)
        dw = ads.CDockWidget(klic)  # objectName = klíč → uložené rozvržení nezávisí na jazyku
        dw.setObjectName(klic)
        dw.setWidget(telo, ads.CDockWidget.eInsertMode.ForceNoScrollArea)
        dw.setIcon(theme.tecka())  # „● NÁHLED“ – malá modrá tečka před názvem jako na webu
        dw.setFeature(F.DockWidgetDeleteOnClose, False)
        dw.tabWidget().setFont(theme.pismo_zahlavi())  # štítkům ho nastaví eventFilter při zobrazení
        dw.tabWidget().installEventFilter(self)  # dvojklik na záhlaví = maximalizace

        def preloz():
            dw.setWindowTitle(t(klic_nazvu))
            dw.toggleViewAction().setText(t(klic_nazvu))
        prekladej(preloz)
        self.sekce[klic] = dw
        return dw

    def sdilej_akce(self, akce):
        """Zkratky (Mezerník, J K L, Delete…) mají kontext okna – samostatné okno sekce je musí mít taky."""
        self._akce = list(akce)
        for okno in self.m.floatingWidgets():
            okno.addActions(self._akce)

    def vychozi_rozmisteni(self):
        """Titulky | Náhled | Nastavení nahoře, Časová osa dole přes celou šířku."""
        s = self.sekce
        titulky = self.m.addDockWidget(ads.LeftDockWidgetArea, s["titulky"])
        nahled = self.m.addDockWidget(ads.RightDockWidgetArea, s["nahled"], titulky)
        self.m.addDockWidget(ads.RightDockWidgetArea, s["nastaveni"], nahled)
        self.m.addDockWidget(ads.BottomDockWidgetArea, s["osa"])

    def vychozi_velikosti(self):
        """Poměr 36 : 40 : 24, časová osa jen tak vysoká, jak potřebuje (volá se nad zobrazeným oknem).
        Oblasti se berou znovu ze sekcí – po restoreState jsou ty původní smazané."""
        sirka, vyska = self.m.width(), self.m.height()
        self.m.setSplitterSizes(self.sekce["titulky"].dockAreaWidget(),
                                [int(sirka * 0.36), int(sirka * 0.40), int(sirka * 0.24)])
        osa = self.sekce["osa"].widget().sizeHint().height() + 40
        self.m.setSplitterSizes(self.sekce["osa"].dockAreaWidget(), [max(vyska - osa, 200), osa])

    def _oblasti(self):
        for kontejner in self.m.dockContainers():
            for i in range(kontejner.dockAreaCount()):
                yield kontejner.dockArea(i)

    def _popisky(self, oblast):
        # findChild podle jména, ne titleBar().button(): ten občas vrátí obal už smazaného tlačítka
        lista = oblast.titleBar()
        for jmeno, klic in (("dockAreaCloseButton", "dok.zavrit"), ("detachGroupButton", "dok.odpojit"),
                            ("tabsMenuButton", "dok.menu")):
            b = lista.findChild(QAbstractButton, jmeno)
            if b is not None:
                b.setToolTip(t(klic))

    def _nova_oblast(self, oblast):
        """Popisky tlačítek v záhlaví (QtAds je má anglicky) – i u oblastí vzniklých přesunem."""
        self._popisky(oblast)
        oblast.titleBar().installEventFilter(self)

    def _preloz_oblasti(self):
        for oblast in self._oblasti():
            self._popisky(oblast)

    # ---------- maximalizace dvojklikem na záhlaví ----------
    def eventFilter(self, obj, e):
        if e.type() == QEvent.Show and obj.inherits("ads::CDockWidgetTab"):
            # písmo záhlaví („● NÁHLED“) – QtAds ho štítku při vložení do oblasti vrátí na výchozí
            for w in obj.findChildren(QLabel):
                if w.font() != theme.pismo_zahlavi():
                    w.setFont(theme.pismo_zahlavi())
            return False
        if e.type() != QEvent.MouseButtonDblClick:
            return False
        dw = None
        if isinstance(obj, ads.CDockWidgetTab):
            dw = obj.dockWidget()
        elif isinstance(obj, ads.CDockAreaTitleBar):
            dw = obj.dockAreaWidget().currentDockWidget()
        if dw is None or dw.isInFloatingContainer():
            return False
        self.prepni_maximalizaci(dw)
        return True

    def _obnov_stav(self, obnoveni):
        """restoreState/openPerspective + hned dokončit odložené mazání. QtAds při obnově plovoucí okna,
        která už nepotřebuje, jen naplánuje ke smazání (deleteLater), ale do té doby je při další obnově
        použije znovu – dvě obnovy po sobě by tak smazaly sekci, kterou mezitím do okna vložil."""
        vysledek = obnoveni()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        return vysledek

    def prepni_maximalizaci(self, dw):
        if self._maximalizace is not None:
            stav, self._maximalizace = self._maximalizace, None
            self._obnov_stav(lambda: self.m.restoreState(stav))
            return
        self._maximalizace = self.m.saveState()
        for jiny in self.sekce.values():
            if jiny is not dw and not jiny.isClosed() and not jiny.isInFloatingContainer():
                jiny.toggleView(False)
        self.zprava.emit(t("rozvrzeni.maximalizovano", nazev=dw.windowTitle()))

    def je_maximalizovano(self):
        return self._maximalizace is not None

    # ---------- stav, zámek, pojmenovaná rozvržení ----------
    def stav(self):
        """Uložitelný stav (maximalizovaná sekce se ukládá v původním rozvržení)."""
        return self._maximalizace if self._maximalizace is not None else self.m.saveState()

    def platny_stav(self, stav):
        """QtAds při nečitelném XML (useknutý nebo cizí soubor) může spadnout celý – proto kontrola předem:
        well-formed XML QtAds a jen sekce, které tahle verze zná."""
        try:
            koren = ElementTree.fromstring(bytes(stav))
        except (ElementTree.ParseError, TypeError, ValueError):
            return False
        if koren.tag != "QtAdvancedDockingSystem":
            return False
        jmena = {e.get("Name") for e in koren.iter("Widget")}
        return bool(jmena) and jmena <= set(self.sekce)

    def neco_videt(self):
        return any(not dw.isClosed() for dw in self.sekce.values())

    def okna_na_obrazovku(self, hlavni):
        """Samostatné okno uložené na monitoru, který už není připojený, se přesune nad hlavní okno."""
        obrazovky = [s.availableGeometry() for s in QGuiApplication.screens()]
        for okno in self.m.floatingWidgets():
            if not any(o.intersects(okno.frameGeometry()) for o in obrazovky):
                okno.move(hlavni.frameGeometry().center() - okno.rect().center())

    def obnov(self, stav):
        self._maximalizace = None
        return bool(stav) and self._obnov_stav(lambda: self.m.restoreState(stav))

    def zamkni(self, zamknout):
        """Zamčené rozvržení: sekce nejde přesouvat, odpojovat ani zavírat (velikost jde měnit dál)."""
        self.zamceno = zamknout
        self.m.lockDockWidgetFeaturesGlobally(ZAMYKATELNE if zamknout else F(0))

    def nacti_rozvrzeni(self, soubor):
        """Uložená rozvržení; nečitelná se vynechají (při otevření by QtAds spadl)."""
        s = QSettings(str(soubor), QSettings.IniFormat)
        self.m.loadPerspectives(s)
        n = s.beginReadArray("Perspectives")
        for i in range(n):
            s.setArrayIndex(i)
            nazev, stav = s.value("Name"), s.value("State")
            if nazev and not (isinstance(stav, QByteArray) and self.platny_stav(stav)):
                self.m.removePerspective(nazev)
        s.endArray()

    def uloz_rozvrzeni(self, soubor):
        s = QSettings(str(soubor), QSettings.IniFormat)
        self.m.savePerspectives(s)
        s.sync()

    def nazvy_rozvrzeni(self):
        return list(self.m.perspectiveNames())

    def pridej_rozvrzeni(self, nazev):
        if self._maximalizace is not None:
            self.prepni_maximalizaci(None)
        self.m.addPerspective(nazev)

    def otevri_rozvrzeni(self, nazev):
        self._maximalizace = None
        self._obnov_stav(lambda: self.m.openPerspective(nazev))

    def smaz_rozvrzeni(self, nazev):
        self.m.removePerspective(nazev)
