# gemini.md — Projektverfassung (Project Constitution)
> **Status:** � Phase 1 – Blueprint ausstehend (Warten auf Genehmigung)
> **Erstellt:** 2026-02-27
> **Protokoll:** B.L.A.S.T. | Architektur: A.N.T. 3-Layer

---

## 📌 Projekt-Identität

| Feld | Wert |
|---|---|
| **Projektname** | ZNS – Zentrales Nachrichten-System |
| **North Star** | Interne Desktop-App für Praxisnetzwerk: Nachrichten von jedem Arbeitsplatz zu jedem anderen, mit Bestätigungs-Overlay |
| **Eigentümer** | lolly |
| **Phase** | Phase 1 – Blueprint Review |

---

## 📐 Daten-Schema (Data-First Rule)

### Input-Payload (Client → Server)
```json
{
  "type": "send_message",
  "sender_id": "string",
  "sender_name": "string",
  "target_room_id": "string | 'broadcast'",
  "message_text": "string",
  "timestamp": "ISO8601"
}
```

### Output-Payload (Server → Client)
```json
{
  "type": "new_message",
  "message_id": "uuid",
  "sender_name": "string",
  "sender_room": "string",
  "message_text": "string",
  "timestamp": "ISO8601",
  "requires_ack": true
}
```

### Acknowledgment-Payload (Client → Server)
```json
{
  "type": "ack_message",
  "message_id": "uuid",
  "ack_by_room": "string",
  "ack_timestamp": "ISO8601"
}
```

### Zimmer-Schema (Rooms – gespeichert in SQLite)
```json
{
  "room_id": "uuid",
  "room_name": "string",
  "created_at": "ISO8601"
}
```

### Client-Konfiguration (lokal gespeichert: config.json)
```json
{
  "room_id": "uuid",
  "room_name": "string",
  "server_host": "string",
  "server_port": 8765
}
```

---

## 📏 Verhaltensregeln (Behavioral Rules)

1. **Overlay-Pflicht:** Jede eingehende Nachricht erscheint IMMER als zentriertes Vollbild-Overlay – unabhängig vom aktiven Fenster.
2. **Bestätigungspflicht:** Das Overlay verschwindet NUR nach aktivem Klick auf „Bestätigen". Kein automatisches Ausblenden.
3. **Persistenz:** Unbestätigte Nachrichten bleiben auch nach Neustart sichtbar (aus DB geladen).
4. **Autostart:** Der Electron-Client startet automatisch mit Windows.
5. **Zimmer-Gedächtnis:** Client speichert Zimmer-Zuordnung lokal (`config.json`). Beim Neustart wird sie automatisch geladen.
6. **Keine Internetabhängigkeit:** Das gesamte System läuft ausschließlich im lokalen Netzwerk (LAN). Keine Cloud, keine externen APIs.
7. **Broadcast:** Nachricht an alle Zimmer gleichzeitig ist möglich.
8. **NIEMALS:** Nachrichten werden NIEMALS automatisch gelöscht/ausgeblendet, bevor sie bestätigt wurden.
9. **Server-Autorität:** Der Server ist einzige Source of Truth. Clients vertrauen immer dem Server.

---

## 🏗️ Architektur-Invarianten

- **Layer 1 (architecture/):** Technische SOPs in Markdown
- **Layer 2 (Navigation):** Entscheidungslogik – kein direktes Ausführen komplexer Aufgaben
- **Layer 3 (tools/):** Deterministische Python-Skripte, atomar und testbar
- `.env` enthält Serverkonfiguration (Host, Port)
- `.tmp/` enthält alle Zwischendateien (ephemer)

### Tech Stack (festgelegt)
| Komponente | Technologie | Begründung |
|---|---|---|
| Server | Python + WebSockets (websockets lib) | Leichtgewichtig, kein Node.js nötig |
| Datenbank | SQLite | Lokal, keine Installation, persistent |
| Client | Electron (Node.js) | Browserunabhängig, native Windows-Integration, Autostart |
| Client-UI | HTML/CSS/JS (im Electron Renderer) | Maximale Kontrolle über das Overlay |
| Kommunikation | WebSocket-Protokoll (ws://) | Echtzeit, bidirektional |

### Die goldene Regel:
> Wenn sich Logik ändert → zuerst die SOP in `architecture/` aktualisieren, DANN den Code.

---

## 🔌 Integrationen

| Service | Status | Notizen |
|---|---|---|
| Lokales LAN/Netzwerk | ✅ Vorhanden | Praxisnetzwerk bereits vorhanden |
| WebSockets (ws://) | ⬜ Zu konfigurieren | Echtzeit-Kommunikation Server↔Client |
| SQLite (am Server) | ⬜ Zu konfigurieren | Nachrichten- und Raum-Persistenz |
| Electron (Client-App) | ⬜ Zu bauen | Desktop-App für alle Arbeitsplätze |
| Python (Server) | ⬜ Zu bauen | WebSocket-Server |
| Windows Autostart | ⬜ Zu konfigurieren | Electron-Client startet mit Windows |

---

## � Dateistruktur (geplant)

```
ZNS/
├── gemini.md               # Projektverfassung (dieses Dokument)
├── task_plan.md            # Phasenplan
├── findings.md             # Recherche & Entdeckungen
├── progress.md             # Fortschrittsprotokoll
├── .env                    # Server-Konfiguration
├── architecture/           # Layer 1: SOPs
│   ├── server_sop.md
│   ├── client_sop.md
│   └── database_sop.md
├── server/                 # Python WebSocket-Server
│   ├── server.py
│   ├── database.py
│   └── requirements.txt
├── client/                 # Electron-App
│   ├── package.json
│   ├── main.js             # Electron Main Process
│   ├── preload.js
│   └── renderer/           # UI (HTML/CSS/JS)
│       ├── index.html
│       ├── overlay.html
│       └── style.css
└── .tmp/                   # Temporäre Dateien (ephemer)
```

---

## �📋 Wartungsprotokoll (Maintenance Log)

| Datum | Änderung | Grund |
|---|---|---|
| 2026-02-27 | Datei erstellt | Protocol 0 Initialisierung |
| 2026-02-27 | Discovery-Antworten + Schema eingetragen | Phase 1 Blueprint |

---

*Diese Datei ist Gesetz. Änderungen nur bei Schema-Änderungen, neuen Regeln oder Architekturmodifikationen.*
