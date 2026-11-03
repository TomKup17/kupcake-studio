@echo off
chcp 65001 >nul
cd /d "%~dp0"
rem Spustí kupcake.studio přímo ze zdrojového kódu – změny v .py se projeví hned, bez sestavování.
rem Okno konzole zůstane otevřené a ukáže případné chyby (traceback). Lze předat video: run_dev.bat video.mp4
if not exist ".venv\Scripts\python.exe" (
    echo [CHYBA] Chybí virtuální prostředí .venv.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" main.py %*
if errorlevel 1 (
    echo.
    echo kupcake.studio skončil s chybou – podrobnosti jsou výše.
    pause
)
