# kupcake.studio – Copyright (C) 2026 Tomáš Kupec
# SPDX-License-Identifier: GPL-3.0-only
"""Z TERMS.cs.md udělá prostý text pro stránku s podmínkami v instalátoru: installer\\PODMINKY.txt.

Inno Setup (LicenseFile) umí jen prostý text nebo RTF – Markdown by ukázal i se značkami. Skript proto odstraní
značky (nadpisy podtrhne, odkazy přepíše na „text (adresa)“), odstavce spojí do jednoho řádku (okno instalátoru
si je zalomí samo) a soubor zapíše v UTF-8 s BOM a konci řádků CRLF, jak to Inno Setup potřebuje.

Spouští ho build.bat před sestavením instalátoru; ručně:  .venv\\Scripts\\python.exe nastroje\\podminky_txt.py
Test tests/test_dokumenty.py hlídá, že uložený PODMINKY.txt odpovídá aktuálnímu TERMS.cs.md.
"""
import re
from pathlib import Path

KOREN = Path(__file__).resolve().parent.parent
ZDROJ = KOREN / "TERMS.cs.md"
CIL = KOREN / "installer" / "PODMINKY.txt"


def _bez_znacek(text):
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", text)   # [text](adresa) → text (adresa)
    text = re.sub(r"<(https?://[^>]+)>", r"\1", text)              # <adresa> → adresa
    return text.replace("**", "").replace("`", "")


def na_text(markdown):
    """Markdown podmínek → prostý text (odstavce na jednom řádku, nadpisy podtržené, odrážky „- “)."""
    vysledek = []
    for blok in re.split(r"\n\s*\n", markdown.replace("\r\n", "\n").strip()):
        radky = blok.split("\n")
        if radky[0].startswith("[English]") or radky[0].startswith("**English**"):
            continue  # přepínač jazyka je jen pro GitHub
        if radky[0].startswith("# "):
            nadpis = _bez_znacek(radky[0][2:].strip())
            vysledek.append(nadpis + "\n" + "=" * len(nadpis))
        elif radky[0].startswith("## "):
            nadpis = _bez_znacek(radky[0][3:].strip())
            vysledek.append(nadpis + "\n" + "-" * len(nadpis))
        elif radky[0].startswith("- "):
            polozky = []
            for r in radky:
                if r.startswith("- "):
                    polozky.append(r[2:].strip())
                else:  # pokračování odrážky
                    polozky[-1] += " " + r.strip()
            vysledek.append("\n".join("- " + _bez_znacek(p) for p in polozky))
        else:
            vysledek.append(_bez_znacek(" ".join(r.strip() for r in radky)))
    return "\n\n".join(vysledek) + "\n"


def vytvor():
    """Obsah souboru PODMINKY.txt jako bajty (UTF-8 s BOM, CRLF)."""
    text = na_text(ZDROJ.read_text(encoding="utf-8"))
    return b"\xef\xbb\xbf" + text.replace("\n", "\r\n").encode("utf-8")


if __name__ == "__main__":
    CIL.write_bytes(vytvor())
    print(f"Zapsáno: {CIL.relative_to(KOREN)}")
