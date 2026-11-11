# kupcake.studio – Copyright (C) 2026 Tomáš Kupec
# SPDX-License-Identifier: GPL-3.0-only
"""Živý náhled: snímek z videa + titulek vykreslený přes libass (stejně jako při exportu)."""
import subprocess

from cesty import DATA_DIR, TMP_DIR, vstup_ffmpeg
from export import NO_WINDOW
from titulky import Titulek, vytvor_ass

MAX_VYSKA = 1280  # náhled stačí zmenšený; libass škáluje ASS podle PlayRes sám
_snimek_klic = None


def _velikost(W, H):
    if H <= MAX_VYSKA:
        return W, H
    return round(W * MAX_VYSKA / H / 2) * 2, MAX_VYSKA


def vykresli(video, t, text, styl, W, H, delka):
    """Vrátí BMP data náhledu v čase t s textem `text` ve stylu `styl`."""
    global _snimek_klic
    tmp = TMP_DIR
    tmp.mkdir(parents=True, exist_ok=True)
    src = tmp / "nahled_snimek.bmp"
    w, h = _velikost(W, H)

    t = min(max(t, 0.0), max(delka - 0.1, 0.0))
    klic = (str(video), round(t, 2), w, h)
    if klic != _snimek_klic or not src.exists():
        subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", *vstup_ffmpeg(video),
             "-frames:v", "1", "-vf", f"scale={w}:{h}", "-update", "1", str(src)],
            check=True, capture_output=True, creationflags=NO_WINDOW)
        _snimek_klic = klic

    ass = vytvor_ass([Titulek(0, 3600, text)], styl, W, H, nahled=True) if text.strip() else ""
    if not ass:
        return src.read_bytes()
    (tmp / "nahled.ass").write_text(ass, encoding="utf-8-sig")
    return subprocess.run(
        ["ffmpeg", "-v", "error", "-i", "tmp/nahled_snimek.bmp",
         "-vf", "subtitles=filename=tmp/nahled.ass:fontsdir=fonts",
         "-frames:v", "1", "-f", "image2pipe", "-c:v", "bmp", "-"],
        check=True, capture_output=True, cwd=DATA_DIR, creationflags=NO_WINDOW).stdout
