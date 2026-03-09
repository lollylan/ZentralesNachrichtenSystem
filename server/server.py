"""
ZNS – Zentrales Nachrichten-System
WebSocket-Server (Python)

Start: python server.py
"""

import asyncio
import datetime
import json
import logging
import ssl
from pathlib import Path
from typing import Any

import websockets
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from database import Database

# ──────────────────────────── Logging ────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("ZNS-Server")

# ──────────────────────────── Zustand ────────────────────────────
db = Database()

# Verbundene Clients: {room_id: websocket}
# Typ-Hint als Any, um Deprecation-Warning der alten WebSocketServerProtocol zu vermeiden
connected: dict[str, Any] = {}


# ──────────────────────────── Hilfsfunktionen ────────────────────────────

async def _send(ws: Any, payload: dict):
    """Sendet JSON sicher an einen einzelnen Client."""
    try:
        await ws.send(json.dumps(payload, ensure_ascii=False))
    except Exception:
        pass


async def _broadcast_rooms():
    """Sendet die aktuelle Zimmerliste an ALLE verbundenen Clients."""
    rooms = db.get_all_rooms()
    msg = {"type": "rooms_update", "rooms": rooms}
    for ws in list(connected.values()):
        await _send(ws, msg)


async def _send_pending_messages(room_id: str, ws: Any):
    """Sendet alle unbestätigten Nachrichten an einen frisch verbundenen Client."""
    pending = db.get_pending_messages(room_id)
    for msg in pending:
        await _send(ws, msg)
    if pending:
        log.info(f"  → {len(pending)} ausstehende Nachricht(en) an '{room_id}' gesendet")


# ──────────────────────────── Handler ────────────────────────────

async def handle_client(ws: Any):
    """Haupthandler für jeden verbundenen Client."""
    room_id = None
    room_name = "Unbekannt"
    remote = ws.remote_address

    log.info(f"Neue Verbindung: {remote}")

    try:
        async for raw in ws:
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                log.warning(f"Ungültige JSON-Nachricht von {remote}")
                continue

            msg_type = data.get("type", "")

            # ── REGISTER ──────────────────────────────────────────
            if msg_type == "register":
                room_id = data.get("room_id")
                room_name = data.get("room_name", room_id)

                if not room_id:
                    continue

                # Doppelte Verbindung: alten Socket ersetzen
                if room_id in connected:
                    log.info(f"  Reconnect: '{room_name}'")

                connected[room_id] = ws
                log.info(f"  Zimmer registriert: '{room_name}' ({room_id})")

                # *** BUGFIX: ensure_room nutzt die Client-UUID als führende ID ***
                # Damit stimmen connected{} und DB-Zimmerlist immer überein!
                db.ensure_room(room_id, room_name)

                # Ausstehende Nachrichten senden
                await _send_pending_messages(room_id, ws)

                # Alle Clients über neue Zimmerliste informieren
                await _broadcast_rooms()

            # ── GET_ROOMS ──────────────────────────────────────────
            elif msg_type == "get_rooms":
                rooms = db.get_all_rooms()
                await _send(ws, {"type": "rooms_update", "rooms": rooms})

            # ── SEND_MESSAGE ───────────────────────────────────────
            elif msg_type == "send_message":
                sender_name = data.get("sender_name", room_name)
                target = data.get("target_room_id", "")
                text = data.get("message_text", "").strip()

                if not text:
                    continue

                # Ziel-Zimmer bestimmen
                if target == "broadcast":
                    all_rooms = db.get_all_rooms()
                    targets = [r for r in all_rooms if r["room_id"] != room_id]
                    is_bc = True
                else:
                    targets = [{"room_id": target}]
                    is_bc = False

                for t in targets:
                    tid = t["room_id"]
                    msg_id = db.save_message(sender_name, tid, text, is_bc)

                    outgoing = {
                        "type": "new_message",
                        "message_id": msg_id,
                        "sender_name": sender_name,
                        "sender_room": sender_name,
                        "message_text": text,
                        "requires_ack": True,
                    }

                    if tid in connected:
                        await _send(connected[tid], outgoing)
                        log.info(f"  Nachricht von '{sender_name}' → '{tid}': {text[:40]}")
                    else:
                        log.info(f"  Nachricht gespeichert ('{tid}' offline)")

            # ── ACK_MESSAGE ────────────────────────────────────────
            elif msg_type == "ack_message":
                msg_id = data.get("message_id")
                ack_room = data.get("ack_by_room", room_id)
                if msg_id:
                    db.acknowledge_message(msg_id, ack_room)
                    log.info(f"  ACK: '{msg_id[:8]}…' von '{ack_room}'")

            # ── CREATE_ROOM ────────────────────────────────────────
            elif msg_type == "create_room":
                new_name = data.get("room_name", "").strip()
                if new_name:
                    db.create_room(new_name)
                    log.info(f"  Neues Zimmer erstellt: '{new_name}'")
                    await _broadcast_rooms()

            # ── DELETE_ROOM ────────────────────────────────────────
            elif msg_type == "delete_room":
                del_id = data.get("room_id", "")
                if del_id:
                    # Eigenes Zimmer darf nicht gelöscht werden
                    if del_id == room_id:
                        await _send(ws, {
                            "type": "error",
                            "message": "Das eigene Zimmer kann nicht gelöscht werden."
                        })
                        continue
                    success = db.delete_room(del_id)
                    if success:
                        log.info(f"  Zimmer gelöscht: '{del_id}'")
                        await _broadcast_rooms()
                    else:
                        await _send(ws, {"type": "error", "message": "Zimmer nicht gefunden."})

            # ── EMERGENCY_CALL ─────────────────────────────────────
            elif msg_type == "emergency_call":
                if not room_id:
                    continue
                emergency_text = f"🚨 NOTFALL – Bitte sofort zu {room_name} kommen! 🚨"
                all_rooms = db.get_all_rooms()
                targets = [r for r in all_rooms if r["room_id"] != room_id]

                for t in targets:
                    tid = t["room_id"]
                    msg_id = db.save_message(room_name, tid, emergency_text, is_broadcast=True)
                    outgoing = {
                        "type": "new_message",
                        "message_id": msg_id,
                        "sender_name": room_name,
                        "sender_room": room_name,
                        "message_text": emergency_text,
                        "requires_ack": True,
                        "is_emergency": True,
                    }
                    if tid in connected:
                        await _send(connected[tid], outgoing)
                    # Wenn offline: Nachricht wurde bereits in DB gespeichert

                log.info(f"  🚨 NOTFALL von '{room_name}' – {len(targets)} Zimmer alarmiert!")

            # ── GET_SENT_MESSAGES ──────────────────────────────────
            elif msg_type == "get_sent_messages":
                if room_name:
                    sent = db.get_sent_messages(room_name, limit=5)
                    await _send(ws, {"type": "sent_messages", "messages": sent})

            else:
                log.warning(f"  Unbekannter Nachrichtentyp: '{msg_type}'")

    except websockets.exceptions.ConnectionClosed:
        pass
    except Exception as e:
        log.error(f"Fehler im Handler: {e}", exc_info=True)
    finally:
        if room_id and connected.get(room_id) is ws:
            del connected[room_id]
            log.info(f"Verbindung getrennt: '{room_name}' ({remote})")
            await _broadcast_rooms()


# ──────────────────────────── TLS ─────────────────────────────

def ensure_ssl_cert(cert_dir: Path):
    """Erstellt ein self-signed TLS-Zertifikat beim ersten Start automatisch."""
    cert_dir.mkdir(exist_ok=True)
    cert_path = cert_dir / "server.crt"
    key_path = cert_dir / "server.key"

    if cert_path.exists() and key_path.exists():
        return cert_path, key_path

    log.info("Erstelle selbst-signiertes TLS-Zertifikat …")
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "ZNS-Server")])
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.utcnow())
        .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=3650))
        .sign(key, hashes.SHA256())
    )

    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        )
    )
    log.info(f"  Zertifikat gespeichert: {cert_path}")
    return cert_path, key_path


# ──────────────────────────── Main ────────────────────────────

async def main():
    host = "0.0.0.0"
    port = 8765

    # SSL-Kontext aufbauen (Cert wird auto-generiert falls nicht vorhanden)
    cert_path, key_path = ensure_ssl_cert(Path("certs"))
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.load_cert_chain(certfile=cert_path, keyfile=key_path)

    log.info("=" * 50)
    log.info("  ZNS – Zentrales Nachrichten-System")
    log.info(f"  Server läuft auf {host}:{port} (WSS/TLS)")
    log.info("  Zum Beenden: Strg+C")
    log.info("=" * 50)

    async with websockets.serve(
        handle_client,
        host,
        port,
        ssl=ssl_context,
        ping_interval=20,
        ping_timeout=10,
    ):
        await asyncio.Future()  # läuft für immer


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Server gestoppt.")
