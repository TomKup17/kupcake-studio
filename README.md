# kupcake.studio

**English** | [Čeština](README.cs.md)

An app by iamtom.kup. The display name is always written `kupcake.studio`; the technical name
(files, folders) is `KupcakeStudio`. Earlier working names: Spellcast, tkStudio.

> **Name and logo:** the name **kupcake.studio**, the cupcake logo and icon and the iamtom.kup brand
> **are not covered by the code licence** – they must not be used for modified versions or other projects
> without the author's consent. **The official version is only available from this repository** (Releases);
> installers from other sources may have been modified. Report security issues as described in
> [SECURITY.md](SECURITY.md).

Automatic subtitles from video: speech transcription (faster-whisper large-v3 on the GPU), a subtitle editor
with a word-level timeline, live preview in the mpv player and burning the subtitles into the video with
FFmpeg (NVENC).

## Beta version

This is a **public test version** (`1.0.0-beta.1`). The app works, but it **may contain bugs** and some
features may still change. On first launch a welcome window shows this notice – you continue only after
ticking **"I understand"** (it shows again only for a new major version, e.g. the move to 1.0).

- Save your work regularly (Ctrl+S); on top of that the project is saved automatically every 2 minutes
  and the app offers to restore it after a crash.
- **The original video is never overwritten** – the app blocks exporting into the same file. Backups are
  still recommended.
- **How to report a bug:** Help → Report a bug / Feedback (or the link in the welcome window). When the app
  shows an error window, click **"Copy report"** and paste it into your message – it contains the version,
  the system and the error trace, not your videos. A description of the steps that led to the error helps
  too, as does the log from `%LOCALAPPDATA%\KupcakeStudio\logs`.

## No warranty

kupcake.studio is free and **provided as is, without any warranty** – express or implied, including the
warranty of merchantability or fitness for a particular purpose. The author is not liable for damage caused
by using it, to the extent permitted by law. See sections 15 and 16 of the
[GNU GPL v3](https://www.gnu.org/licenses/gpl-3.0.html) licence (full text in [LICENSE](LICENSE)).
In the app: About → "Provided without warranty · GPL-3.0". The complete **Terms of Use** are in
[TERMS.md](TERMS.md) (Czech: [TERMS.cs.md](TERMS.cs.md)); the app shows them in About and in the welcome
window, the installer on its licence page.

## Privacy

Everything is processed **only on your computer** – transcription, word timing, voice separation, preview,
playback and export. Videos, audio, transcripts, subtitles, projects and settings are **never sent anywhere**
and the app **collects no data**: no telemetry, no accounts, no analytics, no identifiers. We can't claim
that the app never talks to the internet, though – it connects in exactly these cases:

| When | Where | What is sent | How to turn it off |
|---|---|---|---|
| **Checking for a new version** – 5 s after start, at most once every 24 h | `api.github.com` (GitHub, Microsoft) | a normal HTTPS request for the list of releases; header `User-Agent: kupcake.studio/<version>`. Like any server, GitHub sees your IP address. Nothing else. | Settings → **Check for new versions** |
| **Downloading a model** – only after your consent in a dialog (name, size, source), the first time a given transcription accuracy, timing language or voice separation is used | `huggingface.co` (+ its CDN `*.hf.co`, `*.huggingface.co`); Demucs from `dl.fbaipublicfiles.com` (Meta) | an HTTPS request for the specific model files + `User-Agent` as above. The server sees your IP address and **which model** you download (so e.g. that you are timing a Czech video). No video, audio or text. | don't give consent (transcription then won't run, or runs without that step) |
| **Links** – Help → Report a bug, buttons in About, "Download" for a new version | **your browser** opens the page from `links.py`, or the release page on `github.com` | nothing – a page just opens; the app itself **never downloads or runs an installer** | click only when you want to |

What the app also does so that nothing "leaks" on its own:

- the Hugging Face libraries (`transformers`, `huggingface_hub`) are forced **offline** with telemetry off
  (`HF_HUB_OFFLINE`, `HF_HUB_DISABLE_TELEMETRY` in `cesty.py`); models are downloaded only by `stahovani.py`
  and never without asking,
- downloads and redirects may only go over HTTPS and only to the hosts above; every file is checked against
  its **SHA-256** from `manifest_modelu.py` – a different file is deleted (see [SECURITY.md](SECURITY.md)),
- FFmpeg and mpv may read **local files only** (`-protocol_whitelist file`, mpv without youtube-dl, without
  scripts and config from the user profile) – a "video" that is really a playlist of internet addresses
  downloads nothing,
- PyTorch, CTranslate2, faster-whisper, Demucs, onnxruntime and Qt don't touch the network in the app
  (verified by a code audit, [docs/BEZPECNOSTNI_AUDIT.md](docs/BEZPECNOSTNI_AUDIT.md), in Czech).

What stays only on your disk (and what you should know before sending it to anyone):

- the **log** `%LOCALAPPDATA%\KupcakeStudio\logs\kupcake.log` – progress and errors; it may contain the
  **names and paths of your videos and projects** and FFmpeg error texts; no transcripts or subtitle content,
- the **error report** ("Copy report") – app version, Windows version, CPU, graphics card and driver,
  error text; paths into your profile are replaced with `%LOCALAPPDATA%`, so it doesn't contain your user name,
- **settings** `%APPDATA%\KupcakeStudio\aplikace.ini` – among other things the list of recent projects (paths)
  and the last export options; **`.kupcake` projects** – the absolute path to the video, the transcript
  (words with times) and the subtitles.

Outside the app: Windows SmartScreen may contact Microsoft on its own the first time an unsigned installer
runs – that's a Windows feature, not the app.

## System requirements

| | Minimum | Recommended |
|---|---|---|
| System | Windows 10 or 11, 64-bit | Windows 11 |
| CPU | 4 cores (x64) | 8 or more cores |
| Memory | 8 GB RAM | 16 GB RAM |
| Graphics card | – (transcription and export run on the CPU, much slower) | NVIDIA with 6 GB VRAM or more, current driver (CUDA 12) |
| Disk space | app about 7 GB + model 1.5–3 GB | 15 GB free (more models, exports) |
| Internet | for the first transcription (model download) | – |

Approximate transcription speed (60 s of continuous speech): RTX 4070 SUPER about 5 s, i7-12700KF CPU about
50 s (Most accurate), with Fast accuracy about 1.5 s / 20 s.

## Installation

1. From this repository's **Releases** (the official version isn't distributed anywhere else), download
   **all** installer files into one folder: `KupcakeStudio-Setup-<version>.exe` and its parts
   `KupcakeStudio-Setup-<version>-1.bin`, `-2.bin`… GitHub only allows files up to 2 GB, so the installer
   is split; it won't run without the `.bin` parts. Size: about **3.1 GB** in total, about **6.9 GB** after
   installation (it includes PyTorch with CUDA, FFmpeg and mpv), plus a speech model of **1.5–3.1 GB**
   on the first transcription, depending on the chosen accuracy.
2. Optionally verify the checksums – they must match the `KupcakeStudio-Setup-<version>.sha256` file in the
   release: `Get-FileHash .\KupcakeStudio-Setup-* -Algorithm SHA256` (PowerShell in the download folder).
3. Run `KupcakeStudio-Setup-<version>.exe` – it installs **without administrator rights**, for you only
   (`%LOCALAPPDATA%\Programs\KupcakeStudio`).

**Windows SmartScreen:** the installer isn't digitally signed yet, so Windows may show "Windows protected
your PC" on first launch. Click **More info → Run anyway**. Only do this for a file downloaded from this
repository's Releases with a matching SHA-256.

**Uninstalling:** Settings → Apps → kupcake.studio. The uninstaller asks whether to also delete the
downloaded models and settings; `.kupcake` projects and exported videos always stay.

## Licence

Copyright (C) 2026 Tomáš Kupec

The kupcake.studio source code is free software under the **GNU General Public License, version 3 only**
(`GPL-3.0-only`) – full text in [LICENSE](LICENSE). Every source file carries the copyright line and the
`SPDX-License-Identifier: GPL-3.0-only` header.

Additional permission (also in [ADDITIONAL_PERMISSION.md](ADDITIONAL_PERMISSION.md)):

> Additional permission under GNU GPL version 3 section 7: If you modify this Program, or any covered work, by linking or combining it with the NVIDIA CUDA and cuDNN runtime libraries or the Intel Math Kernel Library (or modified versions of those libraries), containing parts covered by the terms of their respective licenses, the licensors of this Program grant you additional permission to convey the resulting work.

**What the GPL does not cover** – these parts have their own terms:

- **third-party programs, libraries, fonts and models.** Each has its own licence. The list with exact
  versions is in [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md) (in Czech), full texts are in the
  `licenses/` folder (also bundled with the installation), and the complete list of bundled Python packages
  is in [licenses/PYTHON_PACKAGES.md](licenses/PYTHON_PACKAGES.md),
- in particular the **NVIDIA** (CUDA, cuDNN) and **Intel** (oneMKL, OpenMP) runtime libraries. They are
  proprietary, they are **not under the GPL** and may be used and redistributed only under their own licences,
- the **name kupcake.studio and the logo** (see the note at the top of this page).

**Source code of the bundled programs:** exact versions and links to the source code of FFmpeg, mpv, the
FFmpeg inside PyAV, Qt, Qt-ADS and LAME are in
[THIRD_PARTY_LICENSES.md, section 2](THIRD_PARTY_LICENSES.md#2-zdrojové-kódy-přibalených-programů).
I will provide the source code on request.

**Meta MMS model** (precise word timing for languages without their own model) is CC BY-NC 4.0 –
non-commercial use only. It is switched off by default; it can be turned on in Settings after confirming
the licence notice.

### Trademarks and patents

ProRes, TikTok, Instagram, YouTube, DaVinci Resolve, Premiere, CapCut, NVIDIA and other product names
mentioned here are trademarks of their respective owners. They are used only to describe compatibility;
kupcake.studio is not affiliated with, endorsed by or sponsored by any of them. The H.264, H.265 and AAC
codecs may be subject to patent licences in some countries.

## Features (version 1.0.0-beta.1)

- `.kupcake` projects (File → Save project, Ctrl+S / Ctrl+O, Recent projects, double-click the file),
  unsaved-changes warning, automatic save every 2 minutes and recovery after a crash (`projekt.py`),
- speech transcription on the GPU with per-word timing, speech language detected automatically or chosen
  manually (100 languages); during transcription and export a full-screen overlay with a filling cupcake,
  real progress, time estimate and a Cancel button (`prekryti.py`, progress also on the Windows taskbar),
- works without a graphics card too: `hardware.py` picks the GPU (float16 / int8_float16 depending on free
  VRAM) or the CPU, and falls back to the CPU when VRAM runs out; transcription accuracy large-v3 /
  large-v3-turbo / medium (`model.py`), time estimate before transcription; testing without a GPU:
  `set KUPCAKE_CPU=1`, then `run_dev.bat`,
- precise timing: aligning words to the audio (wav2vec2, `zarovnani.py`), optionally separating the voice
  from music (Demucs, `hlas.py`); subtitle offset and lead-in in Settings → Timing, Re-align selection
  (Ctrl+Shift+A),
- subtitle editor, word-level timeline (groups, cuts, ripple delete, loop, markers, J/K/L…;
  **F1** shows all shortcuts),
- style panel with live preview in the player and named presets (`presety.py`, `presety.json`
  in the settings folder); a dot next to a group shows that it differs from the preset,
- after export, a notification in the corner of the window with an Open folder button (`notifikace.py`),
- freely movable and detachable panels with saved layouts (see below),
- interface in 5 languages,
- export through a panel with options (`export_panel.py`, FFmpeg commands in `export.py`): video with
  burned-in subtitles (H.264/H.265 via NVENC or the CPU, MOV ProRes), subtitles as SRT/VTT/ASS, transparent
  subtitles (ProRes 4444 with alpha), presets for TikTok/Reels and YouTube, a video range, loudness
  normalisation,
- look in the brand colours with a cupcake in the logo and an animation while working (see below).

## Look

Everything is in `theme.py` – don't hard-code colours anywhere else. Background `#080808`, panels
`#111214`, borders `#1F2226`, text `#F2EFEA`, secondary text `#8A8F98`. The brand colours have two roles
that never mix:

- **blue `#00B4FF`** (`theme.AKCENT`) – selection and focus: selected words and rows, the active field, tabs,
  checkboxes and toggles,
- **orange `#FF6A00`** (`theme.AKCE`) – "now" and "action": the playhead, markers, loop, the Play button,
  the player's seek bar and time, the subtitle currently playing, spin box arrows, the snapping magnet,
  locks on the timeline, the line of the panel you're working in, the pulsing logo dot while processing,
  notifications and the main buttons (`objectName` `primary`: Export video, Save preset). Nowhere else.

Contrast: dark text on orange and orange text on the background are 7 : 1 (`theme.kontrast()`). The main
buttons are "pills" (`primary` orange, `sekundarni` outlined), panel headers are JetBrains Mono in capitals
with a blue dot.

The video area is a native window (mpv draws into it); `prehravac.py` therefore sets
`Qt.AA_DontCreateNativeWidgetSiblings`, otherwise Qt would make the controls next to it native as well and
they would stay in the old place when a panel is moved. Don't use graphics effects (`QGraphicsEffect`) –
glow is drawn in `paint()`/`paintEvent`.

The cupcake (icon, logo, animation) is drawn by **`kupcake.py`** – one drawing for everything, the chosen
variant is in `kupcake.VARIANTA`. `CupcakeAnimace` (the cherry bounces, blue sparkles flash around it,
1.2 s loop) sits next to the status text during transcription and export, in the empty preview and in About.
Icon: `python ikona/ikona.py nahledy` (drafts in `icon_drafts/`), `python ikona/ikona.py export C`
→ `kupcake.ico`.

The list of changes by version is in [CHANGELOG.md](CHANGELOG.md) (in Czech).

## How the app is made

I design kupcake.studio, decide how it works and looks, direct its development and test it myself. The code
is written with the help of an AI assistant (Claude Code).

## Development

- **`run_dev.bat`** – runs kupcake.studio straight from the source code. Just save changes in the `.py`
  files and start the app again, nothing is built. The console window shows any errors.
  You can pass a video directly: `run_dev.bat video.mp4`.
- The version run from source and the installed version share the same settings and model.
- Dependencies are in **`requirements.txt`** (new environment:
  `py -3.12 -m venv .venv` and `.venv\Scripts\python.exe -m pip install -r requirements.txt`).
- **libmpv** (the player) isn't in the repository – `libmpv-2.dll` is over 100 MB, more than GitHub allows.
  Download the archive `mpv-dev-x86_64-<date>-git-<hash>.7z` from
  [shinchiro/mpv-winbuild-cmake → Releases](https://github.com/shinchiro/mpv-winbuild-cmake/releases)
  and extract `libmpv-2.dll` into the `mpv\` folder. The app also starts from source without it, but the
  preview then shows single frames without playback (`nahled.py`); building the installer needs it.
  The released installer uses the build of 21 October 2026 (`mpv-dev-x86_64-20261021-git-e471496c56.7z`);
  if you bundle a different one, update its version and source link in `THIRD_PARTY_LICENSES.md`.
- **Licence list:** after changing dependencies (ideally after a build) run
  `.venv\Scripts\python.exe licenses\prenes_licence.py` – it regenerates
  `licenses/PYTHON_PACKAGES.md` and the licence texts in `licenses/python/` from what is really in the build.
  `nastroje\podminky_txt.py` turns `TERMS.cs.md` into the installer's terms page (`build.bat` runs it).
- **Security tests** in the `tests/` folder (downloads and redirects, model integrity, projects, FFmpeg,
  updates, privacy; they download nothing and don't touch the user's settings):
  `.venv\Scripts\python.exe -m unittest discover -s tests -v` (`python -m pytest tests` works too).
  Audit results and findings: [docs/BEZPECNOSTNI_AUDIT.md](docs/BEZPECNOSTNI_AUDIT.md) (in Czech).

## How to release a new version

1. Check the changes with `run_dev.bat`.
2. Run **`build.bat`** and enter the new version as `X.Y.Z` when asked
   (e.g. `1.0.1` – fixes, `1.1.0` – new features). Enter keeps the current one.
   Without asking: `build.bat 1.0.1`.
3. Wait about 10 minutes. The result in the `dist` folder: **`KupcakeStudio-Setup-X.Y.Z.exe`**, the parts
   `KupcakeStudio-Setup-X.Y.Z-1.bin`, `-2.bin` (each under 2 GB) and `KupcakeStudio-Setup-X.Y.Z.sha256`
   with the checksums of all files. `build.bat` lists them at the end.
4. Run the installer – it installs over the old version (also over Spellcast and tkStudio). Settings and the
   model stay.
5. Add what's new to `CHANGELOG.md`.
6. Push the changes to GitHub: `git add -A`, `git commit -m "Version X.Y.Z"`, `git push`.
7. On GitHub: **Releases → Draft a new release**, tag **`vX.Y.Z`** (the update check uses it to recognise
   a new version), description from `CHANGELOG.md`, and attach **all** files from step 3. Mark beta versions
   (`1.0.0-beta.2`) as **Set as a pre-release** – they are offered only to beta users, stable versions
   won't get them.

The version number lives only in **`version.py`** – `build.bat` writes it there and from there it goes into
the app (About), into `KupcakeStudio.exe` (Properties → Details) and into the installer name.

## Languages

The interface is available in Czech, English, German, Spanish and Slovak (**Settings → Language**,
switches immediately). On first launch the language follows Windows; an unsupported language = English.

### How to add a new language

1. Copy `locales\en.json` (or `cs.json`) as `locales\<code>.json` – ISO 639-1 code,
   e.g. `pl.json` for Polish.
2. At the top, set `"_jazyk"` to the language's own name (`"Polski"`) and `"_poradi"`
   to its position in the menu.
3. Translate the values (texts on the right). **Don't change the keys on the left** and keep
   `{parameters}` in curly braces, e.g. `"Words deleted: {n}"` → `"Usunięto słów: {n}"`. `&` in menu names
   marks the Alt+key letter.
4. Done – the new language appears in the menu by itself, no code changes needed. Missing texts are shown
   in Czech. For the installer run `build.bat` (the `locales` folder is bundled automatically).

The **speech** language for transcription is chosen separately after opening a video (the default is
automatic detection; the last choice is remembered).

## Panel layout

The Subtitles, Preview, Settings and Timeline panels can be grabbed by their header and dragged elsewhere
(Qt Advanced Docking System, `doky.py`; look in `theme.qss_doku()`):

- dropping on the edge of another panel = next to it, in the middle = as a tab, outside the window =
  a separate window (also on a second monitor; the ⧉ button in the header does the same),
- double-click a header = panel fills the whole window, another double-click restores the layout,
- **View → Panels** – show/hide individual panels (the cross in the header only hides the panel),
- **View → Saved layouts** – named layouts (e.g. "Timing", "Style"),
- **View → Lock layout** and **Restore default layout**.

The layout, including separate windows, is saved on close and restored on the next launch.
Third-party library licences: `THIRD_PARTY_LICENSES.md` and the `licenses` folder.

## Where things are

| What | Where |
|---|---|
| Installed app | `%LOCALAPPDATA%\Programs\KupcakeStudio` (since 1.6 without admin rights; up to 1.5 `C:\Program Files\KupcakeStudio`) |
| Settings (saved style) | `%APPDATA%\KupcakeStudio\styl.json` |
| Interface and speech language | `%APPDATA%\KupcakeStudio\aplikace.ini` |
| Window layout / saved layouts | `%APPDATA%\KupcakeStudio\rozlozeni.ini`, `rozvrzeni_vlastni.ini` |
| Speech model (~3 GB, downloaded on the first transcription) | `%LOCALAPPDATA%\KupcakeStudio\models` |
| Precise-timing models (~1.2 GB per language) and Demucs | `…\models\zarovnani`, `…\models\demucs` |
| Temporary files | `%LOCALAPPDATA%\KupcakeStudio\tmp` |

On first launch, settings, layout, style and the downloaded model are moved automatically from the
`tkStudio` and `Spellcast` folders (`cesty.migruj_stara_data`; if both exist, the newer tkStudio wins);
the `.migrace` marker in the settings makes sure it happens only once.

The installer has a fixed `AppId` (in `installer\KupcakeStudio.iss`) – **never change it**, otherwise a new
version would install next to the old one instead of over it. Thanks to it, a new version also replaces an
installed Spellcast or tkStudio (it removes the old folder, shortcuts and context menu entry).

## Tools needed to build

- `.venv` with Python 3.12 (already exists)
- FFmpeg in PATH – bundled into the app (`winget install Gyan.FFmpeg`)
- Inno Setup 6 – creates the installer (`winget install JRSoftware.InnoSetup`)
