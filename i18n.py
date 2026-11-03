"""Překlady rozhraní.

Texty jsou v locales/<kód>.json (klíč → text, parametry ve tvaru {jmeno}). Nový jazyk = nový JSON soubor,
kód se měnit nemusí. Chybějící klíč se vezme z češtiny (výchozí, vždy úplná), jinak se zobrazí klíč.

  t("klic", n=3)          – přeložený text
  prekladej(lambda: ...)  – nastaví text hned a znovu při každé změně jazyka (živé přepnutí bez restartu)
"""
import json

from PySide6.QtCore import QLibraryInfo, QLocale, QSettings, QTranslator
from PySide6.QtWidgets import QApplication

from cesty import APP_DIR, NASTAVENI_DIR

LOCALES_DIR = APP_DIR / "locales"
VYCHOZI = "cs"      # úplný jazyk, ze kterého se doplňují chybějící klíče
ZALOZNI = "en"      # když jazyk Windows není podporovaný

_jazyk = VYCHOZI
_texty, _zaloha = {}, {}
_registr = []       # funkce, které nastavují texty widgetů
_qt_preklad = None


def _nacti_json(kod):
    try:
        return json.loads((LOCALES_DIR / f"{kod}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def dostupne():
    """[(kód, název jazyka v jeho vlastní podobě)] v pořadí podle "_poradi" v souborech."""
    jazyky = []
    for f in LOCALES_DIR.glob("*.json"):
        data = _nacti_json(f.stem)
        if data.get("_jazyk"):
            jazyky.append((data.get("_poradi", 99), f.stem, data["_jazyk"]))
    return [(kod, nazev) for _, kod, nazev in sorted(jazyky)]


def nastaveni():
    return QSettings(str(NASTAVENI_DIR / "aplikace.ini"), QSettings.IniFormat)


def jazyk_systemu():
    kod = QLocale.system().name().split("_")[0].lower()
    return kod if kod in dict(dostupne()) else ZALOZNI


def aktualni():
    return _jazyk


def nastav(kod, ulozit=False):
    """Přepne jazyk a znovu nastaví všechny zaregistrované texty."""
    global _jazyk, _texty, _zaloha
    if kod not in dict(dostupne()):
        kod = ZALOZNI
    _jazyk = kod
    _zaloha = _nacti_json(VYCHOZI)
    _texty = _nacti_json(kod)
    if ulozit:
        nastaveni().setValue("jazyk/rozhrani", kod)
    _nastav_qt(kod)
    for fn in list(_registr):
        try:
            fn()
        except RuntimeError:  # widget už neexistuje
            _registr.remove(fn)


def nacti_ulozeny():
    """Při startu: uložený jazyk, poprvé jazyk Windows (nebo angličtina)."""
    nastav(nastaveni().value("jazyk/rozhrani") or jazyk_systemu())


def _nastav_qt(kod):
    """Texty ve vestavěných dialozích Qt (Ano/Ne, výběr barvy…) a formát čísel."""
    global _qt_preklad
    app = QApplication.instance()
    QLocale.setDefault(QLocale(kod))
    if app is None:
        return
    if _qt_preklad is not None:
        app.removeTranslator(_qt_preklad)
        _qt_preklad = None
    preklad = QTranslator(app)
    if preklad.load(f"qtbase_{kod}", QLibraryInfo.path(QLibraryInfo.TranslationsPath)):
        app.installTranslator(preklad)
        _qt_preklad = preklad


def ma(klic):
    return klic in _texty or klic in _zaloha


def t(klic, **parametry):
    text = _texty.get(klic) or _zaloha.get(klic) or klic
    return text.format(**parametry) if parametry else text


def prekladej(fn):
    """Zavolá fn hned a znovu po každé změně jazyka. fn nastavuje texty (setText, setTitle…)."""
    fn()
    _registr.append(fn)
    return fn
