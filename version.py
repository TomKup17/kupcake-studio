# kupcake.studio – Copyright (C) 2026 Tomáš Kupec
# SPDX-License-Identifier: GPL-3.0-only
# Jediné místo s číslem verze (a datem sestavení) aplikace kupcake.studio – propisuje se do aplikace (O aplikaci), do KupcakeStudio.exe
# (Vlastnosti → Podrobnosti) i do názvu instalátoru. Mění ho build.bat, ručně ho upravovat netřeba.
VERZE = "1.0.0-beta.1"
DATUM = "2026-11-03"  # datum sestavení – build.bat ho zapíše spolu s verzí

if __name__ == "__main__":
    # build.bat:  python version.py          -> vypíše verzi
    #             python version.py 1.0.1    -> ověří tvar X.Y.Z (nebo X.Y.Z-beta.N), zapíše ji sem a vypíše
    #             python version.py --cislo  -> jen číselná část (1.0.0) pro údaje o verzi v .exe
    import re
    import sys
    from pathlib import Path

    if len(sys.argv) > 1 and sys.argv[1] == "--cislo":
        print(VERZE.split("-")[0])
        sys.exit(0)
    if len(sys.argv) > 1:
        nova = sys.argv[1].strip()
        if not re.fullmatch(r"\d+\.\d+\.\d+(-[0-9A-Za-z]+(\.[0-9A-Za-z]+)*)?", nova):
            sys.exit(f"[CHYBA] Verze musí mít tvar X.Y.Z nebo X.Y.Z-beta.N, např. 1.0.1 – zadáno: {nova!r}")
        import datetime
        soubor = Path(__file__)
        text = re.sub(r'^VERZE = "[^"]*"', f'VERZE = "{nova}"', soubor.read_text(encoding="utf-8"),
                      count=1, flags=re.M)
        text = re.sub(r'^DATUM = "[^"]*"', f'DATUM = "{datetime.date.today().isoformat()}"', text,
                      count=1, flags=re.M)
        soubor.write_text(text, encoding="utf-8")
        VERZE = nova
    print(VERZE)
