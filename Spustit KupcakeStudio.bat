@echo off
rem kupcake.studio – Copyright (C) 2026 Tomáš Kupec
rem SPDX-License-Identifier: GPL-3.0-only
cd /d "%~dp0"
start "" ".venv\Scripts\pythonw.exe" main.py %*
