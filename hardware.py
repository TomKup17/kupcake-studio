# kupcake.studio – Copyright (C) 2026 Tomáš Kupec
# SPDX-License-Identifier: GPL-3.0-only
"""Rozpoznání hardwaru pro přepis a volba výpočtu.

GPU: NVIDIA s CUDA – název a volná VRAM přes NVML (knihovna ovladače NVIDIA, bez načítání PyTorch),
použitelnost CUDA podle CTranslate2. Procesor: název z registru Windows.

Volba (Whisper large-v3): NVIDIA s ≥ 6 GB volné VRAM → float16, 4–6 GB → int8_float16, méně nebo bez
NVIDIA → procesor (int8). Menší modely (turbo, medium) potřebují méně VRAM. Uživatel může výpočet vynutit
na procesor (Nastavení → Přepis počítat na), pro testy i proměnnými prostředí:
  KUPCAKE_CPU=1        – jako by žádná NVIDIA GPU nebyla (přepis, zarovnání i export na procesoru),
  KUPCAKE_VRAM_GB=4.5  – předstíraná volná VRAM (vyzkoušení prahů na silné kartě).
"""
import ctypes
import os
from dataclasses import dataclass

# model → (min. volná VRAM pro float16, min. pro int8_float16) v GB
PRAHY = {"large-v3": (6.0, 4.0), "turbo": (3.5, 2.5), "medium": (3.5, 2.5)}
# rychlost přepisu jako násobek reálného času – změřeno na RTX 4070 SUPER a i7-12700KF (20 vláken),
# 60 s souvislé řeči (150 slov), beam 5; na jiném hardwaru jen odhad (procesor se škáluje podle vláken)
RYCHLOST = {
    ("cuda", "float16"): {"large-v3": 12.0, "turbo": 39.0, "medium": 20.0},
    ("cuda", "int8_float16"): {"large-v3": 11.0, "turbo": 35.0, "medium": 16.5},
    ("cpu", "int8"): {"large-v3": 1.2, "turbo": 3.1, "medium": 1.9},
}
VLAKNA_MERENI = 20
NACTENI_S = {"cuda": 7.0, "cpu": 6.0}       # načtení modelu (na GPU i CUDA knihoven) + zvuk
ZAROVNANI = {"cuda": 65.0, "cpu": 8.0}      # přesné časování jako násobek reálného času


@dataclass
class Hardware:
    gpu: str = ""            # název NVIDIA karty, "" = žádná
    vram_celkem: float = 0.0  # GB
    vram_volna: float = 0.0   # GB
    cuda: bool = False        # CTranslate2 vidí CUDA zařízení
    cpu: str = ""
    vlakna: int = 1


def _nvml():
    """(název, VRAM celkem, VRAM volná) první NVIDIA karty, nebo None."""
    try:
        nvml = ctypes.WinDLL("nvml.dll")
    except OSError:
        try:
            nvml = ctypes.WinDLL(os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"),
                                              "NVIDIA Corporation", "NVSMI", "nvml.dll"))
        except OSError:
            return None

    class Pamet(ctypes.Structure):
        _fields_ = [("total", ctypes.c_ulonglong), ("free", ctypes.c_ulonglong), ("used", ctypes.c_ulonglong)]
    try:
        if nvml.nvmlInit_v2() != 0:
            return None
        try:
            zarizeni = ctypes.c_void_p()
            if nvml.nvmlDeviceGetHandleByIndex_v2(0, ctypes.byref(zarizeni)) != 0:
                return None
            jmeno = ctypes.create_string_buffer(96)
            nvml.nvmlDeviceGetName(zarizeni, jmeno, 96)
            pamet = Pamet()
            if nvml.nvmlDeviceGetMemoryInfo(zarizeni, ctypes.byref(pamet)) != 0:
                return None
            return jmeno.value.decode(errors="replace"), pamet.total / 2**30, pamet.free / 2**30
        finally:
            nvml.nvmlShutdown()
    except (OSError, AttributeError):
        return None


def _cpu():
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as k:
            return " ".join(winreg.QueryValueEx(k, "ProcessorNameString")[0].split())
    except OSError:
        return ""


def _windows():
    """„Windows 11 Home 25H2 (build 26300.1234)“ – registr hlásí u Windows 11 pořád „Windows 10“, opraví se podle buildu."""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion") as k:
            def hodnota(jmeno, vychozi=""):
                try:
                    return winreg.QueryValueEx(k, jmeno)[0]
                except OSError:
                    return vychozi
            nazev, build = str(hodnota("ProductName", "Windows")), str(hodnota("CurrentBuild", "?"))
            if build.isdigit() and int(build) >= 22000:
                nazev = nazev.replace("Windows 10", "Windows 11")
            return f"{nazev} {hodnota('DisplayVersion')} (build {build}.{hodnota('UBR', 0)})"
    except OSError:
        import platform
        return platform.platform()


def _ovladac_nvidia():
    try:
        nvml = ctypes.WinDLL("nvml.dll")
        if nvml.nvmlInit_v2() != 0:
            return ""
        try:
            verze = ctypes.create_string_buffer(80)
            return verze.value.decode() if nvml.nvmlSystemGetDriverVersion(verze, 80) == 0 else ""
        finally:
            nvml.nvmlShutdown()
    except (OSError, AttributeError):
        return ""


def info_o_systemu():
    """Text pro hlášení chyb: verze aplikace, Windows, procesor, grafická karta, ovladač, CUDA, volby přepisu."""
    import platform
    import sys

    from PySide6 import __version__ as pyside
    from version import DATUM, VERZE
    hw = zjisti()
    try:
        import ctranslate2
        cuda = ctranslate2.get_cuda_device_count()
        cuda_text = f"ano ({cuda} zařízení, CTranslate2 {ctranslate2.__version__})" if cuda else "ne"
    except Exception as e:
        cuda_text = f"nelze zjistit ({e})"
    if vynuceny_procesor():
        cuda_text += " – vynucen procesor (KUPCAKE_CPU)"
    radky = [
        f"kupcake.studio {VERZE} (sestaveno {DATUM}){'' if getattr(sys, 'frozen', False) else ' – ze zdrojového kódu'}",
        f"Windows: {_windows()}",
        f"Procesor: {hw.cpu or '?'} ({hw.vlakna} vláken)",
        f"Grafická karta: {f'{hw.gpu}, {hw.vram_celkem:.1f} GB VRAM ({hw.vram_volna:.1f} GB volné)' if hw.gpu else 'NVIDIA nenalezena'}",
        f"Ovladač NVIDIA: {_ovladac_nvidia() or '–'}",
        f"CUDA: {cuda_text}",
        f"Přepis by běžel na: {' / '.join(volba('large-v3', hw=hw))}",
        f"Python {platform.python_version()}, PySide6 {pyside}",
    ]
    return "\n".join(radky)


def vynuceny_procesor():
    return os.environ.get("KUPCAKE_CPU", "") not in ("", "0")


def zjisti():
    """Aktuální stav (volná VRAM se mění – volá se před každým přepisem)."""
    hw = Hardware(cpu=_cpu(), vlakna=os.cpu_count() or 1)
    if vynuceny_procesor():
        return hw
    gpu = _nvml()
    if gpu:
        hw.gpu, hw.vram_celkem, hw.vram_volna = gpu
    try:
        import ctranslate2
        hw.cuda = ctranslate2.get_cuda_device_count() > 0
    except Exception:
        hw.cuda = False
    if os.environ.get("KUPCAKE_VRAM_GB"):
        hw.vram_volna = float(os.environ["KUPCAKE_VRAM_GB"])
    return hw


def volba(model="large-v3", rezim="auto", hw=None):
    """(zařízení, compute_type) pro přepis. rezim: "auto" nebo "cpu" (vynutit procesor)."""
    hw = hw or zjisti()
    plne, usporne = PRAHY.get(model, PRAHY["large-v3"])
    if rezim != "cpu" and hw.gpu and hw.cuda:
        if hw.vram_volna >= plne:
            return "cuda", "float16"
        if hw.vram_volna >= usporne:
            return "cuda", "int8_float16"
    return "cpu", "int8"


def popis(zarizeni, hw=None):
    """„NVIDIA GeForce RTX 4070 SUPER (12 GB)“ / „procesor Intel Core i7-12700KF (20 vláken)“."""
    from i18n import t
    hw = hw or zjisti()
    if zarizeni == "cuda" and hw.gpu:
        return f"{hw.gpu} ({hw.vram_celkem:.0f} GB)"
    return t("hw.procesor", cpu=hw.cpu or "CPU", vlakna=hw.vlakna)


def odhad_s(delka, model, zarizeni, compute, presne=True, vlakna=None):
    """Odhad doby přepisu (s) videa o délce delka (s) – počítá se souvislou řečí (ticho jde rychleji)."""
    rychlost = RYCHLOST.get((zarizeni, compute), RYCHLOST[("cpu", "int8")]).get(model, 1.0)
    zarovnani = ZAROVNANI[zarizeni]
    if zarizeni == "cpu":  # slabší procesor = pomaleji (zhruba úměrně počtu vláken, s rezervou)
        k = min(max((vlakna or os.cpu_count() or 4) / VLAKNA_MERENI, 0.15), 1.0) ** 0.8
        rychlost, zarovnani = rychlost * k, zarovnani * k
    cas = NACTENI_S[zarizeni] + delka / rychlost
    if presne:
        cas += 2 + delka / zarovnani
    return cas
