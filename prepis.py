# kupcake.studio – Copyright (C) 2026 Tomáš Kupec
# SPDX-License-Identifier: GPL-3.0-only
"""Přepis řeči na slova s časy (faster-whisper large-v3, CUDA; jazyk zvolený nebo rozpoznaný).

Postup: zvuk (mono 16 kHz, normalizovaná hlasitost; volitelně jen hlas oddělený Demucsem) → Whisper
s VAD, beam 5 a bez navazování na předchozí text → přesné časování slov (zarovnani.py, volitelné).
"""
import logging
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np

from cesty import vstup_ffmpeg
from i18n import t

_log = logging.getLogger("kupcake").info  # výchozí log: do souboru (logy.py)
NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0


def _pridej_cuda_dll():
    """cuBLAS a cuDNN z pip balíčků nvidia-* musí být vidět pro ctranslate2
    (ve venv v site-packages, v KupcakeStudio.exe ve složce _internal)."""
    zaklady = [Path(sys.prefix) / "Lib" / "site-packages" / "nvidia"]
    if hasattr(sys, "_MEIPASS"):
        zaklady.insert(0, Path(sys._MEIPASS) / "nvidia")
    for base in zaklady:
        for sub in ("cublas", "cudnn", "cuda_nvrtc", "cuda_runtime"):
            d = base / sub / "bin"
            if d.is_dir():
                os.add_dll_directory(str(d))
                os.environ["PATH"] = str(d) + os.pathsep + os.environ.get("PATH", "")


_pridej_cuda_dll()
from faster_whisper import WhisperModel  # noqa: E402

SAMPLE_RATE = 16000
_modely = {}


def posun_zvuku(video):
    """O kolik později než začátek souboru (a obraz) začíná zvuková stopa (s). Časy slov se o něj posunou,
    jinak by byly titulky u takových videí (typicky z telefonu) celé posunuté."""
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=start_time:format=start_time",
             "-of", "json", *vstup_ffmpeg(video, ffprobe=True)], check=True, capture_output=True, text=True, creationflags=NO_WINDOW).stdout
        data = json.loads(out)
        a = float(data["streams"][0].get("start_time") or 0)
        f = float(data.get("format", {}).get("start_time") or 0)
        return max(round(a - f, 3), 0.0)
    except (OSError, ValueError, KeyError, IndexError, subprocess.CalledProcessError):
        return 0.0


def normalizuj(audio):
    """Hlasitost na jednotnou úroveň (tichá videa i přebuzená): špičky (99,9. percentil) na 0,9."""
    if not len(audio):
        return audio
    spicka = float(np.percentile(np.abs(audio), 99.9))
    return np.clip(audio * (0.9 / spicka), -1, 1).astype(np.float32) if spicka > 1e-4 else audio


def nacti_zvuk(video):
    # zvuk přes ffmpeg (16 kHz mono float32) – nezávislé na PyAV
    pcm = subprocess.run(
        ["ffmpeg", "-v", "error", *vstup_ffmpeg(video), "-vn", "-ac", "1", "-ar", str(SAMPLE_RATE),
         "-f", "f32le", "-"],
        check=True, capture_output=True, creationflags=NO_WINDOW,
    ).stdout
    return np.frombuffer(pcm, dtype=np.float32)


def nacti_model(zarizeni, cesta, compute=None):
    """Model v paměti se drží jen jeden (jiný model / zařízení ten předchozí uvolní – šetří VRAM)."""
    compute = compute or ("float16" if zarizeni == "cuda" else "int8")
    klic = (zarizeni, compute, str(cesta))
    if klic not in _modely:
        _modely.clear()
        _modely[klic] = WhisperModel(str(cesta), device=zarizeni, compute_type=compute,
                                     cpu_threads=0 if zarizeni == "cuda" else max((os.cpu_count() or 4) - 2, 2))
    return _modely[klic]


def _je_nedostatek_pameti(chyba):
    text = str(chyba).lower()
    return "out of memory" in text or "cudaerrormemoryallocation" in text or "cublas_status_alloc_failed" in text


def _prepis(audio, zarizeni, cesta, jazyk, progress, compute=None):
    """jazyk=None → Whisper jazyk rozpozná sám z prvních 30 s řeči."""
    delka = max(len(audio) / SAMPLE_RATE, 0.001)
    model = nacti_model(zarizeni, cesta, compute)
    segments, info = model.transcribe(
        audio, language=jazyk, word_timestamps=True,
        vad_filter=True,                     # Silero VAD – ticho a šum se nepřepisují
        condition_on_previous_text=False,    # omezí „rozjíždění“ a halucinace v dlouhých videích
        beam_size=5)
    slova, useky = [], []
    for seg in segments:
        indexy = []
        for w in seg.words or []:
            text = w.word.strip()
            if text:
                indexy.append(len(slova))
                slova.append({"text": text, "start": round(float(w.start), 3), "end": round(float(w.end), 3)})
        useky.append((float(seg.start), float(seg.end), indexy))
        progress(min(seg.end / delka, 1.0))
    return {"slova": slova, "useky": useky, "jazyk": info.language, "rozpoznano": jazyk is None}


def prepis(video, jazyk=None, progress=lambda p, faze=None: None, log=_log, presne=True, oddelit_hlas=False,
           model="large-v3", rezim="auto"):
    """Vrátí {"slova": [{text, start, end}], "jazyk": kód, "rozpoznano": bool, "zarovnano": bool,
    "audio": zvuk 16 kHz pro pozdější „Znovu zarovnat výběr“, "zarizeni": popis, "varovani": text|None}.
    jazyk=None = automaticky rozpoznat. model = přesnost přepisu (model.MODELY), rezim = "auto" / "cpu".
    Zařízení a přesnost výpočtu vybere hardware.volba(); když GPU dojde paměť (nebo CUDA selže),
    přepis pokračuje na procesoru a výsledek nese srozumitelné upozornění.
    presne = přesné časování (forced alignment, pomalejší); oddelit_hlas = Demucs před přepisem.
    progress(podíl, fáze) hlásí celkový průběh po fázích (prubeh.Faze); vyhozené Zruseno práci ukončí."""
    import hardware
    import zarovnani
    from model import je_pripraven, priprav_model
    from prubeh import Faze, Zruseno
    hw = hardware.zjisti()
    zarizeni, compute = hardware.volba(model, rezim, hw)
    zarovnani.nastav_zarizeni("cpu" if zarizeni == "cpu" else None)  # časování a Demucs na stejném zařízení
    varovani = None
    vahy = ([("model", 25)] if not je_pripraven(model) else []) + [("audio", 15 if oddelit_hlas else 5)]
    vahy += [("prepis", 70)] + ([("zarovnani", 20), ("docisteni", 5)] if presne else [])
    faze = Faze(progress, vahy)
    if not je_pripraven(model):
        cesta = priprav_model(model, faze.zacni("model"), log)  # poprvé zkopíruje/stáhne model (s průběhem)
    else:
        cesta = priprav_model(model, log=log)
    p_audio = faze.zacni("audio")
    log(t("log.zvuk"))
    audio = None
    if oddelit_hlas:
        from hlas import oddel_hlas
        from stahovani import Odmitnuto
        try:
            audio = oddel_hlas(video, SAMPLE_RATE, log, p_audio)
        except Odmitnuto as e:  # model Demucs nestahovat → přepis bez oddělení hlasu
            log(str(e))
    if audio is None:
        audio = nacti_zvuk(video)
    audio = normalizuj(audio)
    p_audio(1.0)
    p_prepis = faze.zacni("prepis")
    vys = None
    if zarizeni == "cuda":
        try:
            log(t("log.prepis_na", zarizeni=hardware.popis("cuda", hw), presnost=compute))
            vys = _prepis(audio, "cuda", cesta, jazyk, p_prepis, compute)
        except Zruseno:
            raise
        except Exception as e:  # málo VRAM, chybějící CUDA knihovny apod. → procesor, ne chyba
            log(t("log.gpu_selhalo", chyba=e))
            _modely.clear()
            varovani = t("prepis.gpu_pamet" if _je_nedostatek_pameti(e) else "prepis.gpu_chyba")
            zarizeni, compute = "cpu", "int8"
            zarovnani.nastav_zarizeni("cpu")
            p_prepis(0.0)
    if vys is None:
        log(t("log.prepis_na", zarizeni=hardware.popis("cpu", hw), presnost=compute))
        vys = _prepis(audio, "cpu", cesta, jazyk, p_prepis, "int8")
    vys["zarizeni"] = hardware.popis(zarizeni, hw)
    vys["varovani"] = varovani
    vys["zarovnano"] = False
    if presne and vys["slova"] and not zarovnani.ma_model(vys["jazyk"]):
        # jazyk bez vlastního modelu a MMS není zapnutý – není to chyba, zůstanou časy z Whisperu
        log(t("log.zarovnani_bez_modelu", jazyk=vys["jazyk"]))
    elif presne and vys["slova"]:
        try:
            log(t("log.zarovnani"))
            zarovnani.zarovnej(vys["slova"], vys["useky"], audio, vys["jazyk"], log, faze.zacni("zarovnani"),
                               lambda: faze.zacni("docisteni"))
            vys["zarovnano"] = True
        except Zruseno:
            raise
        except Exception as e:  # bez modelu/sítě/GPU zůstanou časy z Whisperu
            log(t("log.zarovnani_selhalo", chyba=e))
    progress(1.0)
    posun = posun_zvuku(video)
    if posun:
        for s in vys["slova"]:
            s["start"], s["end"] = round(s["start"] + posun, 3), round(s["end"] + posun, 3)
    vys["audio"], vys["posun_zvuku"] = audio, posun
    return vys