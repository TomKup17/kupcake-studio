"""Bezpečné stahování modelů: jen HTTPS z oficiálních zdrojů (huggingface.co, dl.fbaipublicfiles.com),
pevná revize z manifest_modelu.py, kontrola velikosti a SHA-256 každého souboru. Soubor, který nesedí,
se smaže a uživatel dostane srozumitelnou chybu.

Nic se nestáhne bez vědomí uživatele: před každým stahováním se volá souhlas (aplikace ukáže dotaz
s názvem, velikostí a zdrojem); bez souhlasu stahování skončí výjimkou Odmitnuto.

Síť: každá adresa (i každé přesměrování) musí být HTTPS na hostitele ze seznamu HOSTY / HOSTY_PRESMEROVANI
(Hugging Face přesměrovává na své CDN *.hf.co). IP adresy, localhost, jiné porty a cizí domény se odmítnou
ještě před připojením; certifikát serveru ověřuje standardní knihovna (ssl.create_default_context) – podvržená
DNS odpověď (DNS rebinding) tak nepomůže, protože útočník nemá platný certifikát pro povolený hostitel.

Ověřené soubory: značka .hotovo nese revizi a otisk (velikost + čas změny) každého ověřeného souboru.
Změní-li se otisk (soubor přepsaný, poškozený, nahrazený), model se při příštím použití znovu ověří SHA-256.
"""
import hashlib
import ipaddress
import json
import logging
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from cesty import NAZEV, VERZE
from i18n import t
from manifest_modelu import DEMUCS, HUGGINGFACE

_log = logging.getLogger("kupcake").info  # výchozí log: do souboru (logy.py)
HOSTY = ("huggingface.co", "dl.fbaipublicfiles.com")  # odkud smí stahování začít
# kam smí vést přesměrování: přesné názvy a přípony domén (Hugging Face CDN: cdn-lfs.hf.co, cas-bridge.xethub.hf.co…)
HOSTY_PRESMEROVANI = HOSTY + (".huggingface.co", ".hf.co")
MAX_PRESMEROVANI = 5
BLOK = 1 << 20
ZNACKA = ".hotovo"   # JSON {"revize": …, "soubory": {jméno: [velikost, mtime_ns]}} – stažené a ověřené soubory


class ChybaOvereni(RuntimeError):
    """Stažený soubor nemá očekávanou velikost nebo SHA-256 (poškozený nebo podvržený), nebo adresa není povolená."""


class Odmitnuto(RuntimeError):
    """Uživatel stažení nepovolil."""


# ---------- souhlas ----------
_souhlas = None


def nastav_souhlas(fn):
    """fn(popis, velikost_bajtu, zdroj) → bool. Aplikace ho nastaví při startu (dotaz v hlavním vlákně)."""
    global _souhlas
    _souhlas = fn


def over_misto(slozka, potreba):
    """Před stahováním: vejde se to na disk (+ 300 MB rezerva)? Jinak srozumitelná chyba místo půlky souboru."""
    import shutil
    slozka = Path(slozka)
    while not slozka.exists() and slozka.parent != slozka:
        slozka = slozka.parent
    volno = shutil.disk_usage(slozka).free
    if volno < potreba + 300 * 2**20:
        raise RuntimeError(t("chyba.misto_model", potreba=f"{(potreba + 300 * 2**20) / 1e9:.1f}",
                             volno=f"{volno / 1e9:.1f}", slozka=str(slozka)))


def zeptej_se(popis, velikost, zdroj):
    if _souhlas is not None and not _souhlas(popis, velikost, zdroj):
        raise Odmitnuto(t("stahovani.odmitnuto", co=popis))


# ---------- HTTPS ----------
def _host_povolen(host, presmerovani):
    povolene = HOSTY_PRESMEROVANI if presmerovani else HOSTY
    return any(host == p or (p.startswith(".") and host.endswith(p) and len(host) > len(p)) for p in povolene)


def over_url(url, presmerovani=False):
    """Vrátí url, když je bezpečná: https, bez uživatele a hesla, jen port 443, hostitel ze seznamu (ne IP adresa,
    ne localhost, ne interní služba). Jinak ChybaOvereni. presmerovani=True povolí i CDN Hugging Face."""
    try:
        cast = urllib.parse.urlsplit(str(url))
        host, port = cast.hostname, cast.port
    except ValueError:
        raise ChybaOvereni(t("stahovani.neni_https", url=url)) from None
    if cast.scheme != "https" or not host or cast.username is not None or cast.password is not None \
            or port not in (None, 443):
        raise ChybaOvereni(t("stahovani.neni_https", url=url))
    try:
        ipaddress.ip_address(host.strip("[]"))
        je_ip = True
    except ValueError:
        je_ip = False
    if je_ip or host == "localhost" or host.endswith(".localhost") or not _host_povolen(host, presmerovani):
        raise ChybaOvereni(t("stahovani.neni_https", url=url))
    return url


class _JenHttps(urllib.request.HTTPRedirectHandler):
    """Přesměrování (Hugging Face → CDN) jen na HTTPS a jen na povolené hostitele, nejvýš MAX_PRESMEROVANI."""
    max_redirections = MAX_PRESMEROVANI

    def redirect_request(self, req, fp, code, msg, headers, novy_url):
        over_url(novy_url, presmerovani=True)
        return super().redirect_request(req, fp, code, msg, headers, novy_url)


_kontext = ssl.create_default_context()  # ověření certifikátu i názvu hostitele (výchozí, tady výslovně)
_otevirac = urllib.request.build_opener(urllib.request.HTTPSHandler(context=_kontext), _JenHttps())
_otevirac.handle_open.pop("http", None)   # nešifrované http se nepoužije ani omylem
_otevirac.handle_open.pop("ftp", None)
_otevirac.handle_open.pop("file", None)
_otevirac.handle_open.pop("data", None)


def _otevri(url, od=0):
    over_url(url)
    hlavicky = {"User-Agent": f"{NAZEV}/{VERZE}"}
    if od:
        hlavicky["Range"] = f"bytes={od}-"
    return _otevirac.open(urllib.request.Request(url, headers=hlavicky), timeout=60)


# ---------- ověření ----------
def sha256(cesta, prubeh=None):
    h = hashlib.sha256()
    with open(cesta, "rb") as f:
        while blok := f.read(BLOK * 8):
            h.update(blok)
            if prubeh:
                prubeh(len(blok))
    return h.hexdigest()


def _over(cesta, velikost, soucet, jmeno, prubeh=None):
    """Při neshodě soubor smaže a vyhodí ChybaOvereni."""
    if cesta.stat().st_size != velikost or sha256(cesta, prubeh) != soucet:
        cesta.unlink(missing_ok=True)
        raise ChybaOvereni(t("stahovani.neshoda", soubor=jmeno))


def _otisk(cesta):
    s = Path(cesta).stat()
    return [s.st_size, s.st_mtime_ns]


def _zapis_znacku(slozka, data, soubory):
    """Značka .hotovo: co bylo ověřeno (revize / SHA-256) a otisk každého ověřeného souboru."""
    data = dict(data, soubory={f: _otisk(Path(slozka) / f) for f in soubory})
    (Path(slozka) / ZNACKA).write_text(json.dumps(data), encoding="utf-8")


def _znacka(slozka):
    try:
        data = json.loads((Path(slozka) / ZNACKA).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _overeno(slozka, znacka, soubory):
    """Soubory mají stejný otisk jako při ověření (značka bez otisků = starší verze → ověřit znovu)."""
    otisky = znacka.get("soubory")
    if not isinstance(otisky, dict):
        return False
    try:
        return all((Path(slozka) / f).is_file() and otisky.get(f) == _otisk(Path(slozka) / f) for f in soubory)
    except OSError:
        return False


class Ukazatel:
    """Průběh v bajtech → progress (0–1) a zpráva do logu, nejvýš ~4× za sekundu."""

    def __init__(self, celkem, klic, progress, log):
        self.celkem, self.klic, self.progress, self.log = max(celkem, 1), klic, progress, log
        self.hotovo, self.posledne, self.start = 0, 0.0, time.time()

    def pridej(self, n, vynutit=False):
        self.hotovo += n
        ted = time.time()
        if vynutit or ted - self.posledne > 0.25:
            self.posledne = ted
            rychlost = self.hotovo / max(ted - self.start, 0.001) / 1e6
            self.progress(min(self.hotovo / self.celkem, 1.0))
            self.log(t(self.klic, hotovo=self.hotovo / 1e9, celkem=self.celkem / 1e9,
                       podil=self.hotovo / self.celkem, rychlost=rychlost))


def _delka_podle_serveru(r, od):
    """Celková velikost souboru, jak ji hlásí server (Content-Length / Content-Range), nebo None."""
    try:
        if r.status == 206:
            rozsah = r.headers.get("Content-Range", "")
            return int(rozsah.rsplit("/", 1)[1]) if "/" in rozsah and rozsah.rsplit("/", 1)[1] != "*" else None
        delka = r.headers.get("Content-Length")
        return int(delka) if delka is not None else None
    except (ValueError, IndexError):
        return None


def stahni_soubor(url, cil, velikost, soucet, ukazatel):
    """Stáhne url do cil přes cil.part (přerušené stahování naváže) a ověří velikost a SHA-256.
    Soubor jiné velikosti, než říká manifest, se odmítne hned podle hlavičky serveru – ne až po stažení."""
    cil = Path(cil)
    docasny = cil.with_name(cil.name + ".part")
    od = docasny.stat().st_size if docasny.exists() else 0
    if od > velikost:  # nesmysl z dřívějška
        docasny.unlink()
        od = 0
    if od < velikost:
        with _otevri(url, od) as r:
            if od and r.status != 206:  # server navázání nepodporuje → od začátku
                od = 0
            celkem = _delka_podle_serveru(r, od)
            if celkem is not None and celkem != velikost:
                docasny.unlink(missing_ok=True)
                raise ChybaOvereni(t("stahovani.neshoda", soubor=cil.name))
            ukazatel.pridej(od)
            with open(docasny, "ab" if od else "wb") as dst:
                while blok := r.read(BLOK):
                    dst.write(blok)
                    ukazatel.pridej(len(blok))
                    if dst.tell() > velikost:
                        break
    else:
        ukazatel.pridej(od)
    _over(docasny, velikost, soucet, cil.name)
    docasny.replace(cil)


# ---------- modely z Hugging Face ----------
def je_pripraveno(repo, cil):
    m = HUGGINGFACE[repo]
    cil = Path(cil)
    znacka = _znacka(cil)
    return znacka.get("revize") == m["revize"] and _overeno(cil, znacka, m["soubory"]) and all(
        (cil / f).stat().st_size == v for f, (v, _) in m["soubory"].items())


def je_stazeno(repo, cil):
    """Všechny soubory leží na disku ve správné velikosti (ověření SHA-256 může ještě chybět – je_pripraveno)."""
    cil = Path(cil)
    return all((cil / f).is_file() and (cil / f).stat().st_size == v for f, (v, _) in HUGGINGFACE[repo]["soubory"].items())


def velikost_repa(repo):
    return sum(v for v, _ in HUGGINGFACE[repo]["soubory"].values())


def priprav_repo(repo, cil, popis, progress=lambda p: None, log=_log):
    """Soubory modelu v pevné revizi do složky cil. Co už je stažené, se jen ověří (jednou – pak značka s otiskem)."""
    m = HUGGINGFACE[repo]
    cil = Path(cil)
    if je_pripraveno(repo, cil):
        return cil
    cil.mkdir(parents=True, exist_ok=True)
    (cil / ZNACKA).unlink(missing_ok=True)
    chybi = {f: vs for f, vs in m["soubory"].items() if not (cil / f).is_file() or (cil / f).stat().st_size != vs[0]}
    if chybi:
        over_misto(cil, sum(v for v, _ in chybi.values()))
        zeptej_se(popis, sum(v for v, _ in chybi.values()), "huggingface.co")
    # soubory z dřívějška (bez značky nebo se změněným otiskem) – ověřit, co nesedí, smazat a stáhnout znovu
    ukazatel = Ukazatel(velikost_repa(repo), "model.stahuji" if chybi else "stahovani.overuji", progress, log)
    for f, (velikost, soucet) in m["soubory"].items():
        soubor = cil / f
        if f not in chybi:
            try:
                _over(soubor, velikost, soucet, f, ukazatel.pridej)
                continue
            except ChybaOvereni:
                ukazatel.hotovo -= velikost  # stáhne se znovu
                zeptej_se(popis, velikost, "huggingface.co")
        url = f"https://huggingface.co/{repo}/resolve/{m['revize']}/{urllib.parse.quote(f)}"
        try:
            stahni_soubor(url, soubor, velikost, soucet, ukazatel)
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            raise RuntimeError(t("model.chyba_stazeni", chyba=e)) from e
    ukazatel.pridej(0, vynutit=True)
    _zapis_znacku(cil, {"repo": repo, "revize": m["revize"]}, m["soubory"])
    return cil


def kopiruj_overene(zdroj, repo, cil, progress=lambda p: None, log=_log):
    """Model z cache Hugging Face → cil; každý soubor se při kopírování ověří proti manifestu.
    Vrátí False, když cache neodpovídá (pak se model stáhne)."""
    m = HUGGINGFACE[repo]
    zdroj, cil = Path(zdroj), Path(cil)
    if any(not (zdroj / f).is_file() or (zdroj / f).stat().st_size != v for f, (v, _) in m["soubory"].items()):
        return False
    cil.mkdir(parents=True, exist_ok=True)
    ukazatel = Ukazatel(velikost_repa(repo), "model.kopiruji", progress, log)
    for f, (velikost, soucet) in m["soubory"].items():
        docasny = cil / (f + ".part")
        h = hashlib.sha256()
        with open(zdroj / f, "rb") as src, open(docasny, "wb") as dst:
            while blok := src.read(BLOK * 8):
                h.update(blok)
                dst.write(blok)
                ukazatel.pridej(len(blok))
        if h.hexdigest() != soucet:
            docasny.unlink(missing_ok=True)
            return False
        docasny.replace(cil / f)
    _zapis_znacku(cil, {"repo": repo, "revize": m["revize"]}, m["soubory"])
    return True


# ---------- Demucs ----------
def priprav_demucs(slozka, popis, log=_log):
    """Váhy Demucs htdemucs (oficiální úložiště Meta) – stažené a ověřené SHA-256. Vrátí cestu k souboru.
    Už ověřený soubor se znovu nehashuje, dokud sedí jeho otisk ve značce (velikost + čas změny)."""
    over_url(DEMUCS["url"])
    slozka = Path(slozka)
    cil = slozka / DEMUCS["url"].rsplit("/", 1)[1]
    znacka = _znacka(slozka)
    if cil.is_file() and znacka.get("sha256") == DEMUCS["sha256"] and _overeno(slozka, znacka, [cil.name]) \
            and cil.stat().st_size == DEMUCS["velikost"]:
        return cil
    slozka.mkdir(parents=True, exist_ok=True)
    (slozka / ZNACKA).unlink(missing_ok=True)
    if cil.is_file():
        try:
            _over(cil, DEMUCS["velikost"], DEMUCS["sha256"], cil.name)
            _zapis_znacku(slozka, {"sha256": DEMUCS["sha256"]}, [cil.name])
            return cil
        except ChybaOvereni:
            pass
    over_misto(slozka, DEMUCS["velikost"])
    zeptej_se(popis, DEMUCS["velikost"], "dl.fbaipublicfiles.com")
    try:
        stahni_soubor(DEMUCS["url"], cil, DEMUCS["velikost"], DEMUCS["sha256"],
                      Ukazatel(DEMUCS["velikost"], "model.stahuji", lambda p: None, log))
    except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
        raise RuntimeError(t("model.chyba_stazeni", chyba=e)) from e
    _zapis_znacku(slozka, {"sha256": DEMUCS["sha256"]}, [cil.name])
    return cil
