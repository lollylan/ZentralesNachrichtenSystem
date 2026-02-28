# client_sop.md — Client-SOP: Electron-App

## Zweck
Der ZNS-Client ist eine Electron-Desktop-App auf jedem Arbeitsplatz. Er zeigt eingehende Nachrichten als Vollbild-Overlay und ermöglicht das Senden von Nachrichten.

## Technologie
- **Electron** (Chromium + Node.js)
- **WebSocket-Client:** `ws` npm-Paket (Main Process)
- **IPC:** `contextBridge` + `preload.js`

## Starten (Entwicklung)
```bash
cd client/
npm install
npm start
```
Oder: `start_client.bat` doppelklicken.

## Architektur

```
main.js (Node.js/Main Process)
  ├── WebSocket-Verbindung (ws-Paket)
  ├── Nachrichten-Queue (messageQueue[])
  ├── Window Management
  │   ├── mainWindow  → index.html (Haupt-UI)
  │   └── overlayWindow → overlay.html (Vollbild-Overlay)
  └── IPC Handler (ipcMain.handle)

preload.js (Bridge)
  └── contextBridge.exposeInMainWorld('zns', {...})

renderer/ (Chromium/Renderer Process)
  ├── index.html  → Nachrichten senden, Zimmer, Einstellungen
  └── overlay.html → Vollbild-Bestätigungsoverlay
```

## Konfiguration
Gespeichert in: `%APPDATA%\zns-client\config.json`
```json
{
  "server_host": "192.168.10.51",
  "server_port": 8765,
  "room_id": "uuid",
  "room_name": "Empfang"
}
```

## Overlay-Verhalten
1. Nachricht eingehend → in `messageQueue` legen
2. Wenn kein Overlay aktiv: `showNextOverlay()` aufrufen
3. Overlay zeigt Nachricht + "Bestätigen"-Button
4. Klick auf "Bestätigen" → ACK an Server → `showNextOverlay()`
5. Queue leer → Overlay verstecken

## Reconnect-Logic
- Bei Verbindungsabbruch: Automatischer Reconnect nach 3 Sekunden
- Bei Reconnect: Server sendet automatisch ausstehende Nachrichten

## Autostart (Windows)
Wird über `app.setLoginItemSettings({ openAtLogin: true })` konfiguriert.
Aktiv nur wenn App gepackt (`app.isPackaged === true`).

## Fehlerbehebung
| Problem | Lösung |
|---|---|
| `Cannot find module 'ws'` | `npm install` im `client/`-Verzeichnis ausführen |
| Overlay erscheint nicht | `alwaysOnTop`-Level prüfen, ggf. als Admin starten |
| Verbindung schlägt fehl | Server-IP und Port in Einstellungen prüfen |
