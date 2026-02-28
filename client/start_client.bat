@echo off
chcp 65001 > nul
title ZNS-Client Setup

echo ================================================
echo   ZNS – Zentrales Nachrichten-System
echo   Client wird eingerichtet...
echo ================================================
echo.

cd /d "%~dp0"

REM Node.js prüfen
where node >nul 2>&1
if errorlevel 1 (
    echo [FEHLER] Node.js ist nicht installiert!
    echo Bitte von https://nodejs.org herunterladen.
    pause
    exit /b 1
)

REM npm install nur wenn node_modules fehlt
if not exist "node_modules\" (
    echo [Setup] Installiere Abhaengigkeiten ^(einmalig^)...
    call npm install
    echo.
)

echo [OK] Starte ZNS-Client...
echo.
npx electron .

pause
