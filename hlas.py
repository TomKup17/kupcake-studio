# kupcake.studio – Copyright (C) 2026 Tomáš Kupec
# SPDX-License-Identifier: GPL-3.0-only
"""Oddělení hlasu od hudby (Demucs htdemucs, MIT) – pro videa s hudbou v pozadí, která mate přepis
i časování. Model (~80 MB) se stáhne při prvním použití do %LOCALAPPDATA%\\KupcakeStudio\\models\\demucs.

Bezpečnost načtení: soubor .th Demucsu je pickle (torch.save slovníku {klass, args, kwargs, state, …}) –
safetensors pro něj autoři nevydávají. Proto:
1. soubor se použije jen po ověření SHA-256 proti pevnému součtu v manifest_modelu.py (stahovani.priprav_demucs
   jiný soubor odmítne a smaže),
2. načítá se výhradně omezeným unpicklerem torch (weights_only=True) s několika povolenými třídami navíc
   (povolene_tridy – třída modelu HTDemucs pod klíčem „klass“, Fraction, numpy skalár/dtype); cokoli jiného
   unpickler odmítne a model se nenačte. Plné torch.load (weights_only=False) se nepoužívá.
"""
import logging
import os
import pickle
import subprocess

import numpy as np

from cesty import MODELY_DIR, vstup_ffmpeg
from i18n import t

_log = logging.getLogger("kupcake").info  # výchozí log: do souboru (logy.py)
NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
SR_DEMUCS = 44100
_model = None


def povolene_tridy():
    """Co smí omezený unpickler kromě tenzorů a základních typů vytvořit. Seznam odpovídá přesně GLOBAL
    odkazům v oficiálním souboru 955717e8-8726e21a.th (zjištěno pickletools bez spuštění): třída modelu,
    fractions.Fraction (kwargs `segment=Fraction(39, 5)`), numpy skalár float64 a jeho dtype (v training_args);
    torch a collections.OrderedDict povoluje torch sám. Žádné funkce, které by spouštěly kód."""
    from fractions import Fraction

    import numpy as np
    from demucs.htdemucs import HTDemucs
    skalar = np._core.multiarray.scalar if hasattr(np, "_core") else np.core.multiarray.scalar
    # skalár pod novým (numpy 2: numpy._core…) i starým názvem (numpy.core…, tak ho má oficiální soubor)
    return [HTDemucs, Fraction, skalar, (skalar, "numpy.core.multiarray.scalar"), np.dtype, np.dtypes.Float64DType]


def nacti_balicek(cesta):
    """Slovník modelu ze souboru .th jen omezeným unpicklerem (weights_only=True + povolene_tridy). Cokoli
    jiného v souboru = pickle.UnpicklingError; plné torch.load se nepoužívá nikdy (ověřeno na oficiálním
    souboru – načte se beze zbytku)."""
    import torch
    try:
        with torch.serialization.safe_globals(povolene_tridy()):
            return torch.load(cesta, map_location="cpu", weights_only=True)
    except pickle.UnpicklingError:
        logging.getLogger("kupcake").error("Demucs: soubor modelu obsahuje nepovolené objekty – nenačten.")
        raise


def _nacti(log):
    """Model htdemucs. Váhy stáhne a ověří SHA-256 stahovani.py (ne torch.hub – ten kontroluje jen 8 znaků
    součtu); až ověřený soubor se načte (nacti_balicek)."""
    global _model
    if _model is None:
        from demucs.states import load_model

        import stahovani
        log(t("log.demucs_model"))
        cesta = stahovani.priprav_demucs(MODELY_DIR / "demucs", t("stahovani.demucs"), log)
        _model = load_model(nacti_balicek(cesta))
    import zarovnani
    _model.to(zarovnani.zarizeni()).eval()  # stejné zařízení jako přepis (na slabším PC procesor)
    return _model


def oddel_hlas(video, sr_vystup, log=_log, progress=lambda p: None):
    """Vrátí jen hlas z videa jako mono float32 se vzorkovací frekvencí sr_vystup."""
    import julius
    import torch
    from demucs.apply import apply_model
    model = _nacti(log)
    pcm = subprocess.run(
        ["ffmpeg", "-v", "error", *vstup_ffmpeg(video), "-vn", "-ac", "2", "-ar", str(SR_DEMUCS), "-f", "f32le", "-"],
        check=True, capture_output=True, creationflags=NO_WINDOW).stdout
    stereo = torch.from_numpy(np.frombuffer(pcm, dtype=np.float32).reshape(-1, 2).T.copy())
    stred, rozptyl = stereo.mean(), stereo.std() + 1e-8
    log(t("log.demucs"))
    zarizeni = next(model.parameters()).device
    vstup = ((stereo - stred) / rozptyl)[None]
    hlasy, kus = [], SR_DEMUCS * 60  # po minutách – kvůli průběhu (a zrušení) mezi kusy
    vokaly = model.sources.index("vocals")
    with torch.inference_mode():
        for od in range(0, vstup.shape[-1], kus):
            stopy = apply_model(model, vstup[..., od:od + kus], device=zarizeni, split=True,
                                overlap=0.25, progress=False)[0]
            hlasy.append(stopy[vokaly].cpu())
            progress(min((od + kus) / vstup.shape[-1], 1.0) * 0.95)
    hlas = torch.cat(hlasy, dim=-1) * rozptyl + stred
    mono = hlas.mean(dim=0)
    progress(1.0)
    return julius.resample_frac(mono, SR_DEMUCS, sr_vystup).cpu().numpy().astype(np.float32)
