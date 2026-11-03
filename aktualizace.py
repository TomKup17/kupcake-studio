"""Kontrola nové verze přes GitHub Releases (repozitář v links.GITHUB_REPO; prázdný = vypnuto).

Bez otravování: nejvýš jednou za 24 hodin, na pozadí (start aplikace se nezdrží), jen přes HTTPS na
api.github.com, nic se neodesílá kromě běžného požadavku (hlavička User-Agent s názvem a verzí aplikace).
Novější verze se nabídne nenápadnou notifikací (Stáhnout / Přeskočit tuto verzi); přeskočená verze se už
znovu nenabízí. Jde vypnout v Nastavení. Beta verze (1.0.0-beta.2) dostávají i předběžná vydání, stabilní
verze jen stabilní.

Aplikace nic nestahuje ani nespouští: tlačítko Stáhnout jen otevře stránku vydání v prohlížeči – a jen tehdy,
když adresa z odpovědi API vede na https://github.com/<repozitář>/ (jinak se použije stránka Releases).
Odpověď se čte nejvýš do MAX_ODPOVED bajtů, přesměrování jinam než na HTTPS api.github.com se nesleduje.
"""
import json
import logging
import re
import ssl
import threading
import time
import urllib.parse
import urllib.request

import links
from cesty import NAZEV
from version import VERZE

INTERVAL_S = 24 * 3600
API_HOST = "api.github.com"
MAX_ODPOVED = 2 * 2**20  # 2 MB – stránka s 10 vydáními má desítky kB
log = logging.getLogger("kupcake")


def _rozloz(verze):
    """„v1.0.0-beta.2“ → ((1, 0, 0), (0, „beta“, 2)); stabilní verze je novější než jakákoli předběžná."""
    if not isinstance(verze, str) or len(verze) > 64:
        return None
    m = re.match(r"v?(\d+)\.(\d+)\.(\d+)(?:-(.+))?$", verze.strip())
    if not m:
        return None
    zaklad = tuple(int(x) for x in m.groups()[:3])
    if not m.group(4):
        return zaklad, (1,)
    casti = tuple(int(c) if c.isdigit() else c for c in re.split(r"[.\-]", m.group(4)))
    return zaklad, (0,) + casti


def je_novejsi(nova, stara=VERZE):
    a, b = _rozloz(nova), _rozloz(stara)
    if a is None or b is None:
        return False
    try:
        return a > b
    except TypeError:  # nesrovnatelné části (číslo × text) – porovnat textově
        return str(a) > str(b)


def stranka_vydani(repo, url):
    """Adresa stránky vydání z API jen tehdy, když vede na https://github.com/<repo>/…; jinak stránka Releases."""
    zaloha = f"https://github.com/{repo}/releases"
    try:
        cast = urllib.parse.urlsplit(str(url or ""))
    except ValueError:
        return zaloha
    if cast.scheme == "https" and cast.hostname == "github.com" and cast.port is None \
            and cast.username is None and cast.path.startswith(f"/{repo}/"):
        return url
    return zaloha


class _JenApi(urllib.request.HTTPRedirectHandler):
    """Přesměrování jen na HTTPS api.github.com (jinak se kontrola tiše vzdá)."""
    max_redirections = 3

    def redirect_request(self, req, fp, code, msg, headers, novy_url):
        cast = urllib.parse.urlsplit(novy_url)
        if cast.scheme != "https" or cast.hostname != API_HOST:
            raise urllib.error.URLError(f"nepovolené přesměrování: {novy_url}")
        return super().redirect_request(req, fp, code, msg, headers, novy_url)


_otevirac = urllib.request.build_opener(
    urllib.request.HTTPSHandler(context=ssl.create_default_context()), _JenApi())
for _protokol in ("http", "ftp", "file", "data"):
    _otevirac.handle_open.pop(_protokol, None)


def _vydani(repo):
    """Seznam vydání z API (nejvýš 10), nebo výjimka."""
    pozadavek = urllib.request.Request(f"https://{API_HOST}/repos/{repo}/releases?per_page=10",
                                       headers={"User-Agent": f"{NAZEV}/{VERZE}",
                                                "Accept": "application/vnd.github+json"})
    with _otevirac.open(pozadavek, timeout=8) as r:
        if r.status != 200:
            raise urllib.error.URLError(f"HTTP {r.status}")
        data = r.read(MAX_ODPOVED + 1)
    if len(data) > MAX_ODPOVED:
        raise ValueError("odpověď API je příliš velká")
    vydani = json.loads(data.decode("utf-8"))
    if not isinstance(vydani, list):
        raise ValueError("neočekávaná odpověď API")
    return vydani


def nejnovejsi(repo=None, predbezne=None):
    """(verze, adresa stránky vydání) nejnovějšího vydání, nebo None. Síťová chyba = None (bez hlášky)."""
    repo = repo if repo is not None else links.GITHUB_REPO
    if not repo or not re.fullmatch(r"[\w.-]+/[\w.-]+", repo) or ".." in repo:
        return None
    predbezne = ("-" in VERZE) if predbezne is None else predbezne
    try:
        vydani = _vydani(repo)
    except Exception as e:  # offline, limit API, neexistující repozitář, vadná odpověď – tiše, zkusí se příště
        log.info("Kontrola aktualizací se nezdařila: %s", e)
        return None
    for v in vydani:
        if not isinstance(v, dict) or v.get("draft") or (v.get("prerelease") and not predbezne):
            continue
        tag = v.get("tag_name", "")
        if _rozloz(tag):
            return tag.strip().lstrip("v"), stranka_vydani(repo, v.get("html_url"))
    return None


def zkontroluj_na_pozadi(nastaveni, hotovo):
    """Spustí kontrolu ve vlákně, pokud je zapnutá a od poslední uplynulo 24 h.
    hotovo(verze, url) se zavolá (z vlákna – volající ho předá do hlavního vlákna signálem)."""
    if not links.GITHUB_REPO or str(nastaveni.value("aktualizace/zapnuto", "true")).lower() != "true":
        return
    try:
        posledni = float(nastaveni.value("aktualizace/posledni", 0) or 0)
    except (TypeError, ValueError):
        posledni = 0.0
    if time.time() - posledni < INTERVAL_S:
        return
    nastaveni.setValue("aktualizace/posledni", time.time())
    nastaveni.sync()
    preskocena = str(nastaveni.value("aktualizace/preskocit", "") or "")

    def prace():
        vysledek = nejnovejsi()
        if vysledek and je_novejsi(vysledek[0]) and vysledek[0] != preskocena:
            log.info("K dispozici je nová verze %s", vysledek[0])
            hotovo(*vysledek)

    threading.Thread(target=prace, name="aktualizace", daemon=True).start()
