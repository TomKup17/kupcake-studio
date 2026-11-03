"""Společný základ testů: izolované APPDATA/LOCALAPPDATA (nastavení ani modely uživatele se nedotknou)
a kořen projektu v sys.path. Importovat jako první v každém testovacím modulu.

Spuštění (z kořene projektu):  .venv\\Scripts\\python.exe -m unittest discover -s tests -v
                             nebo  .venv\\Scripts\\python.exe -m pytest tests
Testy nic nestahují – síť je nahrazená falešnými odpověďmi."""
import os
import sys
import tempfile
from pathlib import Path

KOREN = Path(__file__).resolve().parent.parent
if str(KOREN) not in sys.path:
    sys.path.insert(0, str(KOREN))

DOCASNE = Path(tempfile.mkdtemp(prefix="kupcake_testy_"))
os.environ["APPDATA"] = str(DOCASNE / "roaming")
os.environ["LOCALAPPDATA"] = str(DOCASNE / "local")
os.environ["KUPCAKE_CPU"] = "1"  # testy nesahají na GPU

import cesty  # noqa: E402  – cesty čtou proměnné prostředí při importu

assert str(cesty.DATA_DIR).startswith(str(DOCASNE)), "testy musí běžet v izolované složce"
