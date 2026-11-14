# kupcake.studio – Copyright (C) 2026 Tomáš Kupec
# SPDX-License-Identifier: GPL-3.0-only
"""Podklady pro malý stahovací instalátor (installer\\KupcakeStudio-Web.iss) – spouští ho build.bat po sestavení
plného instalátoru. Vytvoří dva soubory, které KupcakeStudio-Web.iss vkládá (#include):

  build\\web_casti.iss    – části plného instalátoru (.exe, -1.bin, -2.bin…) s velikostí a SHA-256 z dist\\*.sha256
                           a velikost nainstalované aplikace (kvůli kontrole místa na disku),
  build\\web_modely.iss   – volby (Tasks) a soubory (Files) AI modelů: Whisper pro přepis, modely přesného časování
                           a Demucs. Adresy, revize, velikosti a SHA-256 jsou z manifest_modelu.py – tedy přesně
                           ty soubory, které by aplikace stáhla sama; uloží se tam, kde je aplikace hledá.

Použití:  python nastroje\\web_instalator.py <verze> [<název> <složka s instalátorem>]
          (název a složka jen pro test, výchozí KupcakeStudio a dist)
Nic nestahuje. Seznamy modelů čte z model.py a zarovnani.py jako text (bez importu – žádné vedlejší účinky).
"""
import ast
import sys
from pathlib import Path

KOREN = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOREN))
from manifest_modelu import DEMUCS, HUGGINGFACE  # noqa: E402  (čistá data)

TECH = "KupcakeStudio"
DIST = KOREN / "dist"
VYSTUP = KOREN / "build"

# jazyk přesného časování → název v instalátoru (pořadí = pořadí voleb)
JAZYKY = {"cs": "čeština", "sk": "slovenština", "en": "angličtina", "de": "němčina", "es": "španělština",
          "fr": "francouzština", "it": "italština", "pl": "polština"}


def prirazeni(soubor, jmeno):
    """Hodnota přiřazení `jmeno = {...}` na nejvyšší úrovni souboru (literál, bez spuštění kódu)."""
    for uzel in ast.parse((KOREN / soubor).read_text(encoding="utf-8")).body:
        if isinstance(uzel, ast.Assign) and any(isinstance(c, ast.Name) and c.id == jmeno for c in uzel.targets):
            return ast.literal_eval(uzel.value)
    raise SystemExit(f"[CHYBA] V {soubor} chybí {jmeno}")


def gb(bajty):
    """Velikost jako ji ukazují Windows (1 GB = 1024³ B) – stejně jako README a web."""
    return f"{bajty / 2**30:.1f}".replace(".", ",") + " GB" if bajty >= 2**30 else f"{round(bajty / 2**20)} MB"


def pas(text):
    """Řetězec pro Pascal a parametry Inno Setup (apostrof zdvojit; uvozovky v datech nejsou)."""
    assert '"' not in text, text
    return text.replace("'", "''")


def casti(verze):
    soucty = DIST / f"{TECH}-Setup-{verze}.sha256"
    if not soucty.is_file():
        raise SystemExit(f"[CHYBA] Chybí {soucty} – nejdřív se musí sestavit plný instalátor.")
    radky = []
    for radek in soucty.read_text(encoding="ascii").split("\n"):
        if radek.strip():
            soucet, jmeno = radek.split(maxsplit=1)
            soubor = DIST / jmeno.strip()
            radky.append((soubor.name, soubor.stat().st_size, soucet.lower()))
    if not any(j.endswith(".exe") for j, _, _ in radky):
        raise SystemExit(f"[CHYBA] V {soucty.name} chybí instalátor .exe")
    aplikace = sum(f.stat().st_size for f in (DIST / TECH).rglob("*") if f.is_file()) if (DIST / TECH).is_dir() else 0
    out = ["; VYGENEROVÁNO nastroje\\web_instalator.py – neupravovat ručně", "",
           f"#define VelikostAplikace \"{aplikace}\"",
           f"#define VelikostCastiCelkem \"{sum(v for _, v, _ in radky)}\"", "",
           "[Code]",
           "// Části plného instalátoru: stáhnou se do {tmp} a ověří SHA-256 (adresa = ZakladUrl + název souboru).",
           "procedure PridejCasti(Stranka: TDownloadWizardPage);",
           "begin"]
    for jmeno, _, soucet in radky:
        out.append(f"  Stranka.Add('{{#ZakladUrl}}{jmeno}', '{jmeno}', '{soucet}');")
    out += ["end;", ""]
    return "\n".join(out), radky


def modely():
    whisper = prirazeni("model.py", "MODELY")
    vychozi = prirazeni("model.py", "VYCHOZI")
    casovani = prirazeni("zarovnani.py", "MODELY")
    tasks, files, seznam = [], [], []

    def soubory_repa(repo, slozka, uloha):
        m = HUGGINGFACE[repo]
        for jmeno, (velikost, soucet) in m["soubory"].items():
            cil = f"{{#DataDir}}\\models\\{slozka}"
            seznam.append(f"  Seznam.Add('{uloha}|{pas(cil)}\\{pas(jmeno)}|{velikost}');")
            files.append(
                f'Source: "https://huggingface.co/{repo}/resolve/{m["revize"]}/{jmeno}"; DestName: "{jmeno}"; '
                f'DestDir: "{cil}"; ExternalSize: {velikost}; Hash: "{soucet}"; '
                f'Flags: external download ignoreversion; Tasks: {uloha}; '
                f"Check: ChybiSoubor('{pas(cil)}\\{pas(jmeno)}', '{velikost}')")
        return sum(v for v, _ in m["soubory"].values())

    # Whisper – výchozí přesnost přepisu (tu aplikace použije, dokud si uživatel nezvolí jinou)
    repo = whisper[vychozi][0]
    files.append(f"; Whisper {vychozi} – přepis řeči")
    velikost = soubory_repa(repo, repo.split("/")[1], "model")
    tasks.append(f'Name: "model"; Description: "Model pro přepis řeči – Whisper {vychozi} ({gb(velikost)})"; '
                 f'GroupDescription: "{{cm:SkupinaModely}}"')

    # přesné časování slov – podle jazyka videí (aplikace ho dělá ve výchozím stavu)
    for jazyk, nazev in JAZYKY.items():
        repo = casovani[jazyk]
        files.append(f"; přesné časování: {nazev}")
        velikost = soubory_repa(repo, f"zarovnani\\{repo.replace('/', '--')}", f"cas_{jazyk}")
        tasks.append(f'Name: "cas_{jazyk}"; Description: "Přesné časování slov – {nazev} ({gb(velikost)})"; '
                     f'GroupDescription: "{{cm:SkupinaCasovani}}"; Flags: unchecked')

    # Demucs – volitelné oddělení hlasu od hudby (v aplikaci ve výchozím stavu vypnuté)
    jmeno = DEMUCS["url"].rsplit("/", 1)[1]
    seznam.append(f"  Seznam.Add('demucs|{{#DataDir}}\\models\\demucs\\{jmeno}|{DEMUCS['velikost']}');")
    files.append("; Demucs – oddělení hlasu od hudby")
    files.append(f'Source: "{DEMUCS["url"]}"; DestName: "{jmeno}"; DestDir: "{{#DataDir}}\\models\\demucs"; '
                 f'ExternalSize: {DEMUCS["velikost"]}; Hash: "{DEMUCS["sha256"]}"; '
                 f'Flags: external download ignoreversion; Tasks: demucs; '
                 f"Check: ChybiSoubor('{{#DataDir}}\\models\\demucs\\{jmeno}', '{DEMUCS['velikost']}')")
    tasks.append(f'Name: "demucs"; Description: "Oddělení hlasu od hudby v pozadí – Demucs ({gb(DEMUCS["velikost"])})"; '
                 f'GroupDescription: "{{cm:SkupinaHlas}}"; Flags: unchecked')

    return "\n".join(["; VYGENEROVÁNO nastroje\\web_instalator.py z manifest_modelu.py – neupravovat ručně", "",
                      "[Tasks]", *tasks, "", "[Files]", *files, "",
                      "[Code]",
                      "// Soubory modelů pro výpočet velikosti (úloha|cesta|velikost v B) – stejné jako v [Files].",
                      "procedure PridejModely(Seznam: TStringList);",
                      "begin", *seznam, "end;", ""])


def main():
    global TECH, DIST
    if len(sys.argv) not in (2, 4):
        raise SystemExit(__doc__)
    verze = sys.argv[1]
    if len(sys.argv) == 4:
        TECH, DIST = sys.argv[2], Path(sys.argv[3])
    VYSTUP.mkdir(exist_ok=True)
    text, radky = casti(verze)
    # UTF-8 s BOM – Inno Setup tak čte češtinu správně
    (VYSTUP / "web_casti.iss").write_text(text, encoding="utf-8-sig", newline="\r\n")
    (VYSTUP / "web_modely.iss").write_text(modely(), encoding="utf-8-sig", newline="\r\n")
    print(f"web_instalator: {len(radky)} části instalátoru, modely z manifestu → build\\web_casti.iss, build\\web_modely.iss")


if __name__ == "__main__":
    main()
