@echo off
chcp 65001 > nul
title ZNS-Server

echo ================================================
echo   ZNS – Zentrales Nachrichten-System
echo   Server wird gestartet...
echo ================================================
echo.

cd /d "%~dp0"

REM Virtuelle Umgebung erstellen falls nicht vorhanden
if not exist "venv\" (
    echo [Setup] Erstelle virtuelle Python-Umgebung...
    python -m venv venv
)

REM Abhaengigkeiten bei jedem Start aktuell halten
echo [Setup] Pruefe Abhaengigkeiten...
venv\Scripts\pip install -q -r requirements.txt
echo.

echo [OK] Starte ZNS-Server...
echo.
venv\Scripts\python server.py

pause
