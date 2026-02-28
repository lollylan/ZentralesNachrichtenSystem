@echo off
chcp 65001 > nul
title ZNS – Build Portable EXE

echo ================================================
echo   ZNS – Zentrales Nachrichten-System
echo   Erstelle portable Windows-App (ohne Installation)
echo ================================================
echo.

cd /d "%~dp0"

REM Node.js pruefen
where node >nul 2>&1
if errorlevel 1 (
    echo [FEHLER] Node.js ist nicht installiert!
    echo Bitte von https://nodejs.org herunterladen.
    pause
    exit /b 1
)

echo [1/3] Installiere Abhaengigkeiten...
call npm install
if errorlevel 1 ( echo [FEHLER] npm install fehlgeschlagen. & pause & exit /b 1 )
echo.

echo [2/3] Baue portable App (das dauert 1-3 Minuten)...
call npx electron-packager . ZNS --platform=win32 --arch=x64 --out=dist --overwrite --asar --ignore="dist|build_exe\.bat|start_client\.bat|\.gitignore"
if errorlevel 1 ( echo [FEHLER] Build fehlgeschlagen. & pause & exit /b 1 )
echo.

echo [3/3] Erstelle ZIP-Archiv...
powershell -Command "Compress-Archive -Path 'dist\ZNS-win32-x64\*' -DestinationPath 'dist\ZNS-Client-Windows.zip' -Force"
echo.

echo ================================================
echo   Ergebnis:
echo.
echo   Ordner: dist\ZNS-win32-x64\ZNS.exe
echo   ZIP:    dist\ZNS-Client-Windows.zip
echo.
echo   Den Ordner "ZNS-win32-x64" ODER das ZIP auf
echo   die Client-PCs kopieren und ZNS.exe starten!
echo   (Kein Node.js, kein Electron, keine Installation noetig)
echo ================================================
echo.

REM Ordner oeffnen
explorer dist\ZNS-win32-x64

pause
