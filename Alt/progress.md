# progress.md — Fortschrittsprotokoll
> **Status:** 🟡 Phase 5 – Bug-Fixes angewendet, neu testen
> **Letzte Aktualisierung:** 2026-02-27

---

## 📊 Aktueller Stand

**Aktuelle Phase:** Bug-Fix Session (nach erstem Live-Test)
**Letzter Schritt:** UUID-Mismatch-Bug behoben, delete_room hinzugefügt
**Nächster Schritt:** Server neu starten, Client-Builds neu erstellen, erneut testen

---

## 📝 Aktivitätslog

### 2026-02-27 – Session 1 (Initialisierung)
- ✅ `gemini.md`, `task_plan.md`, `findings.md`, `progress.md` erstellt

### 2026-02-27 – Session 2 (Build)
- ✅ Alle Server- und Client-Dateien erstellt
- ✅ dist/ZNS-win32-x64/ZNS.exe gebaut (169 MB, portable)

### 2026-02-27 – Session 3 (Bug-Fix nach Live-Test)
- ✅ **Bug gefixt: UUID-Mismatch** 
  - Ursache: `create_room()` erzeugte neue UUID statt Client-UUID zu verwenden
  - Fix: Neue Funktion `ensure_room(room_id, room_name)` in `database.py`
  - Server nutzt jetzt die Client-UUID als führende ID → `connected{}` und DB sind synchron
- ✅ **DeprecationWarning gefixt**
  - `websockets.WebSocketServerProtocol` → `Any` (neue websockets-API)
- ✅ **Feature: Zimmer löschen**
  - `delete_room()` in `database.py` (mit Kaskadenlöschung Nachrichten+ACKs)
  - `delete_room`-Handler in `server.py` (eigenes Zimmer geschützt)
  - `delete-room` IPC-Handler in `main.js`
  - `deleteRoom()` in `preload.js`
  - Löschen-Button mit Bestätigungsdialog in `index.html`

---

## ⚠️ Wichtig nach dem Update

**Die bestehende `zns.db` enthält fehlerhafte UUIDs!**
Bitte die DB löschen bevor du den Server neu startest:
```
server\zns.db → löschen
```
Server dann neu starten → frische DB wird automatisch erstellt.
Alle Clients dann neu einrichten (oder config.json in %APPDATA%\zns-client\ löschen).

---

## 🧪 Tests & Ergebnisse

| Datum | Test | Ergebnis | Notizen |
|---|---|---|---|
| 2026-02-27 | Server starten | ✅ OK | Läuft auf 0.0.0.0:8765 |
| 2026-02-27 | Client verbinden | ✅ OK | Verbindung erfolgreich |
| 2026-02-27 | Zimmer registrieren | ✅ OK | 'Anmeldung links', 'Server Test 2' |
| 2026-02-27 | Nachricht senden | ❌ Bug | UUID-Mismatch → offline gespeichert |
| 2026-02-27 | UUID-Bug-Fix | ✅ Gefixt | ensure_room() implementiert |

---

## ❌ Fehler & Korrekturen (Self-Annealing Log)

| Datum | Fehler | Ursache | Lösung | SOP aktualisiert? |
|---|---|---|---|---|
| 2026-02-27 | Nachrichten werden als 'offline' gespeichert | Client-UUID ≠ DB-UUID | `ensure_room()` statt `create_room()` im register-Handler | Nein (trivial) |
| 2026-02-27 | DeprecationWarning `WebSocketServerProtocol` | websockets 12+ API | `Any` Typ-Hint verwendet | Nein |
