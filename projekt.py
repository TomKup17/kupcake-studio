"""Projekt kupcake.studio (.kupcake): rozpracovaná práce v jednom souboru – video (cesta), titulky se slovy
a časy, značky, styl, časování, smyčka a rozvržení sekcí.

Formát je čitelný JSON (nikdy pickle), zapisuje se atomicky (dočasný soubor + přejmenování), takže pád
uprostřed ukládání nepoškodí poslední uložený projekt. Cesta k videu se ukládá absolutně i relativně
k projektu – projekt přenesený i s videem do jiné složky se tak pořád najde.

Načítání nevěří obsahu souboru: každá hodnota se převede na očekávaný typ (čísla, texty, seznamy),
cokoli jiného skončí srozumitelnou ChybaProjektu místo pádu uvnitř aplikace. Projekt nikdy nespouští
kód – cesta k videu je jen cesta k souboru, který se otevře přes FFmpeg/mpv (jen místní soubory).

Automatické ukládání: každé 2 minuty (jsou-li neuložené změny) do %LOCALAPPDATA%\\KupcakeStudio\\autosave.
Při běžném zavření se soubor smaže; když tam po spuštění leží, aplikace minule nedoběhla a nabídne obnovu.
"""
import base64
import json
import os
from dataclasses import asdict
from pathlib import Path

from cesty import DATA_DIR
from titulky import Slovo, Styl, Titulek, Znacka

PRIPONA = ".kupcake"
FORMAT = 1
AUTOSAVE = DATA_DIR / "autosave" / ("obnova" + PRIPONA)
AUTOSAVE_MS = 2 * 60 * 1000
MAX_VELIKOST = 64 * 2**20  # projekt větší než 64 MB není projekt kupcake.studio (titulky mají desítky kB)


class ChybaProjektu(Exception):
    """Soubor není projekt kupcake.studio nebo je poškozený / z novější verze."""


# ---------- převod ----------
def _titulky_do(titulky):
    return [{"start": t.start, "end": t.end, "text": t.text, "zamceno": t.zamceno,
             "slova": [[s.text, s.start, s.end] for s in t.slova]} for t in titulky]


def _cislo(x):
    """float z čísla (ne bool, ne text) – JSON z cizího zdroje může mít cokoliv."""
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        raise TypeError(f"očekáváno číslo, je {type(x).__name__}")
    v = float(x)
    if v != v or v in (float("inf"), float("-inf")):
        raise ValueError("čas není konečné číslo")
    return v


def _text(x):
    if not isinstance(x, str):
        raise TypeError(f"očekáván text, je {type(x).__name__}")
    return x


def _seznam(x):
    if not isinstance(x, list):
        raise TypeError(f"očekáván seznam, je {type(x).__name__}")
    return x


def _titulky_z(data):
    return [Titulek(_cislo(t["start"]), _cislo(t["end"]), _text(t["text"]),
                    [Slovo(_text(s[0]), _cislo(s[1]), _cislo(s[2])) for s in _seznam(t.get("slova", []))],
                    bool(t.get("zamceno", False))) for t in _seznam(data)]


def _slova_z(data):
    """Slova přepisu [{text, start, end}] – jen správně tvarované položky; jinak prázdné (přepis se nehodí)."""
    if not isinstance(data, list):
        return []
    slova = []
    for s in data:
        if isinstance(s, dict):
            try:
                slova.append({"text": _text(s["text"]), "start": _cislo(s["start"]), "end": _cislo(s["end"])})
            except (KeyError, TypeError, ValueError):
                return []
    return slova


def sestav(video, info, titulky, znacky, styl, slova, jazyk, posun_zvuku, zarovnano, smycka, rozvrzeni,
           cesta_projektu=None, verze=""):
    """Slovník projektu připravený k uložení."""
    video = Path(video)
    relativni = None
    if cesta_projektu:
        try:
            relativni = os.path.relpath(video, Path(cesta_projektu).parent)
        except ValueError:  # jiný disk
            relativni = None
    return {
        "kupcake.studio": FORMAT,
        "verze_aplikace": verze,
        "video": {"cesta": str(video), "relativni": relativni, "info": list(info)},
        "titulky": _titulky_do(titulky),
        "znacky": [{"t": z.t, "text": z.text} for z in znacky],
        "styl": asdict(styl),
        "prepis": {"slova": slova, "jazyk": jazyk, "posun_zvuku": posun_zvuku, "zarovnano": zarovnano},
        "smycka": list(smycka) if smycka else None,
        "rozvrzeni": base64.b64encode(bytes(rozvrzeni)).decode("ascii") if rozvrzeni else None,
    }


def uloz(cesta, data):
    """Atomický zápis: nejdřív vedle do .tmp (zapsáno až na disk), pak přejmenovat – starý soubor zůstane,
    kdyby zápis selhal nebo aplikace spadla uprostřed."""
    cesta = Path(cesta)
    cesta.parent.mkdir(parents=True, exist_ok=True)
    docasny = cesta.with_name(cesta.name + ".tmp")
    text = json.dumps(data, ensure_ascii=False, indent=1)  # nejdřív celý text – chyba tu nic na disku nezmění
    try:
        with open(docasny, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(docasny, cesta)
    except BaseException:
        docasny.unlink(missing_ok=True)
        raise


def nacti(cesta):
    """Vrátí slovník projektu s rozbalenými objekty (titulky, značky, styl); při chybě ChybaProjektu."""
    cesta = Path(cesta)
    try:
        if cesta.stat().st_size > MAX_VELIKOST:
            raise ChybaProjektu("soubor je příliš velký na projekt kupcake.studio")
        data = json.loads(cesta.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as e:
        raise ChybaProjektu(str(e)) from e
    if not isinstance(data, dict) or "kupcake.studio" not in data:
        raise ChybaProjektu("není to projekt kupcake.studio")
    try:
        format_souboru = int(data["kupcake.studio"])
    except (TypeError, ValueError) as e:
        raise ChybaProjektu(f"poškozený projekt ({e})") from e
    if format_souboru > FORMAT:
        raise ChybaProjektu("projekt je z novější verze aplikace")
    try:
        v = data["video"]
        prepis = data.get("prepis") or {}
        if not isinstance(prepis, dict):
            prepis = {}
        jazyk = prepis.get("jazyk")
        smycka = data.get("smycka")
        rozvrzeni = data.get("rozvrzeni")
        vysledek = {
            "video": Path(_text(v["cesta"])),
            "video_relativni": _text(v["relativni"]) if v.get("relativni") is not None else None,
            "info": tuple(_cislo(x) for x in _seznam(v.get("info") or [])),
            "titulky": _titulky_z(data.get("titulky", [])),
            "znacky": [Znacka(_cislo(z["t"]), _text(z.get("text", ""))) for z in _seznam(data.get("znacky", []))],
            "styl": Styl.z_dict(data.get("styl", {})),
            "slova": _slova_z(prepis.get("slova")),
            "jazyk": jazyk if isinstance(jazyk, str) and 0 < len(jazyk) <= 8 else None,
            "posun_zvuku": _cislo(prepis.get("posun_zvuku") or 0.0),
            "zarovnano": bool(prepis.get("zarovnano", False)),
            "smycka": (_cislo(smycka[0]), _cislo(smycka[1])) if smycka and len(_seznam(smycka)) == 2 else None,
            "rozvrzeni": base64.b64decode(_text(rozvrzeni), validate=True) if rozvrzeni else None,
        }
    except (KeyError, TypeError, ValueError, IndexError, AttributeError) as e:
        raise ChybaProjektu(f"poškozený projekt ({e})") from e
    return vysledek


def najdi_video(projekt, cesta_projektu):
    """Video projektu: uložená absolutní cesta, jinak relativní vůči projektu; None = nenalezeno."""
    try:
        if projekt["video"].is_file():
            return projekt["video"]
        if projekt.get("video_relativni") and cesta_projektu:
            kandidat = (Path(cesta_projektu).parent / projekt["video_relativni"]).resolve()
            if kandidat.is_file():
                return kandidat
    except OSError:  # cesta s nepovolenými znaky apod.
        pass
    return None
