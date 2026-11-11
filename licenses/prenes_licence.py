# kupcake.studio – Copyright (C) 2026 Tomáš Kupec
# SPDX-License-Identifier: GPL-3.0-only
"""Doplní do licenses/ plná znění licencí přibalených knihoven a vygeneruje úplný seznam balíčků Pythonu,
které jsou skutečně v sestavené aplikaci: licenses/PYTHON_PACKAGES.md (název, verze, licence) a
licenses/python/<balíček>.txt (plné znění licencí každého balíčku).

Spouští se ručně po změně závislostí – nejlépe po sestavení, aby seznam odpovídal obsahu instalátoru:
    .venv\\Scripts\\python.exe licenses\\prenes_licence.py

Které balíčky jsou přibalené, se pozná ze seznamů PyInstalleru (build\\KupcakeStudio\\PYZ-00.toc a
COLLECT-00.toc): balíček se počítá, když je v sestavení aspoň jeden jeho soubor. Bez sestavení se vezmou
všechny balíčky z .venv kromě nástrojů pro vývoj. Nepotřebuje nic mimo standardní knihovnu (importlib.metadata).

(Inter, JetBrains Mono, Montserrat a QtAds jsou ve složce natrvalo; knihovny, které nejsou balíčky Pythonu –
mpv, knihovny uvnitř PyAV, Intel MKL, běhové knihovny Microsoft – popisuje ručně THIRD_PARTY_LICENSES.md.)
"""
import ast
import re
import shutil
import sys
from html.parser import HTMLParser
from importlib.metadata import PackageNotFoundError, distribution, distributions
from pathlib import Path

CIL = Path(__file__).resolve().parent
KOREN = CIL.parent
SLOZKA_BALICKU = CIL / "python"
SEZNAM = CIL / "PYTHON_PACKAGES.md"
SESTAVENI = KOREN / "build" / "KupcakeStudio"

# ---------- 1. pojmenované kopie hlavních licencí (odkazuje na ně THIRD_PARTY_LICENSES.md) ----------
# (balík, soubor v metadatech nebo None = první licenční soubor, cílový název)
Z_METADAT = [
    ("torch", "LICENSE", "PyTorch-BSD-3-Clause.txt"),
    ("torch", "NOTICE", "PyTorch-NOTICE.txt"),
    ("torchaudio", None, "torchaudio-BSD-2-Clause.txt"),
    ("transformers", None, "transformers-Apache-2.0.txt"),
    ("transformers", None, "tokenizers-Apache-2.0.txt"),  # tokenizers (HF) nemá v balíku licenci – stejná Apache 2.0
    ("safetensors", None, "safetensors-Apache-2.0.txt"),
    ("huggingface_hub", None, "huggingface_hub-Apache-2.0.txt"),
    ("demucs", None, "Demucs-MIT.txt"),
    ("julius", None, "julius-MIT.txt"),
    ("einops", None, "einops-MIT.txt"),
    ("uroman", None, "uroman-LICENSE.txt"),  # vlastní licence uromanu (znění MIT + povinnost uvést jeho použití)
    ("faster-whisper", None, "faster-whisper-MIT.txt"),
    ("av", "LICENSE", "PyAV-BSD-3-Clause.txt"),
    ("onnxruntime", None, "onnxruntime-MIT.txt"),
    ("numpy", "numpy-2", "NumPy-BSD-3-Clause.txt"),
    ("python-mpv", "LICENSE.GPL", "python-mpv-GPL-2.0.txt"),
    ("python-mpv", "LICENSE.LGPL", "python-mpv-LGPL-2.1.txt"),
    ("lameenc", None, "lameenc-LGPL-3.0.txt"),
    # PySide6/Shiboken6 = LGPL v3; jejich balíčky nesou jen odkaz na komerční licenci, proto standardní znění
    # LGPL v3 z balíčku lameenc (text licence je u všech stejný)
    ("lameenc", None, "Qt-PySide6-LGPL-3.0.txt"),
    ("nvidia-cublas-cu12", None, "NVIDIA-CUDA-EULA.txt"),
    ("nvidia-cudnn-cu12", None, "NVIDIA-cuDNN-license.txt"),
]

MIT = """MIT License

{copyright}

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
MIT_CTRANSLATE2 = MIT.format(copyright="Copyright (c) 2018-     SYSTRAN.\nCopyright (c) 2019-     The OpenNMT Authors.")
MIT_SILERO = MIT.format(copyright="Copyright (c) 2020-present Silero Team")


def licencni_soubor(balik, hledat):
    dist = distribution(balik)
    for f in dist.files or []:
        cesta = str(f).replace("\\", "/")
        jmeno = cesta.rsplit("/", 1)[-1].upper()
        if "/licenses/" in cesta.lower() and cesta.lower().count("/") > 2 and balik == "numpy" and hledat:
            continue  # numpy: jen hlavní licence, ne licence vnořených částí
        if hledat and not (jmeno.startswith(hledat.upper()) or (hledat == "numpy-2" and jmeno == "LICENSE.TXT")):
            continue
        if jmeno.startswith(("LICENSE", "LICENCE", "COPYING", "NOTICE")):
            return Path(dist.locate_file(f))
    raise FileNotFoundError(f"{balik}: licenční soubor {hledat or ''} nenalezen")


def pojmenovane_kopie():
    for balik, hledat, nazev in Z_METADAT:
        shutil.copyfile(licencni_soubor(balik, hledat), CIL / nazev)
        print("OK", nazev)
    # CTranslate2 (MIT) licenci v balíku nemá – text MIT s jeho copyrightem (github.com/OpenNMT/CTranslate2/LICENSE)
    (CIL / "CTranslate2-MIT.txt").write_text(MIT_CTRANSLATE2, encoding="utf-8")
    print("OK CTranslate2-MIT.txt")
    # Silero VAD (model silero_vad_v6.onnx přibalený ve faster-whisper) – MIT, github.com/snakers4/silero-vad/LICENSE
    (CIL / "Silero-VAD-MIT.txt").write_text(MIT_SILERO, encoding="utf-8")
    print("OK Silero-VAD-MIT.txt")
    # FFmpeg (build gyan.dev, GPL v3) – licence a popis sestavení (verze, zdrojový commit, seznam knihoven)
    # leží vedle bin\ffmpeg.exe
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        slozka = Path(ffmpeg).resolve().parent.parent
        shutil.copyfile(slozka / "LICENSE", CIL / "FFmpeg-GPL-3.0.txt")
        print("OK FFmpeg-GPL-3.0.txt")
        if (slozka / "README.txt").is_file():
            shutil.copyfile(slozka / "README.txt", CIL / "FFmpeg-gyan-README.txt")
            print("OK FFmpeg-gyan-README.txt")
    python_a_jeho_knihovny()


# ---------- 2. Python a knihovny v něm (OpenSSL, expat, libffi, zlib, libmpdec…) ----------
class _TextZHtml(HTMLParser):
    """Stránka license.html z dokumentace Pythonu → prostý text (nadpisy, odstavce, předformátované bloky)."""

    def __init__(self):
        super().__init__()
        self.casti, self.preskoc, self.pre = [], 0, 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "nav"):
            self.preskoc += 1
        if tag == "pre":
            self.pre += 1
        if tag in ("h1", "h2", "h3", "h4"):
            self.casti.append("\n\n" + "=" * 70 + "\n")
        if tag in ("p", "div", "li", "pre"):
            self.casti.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "nav"):
            self.preskoc -= 1
        if tag == "pre":
            self.pre -= 1
            self.casti.append("\n")
        if tag in ("h1", "h2", "h3", "h4"):
            self.casti.append("\n" + "=" * 70 + "\n")

    def handle_data(self, data):
        if not self.preskoc:
            self.casti.append(data if self.pre else re.sub(r"\s+", " ", data))


def python_a_jeho_knihovny():
    """Licence Pythonu (PSF, bzip2, libffi, OpenSSL, kód Microsoftu) a oznámení ke knihovnám uvnitř Pythonu
    (expat, zlib, libmpdec…) – z instalace Pythonu, ze které je .venv vytvořené."""
    verze = f"{sys.version_info.major}.{sys.version_info.minor}"
    licence = Path(sys.base_prefix) / "LICENSE.txt"
    if licence.is_file():
        shutil.copyfile(licence, CIL / f"Python-{verze}-LICENSE.txt")
        print(f"OK Python-{verze}-LICENSE.txt")
    stranka = Path(sys.base_prefix) / "Doc" / "html" / "license.html"
    if not stranka.is_file():
        print("POZOR: dokumentace Pythonu (Doc\\html\\license.html) není nainstalovaná – oznámení ke knihovnám "
              "uvnitř Pythonu se nepřenesla (https://docs.python.org/3/license.html).")
        return
    p = _TextZHtml()
    p.feed(stranka.read_text(encoding="utf-8"))
    text = "".join(p.casti).replace("¶", "")
    od = text.find("Licenses and Acknowledgements for Incorporated Software")
    do = text.find("Table of Contents", od)
    if od < 0:
        print("POZOR: v license.html chybí oddíl o přibalených knihovnách")
        return
    text = re.sub(r"\n{4,}", "\n\n\n", text[od:do if do > od else None]).strip()
    hlavicka = (f"Python {sys.version.split()[0]} – licences and acknowledgements for incorporated software\n"
                f"(extracted from the Python documentation, Doc/html/license.html; "
                f"https://docs.python.org/{verze}/license.html)\n\n")
    (CIL / f"Python-{verze}-incorporated-software.txt").write_text(hlavicka + text + "\n", encoding="utf-8")
    print(f"OK Python-{verze}-incorporated-software.txt")


# ---------- 3. úplný seznam přibalených balíčků Pythonu ----------
# jen pro vývoj a sestavení – do aplikace se nepřibalují (použije se, když chybí seznamy ze sestavení)
NASTROJE = {"pip", "pyflakes", "altgraph", "pefile", "pywin32-ctypes", "pyinstaller-hooks-contrib"}

# licence tam, kde ji metadata balíčku neuvádějí jednoznačně (ověřeno podle licenčního souboru balíčku)
LICENCE = {
    "colorama": "BSD-3-Clause",
    "demucs": "MIT",
    "jinja2": "BSD-3-Clause",
    "julius": "MIT",
    "markdown-it-py": "MIT",
    "mdurl": "MIT",
    "mpmath": "BSD-3-Clause",
    "onnxruntime": "MIT",
    "protobuf": "BSD-3-Clause",
    "pyinstaller": "GPL-2.0-or-later s výjimkou pro zavaděč (bootloader exception)",
    "pyside6-qtads": "LGPL-2.1-only (vazby zčásti MIT)",
    "python-mpv": "GPL-2.0-or-later OR LGPL-2.1-or-later",
    "safetensors": "Apache-2.0",
    "setuptools": "MIT",
    "sympy": "BSD-3-Clause",
    "tokenizers": "Apache-2.0",
    "torchaudio": "BSD-2-Clause",
    "transformers": "Apache-2.0",
    "uroman": "licence uromanu (znění MIT + povinnost uvést použití uromanu)",
}
QT = ("pyside6", "pyside6-addons", "pyside6-essentials", "pyside6-pdf", "pyside6-webengine", "shiboken6")
LICENCE_QT = "LGPL-3.0-only (balíček nabízí LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only)"
ODDELOVAC = "\n" + "=" * 78 + "\n"


def norm(jmeno):
    return re.sub(r"[-_.]+", "-", jmeno).lower()


def zdroje_sestaveni():
    """Cesty všech souborů, které PyInstaller do aplikace zabalil; None = sestavení chybí."""
    cesty = set()
    for toc in ("PYZ-00.toc", "COLLECT-00.toc"):
        soubor = SESTAVENI / toc
        if not soubor.is_file():
            return None
        for cast in ast.literal_eval(soubor.read_text(encoding="utf-8")):
            if isinstance(cast, list):
                cesty.update(str(Path(polozka[1])).lower() for polozka in cast)
    return cesty


def pribalene_balicky():
    zdroje = zdroje_sestaveni()
    if zdroje is None:
        print("POZOR: sestavení (build\\KupcakeStudio) chybí – beru všechny balíčky z .venv kromě nástrojů.")
    balicky = {}
    for d in distributions():
        jmeno = d.metadata["Name"]
        if not jmeno:
            continue
        if zdroje is None:
            pribaleno = norm(jmeno) not in NASTROJE
        else:  # aspoň jeden soubor balíčku (mimo jeho metadata) je v sestavení
            pribaleno = any(not str(f).replace("\\", "/").split("/")[0].endswith((".dist-info", ".egg-info"))
                            and str(Path(d.locate_file(f))).lower() in zdroje for f in d.files or [])
        if pribaleno:
            balicky[norm(jmeno)] = d
    return [balicky[k] for k in sorted(balicky)]


def licence_balicku(d):
    jmeno = norm(d.metadata["Name"])
    if jmeno in QT:
        return LICENCE_QT
    if jmeno in LICENCE:
        return LICENCE[jmeno]
    vyraz = d.metadata.get("License-Expression")
    if vyraz:
        return vyraz
    licence = (d.metadata.get("License") or "").strip().splitlines()
    if licence and len(licence[0]) <= 60:
        return licence[0]
    tridy = [c.split("::")[-1].strip() for c in d.metadata.get_all("Classifier", []) if c.startswith("License ::")]
    return "; ".join(tridy) or "viz text licence"


def licencni_soubory(d):
    """[(cesta v balíčku, soubor)] – LICENSE / COPYING / NOTICE / AUTHORS z metadat balíčku (i vnořené licence
    přibalených částí, např. NumPy) nebo z kořene balíčku (onnxruntime)."""
    nalezene = {}
    for f in d.files or []:
        cesta = str(f).replace("\\", "/")
        casti = cesta.split("/")
        jmeno = casti[-1]
        if jmeno.lower().endswith((".py", ".pyc")) or jmeno.startswith("LicenseRef-"):
            continue  # LicenseRef-Qt-Commercial.txt = jen odkaz na komerční licenci Qt
        if not re.match(r"(?i)(licen[cs]e|copying|notice|authors|thirdpartynotices)", jmeno):
            continue
        if casti[0].endswith(".dist-info") or len(casti) == 2:
            soubor = Path(d.locate_file(f))
            if soubor.is_file():
                nalezene[cesta] = soubor
    return sorted(nalezene.items())


def precti(soubor):
    data = soubor.read_bytes()
    for kodovani in ("utf-8-sig", "cp1252"):
        try:
            return data.decode(kodovani).replace("\r\n", "\n").replace("\r", "\n").strip("\n")
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace").replace("\r\n", "\n").strip("\n")


def nahradni_text(jmeno):
    """Plné znění pro balíčky, které licenční soubor nenesou: (poznámka, text)."""
    if jmeno == "ctranslate2":
        return "Balíček licenční soubor neobsahuje; znění z https://github.com/OpenNMT/CTranslate2 (LICENSE).", MIT_CTRANSLATE2
    if jmeno == "tokenizers":
        return ("Balíček licenční soubor neobsahuje; standardní znění Apache License 2.0 "
                "(https://github.com/huggingface/tokenizers, LICENSE)."), precti(licencni_soubor("transformers", None))
    if jmeno in QT:
        poznamka = ("Balíček nese jen odkaz na komerční licenci Qt. kupcake.studio používá Qt for Python pod LGPL v3; "
                    "níže je standardní znění GNU LGPL v3, které navazuje na GNU GPL v3 (soubor LICENSE v kořeni "
                    "projektu). Zdrojové kódy: THIRD_PARTY_LICENSES.md, oddíl Zdrojové kódy přibalených programů.")
        return poznamka, precti(licencni_soubor("lameenc", None))
    return None


def seznam_balicku():
    balicky = pribalene_balicky()
    SLOZKA_BALICKU.mkdir(exist_ok=True)
    zapsane, radky, bez_textu = set(), [], []
    for d in balicky:
        nazev, jmeno, verze = d.metadata["Name"], norm(d.metadata["Name"]), d.version
        licence = licence_balicku(d)
        web = d.metadata.get("Home-page") or next(
            (u.split(",", 1)[1].strip() for u in d.metadata.get_all("Project-URL", [])
             if u.split(",")[0].strip().lower() in ("homepage", "home", "repository", "source", "source code")), "")
        casti = [f"{nazev} {verze}", f"Licence: {licence}"] + ([f"Web: {web}"] if web else [])
        texty = [(cesta.split("/")[-1] if cesta.count("/") < 3 else cesta.split("/", 2)[-1], precti(soubor))
                 for cesta, soubor in licencni_soubory(d)]
        nahrada = nahradni_text(jmeno)
        if nahrada and (jmeno in QT or not texty):
            casti.append(f"Poznámka: {nahrada[0]}")
            texty = [("znění licence", nahrada[1])]
        if not texty:
            bez_textu.append(nazev)
            casti.append("Poznámka: balíček licenční soubor neobsahuje – viz web projektu.")
        obsah = "\n".join(casti) + "\n" + "".join(f"{ODDELOVAC}{popis}{ODDELOVAC}\n{text}\n" for popis, text in texty)
        soubor = SLOZKA_BALICKU / f"{jmeno}.txt"
        soubor.write_text(obsah, encoding="utf-8", newline="\n")
        zapsane.add(soubor.name)
        radky.append(f"| {nazev} | {verze} | {licence} | `python/{soubor.name}` |")
    for stary in SLOZKA_BALICKU.glob("*.txt"):  # balíčky, které už přibalené nejsou
        if stary.name not in zapsane:
            stary.unlink()
            print("smazáno", stary.name)
    zdroj = ("obsahu sestavení (`build\\KupcakeStudio\\*.toc`)" if zdroje_sestaveni() is not None
             else "balíčkům v `.venv` (sestavení nebylo k dispozici)")
    SEZNAM.write_text("\n".join([
        "# Balíčky Pythonu přibalené v aplikaci",
        "",
        "Python packages bundled in the app – name, version, licence and the file with the full licence text.",
        "",
        "Vygenerováno skriptem `licenses/prenes_licence.py` – neupravovat ručně. Seznam odpovídá " + zdroj + ":",
        f"{len(radky)} balíčků. Knihovny, které nejsou balíčky Pythonu (FFmpeg, mpv, knihovny uvnitř PyAV, Qt-ADS,",
        "Intel MKL, běhové knihovny Microsoft, Python sám), popisuje `THIRD_PARTY_LICENSES.md`.",
        "",
        "| Balíček | Verze | Licence | Plné znění (`licenses/`) |",
        "|---|---|---|---|",
        *radky,
        "",
    ]), encoding="utf-8", newline="\n")
    print(f"OK PYTHON_PACKAGES.md – {len(radky)} balíčků, texty v licenses/python/")
    if bez_textu:
        print("POZOR: bez licenčního textu:", ", ".join(bez_textu))


if __name__ == "__main__":
    try:
        pojmenovane_kopie()
    except (PackageNotFoundError, FileNotFoundError) as e:
        raise SystemExit(f"[CHYBA] {e}")
    seznam_balicku()
