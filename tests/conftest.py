# kupcake.studio – Copyright (C) 2026 Tomáš Kupec
# SPDX-License-Identifier: GPL-3.0-only
"""Pro pytest: složka tests a kořen projektu v sys.path (unittest discover to dělá sám)."""
import sys
from pathlib import Path

for p in (Path(__file__).resolve().parent, Path(__file__).resolve().parent.parent):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
import _zaklad  # noqa: E402,F401
