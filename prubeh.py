"""Průběh dlouhé práce po fázích s vahou a její zrušení.

Práce běží ve vlákně (main.Uloha) a hlásí průběh voláním progress(podíl, faze=None). Fáze mají váhu
podle typické doby trvání, takže celková procenta odpovídají skutečnému postupu:

    faze = Faze(progress, [("audio", 5), ("prepis", 70), ("zarovnani", 20), ("docisteni", 5)])
    p = faze.zacni("prepis")   # → progress(0.05, "prepis")
    p(0.5)                     # → progress(0.40)  (5 % + polovina ze 70 %)

Zrušení: vlákno nastaví příznak a nejbližší hlášení průběhu vyhodí Zruseno – práce skončí na nejbližším
bezpečném místě (mezi segmenty přepisu, úseky zarovnání, bloky stahování).
"""


class Zruseno(Exception):
    """Uživatel zpracování zrušil."""


class Faze:
    def __init__(self, progress, vahy):
        celkem = sum(v for _, v in vahy) or 1
        self.progress = progress
        self.od, self.podil, k = {}, {}, 0.0
        for klic, vaha in vahy:
            self.od[klic], self.podil[klic] = k / celkem, vaha / celkem
            k += vaha

    def zacni(self, klic):
        """Ohlásí začátek fáze a vrátí její vlastní progress(0–1) přepočtený na celek."""
        od, podil = self.od[klic], self.podil[klic]
        self.progress(od, klic)
        return lambda p: self.progress(od + podil * min(max(p, 0.0), 1.0))
