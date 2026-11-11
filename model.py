# kupcake.studio – Copyright (C) 2026 Tomáš Kupec
# SPDX-License-Identifier: GPL-3.0-only
"""Modely Whisper pro přepis – nepřibalují se, při prvním použití se připraví do %LOCALAPPDATA%\\KupcakeStudio\\models.

Tři přesnosti (volba „Přesnost přepisu“): large-v3 (nejpřesnější), large-v3-turbo (rychlá), medium (úsporná).
Když je model už v cache Hugging Face (~/.cache/huggingface), jen se zkopíruje; jinak se stáhne
z huggingface.co. Obojí v pevné revizi a s kontrolou SHA-256 každého souboru (stahovani.py,
manifest_modelu.py); stažení se nejdřív potvrdí uživatelem. Přerušené stahování naváže.
"""
import logging
import os
from pathlib import Path

import stahovani
from cesty import MODELY_DIR
from i18n import t

# klíč → (repozitář, soubory); z nich nastroje/vytvor_manifest.py sestaví manifest se SHA-256
_log = logging.getLogger("kupcake").info  # výchozí log: do souboru (logy.py)
MODELY = {
    "large-v3": ("Systran/faster-whisper-large-v3",
                 ["config.json", "preprocessor_config.json", "tokenizer.json", "vocabulary.json", "model.bin"]),
    "turbo": ("dropbox-dash/faster-whisper-large-v3-turbo",
              ["config.json", "preprocessor_config.json", "tokenizer.json", "vocabulary.json", "model.bin"]),
    "medium": ("Systran/faster-whisper-medium", ["config.json", "tokenizer.json", "vocabulary.txt", "model.bin"]),
}
VYCHOZI = "large-v3"
# dřívější adresy repozitářů (Hugging Face je přesměrovává): model stažený knihovnou pod starým jménem
# se v cache Hugging Face najde i tak. Složka modelu v aplikaci se nemění (jen část za lomítkem).
DRIVE = {"dropbox-dash/faster-whisper-large-v3-turbo": ["mobiuslabsgmbh/faster-whisper-large-v3-turbo"]}


def repo(klic=VYCHOZI):
    return MODELY.get(klic, MODELY[VYCHOZI])[0]


def slozka(klic=VYCHOZI):
    return MODELY_DIR / repo(klic).split("/")[1]


def je_pripraven(klic=VYCHOZI):
    """Stažený a ověřený (SHA-256) – jde rovnou použít."""
    return stahovani.je_pripraveno(repo(klic), slozka(klic))


def je_stazen(klic=VYCHOZI):
    """Soubory jsou na disku (před přepisem se případně jen ověří, nic se nestahuje)."""
    return stahovani.je_stazeno(repo(klic), slozka(klic))


def velikost(klic=VYCHOZI):
    return stahovani.velikost_repa(repo(klic))


def _najdi_v_cache(r):
    hub = Path(os.environ.get("HF_HOME") or Path.home() / ".cache" / "huggingface") / "hub"
    revize = stahovani.HUGGINGFACE[r]["revize"]
    kandidati = []
    for jmeno in [r] + DRIVE.get(r, []):
        snapshots = hub / f"models--{jmeno.replace('/', '--')}" / "snapshots"
        kandidati += [snapshots / revize] + sorted(snapshots.glob("*"), reverse=True)
    return next((s for s in kandidati if s.is_dir()), None)


def priprav_model(klic=VYCHOZI, progress=lambda p: None, log=_log):
    """Vrátí složku s modelem; při prvním použití ho zkopíruje z cache nebo stáhne (a vždy ověří)."""
    r, cil = repo(klic), slozka(klic)
    if stahovani.je_pripraveno(r, cil):
        return cil
    soubory = stahovani.HUGGINGFACE[r]["soubory"]
    uz_je = all((cil / f).is_file() and (cil / f).stat().st_size == v for f, (v, _) in soubory.items())
    zdroj = None if uz_je else _najdi_v_cache(r)  # stažený model (např. ze starší verze) se jen ověří
    if not (zdroj and stahovani.kopiruj_overene(zdroj, r, cil, progress, log)):
        log(t("model.zjistuji"))
        stahovani.priprav_repo(r, cil, t(f"stahovani.whisper.{klic}"), progress, log)
    progress(0.0)
    return cil
