@echo off
REM ================================================================
REM  ZNS - Zentrales Nachrichten-System
REM  Startet den Server. Beim ersten Start wird alles Noetige
REM  automatisch eingerichtet.
REM ================================================================

title ZNS Server
cd /d "%~dp0"

REM Umlaute in der Konsole korrekt darstellen
chcp 65001 >nul
set PYTHONIOENCODING=utf-8

REM --- Python vorhanden? ---
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  FEHLER: Python wurde nicht gefunden.
    echo  Bitte Python 3.9 oder neuer installieren: https://www.python.org/downloads/
    echo  Wichtig: Beim Installieren "Add Python to PATH" ankreuzen.
    echo.
    pause
    exit /b 1
)

REM --- Virtuelle Umgebung beim ersten Start anlegen ---
if not exist "venv\Scripts\python.exe" (
    echo  Richte die Python-Umgebung ein ^(nur beim ersten Start^) ...
    python -m venv venv
    if errorlevel 1 (
        echo  FEHLER: Die Python-Umgebung konnte nicht angelegt werden.
        pause
        exit /b 1
    )
    "venv\Scripts\python.exe" -m pip install --quiet --upgrade pip
    "venv\Scripts\python.exe" -m pip install --quiet -r requirements.txt
    echo  Einrichtung abgeschlossen.
    echo.
)

REM --- Server starten ---
"venv\Scripts\python.exe" server.py

echo.
echo  Der Server wurde beendet.
pause
