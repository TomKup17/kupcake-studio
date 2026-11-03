"""Kolečko myši nemění hodnoty polí jen tím, že nad nimi kurzor projíždí.

Číselná pole, rozbalovací seznamy a posuvníky reagují na kolečko, až když do nich uživatel klikne
(mají fokus – vidět podle modrého obrysu). Jinak se kolečko předá nejbližšímu posouvatelnému
panelu, takže se panel Nastavení posouvá, jako by tam pole nebylo. Klik mimo pole nebo Esc fokus zruší.
Platí plošně pro všechny takové prvky, i budoucí – filtr je nainstalovaný na celou aplikaci.
"""
from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtWidgets import QAbstractScrollArea, QAbstractSpinBox, QApplication, QComboBox, QSlider

# QSlider, ne QAbstractSlider – posuvníky panelů (QScrollBar) ne
_TYPY = tuple(typ.__name__ for typ in (QAbstractSpinBox, QComboBox, QSlider))


def _je_pole(obj):
    # QObject.inherits("Název") místo isinstance/staticMetaObject – čistě v C++, bezpečné i u widgetů uprostřed
    # mazání a i když se filtr spustí během úklidu paměti Pythonu (wrapper staticMetaObject pak už neplatí)
    return obj.isWidgetType() and any(obj.inherits(typ) for typ in _TYPY)


def _pole(w):
    """Pole, ke kterému widget patří: on sám, nebo jeho rodič (vnitřní řádek číselného pole / seznamu)."""
    if w is None:
        return None
    if _je_pole(w):
        return w
    rodic = w.parentWidget()
    return rodic if rodic is not None and _je_pole(rodic) else None


def _aktivni_pole():
    return _pole(QApplication.focusWidget())


def _uvnitr(w, predek):
    """w je predek nebo jeho potomek – i přes hranici okna (rozbalený seznam je samostatné okno)."""
    while w is not None:
        if w is predek:
            return True
        w = w.parentWidget()
    return False


class ZamekKolecka(QObject):
    def eventFilter(self, obj, e):
        typ = e.type()
        if typ == QEvent.Polish and _je_pole(obj):
            # WheelFocus by dal poli fokus už otočením kolečka; NoFocus (např. posuvník přehrávače) se nemění
            if obj.focusPolicy() & Qt.WheelFocus == Qt.WheelFocus:
                obj.setFocusPolicy(Qt.StrongFocus)
        elif typ == QEvent.Wheel and _je_pole(obj):
            if _aktivni_pole() is obj or obj.focusPolicy() == Qt.NoFocus:
                return False  # aktivní pole (nebo prvek, který fokus mít nemůže) – kolečko mění hodnotu
            panel = obj.parentWidget()
            while panel is not None and not isinstance(panel, QAbstractScrollArea):
                panel = panel.parentWidget()
            if panel is not None:
                QApplication.sendEvent(panel.viewport(), e)  # posune panel místo změny hodnoty
            return True
        elif typ == QEvent.MouseButtonPress:
            pole = _aktivni_pole()
            if pole is not None and obj.isWidgetType() and not _uvnitr(obj, pole):
                QApplication.focusWidget().clearFocus()
        elif (typ == QEvent.KeyPress and e.key() == Qt.Key_Escape and obj.isWidgetType()
              and obj.window().windowType() != Qt.Popup):  # Esc v rozbaleném seznamu ho jen zavře
            pole = _aktivni_pole()
            if pole is not None and _uvnitr(obj, pole):
                QApplication.focusWidget().clearFocus()
                return True
        return False


def zapni(app):
    app._zamek_kolecka = ZamekKolecka(app)
    app.installEventFilter(app._zamek_kolecka)
