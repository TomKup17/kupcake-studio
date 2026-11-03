"""Doplní do licenses/ plná znění licencí přibalených knihoven – z jejich metadat v .venv, FFmpeg z jeho složky.
Spouští se ručně po změně závislostí:  .venv\\Scripts\\python.exe licenses\\prenes_licence.py
(Inter, JetBrains Mono, Montserrat a QtAds jsou ve složce natrvalo.)
"""
import shutil
from importlib.metadata import distribution
from pathlib import Path

CIL = Path(__file__).parent

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
    ("uroman", None, "uroman-MIT.txt"),
    ("faster-whisper", None, "faster-whisper-MIT.txt"),
    ("av", None, "PyAV-BSD-3-Clause.txt"),
    ("onnxruntime", None, "onnxruntime-MIT.txt"),
    ("numpy", "numpy-2", "NumPy-BSD-3-Clause.txt"),
    ("python-mpv", "LICENSE.GPL", "python-mpv-GPL-2.0.txt"),
    ("python-mpv", "LICENSE.LGPL", "python-mpv-LGPL-2.1.txt"),
    ("lameenc", None, "Qt-PySide6-LGPL-3.0.txt"),  # PySide6/Shiboken6 = LGPL v3 (v balíku je jen odkaz na komerční)
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


for balik, hledat, nazev in Z_METADAT:
    shutil.copyfile(licencni_soubor(balik, hledat), CIL / nazev)
    print("OK", nazev)

# CTranslate2 (MIT) licenci v balíku nemá – text MIT s jeho copyrightem (github.com/OpenNMT/CTranslate2/LICENSE)
(CIL / "CTranslate2-MIT.txt").write_text(MIT.format(
    copyright="Copyright (c) 2018-     SYSTRAN.\nCopyright (c) 2019-     The OpenNMT Authors."), encoding="utf-8")
print("OK CTranslate2-MIT.txt")
# FFmpeg (build gyan.dev, GPL v3) – licence leží vedle bin\ffmpeg.exe
ffmpeg = shutil.which("ffmpeg")
if ffmpeg:
    shutil.copyfile(Path(ffmpeg).resolve().parent.parent / "LICENSE", CIL / "FFmpeg-GPL-3.0.txt")
    print("OK FFmpeg-GPL-3.0.txt")
