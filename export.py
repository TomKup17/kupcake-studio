"""Export přes FFmpeg: video s vypálenými titulky (H.264 / H.265 / MOV ProRes), průhledné titulky
(MOV ProRes 4444 s alfa kanálem) a titulky jako soubor (SRT / VTT / ASS – zapisuje je main.py).

Volby exportu nese dataclass Volby (pamatuje si je aplikace); sestav_prikaz() z nich udělá příkaz FFmpeg.
"""
import os
import subprocess
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from cesty import DATA_DIR, TMP_DIR, vstup_ffmpeg
from i18n import t

NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

PRESETY = {"vertikalni": (1080, 1920), "youtube": (1920, 1080)}  # TikTok/Reels/Shorts, YouTube
ROZLISENI = (2160, 1080, 720)          # kratší strana: 4K, 1080p, 720p
FPS = (30, 60)
# kvalita → nastavení kodéru (NVENC cq / x264+x265 crf / profil ProRes)
KVALITA = {
    "h264_nvenc": {"vysoka": 19, "standardni": 23, "maly": 28},
    "libx264": {"vysoka": 18, "standardni": 22, "maly": 27},
    "hevc_nvenc": {"vysoka": 21, "standardni": 26, "maly": 31},
    "libx265": {"vysoka": 20, "standardni": 25, "maly": 30},
    "prores_ks": {"vysoka": 3, "standardni": 2, "maly": 1},   # 422 HQ / 422 / 422 LT
}
# odhad velikosti: bity na pixel a snímek (hrubý průměr pro běžná videa s titulky)
BPP = {"h264": {"vysoka": 0.11, "standardni": 0.07, "maly": 0.04},
       "h265": {"vysoka": 0.066, "standardni": 0.042, "maly": 0.024},
       "mov": {"vysoka": 3.54, "standardni": 2.36, "maly": 1.64},
       "pruhledne": 1.2}  # ProRes 4444 – průhledné snímky se komprimují dobře
ZVUK_BPS = 192_000
PRIPONY = {"h264": ".mp4", "h265": ".mp4", "mov": ".mov", "pruhledne": ".mov",
           "srt": ".srt", "vtt": ".vtt", "ass": ".ass"}


@dataclass
class Volby:
    co: str = "video"             # video | titulky | pruhledne
    preset: str = "original"      # original | vertikalni | youtube | vlastni
    pomer: str = "okraje"         # poměr stran neodpovídá presetu: okraje | puvodni
    format: str = "h264"          # h264 | h265 | mov
    rozliseni: str = "original"   # original | 2160 | 1080 | 720 (kratší strana)
    kvalita: str = "vysoka"       # vysoka | standardni | maly
    fps: str = "original"         # original | 30 | 60
    zvuk: str = "zachovat"        # zachovat | bez
    normalizace: bool = False     # sjednotit hlasitost pro sociální sítě (−14 LUFS)
    rozsah: str = "cele"          # cele | usek (smyčka nebo výběr na ose)
    nvenc: bool = True
    format_titulku: str = "srt"   # srt | vtt | ass
    otevrit_slozku: bool = False
    slozka: str = ""

    @classmethod
    def z_dict(cls, data):
        znama = {f.name: f.type for f in fields(cls)}
        vychozi = cls()
        hodnoty = {}
        for k, v in (data or {}).items():
            if k in znama and isinstance(v, type(getattr(vychozi, k))):
                hodnoty[k] = v
        return cls(**hodnoty)

    def jako_dict(self):
        return asdict(self)

    def pripona(self):
        if self.co == "titulky":
            return PRIPONY[self.format_titulku]
        return PRIPONY["pruhledne" if self.co == "pruhledne" else self.format]


class PrepisZdroje(RuntimeError):
    """Výstup by přepsal zdrojové video – export se nesmí spustit."""


def je_stejny_soubor(a, b):
    """Jde o tentýž soubor? Nejen stejný zápis cesty: i jiná velikost písmen, relativní cesta, zkrácený název
    (VIDEO~1.MP4), hardlink nebo jiná cesta přes připojenou jednotku (os.path.samefile)."""
    a, b = Path(a), Path(b)
    try:
        if a.resolve() == b.resolve():
            return True
    except OSError:
        pass
    try:
        return a.exists() and b.exists() and os.path.samefile(a, b)
    except OSError:
        return False


def _sude(x):
    return max(2, int(round(x / 2)) * 2)


def pomer_sedi(volby, W, H):
    """Odpovídá poměr stran videa zvolenému presetu (TikTok / YouTube)?"""
    if volby.preset not in PRESETY:
        return True
    bw, bh = PRESETY[volby.preset]
    return abs(W / H - bw / bh) < 0.01


def rozmery(volby, W, H):
    """(šířka, výška výstupu, šířka, výška obrazu videa v něm). Obraz je menší než výstup jen s okraji."""
    if volby.preset in PRESETY:
        bw, bh = PRESETY[volby.preset]
        if pomer_sedi(volby, W, H):
            return bw, bh, bw, bh
        k = min(bw / W, bh / H)
        vw, vh = _sude(W * k), _sude(H * k)
        return (bw, bh, vw, vh) if volby.pomer == "okraje" else (vw, vh, vw, vh)
    if volby.preset == "vlastni" and volby.rozliseni != "original":
        k = min(int(volby.rozliseni) / min(W, H), 1.0)  # nikdy nezvětšovat
        return _sude(W * k), _sude(H * k), _sude(W * k), _sude(H * k)
    return W, H, W, H


def vystupni_fps(volby, fps_zdroj):
    if volby.preset == "vlastni" and volby.fps != "original":
        return float(volby.fps)
    return fps_zdroj


_nvenc = {}


def nvenc_dostupny(kodek="h264_nvenc"):
    """Umí tenhle počítač kódovat na grafické kartě? (krátký zkušební běh, výsledek se pamatuje)
    KUPCAKE_CPU=1 předstírá počítač bez NVIDIA karty (viz hardware.py)."""
    import hardware
    if hardware.vynuceny_procesor():
        return False
    if kodek not in _nvenc:
        try:
            r = subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=s=256x256:d=0.1", "-c:v", kodek,
                                "-f", "null", "-"], capture_output=True, timeout=20, creationflags=NO_WINDOW)
            _nvenc[kodek] = r.returncode == 0
        except (OSError, subprocess.SubprocessError):
            _nvenc[kodek] = False
    return _nvenc[kodek]


def kodek(volby):
    """Jméno kodéru FFmpeg podle formátu a NVENC (ProRes je vždy na procesoru)."""
    if volby.co == "pruhledne" or volby.format == "mov":
        return "prores_ks"
    gpu = {"h264": "h264_nvenc", "h265": "hevc_nvenc"}[volby.format]
    if volby.nvenc and nvenc_dostupny(gpu):
        return gpu
    return {"h264": "libx264", "h265": "libx265"}[volby.format]


def _argumenty_kodeku(volby, jmeno):
    q = KVALITA[jmeno][volby.kvalita]
    if jmeno == "prores_ks":
        if volby.co == "pruhledne":
            return ["-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le", "-vendor", "apl0"]
        return ["-c:v", "prores_ks", "-profile:v", str(q), "-pix_fmt", "yuv422p10le", "-vendor", "apl0"]
    if jmeno.endswith("_nvenc"):
        a = ["-c:v", jmeno, "-preset", "p5", "-tune", "hq", "-rc", "vbr", "-cq", str(q), "-b:v", "0"]
    else:
        a = ["-c:v", jmeno, "-preset", "medium", "-crf", str(q)]
    a += ["-pix_fmt", "yuv420p"]
    if volby.format == "h265":
        a += ["-tag:v", "hvc1"]  # přehraje se i v QuickTime / na iPhonu
    return a


def odhad_velikosti(volby, W, H, fps_zdroj, delka):
    """Odhad velikosti výstupu v bajtech (jen orientačně)."""
    if volby.co == "titulky":
        return None
    ow, oh, vw, vh = rozmery(volby, W, H)
    w, h = (ow, oh) if volby.co == "pruhledne" else (vw, vh)  # černé okraje se zkomprimují skoro na nic
    fps = vystupni_fps(volby, fps_zdroj)
    bpp = BPP["pruhledne"] if volby.co == "pruhledne" else BPP[volby.format][volby.kvalita]
    zvuk = ZVUK_BPS if volby.co == "video" and volby.zvuk == "zachovat" else 0
    return (bpp * w * h * fps + zvuk) / 8 * delka


def sestav_prikaz(volby, video, vystup, info, fps_zdroj, rozsah=None):
    """Příkaz FFmpeg (spouští se s cwd=DATA_DIR, titulky leží v tmp/titulky.ass).
    info = (W, H, délka) zdroje, rozsah = (od, do) nebo None = celé video."""
    W, H, delka = info
    ow, oh, vw, vh = rozmery(volby, W, H)
    fps = vystupni_fps(volby, fps_zdroj)
    od, do = rozsah if rozsah else (0.0, delka)
    sub = "subtitles=filename=tmp/titulky.ass:fontsdir=fonts"
    cmd = ["ffmpeg", "-y", "-hide_banner", "-v", "error", "-nostats", "-progress", "pipe:1"]
    if volby.co == "pruhledne":
        cmd += ["-f", "lavfi", "-i", f"color=c=black@0.0:s={ow}x{oh}:r={fps:.6g}:d={do - od:.3f},format=rgba",
                "-vf", sub + ":alpha=1"]
        cmd += _argumenty_kodeku(volby, "prores_ks") + ["-an", str(vystup)]
        return cmd
    if rozsah:
        cmd += ["-ss", f"{od:.3f}", "-t", f"{do - od:.3f}"]
    cmd += vstup_ffmpeg(video) + ["-map", "0:v:0"]
    filtry = []
    if (vw, vh) != (W, H):
        filtry += [f"scale={vw}:{vh}:flags=lanczos", "setsar=1"]
    if (ow, oh) != (vw, vh):
        filtry.append(f"pad={ow}:{oh}:(ow-iw)/2:(oh-ih)/2:color=black")
    filtry.append(sub)
    jmeno = kodek(volby)
    cmd += ["-vf", ",".join(filtry)]
    if fps != fps_zdroj:
        cmd += ["-r", f"{fps:.6g}"]
    cmd += _argumenty_kodeku(volby, jmeno)
    if volby.zvuk == "zachovat":
        cmd += ["-map", "0:a:0?", "-c:a", "aac", "-b:a", "192k"]
        if volby.normalizace:
            cmd += ["-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000"]  # loudnorm jinak vrací 192 kHz
    else:
        cmd += ["-an"]
    if Path(vystup).suffix.lower() == ".mp4":
        cmd += ["-movflags", "+faststart"]
    return cmd + [str(vystup)]


class Export:
    def __init__(self):
        self.proc = None
        self.zruseno = False

    def zrus(self):
        self.zruseno = True
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()

    def vypal(self, video, ass_text, vystup, delka, progress=lambda p: None, volby=None, info=None,
              fps_zdroj=30.0, rozsah=None):
        """delka = délka výstupu (pro průběh). Bez voleb: původní rozlišení, H.264 (NVENC), zvuk AAC."""
        video, vystup = Path(video).resolve(), Path(vystup).resolve()  # ffmpeg běží s cwd=DATA_DIR
        if je_stejny_soubor(video, vystup):  # poslední pojistka – FFmpeg s -y by zdroj přepsal
            raise PrepisZdroje(t("export.prepis_puvodni"))
        tmp = TMP_DIR
        tmp.mkdir(parents=True, exist_ok=True)
        (tmp / "titulky.ass").write_text(ass_text, encoding="utf-8-sig")
        volby = volby or Volby()
        if info is None:
            from titulky import video_info
            info = video_info(video)
        cmd = sestav_prikaz(volby, video, vystup, info, fps_zdroj, rozsah)
        err_path = tmp / "ffmpeg.log"
        with open(err_path, "w", encoding="utf-8", errors="replace") as err:
            self.proc = subprocess.Popen(cmd, cwd=DATA_DIR, stdout=subprocess.PIPE, stderr=err,
                                         text=True, creationflags=NO_WINDOW)
            for line in self.proc.stdout:
                if line.startswith("out_time_us=") and delka > 0:
                    try:
                        progress(min(int(line.split("=")[1]) / 1e6 / delka, 1.0))
                    except ValueError:
                        pass
            self.proc.wait()
        if self.zruseno:
            Path(vystup).unlink(missing_ok=True)
            raise RuntimeError(t("export.zrusen"))
        if self.proc.returncode != 0:
            chyba = err_path.read_text(encoding="utf-8", errors="replace").strip()
            raise RuntimeError(chyba[-1500:] or t("export.ffmpeg_kod", kod=self.proc.returncode))
        progress(1.0)
