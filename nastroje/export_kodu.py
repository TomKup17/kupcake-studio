"""Vypíše celý aktuální zdrojový kód kupcake.studio do jednoho souboru kod_programu.md v kořeni projektu.

Spouští se přes export_kodu.bat (nebo  .venv\\Scripts\\python.exe nastroje\\export_kodu.py). Kód nemění.
Pořadí: main.py, ostatní Python soubory po složkách, skripty .bat, instalátor .iss, jazykové soubory,
requirements.txt, konfigurace. Binární soubory (DLL, obrázky, ikony, fonty) jen v seznamu na konci.
"""
import datetime
import re
from pathlib import Path

KOREN = Path(__file__).resolve().parent.parent
VYSTUP = KOREN / "kod_programu.md"
VYNECHAT_SLOZKY = {".venv", "venv", "build", "dist", "__pycache__", ".git", "models", ".claude"}
BINARNI = {".dll", ".exe", ".pyd", ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".ttf", ".otf", ".woff",
           ".woff2", ".mp4", ".mov", ".mkv", ".wav", ".mp3", ".zip", ".bin", ".safetensors", ".th"}
JAZYK = {".py": "python", ".spec": "python", ".bat": "bat", ".iss": "ini", ".json": "json", ".txt": "text",
         ".gitignore": "gitignore"}


def soubory():
    for f in sorted(KOREN.rglob("*"), key=lambda p: str(p.relative_to(KOREN)).lower()):
        if f.is_file() and not (set(f.relative_to(KOREN).parts[:-1]) & VYNECHAT_SLOZKY) and f != VYSTUP:
            yield f


def pripona(f):
    return f.suffix.lower() if f.suffix else f.name.lower()


def poradi(f):
    """Skupina (0–6) a klíč řazení uvnitř ní; None = soubor do výpisu kódu nepatří."""
    rel = f.relative_to(KOREN)
    p = pripona(f)
    if rel.as_posix() == "main.py":
        return (0, "")
    if p == ".py":
        return (1, (len(rel.parts) > 1, rel.as_posix().lower()))  # kořen, pak podle složek
    if p == ".bat":
        return (2, rel.as_posix().lower())
    if p == ".iss":
        return (3, rel.as_posix().lower())
    if p == ".json" and rel.parts[0] == "locales":
        return (4, rel.as_posix().lower())
    if rel.as_posix() == "requirements.txt":
        return (5, "")
    if p in (".spec", ".gitignore"):
        return (6, rel.as_posix().lower())
    return None


def precti(f):
    data = f.read_bytes()
    for kodovani in ("utf-8-sig", "cp1250"):
        try:
            return data.decode(kodovani)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def kotva(text):
    """Odkaz na nadpis v obsahu (styl GitHubu: malá písmena, bez interpunkce, mezery → pomlčky)."""
    return re.sub(r"[^\w\- ]", "", text.lower()).replace(" ", "-")


def velikost(b):
    return f"{b / 2**20:.1f} MB" if b >= 2**20 else f"{b / 1024:.1f} kB" if b >= 1024 else f"{b} B"


def main():
    import sys
    sys.path.insert(0, str(KOREN))
    from version import VERZE

    kod, binarni, jine = [], [], []
    for f in soubory():
        klic = poradi(f)
        if klic is not None:
            kod.append((klic, f))
        elif pripona(f) in BINARNI:
            binarni.append(f)
        else:
            jine.append(f)
    kod.sort(key=lambda x: x[0])
    obsahy = [(f, precti(f)) for _, f in kod]
    radku = {f: len(text.splitlines()) for f, text in obsahy}

    vystup = [
        "# kupcake.studio – zdrojový kód",
        "",
        f"- **Datum:** {datetime.date.today():%d. %m. %Y}",
        f"- **Verze:** {VERZE} (z `version.py`)",
        f"- **Souborů s kódem:** {len(obsahy)} · **řádků celkem:** {sum(radku.values()):,}".replace(",", " "),
        "",
        "Vygenerováno skriptem `export_kodu.bat` (`nastroje/export_kodu.py`). Soubor je jen pro čtení – kód se "
        "upravuje v jednotlivých souborech, tento výpis se pak vygeneruje znovu.",
        "",
        "## Obsah",
        "",
        "| # | Soubor | Řádků |",
        "|---:|---|---:|",
    ]
    for i, (f, _) in enumerate(obsahy, 1):
        rel = f.relative_to(KOREN).as_posix()
        vystup.append(f"| {i} | [{rel}](#{kotva(rel)}) | {radku[f]:,} |".replace(",", " "))
    vystup.append(f"| | **Celkem** | **{sum(radku.values()):,}** |".replace(",", " "))
    vystup.append("")

    for f, text in obsahy:
        rel = f.relative_to(KOREN).as_posix()
        delka_plotu = max([3] + [len(m) + 1 for m in re.findall(r"`{3,}", text)])
        plot = "`" * delka_plotu
        vystup += [f"## {rel}", "", f"{plot}{JAZYK.get(pripona(f), '')}", text.rstrip("\n"), plot, ""]

    vystup += ["## Binární soubory (bez výpisu)", "", "| Soubor | Velikost |", "|---|---:|"]
    for f in binarni:
        vystup.append(f"| {f.relative_to(KOREN).as_posix()} | {velikost(f.stat().st_size)} |")
    vystup += ["", "## Ostatní soubory (nejsou kód – bez výpisu)", "",
               "Dokumentace a plná znění licencí třetích stran:", ""]
    for f in jine:
        vystup.append(f"- {f.relative_to(KOREN).as_posix()} ({velikost(f.stat().st_size)})")
    vystup.append("")

    VYSTUP.write_text("\n".join(vystup), encoding="utf-8")
    print(f"Hotovo: {VYSTUP.name} – {len(obsahy)} souborů, {sum(radku.values())} řádků, "
          f"{len(binarni)} binárních souborů v seznamu.")


if __name__ == "__main__":
    main()
