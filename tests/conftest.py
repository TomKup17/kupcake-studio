"""Pro pytest: složka tests a kořen projektu v sys.path (unittest discover to dělá sám)."""
import sys
from pathlib import Path

for p in (Path(__file__).resolve().parent, Path(__file__).resolve().parent.parent):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
import _zaklad  # noqa: E402,F401
