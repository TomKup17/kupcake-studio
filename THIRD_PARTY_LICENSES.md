# Licence knihoven třetích stran

kupcake.studio používá níže uvedené knihovny, nástroje a písma. Plná znění licencí jsou ve složce
`licenses/` (v nainstalované aplikaci `%LOCALAPPDATA%\Programs\KupcakeStudio\_internal\licenses`), u ostatních
je odkaz na zdroj.

## Qt Advanced Docking System (QtAds) + PySide6-QtAds

Volně přesouvatelné a odpojitelné sekce rozhraní (dokování). Nové ve verzi 1.1.0.

| | |
|---|---|
| Knihovna | Qt Advanced Docking System 4.x (C++), Python vazby PySide6-QtAds 5.1.1.1 |
| Autoři | Uwe Kindler, githubuser0xFFFF a přispěvatelé; vazby CJ Niemira, metgem, mborgerson |
| Licence | **GNU LGPL v2.1** (vazby navíc část kódu pod MIT) |
| Zdroj | https://github.com/githubuser0xFFFF/Qt-Advanced-Docking-System, https://github.com/mborgerson/pyside6_qtads |
| Plné znění | `licenses/QtAds-LGPL-2.1.txt`, `licenses/PySide6-QtAds.txt` |

Splnění LGPL: knihovna se nemění a je přibalena jako samostatný dynamický modul
(`_internal\PySide6QtAds\PySide6QtAds.pyd`). Uživatel ho může nahradit vlastní sestavenou verzí
se stejným rozhraním. Zdrojový kód je dostupný na odkazech výše.

## Přesné časování a oddělení hlasu (nové ve verzi 1.4.0)

Knihovny jsou přibalené k aplikaci; **modely se nepřibalují** – stáhnou se při prvním použití
do `%LOCALAPPDATA%\KupcakeStudio\models` (zarovnání do `zarovnani\`, Demucs do `demucs\`).

| Komponenta | Licence | Zdroj | Plné znění (`licenses/`) |
|---|---|---|---|
| PyTorch 2.11 (s CUDA 12.8 runtime) | BSD 3-Clause (CUDA runtime: NVIDIA Software License) | https://github.com/pytorch/pytorch | `PyTorch-BSD-3-Clause.txt`, `PyTorch-NOTICE.txt` |
| torchaudio 2.11 | BSD 2-Clause | https://github.com/pytorch/audio | `torchaudio-BSD-2-Clause.txt` |
| Hugging Face transformers, safetensors | Apache 2.0 | https://github.com/huggingface/transformers | `transformers-Apache-2.0.txt`, `safetensors-Apache-2.0.txt` |
| Demucs 4 (knihovna i model htdemucs) | MIT | https://github.com/adefossez/demucs | `Demucs-MIT.txt` |
| julius, einops | MIT | https://github.com/adefossez/julius, https://github.com/arogozhnikov/einops | `julius-MIT.txt`, `einops-MIT.txt` |
| uroman (převod písma do latinky pro MMS) | MIT s požadavkem na uvedení autora | https://github.com/isi-nlp/uroman | `uroman-MIT.txt` |

This project uses the universal romanizer software 'uroman' written by Ulf Hermjakob, USC Information
Sciences Institute (2015-2020).

Akustické modely pro zarovnání slov (wav2vec2 / CTC). Postup zarovnání odpovídá WhisperX (BSD 2-Clause,
https://github.com/m-bain/whisperX), WhisperX samotný se nepřibaluje.

| Jazyk | Model | Licence |
|---|---|---|
| čeština | `comodoro/wav2vec2-xls-r-300m-cs-250` | Apache 2.0 |
| slovenština | `comodoro/wav2vec2-xls-r-300m-sk-cv8` | Apache 2.0 |
| angličtina | `facebook/wav2vec2-base-960h` | Apache 2.0 |
| němčina, španělština, francouzština, italština, polština | `jonatasgrosman/wav2vec2-large-xlsr-53-<jazyk>` | Apache 2.0 |
| **ostatní jazyky** | `MahmoudAshraf/mms-300m-1130-forced-aligner` (Meta MMS) | **CC BY-NC 4.0 – jen nekomerční použití** |

Pozor na MMS: model Meta MMS smí být použit jen **nekomerčně** (CC BY-NC 4.0,
https://creativecommons.org/licenses/by-nc/4.0/). Aplikace ho použije jen pro jazyky, které nemají vlastní
model výše. Pokud by se kupcake.studio prodávalo nebo používalo komerčně, je potřeba MMS nahradit modelem
s volnou licencí (stačí v `zarovnani.py` nastavit `POUZIT_MMS = False` – takové jazyky pak zůstanou na časech z Whisperu).

## Ikony sociálních sítí

Ikony Instagram, TikTok a GitHub v okně O aplikaci (`ikony/znacka_*.svg`) jsou z projektu
**Simple Icons** 13.21.0 (https://simpleicons.org) pod licencí **CC0 1.0**. Loga a názvy Instagram, TikTok
a GitHub jsou ochranné známky svých vlastníků; jsou použita jednobarevně jen jako odkaz na profil autora.

## Písma

Všechna písma jsou pod **SIL Open Font License 1.1** – smí se přibalit k aplikaci a šířit s ní,
nesmí se prodávat samostatně.

| Písmo | Použití | Autoři | Plné znění |
|---|---|---|---|
| Inter | texty rozhraní (nové v 1.1.0) | The Inter Project Authors (Rasmus Andersson) | `licenses/Inter-OFL-1.1.txt` |
| JetBrains Mono | časy a časová osa (nové v 1.1.0) | The JetBrains Mono Project Authors | `licenses/JetBrainsMono-OFL-1.1.txt` |
| Montserrat (ExtraBold, Black) | písmo titulků | The Montserrat Project Authors (Julieta Ulanovsky) | `licenses/Montserrat-OFL-1.1.txt` |

## Ostatní

| Komponenta | Licence | Zdroj | Plné znění (`licenses/`) |
|---|---|---|---|
| Qt 6 / PySide6, Shiboken6 | LGPL v3 | https://www.qt.io/qt-for-python | `Qt-PySide6-LGPL-3.0.txt` |
| faster-whisper | MIT | https://github.com/SYSTRAN/faster-whisper | `faster-whisper-MIT.txt` |
| CTranslate2 | MIT | https://github.com/OpenNMT/CTranslate2 | `CTranslate2-MIT.txt` |
| PyAV | BSD 3-Clause | https://github.com/PyAV-Org/PyAV | `PyAV-BSD-3-Clause.txt` |
| onnxruntime | MIT | https://github.com/microsoft/onnxruntime | `onnxruntime-MIT.txt` |
| tokenizers, huggingface_hub | Apache 2.0 | https://github.com/huggingface | `tokenizers-Apache-2.0.txt`, `huggingface_hub-Apache-2.0.txt` |
| NumPy | BSD 3-Clause | https://numpy.org | `NumPy-BSD-3-Clause.txt` |
| Model Whisper large-v3 (stahuje se při prvním přepisu) | MIT | https://huggingface.co/Systran/faster-whisper-large-v3 | – (model se nepřibaluje) |
| Model Whisper large-v3-turbo (přesnost „Rychlá“, stahuje se při výběru) | MIT | https://huggingface.co/mobiuslabsgmbh/faster-whisper-large-v3-turbo | – (model se nepřibaluje) |
| Model Whisper medium (přesnost „Úsporná“, stahuje se při výběru) | MIT | https://huggingface.co/Systran/faster-whisper-medium | – (model se nepřibaluje) |
| NVIDIA CUDA / cuBLAS / cuDNN (runtime knihovny) | NVIDIA Software License | https://docs.nvidia.com/cuda/eula/ | `NVIDIA-CUDA-EULA.txt`, `NVIDIA-cuDNN-license.txt` |
| libmpv (mpv) + python-mpv | LGPL v2.1+ (mpv), GPL v2+/LGPL v2.1+ (python-mpv) | https://mpv.io, https://github.com/jaseg/python-mpv | `python-mpv-LGPL-2.1.txt`, `python-mpv-GPL-2.0.txt` |
| FFmpeg 9.0 (build gyan.dev „full“) | GPL v3 | https://ffmpeg.org, https://www.gyan.dev/ffmpeg/builds/ | `FFmpeg-GPL-3.0.txt` |

Plná znění licencí knihoven doplňuje skript `licenses/prenes_licence.py` (z metadat balíčků v `.venv`
a ze složky FFmpeg) – spustit po každé změně závislostí.
