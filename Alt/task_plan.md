# task_plan.md — Projektplan & Checklisten
> **Status:** 🟡 Phase 1 – Blueprint Review
> **Letzte Aktualisierung:** 2026-02-27

---

## 🎯 Ziel (North Star)
**ZNS – Zentrales Nachrichten-System:**
Interne Desktop-App für ein Praxisnetzwerk, bei der Mitarbeiter von jedem Arbeitsplatz aus schnelle Nachrichten an jeden anderen Arbeitsplatz schicken können. Nachrichten erscheinen als Vollbild-Overlay in der Mitte des Bildschirms und müssen aktiv bestätigt werden.

---

## 📋 B.L.A.S.T. Phasenübersicht

| Phase | Name | Status | Freigabe |
|---|---|---|---|
| Phase 0 | Initialisierung | ✅ Abgeschlossen | ✅ |
| Phase 1 | Blueprint | 🟡 Warte auf Genehmigung | ⬜ Noch nicht |
| Phase 2 | Link | 🔴 Ausstehend | ⬜ Nicht freigegeben |
| Phase 3 | Architect | 🔴 Ausstehend | ⬜ Nicht freigegeben |
| Phase 4 | Stylize | 🔴 Ausstehend | ⬜ Nicht freigegeben |
| Phase 5 | Trigger | 🔴 Ausstehend | ⬜ Nicht freigegeben |

---

## ✅ Phase 0 – Initialisierungs-Checkliste

- [x] `gemini.md` erstellt
- [x] `task_plan.md` erstellt
- [x] `findings.md` erstellt
- [x] `progress.md` erstellt
- [x] Discovery-Fragen gestellt
- [x] Discovery-Antworten erhalten
- [x] Daten-Schema in `gemini.md` definiert
- [ ] Blueprint genehmigt ← **AKTUELLER SCHRITT**

---

## 📦 Phase 1 – Blueprint-Checkliste

- [x] North Star definiert: Praxis-Messaging mit Bestätigungs-Overlay
- [x] Integrationen: Nur LAN – kein externer Service benötigt
- [x] Datenquelle (Source of Truth): SQLite-Datenbank am Server
- [x] Delivery-Payload: Electron-Overlay-Fenster auf allen Clients
- [x] Verhaltensregeln in `gemini.md` festgelegt
- [x] JSON Input/Output/Ack Schema in `gemini.md` gespeichert
- [ ] Blueprint vom User genehmigt ← **WARTE AUF BESTÄTIGUNG**

### SOPs zu erstellen (nach Genehmigung):
- [ ] `architecture/server_sop.md` – Python WebSocket-Server
- [ ] `architecture/client_sop.md` – Electron-Client
- [ ] `architecture/database_sop.md` – SQLite-Schema & Queries

---

## 🔌 Phase 2 – Link-Checkliste

*(nach Phase 1 freigeben)*

- [ ] Python-Umgebung auf Server prüfen
- [ ] `websockets` Bibliothek installierbar?
- [ ] Node.js + Electron installierbar auf Client-PC?
- [ ] Netzwerk-Verbindung (LAN) Server ↔ Client testbar?
- [ ] Minimaler WebSocket-Handshake erfolgreich?

---

## ⚙️ Phase 3 – Architect-Checkliste

*(nach Phase 2 freigeben)*

### Server (Python)
- [ ] `server/server.py` – WebSocket-Server mit Routing
- [ ] `server/database.py` – SQLite-Wrapper (Rooms, Messages, Acks)
- [ ] `server/requirements.txt` – Dependencies
- [ ] Zimmer erstellen/auflisten (REST oder WS-Kommando)
- [ ] Nachricht empfangen + an Ziel-Room weiterleiten
- [ ] Ack empfangen + in DB speichern
- [ ] Broadcast an alle Rooms
- [ ] Unbestätigte Nachrichten beim Client-Connect senden

### Client (Electron)
- [ ] `client/main.js` – Hauptprozess, Window-Management
- [ ] `client/preload.js` – Sicherer IPC-Bridge
- [ ] `client/renderer/index.html` – Haupt-UI (Nachrichten senden)
- [ ] `client/renderer/overlay.html` – Vollbild-Overlay
- [ ] `client/renderer/style.css` – Styling
- [ ] Room-Auswahl beim Erststart (mit Speicherung in `config.json`)
- [ ] Autostart-Eintrag in Windows Registry
- [ ] WebSocket-Verbindung mit Reconnect-Logic

---

## ✨ Phase 4 – Stylize-Checkliste

- [ ] Overlay-Design (gut sichtbar, professionell, medizinischer Kontext)
- [ ] Hauptfenster-Design (Nachrichten senden, Raum-Auswahl)
- [ ] Responsive Layout
- [ ] Feedback vom User einholen

---

## 🛰️ Phase 5 – Trigger-Checkliste

- [ ] Server als Windows-Dienst oder als Task Scheduler einrichten
- [ ] Client-Autostart konfigurieren
- [ ] `gemini.md` Wartungslog finalisieren
- [ ] README.md erstellen

---

## 🚫 Ausführungs-Sperren (Execution Guards)

> Diese Bedingungen MÜSSEN erfüllt sein, bevor Skripte in `server/` oder `client/` geschrieben werden:

1. ✅ Discovery-Antworten vollständig
2. ✅ Daten-Schema in `gemini.md` definiert
3. ❌ Blueprint vom User genehmigt → **NOCH OFFEN**
