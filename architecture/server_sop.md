# server_sop.md — Server-SOP: Python WebSocket-Server

## Zweck
Der ZNS-Server ist der einzige Vermittler zwischen allen Clients. Er empfängt Nachrichten, leitet sie weiter, speichert sie persistent und verwaltet Zimmer.

## Technologie
- **Python 3.10+**
- **Bibliothek:** `websockets` (asyncio-basiert)
- **Datenbank:** SQLite (`zns.db` im Serververzeichnis)

## Starten
```bash
cd server/
python -m venv venv
venv\Scripts\pip install -r requirements.txt
venv\Scripts\python server.py
```
Oder: `start_server.bat` doppelklicken.

## Nachrichten-Protokoll (WebSocket-JSON)

| Typ | Richtung | Beschreibung |
|---|---|---|
| `register` | Client→Server | Zimmer anmelden, ausstehende Nachrichten werden gesendet |
| `get_rooms` | Client→Server | Aktuelle Zimmerliste anfordern |
| `send_message` | Client→Server | Nachricht senden (oder Broadcast) |
| `ack_message` | Client→Server | Nachricht bestätigen |
| `create_room` | Client→Server | Neues Zimmer anlegen |
| `new_message` | Server→Client | Eingehende Nachricht (Overlay auslösen) |
| `rooms_update` | Server→Client | Aktualisierte Zimmerliste |

## Wichtige Regeln
1. **Reconnect:** Gleiche `room_id` darf erneut verbinden – altes Socket wird ersetzt.
2. **Ausstehende Nachrichten:** Werden beim `register` automatisch gesendet.
3. **Broadcast:** `target_room_id: "broadcast"` → alle Zimmer außer Sender.
4. **`0.0.0.0`:** Server lauscht auf allen Interfaces – erreichbar aus dem gesamten LAN.

## Fehlerbehebung
| Fehler | Lösung |
|---|---|
| Port bereits belegt | Anderen Port in `.env` konfigurieren |
| `ModuleNotFoundError: websockets` | `pip install -r requirements.txt` |
| Clients verbinden sich nicht | Firewall-Regel für Port 8765 (TCP) prüfen |
