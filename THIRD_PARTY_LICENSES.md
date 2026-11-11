# Licence knihoven třetích stran

kupcake.studio používá níže uvedené programy, knihovny, modely a písma. Plná znění licencí jsou ve složce
`licenses/` (v nainstalované aplikaci `%LOCALAPPDATA%\Programs\KupcakeStudio\_internal\licenses`).
Údaje o verzích odpovídají obsahu instalátoru 1.0.0-beta (ověřeno proti složce `_internal` a `.venv`).

*This file is in Czech. Component names, versions, licence identifiers and links are language-neutral;
the source-code offer is repeated in English in the section "Zdrojové kódy přibalených programů".*

**Vlastní kód kupcake.studio** je pod licencí GNU GPL verze 3 (`GPL-3.0-only`), Copyright (C) 2026 Tomáš Kupec –
soubory [LICENSE](LICENSE) a [ADDITIONAL_PERMISSION.md](ADDITIONAL_PERMISSION.md). **Součásti uvedené
v tomto souboru pod tuto licenci nespadají** – každá se šíří pod vlastní licencí svého autora. Platí to
zejména pro proprietární knihovny NVIDIA (CUDA, cuDNN) a Intel (oneMKL, OpenMP) a běhové knihovny Microsoft
(oddíl 4): ty **nejsou pod GPL** a řídí se podmínkami svých výrobců. Název kupcake.studio a logo také nejsou
součástí licence kódu.

Obsah: [1. Programy a knihovny pod GPL a LGPL](#1-programy-a-knihovny-pod-gpl-a-lgpl) ·
[2. Zdrojové kódy přibalených programů](#2-zdrojové-kódy-přibalených-programů) ·
[3. Přepis, časování a oddělení hlasu](#3-přepis-časování-a-oddělení-hlasu) ·
[4. Proprietární knihovny](#4-proprietární-knihovny-nejsou-pod-gpl) ·
[5. Python a ostatní balíčky](#5-python-a-ostatní-balíčky) ·
[6. Modely](#6-modely-nepřibalují-se--stahují-se-po-souhlasu) ·
[7. Písma a ikony](#7-písma-a-ikony) · [8. Nástroje sestavení](#8-nástroje-sestavení)

## 1. Programy a knihovny pod GPL a LGPL

| Komponenta | Přesná verze | Licence | Jak je v aplikaci | Plné znění (`licenses/`) |
|---|---|---|---|---|
| **FFmpeg** (`ffmpeg\ffmpeg.exe`, `ffprobe.exe`) | 9.0.2, sestavení „full“ z gyan.dev (`9.0.2-full_build-www.gyan.dev`) | **GPL-3.0-or-later** (sestaveno s `--enable-gpl --enable-version3`, bez `--enable-nonfree`) | samostatné programy, které aplikace spouští | `FFmpeg-GPL-3.0.txt`; popis sestavení a seznam knihoven v něm: `FFmpeg-gyan-README.txt` |
| **mpv** (`mpv\libmpv-2.dll`) | mpv v0.41.0-1227-ge471496c5, sestavení shinchiro z 21. 10. 2026; uvnitř FFmpeg N-127893-g9a861e968, x264, x265 a další knihovny | **GPL** (mpv: GPL-2.0-or-later; sestavení obsahuje kodéry x264 a x265, proto se šíří pod GPL, ne LGPL) | dynamická knihovna (přehrávač) | GPL v2: `python-mpv-GPL-2.0.txt`, GPL v3: `FFmpeg-GPL-3.0.txt` |
| python-mpv | 1.0.8 | GPL-2.0-or-later nebo LGPL-2.1-or-later | modul Pythonu | `python-mpv-GPL-2.0.txt`, `python-mpv-LGPL-2.1.txt` |
| **Qt 6, PySide6, Shiboken6** (Qt for Python) | 6.12.0 | **LGPL-3.0-only** | samostatné dynamické knihovny (`PySide6\*.dll`, `*.pyd`, `shiboken6\`) | `Qt-PySide6-LGPL-3.0.txt` (navazuje na GPL v3 – soubor `LICENSE`) |
| **Qt Advanced Docking System** + vazby PySide6-QtAds | Qt-ADS 5.1.1, PySide6-QtAds 5.1.1.1 | **LGPL-2.1** (vazby zčásti MIT) | samostatný modul `PySide6QtAds\PySide6QtAds.pyd` | `QtAds-LGPL-2.1.txt`, `PySide6-QtAds.txt` |
| **PyAV** | 19.0.2 | obal BSD-3-Clause; přibalené knihovny viz tabulka níže | modul Pythonu + knihovny ve složce `av.libs` | `PyAV-BSD-3-Clause.txt` |
| **lameenc** + **LAME** | lameenc 1.9.0, uvnitř LAME 4.0 | lameenc LGPL-3.0-or-later, LAME LGPL-2.0-or-later | modul `lameenc.cp312-win_amd64.pyd` (závislost knihovny Demucs) | `lameenc-LGPL-3.0.txt`; novější verze LGPL: `python-mpv-LGPL-2.1.txt` |

Knihovny Qt a Qt-ADS (LGPL) se nemění a jsou přibalené jako samostatné dynamické knihovny – jdou nahradit
vlastní sestavenou verzí se stejným rozhraním. Autoři Qt-ADS: Uwe Kindler, githubuser0xFFFF a přispěvatelé;
vazby CJ Niemira, metgem, mborgerson. Qt obsahuje další součásti třetích stran (mj. PDFium, BSD-3-Clause,
v `Qt6Pdf.dll` a softwarové vykreslování Mesa, MIT, v `opengl32sw.dll`): https://doc.qt.io/qt-6/licenses-used-in-qt.html.

### Knihovny přibalené v PyAV (`av.libs`)

Binární balíček PyAV 19.0.2 obsahuje vlastní sestavení FFmpeg a jeho závislostí (projekt pyav-ffmpeg,
vydání 9.0.2-1). Verze jsou vyčtené z knihoven a z receptu sestavení.

| Knihovna | Verze | Licence |
|---|---|---|
| FFmpeg – `avcodec`, `avformat`, `avutil`, `avfilter`, `avdevice`, `swscale`, `swresample` | 9.0.2 | knihovny samy hlásí LGPL-3.0-or-later; jsou ale sestavené s libx264 a libx265, **celek se proto šíří pod GPL** (verze 3) |
| **libx264** | core 165 (commit b35605ac) | **GPL-2.0-or-later** |
| **libx265** | 4.3 | **GPL-2.0-or-later** |
| libvpx (VP8/VP9) | 1.17.0 | BSD-3-Clause |
| dav1d (AV1) | 1.5.4 | BSD-2-Clause |
| SVT-AV1 | 4.2.0 | BSD-3-Clause-Clear + Alliance for Open Media Patent License 1.0 |
| Opus | 1.6.1 | BSD-3-Clause |
| libwebp (+ libsharpyuv, libwebpmux) | 1.6.0 | BSD-3-Clause |
| libvmaf (VMAF) | 3.2.1 | BSD-2-Clause-Patent |
| libvpl (Intel Video Processing Library) | 2.16.0 | MIT |
| lamer / LAME (MP3, součást `avcodec`) | 3.101.0 | LGPL-2.0-or-later |
| zlib | 1.3.2 | Zlib |
| libiconv | – | LGPL-2.1-or-later |
| běhové knihovny GCC (`libgcc_s_seh`, `libstdc++`) a `libwinpthread` | – | GPL-3.0-or-later s výjimkou GCC Runtime Library Exception; winpthreads MIT / BSD |
| hlavičky nv-codec-headers 13.0.19.0 a AMF 1.5.2 (jen rozhraní NVENC/AMF) | – | MIT |

PyAV je závislost knihovny faster-whisper. Aplikace přes něj video nekóduje – zvuk čte i exportuje
samostatným programem FFmpeg (oddíl výše).

## 2. Zdrojové kódy přibalených programů

Ke každému programu a knihovně pod GPL nebo LGPL, které jsou v instalátoru v binární podobě, je tady přesná
verze a odkaz na odpovídající zdrojový kód. Zdrojový kód samotné aplikace kupcake.studio je v repozitáři
https://github.com/TomKup17/kupcake-studio (stejné místo jako instalátor).

| Program | Binární sestavení v instalátoru | Zdrojový kód |
|---|---|---|
| **FFmpeg 9.0.2** (`ffmpeg.exe`, `ffprobe.exe`) | `ffmpeg-9.0.2-full_build` – https://github.com/GyanD/codexffmpeg/releases/tag/9.0.2 (https://www.gyan.dev/ffmpeg/builds/) | FFmpeg, commit uvedený autorem sestavení: https://github.com/FFmpeg/FFmpeg/commit/946fcce07b · archiv vydání https://ffmpeg.org/releases/ffmpeg-9.0.2.tar.xz · seznam přibalených knihoven: `licenses/FFmpeg-gyan-README.txt` |
| **mpv** (`libmpv-2.dll`) | `mpv-dev-x86_64-20261021-git-e471496c56.7z` – https://github.com/shinchiro/mpv-winbuild-cmake/releases/tag/20261021 | mpv: https://github.com/mpv-player/mpv/tree/e471496c56 · FFmpeg: https://github.com/FFmpeg/FFmpeg/commit/9a861e968 · recepty sestavení (stahují zdrojové kódy všech knihoven včetně x264 a x265): https://github.com/shinchiro/mpv-winbuild-cmake |
| **FFmpeg a kodeky uvnitř PyAV** (`av.libs`) | PyAV 19.0.2 – https://github.com/PyAV-Org/PyAV/tree/v19.0.2, knihovny z pyav-ffmpeg 9.0.2-1 | recept sestavení se záplatami a adresami zdrojových archivů všech knihoven: https://github.com/PyAV-Org/pyav-ffmpeg/tree/9.0.2-1 (soubor `scripts/pkg.py`) · FFmpeg: https://ffmpeg.org/releases/ffmpeg-9.0.2.tar.xz |
| **Qt 6.12.0** | knihovny Qt z balíčků PySide6 6.12.0 (PyPI) | https://download.qt.io/official_releases/qt/6.12/6.12.0/single/qt-everywhere-src-6.12.0.tar.xz |
| **PySide6 a Shiboken6 6.12.0** | balíčky PySide6, PySide6_Essentials, PySide6_Addons, shiboken6 (PyPI) | https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-6.12.0-src/pyside-setup-everywhere-src-6.12.0.tar.xz |
| **Qt Advanced Docking System 5.1.1** | uvnitř PySide6-QtAds 5.1.1.1 (PyPI) | Qt-ADS: https://github.com/githubuser0xFFFF/Qt-Advanced-Docking-System/tree/v5.1.1 (commit 023ce959) · vazby: https://github.com/mborgerson/pyside6_qtads/releases/tag/v5.1.1.1 |
| **LAME 4.0** | uvnitř lameenc 1.9.0 (PyPI) | LAME: https://sourceforge.net/projects/lame/files/lame/4.0/lame-4.0.tar.gz/download · lameenc: https://github.com/chrisstaite/lameenc/releases/tag/v1.9.0 |
| python-mpv 1.0.8 | balíček python-mpv (PyPI), zdrojový kód je přímo v instalaci (`mpv.py`) | https://github.com/jaseg/python-mpv/tree/v1.0.8 |

**Zdrojové kódy na požádání poskytnu.** Kdyby některý odkaz přestal fungovat nebo bys potřeboval zdrojový kód
přesně odpovídající některé přibalené knihovně pod GPL nebo LGPL, napiš přes
[GitHub Issues](https://github.com/TomKup17/kupcake-studio/issues) nebo přes kontakt na https://tomkup.cz.

*In English: for every GPL or LGPL program and library shipped in binary form in the installer, the table
above gives the exact version and a link to the corresponding source code. If a link stops working, or you
need the source code matching one of the bundled GPL/LGPL components, I will provide it on request – contact me
via GitHub Issues (https://github.com/TomKup17/kupcake-studio/issues) or https://tomkup.cz.*

## 3. Přepis, časování a oddělení hlasu

Knihovny jsou přibalené k aplikaci; **modely se nepřibalují** (oddíl 6), kromě malého modelu Silero VAD.

| Komponenta | Verze | Licence | Zdroj | Plné znění (`licenses/`) |
|---|---|---|---|---|
| faster-whisper | 1.2.1 | MIT | https://github.com/SYSTRAN/faster-whisper | `faster-whisper-MIT.txt` |
| **Silero VAD** – model `silero_vad_v6.onnx` přibalený ve faster-whisper (rozpoznání řeči a ticha) | v6 | MIT | https://github.com/snakers4/silero-vad | `Silero-VAD-MIT.txt` |
| CTranslate2 (obsahuje Intel oneMKL a Intel OpenMP – oddíl 4) | 4.8.4 | MIT | https://github.com/OpenNMT/CTranslate2 | `CTranslate2-MIT.txt` |
| onnxruntime | 1.31.1 | MIT | https://github.com/microsoft/onnxruntime | `onnxruntime-MIT.txt`, `python/onnxruntime.txt` (včetně oznámení třetích stran) |
| PyTorch (obsahuje knihovny NVIDIA CUDA, Intel oneMKL a Intel OpenMP – oddíl 4; dále libuv, MIT) | 2.11.0+cu128 | BSD-3-Clause | https://github.com/pytorch/pytorch | `PyTorch-BSD-3-Clause.txt`, `PyTorch-NOTICE.txt` |
| torchaudio | 2.11.0+cu128 | BSD-2-Clause | https://github.com/pytorch/audio | `torchaudio-BSD-2-Clause.txt` |
| Hugging Face transformers, tokenizers, safetensors, huggingface_hub | 5.22.1, 0.23.3, 0.8.0, 2.4.0 | Apache-2.0 | https://github.com/huggingface | `transformers-Apache-2.0.txt`, `tokenizers-Apache-2.0.txt`, `safetensors-Apache-2.0.txt`, `huggingface_hub-Apache-2.0.txt` |
| **hf-xet** (součást huggingface_hub) | 1.7.1 | Apache-2.0 | https://github.com/huggingface/xet-core | `python/hf-xet.txt` |
| Demucs (knihovna) | 4.1.0 | MIT | https://github.com/adefossez/demucs | `Demucs-MIT.txt` |
| julius, einops | 0.2.8, 0.8.2 | MIT | https://github.com/adefossez/julius, https://github.com/arogozhnikov/einops | `julius-MIT.txt`, `einops-MIT.txt` |
| **uroman** (převod písma do latinky pro model MMS) | 1.3.1.1 | vlastní volná licence: znění odpovídá MIT, navíc ukládá uvést použití uromanu (není to čistá MIT) | https://github.com/isi-nlp/uroman | `uroman-LICENSE.txt` |
| NumPy (obsahuje OpenBLAS, BSD-3-Clause) | 2.5.4 | BSD-3-Clause a další volné licence | https://numpy.org | `NumPy-BSD-3-Clause.txt`, `python/numpy.txt` |

This project uses the universal romanizer software 'uroman' written by Ulf Hermjakob, USC Information
Sciences Institute (2015-2020).

Postup zarovnání slov odpovídá WhisperX (BSD-2-Clause, https://github.com/m-bain/whisperX); WhisperX samotný
se nepřibaluje.

## 4. Proprietární knihovny (nejsou pod GPL)

Tyto knihovny jsou v aplikaci jen v binární podobě, bez zdrojového kódu, a **nejsou pod GPL ani pod jinou
svobodnou licencí**. Smí se šířit a používat jen za podmínek svých výrobců. Vlastní kód kupcake.studio k jejich
spojení s programem uděluje dodatečné svolení podle čl. 7 GPLv3 – viz
[ADDITIONAL_PERMISSION.md](ADDITIONAL_PERMISSION.md).

| Komponenta | Kde je | Licence | Plné znění / podmínky |
|---|---|---|---|
| **NVIDIA CUDA runtime** – cuBLAS, cuFFT, cuRAND, cuSOLVER, cuSPARSE, NVRTC, nvJitLink, CUPTI, CUDA runtime (`cudart`), NVTX a související | `torch\lib\*.dll`, `nvidia\cublas`, `nvidia\cuda_nvrtc` (balíčky nvidia-cublas-cu12 12.9.2.10, nvidia-cuda-nvrtc-cu12 12.9.86 a knihovny uvnitř PyTorch 2.11.0+cu128) | proprietární – NVIDIA CUDA Toolkit End User License Agreement (EULA) | `NVIDIA-CUDA-EULA.txt`, https://docs.nvidia.com/cuda/eula/ |
| **NVIDIA cuDNN** | `torch\lib\cudnn*.dll`, `nvidia\cudnn`, `ctranslate2\cudnn64_9.dll` (nvidia-cudnn-cu12 9.27.0.42) | proprietární – License Agreement for NVIDIA Software Development Kits s dodatkem pro cuDNN | `NVIDIA-cuDNN-license.txt` |
| **Intel oneAPI Math Kernel Library (oneMKL)** | součást `torch\lib\torch_cpu.dll` a `ctranslate2\ctranslate2.dll` | proprietární – Intel Simplified Software License | https://www.intel.com/content/www/us/en/developer/articles/license/onemkl-license-faq.html |
| **Intel OpenMP Runtime** (`libiomp5md.dll`, `libiompstubs5md.dll`) | `torch\lib`, `ctranslate2` | proprietární – Intel End User License Agreement for Developer Tools | https://www.intel.com/content/www/us/en/developer/articles/license/end-user-license-agreement.html |
| **Microsoft Visual C++ Runtime** (`vcruntime140*.dll`, `msvcp140*.dll`) | kořen `_internal`, `PySide6`, `numpy.libs` | proprietární, volně šiřitelné s aplikací (Microsoft Visual Studio – Distributable Code) | https://learn.microsoft.com/en-us/visualstudio/releases/2022/redistribution |

## 5. Python a ostatní balíčky

| Komponenta | Verze | Licence | Plné znění (`licenses/`) |
|---|---|---|---|
| **Python** (`python312.dll`, standardní knihovna) | 3.12.4 | PSF-2.0 | `Python-3.12-LICENSE.txt` |
| **OpenSSL** (`libcrypto-3.dll`, `libssl-3.dll`) | 3.0.13 | Apache-2.0 | `Python-3.12-LICENSE.txt`, `Python-3.12-incorporated-software.txt` |
| **SQLite** (`sqlite3.dll`) | 3.45.3 | volné dílo (public domain) | https://www.sqlite.org/copyright.html |
| **libffi** (`libffi-8.dll`) | 3.4 | MIT | `Python-3.12-LICENSE.txt` |
| **expat** (`pyexpat.pyd`) | 2.6.2 | MIT | `Python-3.12-incorporated-software.txt` |
| zlib, bzip2, liblzma (XZ Utils), libmpdec (součásti Pythonu) | 1.3.1, 1.0.8, –, – | Zlib, bzip2, 0BSD / volné dílo, BSD-2-Clause | `Python-3.12-LICENSE.txt`, `Python-3.12-incorporated-software.txt` |

Aplikace obsahuje software vyvinutý projektem OpenSSL (https://www.openssl.org/).

**Úplný seznam všech balíčků Pythonu, které jsou v instalátoru** (55 balíčků – název, verze, licence), je
v souboru [licenses/PYTHON_PACKAGES.md](licenses/PYTHON_PACKAGES.md); plné znění licencí každého z nich je ve
složce `licenses/python/`. Patří sem i menší závislosti, které tento přehled jednotlivě neuvádí (anyio, click,
filelock, fsspec, Jinja2, networkx, packaging, protobuf, PyYAML, regex, rich, sympy, tqdm a další – licence MIT,
BSD, Apache-2.0, MPL-2.0, PSF-2.0).

Seznam i texty generuje skript `licenses/prenes_licence.py` z metadat balíčků v `.venv` podle skutečného obsahu
sestavení – spustit po každé změně závislostí a po sestavení.

## 6. Modely (nepřibalují se – stahují se po souhlasu)

Modely nejsou součástí instalátoru. Aplikace je stáhne až po potvrzení uživatele přímo ze serverů Hugging Face
a Meta do `%LOCALAPPDATA%\KupcakeStudio\models` (přesné revize a kontrolní součty: `manifest_modelu.py`).

| Model | K čemu | Licence | Zdroj |
|---|---|---|---|
| Whisper large-v3 (`Systran/faster-whisper-large-v3`) | přepis – přesnost „Nejpřesnější“ | MIT | https://huggingface.co/Systran/faster-whisper-large-v3 |
| Whisper large-v3-turbo (`dropbox-dash/faster-whisper-large-v3-turbo`, dříve `mobiuslabsgmbh/…`) | přepis – přesnost „Rychlá“ | MIT | https://huggingface.co/dropbox-dash/faster-whisper-large-v3-turbo |
| Whisper medium (`Systran/faster-whisper-medium`) | přepis – přesnost „Úsporná“ | MIT | https://huggingface.co/Systran/faster-whisper-medium |
| wav2vec2 – čeština `comodoro/wav2vec2-xls-r-300m-cs-250`, slovenština `comodoro/wav2vec2-xls-r-300m-sk-cv8` | přesné časování slov | Apache-2.0 | https://huggingface.co/comodoro |
| wav2vec2 – angličtina `facebook/wav2vec2-base-960h` | přesné časování slov | Apache-2.0 | https://huggingface.co/facebook/wav2vec2-base-960h |
| wav2vec2 – němčina, španělština, francouzština, italština, polština `jonatasgrosman/wav2vec2-large-xlsr-53-<jazyk>` | přesné časování slov | Apache-2.0 | https://huggingface.co/jonatasgrosman |
| **Meta MMS** `MahmoudAshraf/mms-300m-1130-forced-aligner` | přesné časování slov v ostatních jazycích – **ve výchozím stavu vypnuto** | **CC BY-NC 4.0 – jen nekomerční použití** | https://huggingface.co/MahmoudAshraf/mms-300m-1130-forced-aligner |
| Demucs htdemucs | oddělení hlasu od hudby | MIT (licence projektu Demucs) | https://github.com/adefossez/demucs |

**Model MMS** smí být použit jen nekomerčně (https://creativecommons.org/licenses/by-nc/4.0/). Aplikace ho
proto sama nepoužívá: jazyky bez vlastního modelu zůstanou na časech z přepisu (Whisper). Kdo ho chce použít
pro nekomerční účely, zapne ho v **Nastavení → Přesné časování i pro další jazyky** a potvrdí upozornění
na licenci; totéž upozornění je v dotazu na stažení modelu. Výchozí stav je v `zarovnani.py` (`POUZIT_MMS = False`).

## 7. Písma a ikony

Všechna písma jsou pod **SIL Open Font License 1.1** – smí se přibalit k aplikaci a šířit s ní,
nesmí se prodávat samostatně.

| Písmo | Použití | Autoři | Plné znění |
|---|---|---|---|
| Inter | texty rozhraní | The Inter Project Authors (Rasmus Andersson) | `licenses/Inter-OFL-1.1.txt` |
| JetBrains Mono | časy a časová osa | The JetBrains Mono Project Authors | `licenses/JetBrainsMono-OFL-1.1.txt` |
| Montserrat (ExtraBold, Black) | písmo titulků | The Montserrat Project Authors (Julieta Ulanovsky) | `licenses/Montserrat-OFL-1.1.txt` |

Ikony Instagram, TikTok a GitHub v okně O aplikaci (`ikony/znacka_*.svg`) jsou z projektu
**Simple Icons** 13.21.0 (https://simpleicons.org) pod licencí **CC0 1.0**. Loga a názvy Instagram, TikTok
a GitHub jsou ochranné známky svých vlastníků; jsou použita jednobarevně jen jako odkaz na profil autora.
Ostatní ikony rozhraní (`ikony/*.svg`) jsou vlastní.

## 8. Nástroje sestavení

| Nástroj | Verze | Licence | Poznámka |
|---|---|---|---|
| PyInstaller (zavaděč v `KupcakeStudio.exe`) | 6.22.3 | GPL-2.0-or-later s výjimkou, která dovoluje šířit zabalené aplikace pod libovolnou licencí | `licenses/python/pyinstaller.txt` |
| Inno Setup (instalátor) | 6 | licence Inno Setup (volná, s uvedením autora) | https://jrsoftware.org/files/is/license.txt – Copyright (C) 1997-2026 Jordan Russell, portions Copyright (C) 2000-2026 Martijn Laan |
