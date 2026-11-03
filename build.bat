@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
rem Sestaví KupcakeStudio.exe (PyInstaller) a instalátor KupcakeStudio-Setup-<verze>.exe (Inno Setup).
rem Verze je v version.py; build.bat se na novou zeptá a zapíše ji tam.
rem Použití:  build.bat                 – zeptá se na verzi
rem           build.bat 1.2.0           – verzi nastaví bez ptaní
rem           build.bat 1.2.0 /nopause  – navíc na konci nečeká na klávesu (pro skripty)

set "PY=.venv\Scripts\python.exe"
if not exist "%PY%" (
    echo [CHYBA] Chybí virtuální prostředí .venv – aplikace se sestavuje z něj.
    goto :chyba
)
set "PAUZA=1"
set "NOVA="
for %%a in (%*) do (
    if /i "%%~a"=="/nopause" (set "PAUZA=") else set "NOVA=%%~a"
)

for /f "delims=" %%v in ('%PY% version.py') do set "STARA=%%v"
if not defined NOVA (
    echo Aktuální verze: %STARA%
    set /p "NOVA=Nová verze (např. 1.0.1, Enter = ponechat %STARA%): "
)
if not defined NOVA set "NOVA=%STARA%"
rem version.py ověří tvar X.Y.Z a verzi do sebe zapíše
%PY% version.py %NOVA% >nul || goto :chyba
if not "%NOVA%"=="%STARA%" echo version.py: %STARA% → %NOVA%
set "VERZE=%NOVA%"
rem číselná část (1.0.0 z 1.0.0-beta.1) – údaje o verzi v .exe a instalátoru musí být jen čísla
for /f "delims=" %%v in ('%PY% version.py --cislo') do set "VERZE_CISLO=%%v"

echo ============================================
echo   kupcake.studio %VERZE% – sestavení
echo ============================================

echo.
echo [1/3] Kontrola nástrojů
where ffmpeg >nul 2>&1 || (
    echo [CHYBA] FFmpeg není v PATH – přibaluje se do aplikace. Nainstaluj: winget install Gyan.FFmpeg
    goto :chyba
)
set "ISCC="
for %%p in ("%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" "%ProgramFiles%\Inno Setup 6\ISCC.exe" "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe") do (
    if exist %%p set "ISCC=%%~p"
)
if not defined ISCC (
    echo [POZOR] Inno Setup 6 nenalezen – sestavím jen aplikaci, instalátor ne.
    echo         Nainstaluj: winget install JRSoftware.InnoSetup
)
rem chybějící PyInstaller se doinstaluje v připnuté verzi z requirements.txt (ne „nejnovější z PyPI“)
"%PY%" -m PyInstaller --version >nul 2>&1 || "%PY%" -m pip install --disable-pip-version-check pyinstaller==6.22.3 || goto :chyba

echo.
echo [2/3] PyInstaller – dist\KupcakeStudio\KupcakeStudio.exe (může trvat několik minut)
"%PY%" -m PyInstaller KupcakeStudio.spec --noconfirm --clean --log-level WARN || goto :chyba

echo.
echo [3/3] Instalátor
if not defined ISCC (
    echo Přeskočeno – chybí Inno Setup. Aplikace je ve složce dist\KupcakeStudio.
    goto :konec
)
"%ISCC%" /Qp /DAppVersion=%VERZE% /DAppVersionNum=%VERZE_CISLO% "installer\KupcakeStudio.iss" || goto :chyba
rem kontrolní součet SHA-256 vedle instalátoru (ke zveřejnění u vydání)
powershell -NoProfile -Command "$h=(Get-FileHash 'dist\KupcakeStudio-Setup-%VERZE%.exe' -Algorithm SHA256).Hash.ToLower(); \"$h  KupcakeStudio-Setup-%VERZE%.exe\" | Out-File -Encoding ascii 'dist\KupcakeStudio-Setup-%VERZE%.exe.sha256'" || goto :chyba
echo.
echo Hotovo: dist\KupcakeStudio-Setup-%VERZE%.exe
type "dist\KupcakeStudio-Setup-%VERZE%.exe.sha256"
goto :konec

:chyba
echo.
echo Sestavení selhalo.
if defined PAUZA pause
exit /b 1

:konec
if defined PAUZA pause
exit /b 0
