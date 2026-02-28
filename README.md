# 🏥 ZNS – Zentrales Nachrichten-System

**Internes Desktop-Nachrichtensystem für Praxisnetzwerke.**  
Nachrichten von jedem Arbeitsplatz zu jedem anderen – mit Bestätigungs-Overlay.

---

## 📋 Überblick

ZNS ist ein lokales Echtzeit-Nachrichtensystem, das speziell für Arztpraxen und medizinische Einrichtungen entwickelt wurde. Es ermöglicht das Senden von Nachrichten zwischen Arbeitsplätzen (z.B. Empfang → EKG-Raum) über das lokale Netzwerk – **ohne Internetverbindung, ohne Cloud**.

### ✨ Features

| Feature | Beschreibung |
|---|---|
| 💬 **Nachrichten** | Text-Nachrichten an einzelne Zimmer oder an alle (Broadcast) |
| 🔔 **Overlay-Benachrichtigung** | Vollbild-Overlay erscheint bei jeder neuen Nachricht – unübersehbar |
| ✅ **Bestätigungspflicht** | Overlay verschwindet NUR nach aktivem Klick auf „Bestätigen" |
| 🚨 **Notfallknopf** | Sofort-Alarm an alle Arbeitsplätze mit einem Klick |
| 🔄 **Persistenz** | Unbestätigte Nachrichten bleiben nach Neustart erhalten |
| 🚀 **Autostart** | Client startet automatisch mit Windows |
| 🏠 **Zimmer-Verwaltung** | Arbeitsplätze (Zimmer) anlegen und verwalten |
| 📊 **Sendehistorie** | Übersicht der letzten gesendeten Nachrichten mit Bestätigungsstatus |

---

## 🏗️ Architektur

```
┌──────────────┐     WebSocket (ws://)     ┌──────────────┐
│  Electron    │◄─────────────────────────►│  Python      │
│  Client      │                           │  Server      │
│  (Desktop)   │                           │  + SQLite DB │
└──────────────┘                           └──────────────┘
       ▲                                          ▲
       │               LAN-Netzwerk               │
       ▼                                          │
┌──────────────┐     WebSocket (ws://)            │
│  Electron    │◄─────────────────────────────────┘
│  Client      │
│  (Desktop)   │
└──────────────┘
```

| Komponente | Technologie | Zweck |
|---|---|---|
| **Server** | Python + `websockets` | Nachrichtenverteilung, Persistenz |
| **Datenbank** | SQLite | Zimmer, Nachrichten, Bestätigungen |
| **Client** | Electron (Node.js) | Desktop-App mit Overlay |
| **Client-UI** | HTML/CSS/JS | Modernes Dark-Mode Interface |
| **Kommunikation** | WebSocket (`ws://`) | Echtzeit, bidirektional |

---

## 📂 Projektstruktur

```
ZNS/
├── README.md               # Dieses Dokument
├── gemini.md               # Projektverfassung
├── .env                    # Server-Konfiguration (HOST, PORT)
├── architecture/           # SOPs (Standard Operating Procedures)
│   ├── server_sop.md
│   ├── client_sop.md
│   └── database_sop.md
├── server/                 # Python WebSocket-Server
│   ├── server.py           # Hauptserver
│   ├── database.py         # SQLite-Datenbankmodul
│   ├── requirements.txt    # Python-Abhängigkeiten
│   └── start_server.bat    # Server starten (Windows)
└── client/                 # Electron Desktop-Client
    ├── main.js             # Electron Main Process
    ├── preload.js          # IPC-Bridge (Sicherheit)
    ├── package.json        # Node.js Konfiguration
    ├── build_exe.bat       # Portable EXE erstellen
    ├── assets/             # Icons
    └── renderer/           # UI
        ├── index.html      # Hauptfenster
        ├── overlay.html    # Bestätigungs-Overlay
        └── style.css       # Design-System
```

---

## 🚀 Installation & Setup

### Voraussetzungen

| Komponente | Benötigt auf | Version |
|---|---|---|
| **Python** | Server-PC | ≥ 3.9 |
| **Node.js** | Build-PC (nur einmalig zum Bauen) | ≥ 18 |
| **LAN** | Alle PCs | – |

### 1. Server einrichten

```bash
# Repository klonen
git clone https://github.com/lollylan/ZentralesNachrichtenSystem.git
cd ZentralesNachrichtenSystem

#  Python-Umgebung einrichten
cd server
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# .env-Datei anpassen (im Projektordner)
# SERVER_HOST=192.168.10.51   ← IP des Server-PCs
# SERVER_PORT=8765

# Server starten
python server.py
# ODER: start_server.bat doppelklicken
```

### 2. Client bauen (einmalig)

```bash
cd client
npm install

# Portable EXE erstellen
# ODER: build_exe.bat doppelklicken
npx electron-packager . ZNS --platform=win32 --arch=x64 --out=dist --overwrite --asar
```

### 3. Client auf Arbeitsplätze verteilen

1. Den Ordner `client/dist/ZNS-win32-x64/` auf den Client-PC kopieren
2. `ZNS.exe` doppelklicken
3. Beim ersten Start: Server-IP eingeben und Arbeitsplatz-Name wählen
4. **Fertig!** ✅ Keine Installation nötig.

---

## 💡 Nutzung

### Nachricht senden
1. **Empfänger** wählen (einzelnes Zimmer oder „Alle Zimmer")
2. **Nachricht** eingeben
3. **Senden** klicken

### Nachricht empfangen
- Ein **Vollbild-Overlay** erscheint automatisch
- Nachricht lesen → **„Bestätigen"** klicken
- Das Overlay verschwindet erst nach Bestätigung

### Notfall
- **🚨 NOTFALL** Button in der Sidebar
- Sendet sofort einen Alarm an **alle** Arbeitsplätze
- Erfordert Bestätigung vor dem Senden (Sicherheit)

---

## ⚙️ Konfiguration

### Server (.env)
```env
SERVER_HOST=192.168.10.51
SERVER_PORT=8765
```

### Client (automatisch bei Erststart)
Die Client-Konfiguration wird bei der Ersteinrichtung erstellt und in `%APPDATA%/zns-client/config.json` gespeichert:
```json
{
  "server_host": "192.168.10.51",
  "server_port": 8765,
  "room_id": "uuid",
  "room_name": "Empfang"
}
```

---

## 🔒 Sicherheit & Design-Entscheidungen

- **Kein Internet** – Läuft ausschließlich im LAN
- **Kein Cloud-Service** – Alle Daten bleiben lokal
- **Context Isolation** – Electron nutzt `contextIsolation: true`
- **Keine node-Integration** – Renderer hat keinen Zugriff auf Node.js APIs
- **Server = Source of Truth** – Clients vertrauen immer dem Server

---

## 📝 Lizenz

MIT License – © 2026 lolly
