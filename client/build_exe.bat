@echo off
REM ================================================================
REM  ZNS - Client als portable EXE bauen
REM  Ergebnis: dist\ZNS-win32-x64\  -> auf die Praxis-PCs kopieren
REM ================================================================

title ZNS - Client bauen
cd /d "%~dp0"

REM --- Node.js vorhanden? ---
node --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  FEHLER: Node.js wurde nicht gefunden.
    echo  Bitte installieren: https://nodejs.org  ^(LTS-Version^)
    echo.
    pause
    exit /b 1
)

REM --- Abhaengigkeiten installieren ---
if not exist "node_modules" (
    echo  Installiere Abhaengigkeiten ^(dauert beim ersten Mal einige Minuten^) ...
    call npm install
    if errorlevel 1 (
        echo  FEHLER: npm install ist fehlgeschlagen.
        pause
        exit /b 1
    )
    echo.
)

REM --- Bauen ---
echo  Baue den Client ...
call npx electron-packager . ZNS --platform=win32 --arch=x64 --out=dist --overwrite --asar --app-version=2.0.0
if errorlevel 1 (
    echo.
    echo  FEHLER: Der Build ist fehlgeschlagen.
    pause
    exit /b 1
)

echo.
echo  ============================================================
echo   Fertig!
echo.
echo   Den Ordner   dist\ZNS-win32-x64\
echo   auf jeden Praxis-PC kopieren und ZNS.exe starten.
echo  ============================================================
echo.
pause
