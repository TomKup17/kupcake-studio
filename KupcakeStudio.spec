# PyInstaller konfigurace pro KupcakeStudio.exe (spouští ji build.bat)
#   .venv\Scripts\python.exe -m PyInstaller KupcakeStudio.spec --noconfirm
# Výsledek: dist\KupcakeStudio\KupcakeStudio.exe – režim onedir (rychlý start), bez konzole, s ikonou.
# Přibalí: FFmpeg + ffprobe (z PATH), libmpv, CUDA knihovny (cuBLAS, cuDNN), PyTorch s CUDA (přesné časování,
# Demucs), fonty, ikony. Modely (Whisper, wav2vec2, Demucs) se NEpřibalují – aplikace je při prvním použití
# připraví do %LOCALAPPDATA%\KupcakeStudio\models.
import shutil
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules, copy_metadata
from PyInstaller.utils.win32.versioninfo import (FixedFileInfo, StringFileInfo, StringStruct, StringTable,
                                                 VarFileInfo, VarStruct, VSVersionInfo)

koren = Path(SPECPATH)
sys.path.insert(0, str(koren))
import cesty  # noqa: E402  – název, verze a autor na jednom místě

nvidia = Path(sys.prefix) / "Lib" / "site-packages" / "nvidia"

datas = [
    ("fonts", "fonts"),
    ("fonty_ui", "fonty_ui"),  # Inter + JetBrains Mono pro rozhraní (OFL)
    ("locales", "locales"),    # překlady rozhraní (cs, en, de, es, sk…)
    ("ikony", "ikony"),
    ("assets", "assets"),      # splash screen: assets/splash/cupcake.png (+ README)
    ("mpv", "mpv"),
    ("kupcake.ico", "."),
    ("licenses", "licenses"),  # plná znění licencí třetích stran (QtAds LGPL 2.1…)
    ("THIRD_PARTY_LICENSES.md", "."),
    ("LICENSE", "."),            # GPL-3.0 – O aplikaci → Licence
    ("CHANGELOG.md", "."),       # O aplikaci → Co je nového
]
datas += collect_data_files("faster_whisper")  # model detekce řeči (silero VAD), malý
# přesné časování (transformers + wav2vec2) a oddělení hlasu (Demucs): konfigurace modelů Demucsu,
# data uromanu a metadata balíčků (transformers si při importu ověřuje verze závislostí)
datas += collect_data_files("demucs") + collect_data_files("uroman")
for balik in ("transformers", "tokenizers", "safetensors", "huggingface_hub", "torch", "numpy", "tqdm", "regex",
              "packaging", "filelock", "requests", "pyyaml", "demucs", "uroman"):
    try:
        datas += copy_metadata(balik)
    except Exception:  # balík nemá metadata (nebo se jmenuje jinak) – nevadí
        pass

binaries = collect_dynamic_libs("ctranslate2")
# cuBLAS / cuDNN / NVRTC z pip balíčků nvidia-* – prepis.py je hledá v _internal/nvidia/<balík>/bin
for balik in ("cublas", "cudnn", "cuda_nvrtc", "cuda_runtime"):
    for dll in (nvidia / balik / "bin").glob("*.dll"):
        binaries.append((str(dll), f"nvidia/{balik}/bin"))
# FFmpeg – aplikace ho volá jménem, cesty.priprav() přidá _internal/ffmpeg na začátek PATH
for program in ("ffmpeg", "ffprobe"):
    cesta = shutil.which(program)
    if not cesta:
        raise SystemExit(f"Nenašel jsem {program}.exe v PATH – nainstaluj FFmpeg (winget install Gyan.FFmpeg).")
    binaries.append((cesta, "ffmpeg"))

_cislo = cesty.VERZE.split("-")[0].split(".")  # 1.0.0-beta.1 -> 1.0.0 (údaje o verzi jsou jen čísla)
cisla = tuple(int(x) for x in _cislo) + (0,) * (4 - len(_cislo))
verze = VSVersionInfo(
    ffi=FixedFileInfo(filevers=cisla, prodvers=cisla, mask=0x3F, flags=0x0, OS=0x40004, fileType=0x1,
                      subtype=0x0, date=(0, 0)),
    kids=[
        StringFileInfo([StringTable("040504B0", [
            StringStruct("CompanyName", cesty.AUTOR),
            StringStruct("FileDescription", f"{cesty.NAZEV} – automatické titulky"),
            StringStruct("FileVersion", cesty.VERZE),
            StringStruct("InternalName", cesty.TECH_NAZEV),
            StringStruct("LegalCopyright", f"© 2026 {cesty.AUTOR}"),
            StringStruct("OriginalFilename", f"{cesty.TECH_NAZEV}.exe"),
            StringStruct("ProductName", cesty.NAZEV),
            StringStruct("ProductVersion", cesty.VERZE),
        ])]),
        VarFileInfo([VarStruct("Translation", [0x0405, 1200])]),
    ],
)

a = Analysis(
    ["main.py"],
    pathex=[str(koren)],
    binaries=binaries,
    datas=datas,
    hiddenimports=["prepis", "model", "export", "nahled", "osa", "prehravac", "dialogy", "jazyky_reci",
                   "doky", "PySide6QtAds", "selftest", "kolecko", "kupcake", "zarovnani", "hlas", "prekryti", "prubeh", "presety", "notifikace", "export_panel", "stahovani", "manifest_modelu", "hardware", "splash", "o_aplikaci", "uvitani", "links", "projekt", "logy", "aktualizace", "rozvrzeni", "upravy", "titulky", "theme", "i18n",
                   "cesty", "uroman", "julius",
                   "demucs.pretrained", "demucs.apply", "demucs.htdemucs", "demucs.hdemucs", "demucs.demucs",
                   "demucs.states"]
                  + collect_submodules("transformers.models.wav2vec2"),
    excludes=["tkinter", "matplotlib", "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets",
              "PySide6.QtQuick", "PySide6.QtQml", "PySide6.Qt3DCore",
              "torchvision", "tensorboard", "torch.utils.tensorboard"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=cesty.TECH_NAZEV,
    icon=str(koren / "kupcake.ico"),
    version=verze,
    console=False,  # --windowed
    upx=False,
)

coll = COLLECT(exe, a.binaries, a.datas, name=cesty.TECH_NAZEV, upx=False)
