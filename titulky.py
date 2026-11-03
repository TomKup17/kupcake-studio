"""Styl titulků, seskupení slov do titulků a generování ASS."""
import json
import os
import subprocess
from dataclasses import asdict, dataclass, field, fields

from cesty import vstup_ffmpeg

NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
MIN_SLOVO = 0.05  # nejkratší povolené slovo (s)
MIN_ZOBRAZENI = 0.12  # zvýraznění kratší než tohle neproblikne samo – slovo se zvýrazní spolu se sousedem


@dataclass
class Styl:
    # výchozí = profil podle Captions (žlutá Montserrat ExtraBold, černý rozmazaný stín)
    font: str = "Montserrat ExtraBold"
    tucne: bool = False
    velikost: float = 0.10          # velikost písma jako podíl šířky videa
    barva_textu: str = "F2EC3C"     # RRGGBB
    barva_obrysu: str = "000000"
    obrys: float = 0.0              # tloušťka obrysu jako podíl velikosti písma
    stin: bool = True
    barva_stinu: str = "000000"
    stin_rozmazani: int = 23        # stupnice Captions 0–100 (0 = ostrý stín)
    stin_x: int = 0                 # posun stínu v px při šířce videa 1080
    stin_y: int = 0
    pozadi: bool = False
    barva_pozadi: str = "000000"
    pruhlednost_pozadi: int = 40    # 0 = plné, 100 = neviditelné
    odsazeni_pozadi: float = 0.25   # odsazení textu od okraje pozadí jako podíl velikosti písma
    zvyrazneni: bool = False        # zvýraznit právě vyslovované slovo
    barva_zvyrazneni: str = "FFFFFF"
    pozice_y: float = 0.475         # svislá pozice středu (0 = nahoře, 1 = dole)
    velka_pismena: bool = True
    max_znaku: int = 15             # max. znaků na obrazovce
    max_slov: int = 0               # max. slov na obrazovce (0 = jen podle znaků)
    fade_in: int = 150              # ms
    fade_out: int = 100             # ms
    max_pauza: float = 0.6          # pauza v řeči (s), po které začne nový titulek
    posun_ms: int = 0               # globální posun všech titulků (+ = později) – opraví systematické zpoždění
    predstih_ms: int = 40           # slovo se ukáže o tolik dřív, než zazní (působí synchronněji; obvykle 30–50)

    def uloz(self, path):
        path.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=1), encoding="utf-8")

    @classmethod
    def nacti(cls, path):
        """Načte uložený styl; neznámé/chybějící klíče ignoruje, při chybě vrátí výchozí."""
        try:
            return cls.z_dict(json.loads(path.read_text(encoding="utf-8-sig")))  # snese i BOM
        except (OSError, ValueError):
            return cls()

    @classmethod
    def z_dict(cls, data):
        """Styl ze slovníku (styl.json, projekt); neznámé klíče a hodnoty špatného typu ignoruje."""
        vychozi = cls()
        hodnoty = {}
        for f in fields(cls):
            if isinstance(data, dict) and f.name in data:
                v, puvodni = data[f.name], getattr(vychozi, f.name)
                if isinstance(puvodni, float) and isinstance(v, int) and not isinstance(v, bool):
                    v = float(v)
                if type(v) is type(puvodni):
                    hodnoty[f.name] = v
        return cls(**hodnoty)


@dataclass(eq=False)
class Slovo:
    text: str
    start: float
    end: float


@dataclass(eq=False)
class Titulek:
    """Titulek je vidět od start do end. start = začátek prvního slova (hlídá srovnej),
    end >= konec posledního slova – rozdíl je „dozvuk“, po který titulek zůstane na obrazovce."""
    start: float
    end: float
    text: str
    slova: list = field(default_factory=list)
    zamceno: bool = False  # zamčený titulek nejde na ose ani v seznamu upravovat


@dataclass(eq=False)
class Znacka:
    """Značka na časové ose – poznámka v čase t (do videa se nevypaluje)."""
    t: float
    text: str = ""


def prepocitej_text(titulek):
    """Text titulku podle jeho slov (po úpravách slov na časové ose)."""
    titulek.text = " ".join(s.text for s in titulek.slova)


def rozdel_slova(text, start, end):
    """Slova bez známých časů rozprostře v intervalu úměrně jejich délce."""
    tokeny = text.split()
    if not tokeny:
        return []
    vahy = [len(t) + 1 for t in tokeny]
    celkem, t, slova = sum(vahy), start, []
    for tok, v in zip(tokeny, vahy):
        d = (end - start) * v / celkem
        slova.append(Slovo(tok, round(t, 3), round(t + d, 3)))
        t += d
    return slova


def nastav_text(titulek, text):
    """Nový text titulku. Při stejném počtu slov zůstanou jejich časy, jinak se rozprostřou."""
    titulek.text = text
    tokeny = text.split()
    if len(tokeny) == len(titulek.slova):
        for s, tok in zip(titulek.slova, tokeny):
            s.text = tok
    else:
        a = titulek.slova[0].start if titulek.slova else titulek.start
        b = titulek.slova[-1].end if titulek.slova else titulek.end
        titulek.slova = rozdel_slova(text, a, b)


def srovnej(titulky, delka=0.0):
    """Začátek titulku = první slovo, konec mezi koncem posledního slova a začátkem dalšího titulku."""
    for t in titulky:
        if t.slova:
            t.start = t.slova[0].start
    for i, t in enumerate(titulky):
        if t.slova:
            t.end = max(t.end, t.slova[-1].end)
        strop = titulky[i + 1].start if i + 1 < len(titulky) else (delka or t.end)
        dno = t.slova[-1].end if t.slova else t.start + MIN_SLOVO
        t.end = max(min(t.end, strop), dno)


def ass_barva(rrggbb, alpha=0):
    return f"&H{alpha:02X}{rrggbb[4:6]}{rrggbb[2:4]}{rrggbb[0:2]}"


def ass_barva_tag(rrggbb):
    return f"&H{rrggbb[4:6]}{rrggbb[2:4]}{rrggbb[0:2]}&"


def ass_cas(t):
    cs = int(round(max(t, 0) * 100))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def video_info(path):
    """(šířka, výška, délka v s) – šířka/výška po aplikaci rotace z metadat."""
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=width,height:stream_side_data=rotation:stream_tags=rotate:format=duration",
         "-of", "json", *vstup_ffmpeg(path, ffprobe=True)],
        check=True, capture_output=True, text=True, creationflags=NO_WINDOW).stdout
    data = json.loads(out)
    s = data["streams"][0]
    w, h = int(s["width"]), int(s["height"])
    rot = s.get("tags", {}).get("rotate")
    for sd in s.get("side_data_list", []):
        rot = sd.get("rotation", rot)
    if rot is not None and abs(int(float(rot))) % 180 == 90:
        w, h = h, w
    return w, h, float(data.get("format", {}).get("duration", 0) or 0)


def ma_zvuk(path):
    """Má video zvukovou stopu? (bez ní nejde přepis – titulky jen ručně)"""
    try:
        out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index",
                              "-of", "csv=p=0", *vstup_ffmpeg(path, ffprobe=True)],
                             check=True, capture_output=True, text=True, creationflags=NO_WINDOW).stdout
        return bool(out.strip())
    except (OSError, subprocess.CalledProcessError):
        return True  # nejde zjistit – zkusit přepis (případná chyba se ukáže tam)


def video_fps(path):
    """Snímková frekvence videa (pro posun o snímek a časový kód); při chybě 30."""
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=avg_frame_rate,r_frame_rate",
             "-of", "json", *vstup_ffmpeg(path, ffprobe=True)],
            check=True, capture_output=True, text=True, creationflags=NO_WINDOW).stdout
        s = json.loads(out)["streams"][0]
        for klic in ("avg_frame_rate", "r_frame_rate"):
            a, _, b = s.get(klic, "0/0").partition("/")
            if float(b or 1) and 1 <= float(a) / float(b or 1) <= 240:
                return float(a) / float(b or 1)
    except (OSError, ValueError, KeyError, IndexError, subprocess.CalledProcessError):
        pass
    return 30.0


def seskup(slova, styl):
    # časy slov z Whisperu se občas překrývají – na časové ose se slova překrývat nesmí
    upravena, konec = [], 0.0
    for w in slova:
        start = max(w["start"], konec)
        end = max(w["end"], start + MIN_SLOVO)
        upravena.append({"text": w["text"], "start": round(start, 3), "end": round(end, 3)})
        konec = end
    slova = upravena

    radky, cur = [], []
    for w in slova:
        text = " ".join(x["text"] for x in cur + [w])
        pauza = cur and w["start"] - cur[-1]["end"] > styl.max_pauza
        moc_slov = styl.max_slov and len(cur) >= styl.max_slov
        if cur and (len(text) > styl.max_znaku or pauza or moc_slov):
            radky.append(cur)
            cur = []
        cur.append(w)
        if w["text"][-1:] in ".!?":
            radky.append(cur)
            cur = []
    if cur:
        radky.append(cur)

    titulky = []
    for i, radek in enumerate(radky):
        start = radek[0]["start"]
        end = radek[-1]["end"] + 0.3
        if i + 1 < len(radky):
            end = min(end, radky[i + 1][0]["start"])
        end = max(end, start + 0.3)
        titulky.append(Titulek(start, end, " ".join(w["text"] for w in radek),
                               [Slovo(w["text"], w["start"], w["end"]) for w in radek]))
    srovnej(titulky)
    return titulky


def _escape(text):
    """Text titulku do ASS tak, aby libass nic z něj nebral jako příkaz:
    - „\\“ + neviditelný spojovač (U+2060) – jinak by „\\N“, „\\n“, „\\h“ z textu udělaly zalomení/mezeru,
    - „{“ „}“ jako „\\{“ „\\}“ – libass je vykreslí doslova, nezačne blok s příkazy,
    - skutečné zalomení řádku → „\\N“."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\\", "\\⁠").replace("{", "\\{").replace("}", "\\}")
    return text.replace("\n", "\\N")


def _skupiny_zvyrazneni(titulek):
    """Indexy slov po skupinách, které se zvýrazní najednou: slovo, které by bylo zvýrazněné kratší dobu
    než MIN_ZOBRAZENI (rychlá řeč), se spojí s dalším – zvýraznění pak skáče po dvou a neproblikává."""
    n, slova = len(titulek.slova), titulek.slova
    skupiny, k = [], 0
    while k < n:
        skupina = [k]
        while skupina[-1] + 1 < n:
            a = titulek.start if skupina[0] == 0 else slova[skupina[0]].start
            b = slova[skupina[-1] + 1].start
            if b - a >= MIN_ZOBRAZENI:
                break
            skupina.append(skupina[-1] + 1)
        skupiny.append(skupina)
        k = skupina[-1] + 1
    # poslední skupina trvá do konce titulku; kdyby byla i tak krátká, připojí se k předchozí
    if len(skupiny) > 1 and titulek.end - slova[skupiny[-1][0]].start < MIN_ZOBRAZENI:
        skupiny[-2] += skupiny.pop()
    return skupiny


def vyrez(titulky, od, do):
    """Kopie titulků pro úsek videa od–do: časy posunuté tak, aby úsek začínal v 0, titulky mimo úsek
    vynechané, zasahující oříznuté."""
    vysledek = []
    for t in titulky:
        if t.end <= od or t.start >= do:
            continue
        slova = [Slovo(s.text, max(s.start, od) - od, min(s.end, do) - od) for s in t.slova
                 if s.end > od and s.start < do]
        vysledek.append(Titulek(max(t.start, od) - od, min(t.end, do) - od, t.text, slova, t.zamceno))
    return vysledek


def _texty_titulku(titulky, styl):
    """(začátek, konec, text) pro textové formáty – s posunem a předstihem stylu, velkými písmeny podle stylu."""
    posun = (getattr(styl, "posun_ms", 0) - getattr(styl, "predstih_ms", 0)) / 1000
    for t in titulky:
        text = (t.text.upper() if styl.velka_pismena else t.text).replace("\r\n", "\n").replace("\r", "\n")
        # prázdný řádek by v SRT/VTT ukončil blok titulku – víc řádků zůstane, prázdné ne
        text = "\n".join(r.strip() for r in text.split("\n") if r.strip())
        if text:
            yield max(t.start + posun, 0), max(t.end + posun, 0), text


def _cas_textovy(t, oddelovac):
    ms = int(round(max(t, 0) * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d}{oddelovac}{ms % 1000:03d}"


def vytvor_srt(titulky, styl):
    """SubRip (.srt) – YouTube, Premiere, DaVinci Resolve, CapCut."""
    bloky = [f"{i}\n{_cas_textovy(a, ',')} --> {_cas_textovy(b, ',')}\n{text}\n"
             for i, (a, b, text) in enumerate(_texty_titulku(titulky, styl), 1)]
    return "\n".join(bloky)


def vytvor_vtt(titulky, styl):
    """WebVTT (.vtt) – web a YouTube."""
    def html(s):  # VTT text je HTML-like: „<“ by začalo značku, „-->“ by rozbilo blok
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    bloky = [f"{_cas_textovy(a, '.')} --> {_cas_textovy(b, '.')}\n{html(text)}\n"
             for a, b, text in _texty_titulku(titulky, styl)]
    return "WEBVTT\n\n" + "\n".join(bloky)


def vytvor_ass(titulky, styl, W, H, nahled=False):
    """nahled=True vynechá prolínání, aby byl titulek v náhledu vidět naplno."""
    size = round(W * styl.velikost)
    blur = styl.stin_rozmazani * W / 1080 * 0.6
    obrys = size * styl.obrys
    x, y = W // 2, round(H * styl.pozice_y)
    sx, sy = x + round(styl.stin_x * W / 1080), y + round(styl.stin_y * W / 1080)
    fad = "" if nahled else f"\\fad({styl.fade_in},{styl.fade_out})"
    bold = -1 if styl.tucne else 0
    okraj = round(W * 0.05)  # dlouhý text se zalomí 5 % od okrajů
    # pozadí = samostatná vrstva s BorderStyle 3 (obdélník), aby text mohl mít vlastní obrys
    alfa_pozadi = round(min(max(styl.pruhlednost_pozadi, 0), 100) * 2.55)
    odsazeni = size * styl.odsazeni_pozadi

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Text,{styl.font},{size},{ass_barva(styl.barva_textu)},&H000000FF,{ass_barva(styl.barva_obrysu)},&H00000000,{bold},0,0,0,100,100,0,0,1,{obrys:.1f},0,5,{okraj},{okraj},0,1
Style: Shadow,{styl.font},{size},{ass_barva(styl.barva_stinu)},&H000000FF,{ass_barva(styl.barva_stinu)},&H00000000,{bold},0,0,0,100,100,0,0,1,{max(1, size * 0.06) + obrys:.1f},0,5,{okraj},{okraj},0,1
Style: Box,{styl.font},{size},&HFF000000,&H000000FF,{ass_barva(styl.barva_pozadi, alfa_pozadi)},&HFF000000,{bold},0,0,0,100,100,0,0,3,{odsazeni:.1f},0,5,{okraj},{okraj},0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    def uprav(s):
        return _escape(s.upper() if styl.velka_pismena else s)

    # časy slov jsou skutečné (kdy zazní); na obrazovce se posunou o globální posun a o předstih
    posun = (getattr(styl, "posun_ms", 0) - getattr(styl, "predstih_ms", 0)) / 1000

    def cas(s):
        return ass_cas(s + posun)

    events = []
    for t in titulky:
        po_slovech = styl.zvyrazneni and t.slova
        slova = [uprav(s.text) for s in t.slova] if po_slovech else []
        text = " ".join(slova) if po_slovech else uprav(t.text)
        if not text.strip():
            continue
        if styl.pozadi:
            events.append(f"Dialogue: 0,{cas(t.start)},{cas(t.end)},Box,,0,0,0,,"
                          f"{{\\pos({x},{y}){fad}}}{text}")
        if styl.stin:
            events.append(f"Dialogue: 1,{cas(t.start)},{cas(t.end)},Shadow,,0,0,0,,"
                          f"{{\\pos({sx},{sy}){fad}\\blur{blur:.1f}\\alpha&H40&}}{text}")
        if not po_slovech:
            events.append(f"Dialogue: 2,{cas(t.start)},{cas(t.end)},Text,,0,0,0,,"
                          f"{{\\pos({x},{y}){fad}}}{text}")
            continue
        # zvýraznění: textová vrstva se rozdělí na úseky, v každém má jiná slova barvu zvýraznění;
        # prolínání jen na začátku prvního a konci posledního úseku, ať text nebliká
        hl, zpet = ass_barva_tag(styl.barva_zvyrazneni), ass_barva_tag(styl.barva_textu)
        n = len(t.slova)
        for skupina in _skupiny_zvyrazneni(t):
            k0, k1 = skupina[0], skupina[-1]
            a = t.start if k0 == 0 else t.slova[k0].start
            b = t.end if k1 == n - 1 else t.slova[k1 + 1].start
            if cas(b) <= cas(a):
                continue
            casti = [f"{{\\c{hl}}}{w}{{\\c{zpet}}}" if j in skupina else w for j, w in enumerate(slova)]
            f = "" if nahled else (f"\\fad({styl.fade_in if k0 == 0 else 0},"
                                   f"{styl.fade_out if k1 == n - 1 else 0})")
            events.append(f"Dialogue: 2,{cas(a)},{cas(b)},Text,,0,0,0,,"
                          f"{{\\pos({x},{y}){f}}}{' '.join(casti)}")
    return header + "\n".join(events) + "\n"
