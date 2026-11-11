@echo off
chcp 65001 >nul
rem kupcake.studio – Copyright (C) 2026 Tomáš Kupec
rem SPDX-License-Identifier: GPL-3.0-only
cd /d "%~dp0"
rem Vypíše celý aktuální zdrojový kód do kod_programu.md (v této složce). Kód se nemění.
if not exist ".venv\Scripts\python.exe" (
    echo [CHYBA] Chybí virtuální prostředí .venv.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" nastroje\export_kodu.py || (
    echo Export kódu selhal.
    pause
    exit /b 1
)
pause
