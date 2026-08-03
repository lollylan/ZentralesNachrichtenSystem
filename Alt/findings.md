# findings.md — Recherche, Entdeckungen & Constraints
> **Status:** 🟡 Phase 1 – Blueprint aktiv
> **Letzte Aktualisierung:** 2026-02-27

---

## 🔍 Projekt-Kontext

**ZNS – Zentrales Nachrichten-System** ist eine interne Praxis-Messaging-App ohne Internetabhängigkeit.
Alle Komponenten laufen im lokalen Netzwerk (LAN). Keine externen APIs.

---

## 🏗️ Tech-Stack Entscheidungen

### Server: Python + `websockets` Bibliothek
- **Wahl:** Python `websockets` (asyncio-basiert) ✅
- **Begründung:** Leichtgewichtig, stabil, kein Node.js auf dem Server nötig
- **Vorteil:** asyncio ermöglicht viele gleichzeitige Client-Verbindungen effizient
- **Best Practice:** Heartbeat/Ping-Mechanismus einbauen, damit Verbindungsabbrüche erkannt werden
- **Wichtig:** Rooms werden serverseitig als Dictionary `{room_id: websocket}` verwaltet

### Datenbank: SQLite
- **Wahl:** SQLite ✅
- **Begründung:** Keine Installation, lokal, persistent, gut für kleine Praxisnetzwerke
- **Tabellen geplant:**
  - `rooms` (room_id, room_name, created_at)
  - `messages` (message_id, sender_room, target_room, message_text, timestamp, is_broadcast)
  - `acknowledgments` (message_id, ack_by_room, ack_timestamp)

### Client: Electron
- **Wahl:** Electron ✅
- **Begründung:** Browserunabhängig, native Windows-Integration, `alwaysOnTop`-Overlay möglich
- **Schlüssel-API:** `BrowserWindow` mit `alwaysOnTop: true` + `fullscreen: true` für Overlay
- **Autostart:** Über Windows Registry oder `app.setLoginItemSettings()` in Electron
- **IPC:** `ipcMain` ↔ `ipcRenderer` über `contextBridge` und `preload.js`

---

## 🧩 Technische Entdeckungen

| Datum | Entdeckung | Auswirkung |
|---|---|---|
| 2026-02-27 | Electron `BrowserWindow` unterstützt `alwaysOnTop: true` | Overlay immer sichtbar, auch bei anderen aktiven Fenstern |
| 2026-02-27 | Electron `app.setLoginItemSettings({ openAtLogin: true })` | Einfacher Autostart ohne Registry-Hack |
| 2026-02-27 | Python `websockets` nutzt asyncio – ideal für Broadcast | Server kann alle Clients gleichzeitig benachrichtigen |
| 2026-02-27 | SQLite ist in Python Standard-Library enthalten | Kein `pip install` nötig für DB |
| 2026-02-27 | Unbestätigte Nachrichten müssen beim Reconnect vom Server gepusht werden | Server muss offene ACKs tracken |

---

## ⚠️ Constraints & Risiken

| Constraint | Typ | Schweregrad |
|---|---|---|
| Alle Clients müssen Node.js + Electron installiert haben | Installation | Mittel |
| Server braucht Python 3.10+ und `websockets` pip-Paket | Installation | Niedrig |
| LAN-IP des Servers muss stabil sein (statische IP empfohlen) | Netzwerk | Hoch |
| Electron-App muss als Admin gestartet sein für Autostart | Windows | Mittel |
| Bei Netzwerkausfall: Client muss Reconnect-Logic haben | Robustheit | Hoch |

---

## 📚 Relevante Ressourcen

- [websockets Doku (Python)](https://websockets.readthedocs.io)
- [Electron BrowserWindow API](https://www.electronjs.org/docs/latest/api/browser-window)
- [Electron IPC Dokumentation](https://www.electronjs.org/docs/latest/tutorial/ipc)
- [Electron setLoginItemSettings](https://www.electronjs.org/docs/latest/api/app#appsetloginitemsettingssettings-macos-windows)

---

## 🐛 Bekannte Fehler & Lösungen

*(wird im Laufe des Projekts befüllt)*
