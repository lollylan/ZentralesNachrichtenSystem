"""
ZNS – Zentrales Nachrichten-System
server.py – WebSocket-Server für das Praxisnetz

Start:  python server.py
        oder start_server.bat doppelklicken

Läuft unverschlüsselt (ws://) – das System ist ausschliesslich für das
interne Praxisnetz gedacht und geht nie ins Internet.

Zusätzlich läuft ein UDP-Suchdienst auf Port 8766: Clients finden den
Server damit automatisch, auch wenn sich seine IP-Adresse geändert hat.
"""

import asyncio
import json
import logging
import socket
from typing import Any

import websockets

from database import Database

WS_PORT = 8765        # WebSocket-Port für die Nachrichten
DISCOVERY_PORT = 8766  # UDP-Port für die automatische Serversuche
DISCOVERY_MAGIC = "ZNS_DISCOVER"

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)-7s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("ZNS")

db = Database()

# Aktuell verbundene Clients: {room_id: websocket}
connected: dict[str, Any] = {}


# ──────────────────────────── Hilfsfunktionen ────────────────────────────

def local_ip() -> str:
    """Ermittelt die LAN-IP dieses Rechners (ohne echte Verbindung aufzubauen)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


async def send_to(ws: Any, payload: dict) -> bool:
    """Sendet JSON an einen Client. Gibt False zurück, wenn die Verbindung weg ist."""
    try:
        await ws.send(json.dumps(payload, ensure_ascii=False))
        return True
    except Exception:
        return False


async def send_to_room(room_id: str, payload: dict) -> bool:
    """Sendet an ein Zimmer, sofern es gerade verbunden ist."""
    ws = connected.get(room_id)
    if not ws:
        return False
    return await send_to(ws, payload)


async def broadcast_room_list():
    """Verteilt die aktuelle Zimmerliste mit Online-Status an alle Clients."""
    rooms = db.get_all_rooms()
    for room in rooms:
        room["online"] = room["room_id"] in connected

    for room_id, ws in list(connected.items()):
        await send_to(ws, {
            "type": "rooms_update",
            "rooms": rooms,
            "unread": db.get_unread_counts(room_id),
        })


async def deliver_message(msg: dict) -> dict:
    """
    Stellt eine Nachricht zu, sofern der Empfänger online ist,
    und vermerkt den Zustellzeitpunkt in der Datenbank.
    """
    target_id = msg["target_id"]
    if target_id in connected:
        ok = await send_to_room(target_id, {"type": "new_message", "message": msg})
        if ok:
            ts = db.mark_delivered(msg["message_id"])
            msg["delivered_at"] = ts or msg.get("delivered_at")
    return msg


# ──────────────────────────── Nachrichten-Handler ────────────────────────────

async def handle_register(ws, data) -> tuple[str, str]:
    """Meldet ein Zimmer an und liefert ihm alles Ausstehende nach."""
    room_id = data.get("room_id")
    room_name = (data.get("room_name") or "").strip() or "Unbenannt"

    if not room_id:
        await send_to(ws, {"type": "error", "message": "Keine Zimmer-ID übermittelt."})
        return None, None

    # Ein bereits verbundener Client mit derselben ID wird ersetzt
    if room_id in connected and connected[room_id] is not ws:
        log.info(f"  Zimmer '{room_name}' verbindet sich neu")

    connected[room_id] = ws
    db.ensure_room(room_id, room_name)
    log.info(f"  Angemeldet: '{room_name}' ({room_id[:8]}…)")

    await send_to(ws, {
        "type": "registered",
        "room_id": room_id,
        "room_name": room_name,
    })

    # Ungelesene Nachrichten nachliefern
    unread = db.get_unread_messages(room_id)
    for msg in unread:
        await send_to(ws, {"type": "new_message", "message": msg})
        db.mark_delivered(msg["message_id"])
    if unread:
        log.info(f"  → {len(unread)} ungelesene Nachricht(en) nachgeliefert")

    await broadcast_room_list()
    return room_id, room_name


async def handle_send_message(ws, data, room_id: str, room_name: str):
    """Nimmt eine Nachricht entgegen und leitet sie weiter."""
    text = (data.get("message_text") or "").strip()
    target_id = data.get("target_id") or ""

    if not text or not room_id:
        return

    if target_id == "broadcast":
        targets = [r["room_id"] for r in db.get_all_rooms() if r["room_id"] != room_id]
    else:
        targets = [target_id]

    sent = []
    for tid in targets:
        msg = db.save_message(room_id, tid, text, is_emergency=False)
        msg["sender_name"] = room_name
        msg = await deliver_message(msg)
        sent.append(msg)

        status = "zugestellt" if tid in connected else "wartet (offline)"
        log.info(f"  '{room_name}' → '{tid[:8]}…': {text[:40]} [{status}]")

    # Absender bekommt seine eigenen Nachrichten zurück, damit sein
    # Chat-Verlauf sofort aktuell ist (inkl. Zustellstatus)
    await send_to(ws, {"type": "messages_sent", "messages": sent})


async def handle_emergency(ws, room_id: str, room_name: str):
    """Notfallruf an alle anderen Zimmer."""
    if not room_id:
        return

    text = f"NOTFALL – bitte sofort zu {room_name} kommen!"
    targets = [r["room_id"] for r in db.get_all_rooms() if r["room_id"] != room_id]

    sent = []
    for tid in targets:
        msg = db.save_message(room_id, tid, text, is_emergency=True)
        msg["sender_name"] = room_name
        msg = await deliver_message(msg)
        sent.append(msg)

    log.warning(f"  NOTFALL von '{room_name}' – {len(targets)} Zimmer alarmiert")
    await send_to(ws, {"type": "messages_sent", "messages": sent})


async def handle_mark_read(data, room_id: str):
    """Bestätigt eine Nachricht und meldet den Lesestatus an den Absender zurück."""
    message_id = data.get("message_id")
    if not message_id or not room_id:
        return

    result = db.mark_read(message_id, room_id)
    if not result:
        return

    # Absender über den Lesestatus informieren (Auto-Refresh der Haken)
    await send_to_room(result["sender_id"], {
        "type": "read_receipt",
        "message_id": message_id,
        "read_at": result["read_at"],
        "reader_id": room_id,
    })
    await broadcast_room_list()


async def handle_get_conversation(ws, data, room_id: str):
    partner_id = data.get("partner_id")
    if not partner_id or not room_id:
        return
    messages = db.get_conversation(room_id, partner_id)
    await send_to(ws, {
        "type": "conversation",
        "partner_id": partner_id,
        "messages": messages,
    })


async def handle_delete_room(ws, data, room_id: str):
    target = data.get("room_id")
    if not target:
        return
    if target == room_id:
        await send_to(ws, {
            "type": "error",
            "message": "Das eigene Zimmer kann nicht gelöscht werden.",
        })
        return

    if db.delete_room(target):
        connected.pop(target, None)
        log.info(f"  Zimmer gelöscht: {target[:8]}…")
        await broadcast_room_list()
    else:
        await send_to(ws, {"type": "error", "message": "Zimmer nicht gefunden."})


# ──────────────────────────── Verbindungs-Schleife ────────────────────────────

async def handle_client(ws):
    room_id = None
    room_name = "Unbekannt"
    peer = ws.remote_address[0] if ws.remote_address else "?"
    log.info(f"Neue Verbindung von {peer}")

    try:
        async for raw in ws:
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                log.warning(f"  Ungültiges JSON von {peer}")
                continue

            msg_type = data.get("type", "")

            if msg_type == "register":
                new_id, new_name = await handle_register(ws, data)
                if new_id:
                    room_id, room_name = new_id, new_name

            elif msg_type == "send_message":
                await handle_send_message(ws, data, room_id, room_name)

            elif msg_type == "emergency":
                await handle_emergency(ws, room_id, room_name)

            elif msg_type == "mark_read":
                await handle_mark_read(data, room_id)

            elif msg_type == "get_conversation":
                await handle_get_conversation(ws, data, room_id)

            elif msg_type == "get_rooms":
                await broadcast_room_list()

            elif msg_type == "rename_room":
                new_name = (data.get("room_name") or "").strip()
                if new_name and room_id:
                    db.rename_room(room_id, new_name)
                    room_name = new_name
                    log.info(f"  Zimmer umbenannt: '{new_name}'")
                    await broadcast_room_list()

            elif msg_type == "delete_room":
                await handle_delete_room(ws, data, room_id)

            elif msg_type == "ping":
                await send_to(ws, {"type": "pong"})

            else:
                log.warning(f"  Unbekannter Nachrichtentyp: '{msg_type}'")

    except websockets.exceptions.ConnectionClosed:
        pass
    except Exception as e:
        log.error(f"Fehler in der Verbindung von {peer}: {e}", exc_info=True)
    finally:
        # Nur austragen, wenn dieser Socket noch der aktuelle ist
        if room_id and connected.get(room_id) is ws:
            del connected[room_id]
            db.touch_room(room_id)
            log.info(f"Getrennt: '{room_name}' ({peer})")
            await broadcast_room_list()


# ──────────────────────────── UDP-Suchdienst ────────────────────────────

class DiscoveryProtocol(asyncio.DatagramProtocol):
    """
    Antwortet auf UDP-Broadcasts der Clients.
    Dadurch findet ein Client den Server auch dann, wenn dessen
    IP-Adresse sich geändert hat.
    """

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data: bytes, addr):
        try:
            if data.decode("utf-8", errors="ignore").strip() != DISCOVERY_MAGIC:
                return
        except Exception:
            return

        antwort = json.dumps({
            "service": "ZNS",
            "ws_port": WS_PORT,
            "hostname": socket.gethostname(),
        })
        self.transport.sendto(antwort.encode("utf-8"), addr)
        log.info(f"  Suchanfrage von {addr[0]} beantwortet")


async def start_discovery_service():
    loop = asyncio.get_running_loop()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.bind(("0.0.0.0", DISCOVERY_PORT))

    await loop.create_datagram_endpoint(DiscoveryProtocol, sock=sock)
    log.info(f"  Suchdienst aktiv auf UDP-Port {DISCOVERY_PORT}")


# ──────────────────────────── Start ────────────────────────────

async def main():
    ip = local_ip()

    log.info("=" * 58)
    log.info("  ZNS – Zentrales Nachrichten-System")
    log.info("")
    log.info(f"  Server-Adresse für die Clients:  {ip}")
    log.info(f"  Port:                            {WS_PORT}")
    log.info("")
    log.info("  Die Clients finden den Server auch automatisch,")
    log.info("  falls sich diese IP-Adresse einmal ändert.")
    log.info("")
    log.info("  Beenden mit Strg+C")
    log.info("=" * 58)

    await start_discovery_service()

    async with websockets.serve(
        handle_client,
        "0.0.0.0",
        WS_PORT,
        ping_interval=20,
        ping_timeout=20,
        max_size=256 * 1024,
    ):
        await asyncio.Future()  # läuft dauerhaft


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Server beendet.")
