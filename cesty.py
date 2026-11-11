# kupcake.studio – Copyright (C) 2026 Tomáš Kupec
# SPDX-License-Identifier: GPL-3.0-only
"""Název aplikace, verze a cesty – zdroje (fonty, ikony, mpv, FFmpeg) a uživatelská data."""
import os
import shutil
import sys
from pathlib import Path

from version import VERZE  # noqa: E402,F401 – verze je v version.py

# Soukromí: knihovny Hugging Face (huggingface_hub, transformers) čtou tyto proměnné při importu, proto se
# nastavují tady – cesty.py se importuje před nimi. Modely stahuje a ověřuje jen stahovani.py; knihovny samy
# nesmí na síť (OFFLINE), nesmí posílat telemetrii ani hledat přihlašovací token uživatele na disku.
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN"] = "1"
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("DO_NOT_TRACK", "1")

NAZEV = "kupcake.studio"      # zobrazovaný název – vždy přesně takto: malými písmeny, s tečkou
TECH_NAZEV = "KupcakeStudio"   # soubory a složky: KupcakeStudio.exe, %APPDATA%\KupcakeStudio…
LOGO = ("kupcake", ".studio")  # v logu: první část tučně v teplé bílé, druhá ve vedlejší šedé
AUTOR = "iamtom.kup"
AUTOR_JMENO = "Tomáš Kupec"
WEB = "https://tomkup.cz"
APP_ID = "iamtomkup.kupcakestudio"  # AppUserModelID – ikona a seskupení na hlavním panelu Windows
MUTEX = "KupcakeStudioBeziMutex"    # podle něj instalátor pozná, že aplikace běží
# dřívější názvy (Spellcast do 1.1, tkStudio 1.2) – jen kvůli přesunu nastavení (migruj_stara_data);
# novější první: když existují obě složky, má přednost obsah z tkStudio
STARE_NAZVY = ("tkStudio", "Spellcast")

# zdroje leží vedle skriptů; v buildu z PyInstalleru ve složce _internal (sys._MEIPASS)
APP_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
FONTY_DIR = APP_DIR / "fonts"
IKONY_DIR = APP_DIR / "ikony"
MPV_DIR = APP_DIR / "mpv"
FFMPEG_DIR = APP_DIR / "ffmpeg"  # jen v buildu; ze zdrojáků se použije FFmpeg z PATH
IKONA = APP_DIR / "kupcake.ico"

_ROAMING = Path(os.environ.get("APPDATA") or Path.home())
_LOKALNI = Path(os.environ.get("LOCALAPPDATA") or Path.home())
# nastavení (roaming) – %APPDATA%\KupcakeStudio
NASTAVENI_DIR = _ROAMING / TECH_NAZEV
STYL_SOUBOR = NASTAVENI_DIR / "styl.json"
# velká a dočasná data (lokální) – %LOCALAPPDATA%\KupcakeStudio
DATA_DIR = _LOKALNI / TECH_NAZEV
TMP_DIR = DATA_DIR / "tmp"
MODELY_DIR = DATA_DIR / "models"

# složky dřívějších verzí – při prvním spuštění se jejich obsah přesune sem
STARE_SLOZKY = [(_ROAMING / n, _LOKALNI / n) for n in STARE_NAZVY]
# dřívější umístění stylu: %LOCALAPPDATA%\Spellcast (verze 1.0), vedle skriptů (Titulkovač)
STARE_NASTAVENI = [_LOKALNI / "Spellcast" / "styl.json", Path(__file__).resolve().parent / "styl.json"]
# z lokální složky stojí za přesun jen model (~3 GB); tmp, fonts a tema si aplikace vytvoří znovu
STARA_DATA = ["models"]
ZNACKA_MIGRACE = ".migrace"


def vstup_ffmpeg(video, ffprobe=False):
    """Argumenty FFmpeg/ffprobe pro vstupní video: absolutní cesta (název začínající „-“ ani „protokol:“ se
    nevyloží jako přepínač či URL) a jen místní soubory – podvržený „video“ soubor, který je ve skutečnosti
    playlist s adresami (HLS, concat…), tak nic nestáhne ani neotevře mimo disk. Vždy jako seznam, bez shellu."""
    cesta = str(Path(video).resolve())
    return ["-protocol_whitelist", "file", cesta] if ffprobe else ["-protocol_whitelist", "file", "-i", cesta]


def _presun(zdroj, cil):
    """Přesune soubor/složku; co v cíli už je, nepřepisuje. Při chybě (soubor drží jiný proces) aspoň zkopíruje."""
    if not zdroj.exists():
        return
    if cil.is_dir() and zdroj.is_dir():  # složka už v cíli je (např. prázdná models) → po položkách
        for polozka in list(zdroj.iterdir()):
            _presun(polozka, cil / polozka.name)
        try:
            zdroj.rmdir()
        except OSError:
            pass
        return
    if cil.exists():
        return
    try:
        shutil.move(str(zdroj), str(cil))
    except OSError:
        try:
            (shutil.copytree if zdroj.is_dir() else shutil.copy2)(zdroj, cil)
        except OSError:
            pass


def migruj_stara_data():
    """Spellcast / tkStudio → kupcake.studio: nastavení, presety, rozvržení, styl a stažený model se přesunou
    do nových složek. Proběhne jednou (značka v nové složce); staré složky se smažou, jen když zůstaly prázdné."""
    znacka = NASTAVENI_DIR / ZNACKA_MIGRACE
    if znacka.exists() or not any(n.is_dir() or d.is_dir() for n, d in STARE_SLOZKY):
        return
    NASTAVENI_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for stare_nastaveni, stara_data in STARE_SLOZKY:
        if stare_nastaveni.is_dir():
            for polozka in list(stare_nastaveni.iterdir()):
                if polozka.name.startswith(".migrace"):  # značky dřívějších přesunů nejsou potřeba
                    polozka.unlink(missing_ok=True)
                else:
                    _presun(polozka, NASTAVENI_DIR / polozka.name)
        for nazev in STARA_DATA:
            _presun(stara_data / nazev, DATA_DIR / nazev)
        for nazev in ("tmp", "fonts", "tema"):  # mezipaměť staré verze – vznikne znovu; co je zamčené, zůstane
            shutil.rmtree(stara_data / nazev, ignore_errors=True)
        for slozka in (stare_nastaveni, stara_data):
            try:
                slozka.rmdir()  # jen prázdnou
            except OSError:
                pass
    znacka.write_text("Nastavení přesunuto ze složek tkStudio / Spellcast (dřívější názvy).\n", encoding="utf-8")

def priprav():
    """Vytvoří složky, přesune staré nastavení, zpřístupní přibalený FFmpeg a fonty pro něj."""
    migruj_stara_data()
    for d in (NASTAVENI_DIR, TMP_DIR, MODELY_DIR):
        d.mkdir(parents=True, exist_ok=True)
    if not STYL_SOUBOR.exists():
        for stare in STARE_NASTAVENI:
            if stare.is_file():
                shutil.move(str(stare), str(STYL_SOUBOR))
                break
    if FFMPEG_DIR.is_dir():
        os.environ["PATH"] = str(FFMPEG_DIR) + os.pathsep + os.environ.get("PATH", "")
    # FFmpeg dostává cesty ve filtru relativně k DATA_DIR (bez escapování „C:\…“), proto kopie fontů
    cil = DATA_DIR / "fonts"
    cil.mkdir(exist_ok=True)
    for f in FONTY_DIR.glob("*.[ot]tf"):
        kopie = cil / f.name
        if not kopie.exists() or kopie.stat().st_size != f.stat().st_size:
            shutil.copy2(f, kopie)
