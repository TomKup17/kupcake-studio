"""Presety stylu titulků: pojmenované styly v presety.json v nastavení.

Vestavěný preset VYCHOZI (výchozí Styl) je vždy k dispozici a nejde přepsat ani smazat. Preset ukládá
vzhled titulků; časování (posun, předstih) patří ke konkrétnímu videu, a proto se presetem nemění.
"""
import json
from dataclasses import asdict, fields, replace

from titulky import Styl

VYCHOZI = ""  # klíč vestavěného presetu (zobrazený název je přeložený)
NEPRENASET = ("posun_ms", "predstih_ms")

# skupiny v sekci Nastavení → hodnoty stylu, které obsahují (tečka „liší se od presetu“ v záhlaví skupiny)
SKUPINY = {
    "text": ("font", "velikost", "barva_textu", "tucne", "velka_pismena"),
    "obrys": ("barva_obrysu", "obrys", "stin", "barva_stinu", "stin_rozmazani", "stin_x", "stin_y"),
    "pozadi": ("pozadi", "barva_pozadi", "pruhlednost_pozadi", "odsazeni_pozadi"),
    "pozice": ("pozice_y", "max_slov", "max_znaku"),
    "efekty": ("zvyrazneni", "barva_zvyrazneni"),
}


def _stejne(a, b):
    if isinstance(a, float) or isinstance(b, float):
        return abs(float(a) - float(b)) < 1e-6
    if isinstance(a, str) and isinstance(b, str):
        return a.casefold() == b.casefold()
    return a == b


class Presety:
    def __init__(self, soubor):
        self.soubor = soubor
        self.presety = {}       # název → slovník hodnot stylu
        self.aktualni = VYCHOZI
        try:
            data = json.loads(soubor.read_text(encoding="utf-8-sig"))  # snese i BOM (soubor upravený ručně)
            self.presety = {str(k): v for k, v in data.get("presety", {}).items() if k and isinstance(v, dict)}
            if data.get("aktualni") in self.presety:
                self.aktualni = data["aktualni"]
        except (OSError, ValueError, AttributeError):
            pass

    def _zapis(self):
        self.soubor.parent.mkdir(parents=True, exist_ok=True)
        self.soubor.write_text(json.dumps({"aktualni": self.aktualni, "presety": self.presety},
                                          ensure_ascii=False, indent=1), encoding="utf-8")

    def nazvy(self):
        return [VYCHOZI] + sorted(self.presety, key=str.casefold)

    def existuje(self, nazev):
        return nazev == VYCHOZI or nazev in self.presety

    def styl(self, nazev=None):
        """Styl presetu (nazev=None = aktuální preset)."""
        nazev = self.aktualni if nazev is None else nazev
        data = self.presety.get(nazev)
        if not data:
            return Styl()
        znama = {f.name for f in fields(Styl)}
        try:
            return Styl(**{k: v for k, v in data.items() if k in znama})
        except TypeError:
            return Styl()

    def pouzij(self, nazev, styl):
        """Nový styl = hodnoty presetu, časování zůstane z dosavadního stylu."""
        return replace(self.styl(nazev), **{k: getattr(styl, k) for k in NEPRENASET})

    def uloz(self, nazev, styl):
        data = asdict(styl)
        for k in NEPRENASET:
            data.pop(k, None)
        self.presety[nazev] = data
        self.aktualni = nazev
        self._zapis()

    def smaz(self, nazev):
        self.presety.pop(nazev, None)
        if self.aktualni == nazev:
            self.aktualni = VYCHOZI
        self._zapis()

    def nastav_aktualni(self, nazev):
        self.aktualni = nazev if self.existuje(nazev) else VYCHOZI
        self._zapis()

    def zmenene_skupiny(self, styl):
        """Skupiny, ve kterých se styl liší od aktuálního presetu."""
        vzor = self.styl()
        return {skupina for skupina, klice in SKUPINY.items()
                if any(not _stejne(getattr(styl, k), getattr(vzor, k)) for k in klice)}

    def vrat_skupinu(self, styl, skupina):
        """Styl s hodnotami jedné skupiny vrácenými na aktuální preset."""
        vzor = self.styl()
        return replace(styl, **{k: getattr(vzor, k) for k in SKUPINY[skupina]})
