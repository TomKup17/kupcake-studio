# kupcake.studio – Copyright (C) 2026 Tomáš Kupec
# SPDX-License-Identifier: GPL-3.0-only
"""Vytvoří manifest_modelu.py: pevná revize (commit) a SHA-256 každého souboru modelů, které aplikace stahuje.

Spouští se jen při změně modelů (vývojář, ne aplikace):  .venv\\Scripts\\python.exe nastroje\\vytvor_manifest.py
- velké soubory (Git LFS): SHA-256 z API Hugging Face pro pevnou revizi,
- malé soubory: obsah pevné revize, ověřený proti git SHA-1 z API (shoduje se s oficiálním repozitářem),
  z něj SHA-256; když už soubor leží v modelech aplikace, použije se ten (po stejné kontrole),
- Demucs htdemucs: stáhne se jednou do paměti, ověří prefix SHA-256 ze jména souboru, uloží se plný součet.
"""
import hashlib
import json
import os
import sys
import urllib.request
from pathlib import Path

KOREN = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOREN))
from zarovnani import MMS, MODELY, SOUBORY as SOUBORY_ZAROVNANI  # noqa: E402

from model import MODELY as WHISPER  # noqa: E402  – přesnosti přepisu: {klíč: (repo, soubory)}
DEMUCS_URL = "https://dl.fbaipublicfiles.com/demucs/hybrid_transformer/955717e8-8726e21a.th"
MODELY_APLIKACE = Path(os.environ["LOCALAPPDATA"]) / "KupcakeStudio" / "models"
UA = {"User-Agent": "kupcake.studio-manifest"}


def stahni(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
        return r.read()


def git_sha1(data):
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def repo(nazev, soubory, slozka):
    meta = json.loads(stahni(f"https://huggingface.co/api/models/{nazev}/revision/main?blobs=true"))
    revize = meta["sha"]
    v_repu = {s["rfilename"]: s for s in meta["siblings"]}
    if soubory is None:  # zarovnání: potřebné JSON + váhy (safetensors přednostně – bez pickle)
        vahy = "model.safetensors" if "model.safetensors" in v_repu else "pytorch_model.bin"
        soubory = [f for f in SOUBORY_ZAROVNANI if f in v_repu] + [vahy]
    vysledek = {}
    for f in soubory:
        s = v_repu[f]
        if s.get("lfs"):
            vysledek[f] = (s["lfs"]["size"], s["lfs"]["sha256"])
            continue
        lokalni = slozka / f
        data = lokalni.read_bytes() if lokalni.is_file() else b""
        if git_sha1(data) != s["blobId"]:
            data = stahni(f"https://huggingface.co/{nazev}/resolve/{revize}/{f}")
        if git_sha1(data) != s["blobId"]:
            raise SystemExit(f"{nazev}/{f}: obsah nesouhlasí s git hashem z API")
        vysledek[f] = (len(data), hashlib.sha256(data).hexdigest())
    print(f"{nazev} @ {revize[:10]}: {', '.join(vysledek)}", flush=True)
    return {"revize": revize, "soubory": vysledek}


manifest = {}
for nazev, soubory in WHISPER.values():
    manifest[nazev] = repo(nazev, soubory, MODELY_APLIKACE / nazev.split("/")[1])
for nazev in list(MODELY.values()) + [MMS]:
    manifest[nazev] = repo(nazev, None, MODELY_APLIKACE / "zarovnani" / nazev.replace("/", "--"))
try:  # Demucs (84 MB) jen když ještě v manifestu není nebo se změnila adresa
    from manifest_modelu import DEMUCS as demucs
    if demucs["url"] != DEMUCS_URL:
        raise ImportError
except ImportError:
    data = stahni(DEMUCS_URL)
    sha = hashlib.sha256(data).hexdigest()
    if not sha.startswith(DEMUCS_URL.rsplit("-", 1)[1].split(".")[0]):
        raise SystemExit("Demucs: SHA-256 nesouhlasí s prefixem ve jménu souboru")
    demucs = {"url": DEMUCS_URL, "velikost": len(data), "sha256": sha}
print("Demucs htdemucs:", demucs["velikost"], demucs["sha256"], flush=True)

radky = ['# kupcake.studio – Copyright (C) 2026 Tomáš Kupec', '# SPDX-License-Identifier: GPL-3.0-only',
         '"""Pevné revize a SHA-256 modelů, které aplikace stahuje. VYGENEROVÁNO nastroje/vytvor_manifest.py –',
         'neupravovat ručně. Každý stažený soubor se proti tomuto seznamu ověří (stahovani.py)."""', "",
         "# repo → {revize: commit, soubory: {jméno: (velikost v B, SHA-256)}}", "HUGGINGFACE = {"]
for nazev, m in manifest.items():
    radky.append(f"    {nazev!r}: {{")
    radky.append(f"        \"revize\": {m['revize']!r},")
    radky.append("        \"soubory\": {")
    for f, (velikost, h) in m["soubory"].items():
        radky.append(f"            {f!r}: ({velikost}, {h!r}),")
    radky.append("        },")
    radky.append("    },")
radky.append("}")
radky.append("")
radky.append("# Demucs htdemucs (oddělení hlasu) – oficiální úložiště Meta")
radky.append(f"DEMUCS = {demucs!r}")
(KOREN / "manifest_modelu.py").write_text("\n".join(radky) + "\n", encoding="utf-8")
print("manifest_modelu.py zapsán")
