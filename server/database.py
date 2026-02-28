import sqlite3
import uuid
from datetime import datetime, timezone

DB_PATH = "zns.db"


class Database:
    """SQLite-Wrapper für ZNS – Zimmer, Nachrichten und Bestätigungen."""

    def __init__(self):
        self._init_db()

    def _get_conn(self):
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Erstellt alle Tabellen falls nicht vorhanden."""
        with self._get_conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS rooms (
                    room_id   TEXT PRIMARY KEY,
                    room_name TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS messages (
                    message_id   TEXT PRIMARY KEY,
                    sender_room  TEXT NOT NULL,
                    target_room  TEXT NOT NULL,
                    message_text TEXT NOT NULL,
                    timestamp    TEXT NOT NULL,
                    is_broadcast INTEGER DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS acknowledgments (
                    message_id   TEXT NOT NULL,
                    ack_by_room  TEXT NOT NULL,
                    ack_timestamp TEXT NOT NULL,
                    PRIMARY KEY (message_id, ack_by_room)
                );
            """)
            conn.commit()

    # ──────────────────────────── ROOMS ────────────────────────────

    def get_all_rooms(self):
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT room_id, room_name, created_at FROM rooms ORDER BY room_name"
            ).fetchall()
        return [dict(r) for r in rows]

    def ensure_room(self, room_id: str, room_name: str) -> dict:
        """
        Registriert ein Zimmer mit der vom Client vorgegebenen room_id.
        - Existiert room_id bereits → no-op, bestehenden Eintrag zurückgeben.
        - Existiert room_name mit anderer ID → room_id und name updaten (Rename nach Neustart)
        - Neu → einfügen.
        WICHTIG: Die Client-ID ist führend, damit connected{} und DB übereinstimmen.
        """
        created_at = datetime.now(timezone.utc).isoformat()
        with self._get_conn() as conn:
            # Prüfen ob room_id schon korrekt eingetragen ist
            existing = conn.execute(
                "SELECT room_id, room_name FROM rooms WHERE room_id = ?", (room_id,)
            ).fetchone()
            if existing:
                return dict(existing)

            # Prüfen ob room_name mit anderer ID existiert → update
            name_conflict = conn.execute(
                "SELECT room_id FROM rooms WHERE room_name = ?", (room_name,)
            ).fetchone()
            if name_conflict:
                # Alten Eintrag auf neue room_id aktualisieren
                conn.execute(
                    "UPDATE rooms SET room_id = ? WHERE room_name = ?",
                    (room_id, room_name),
                )
                conn.commit()
                return {"room_id": room_id, "room_name": room_name, "created_at": created_at}

            # Neu einfügen
            conn.execute(
                "INSERT INTO rooms (room_id, room_name, created_at) VALUES (?, ?, ?)",
                (room_id, room_name, created_at),
            )
            conn.commit()
        return {"room_id": room_id, "room_name": room_name, "created_at": created_at}

    def create_room(self, room_name: str) -> dict:
        """Legt ein Zimmer mit server-generierter UUID an (für manuelle Erstellung via UI)."""
        # Prüfen ob Name schon existiert
        with self._get_conn() as conn:
            existing = conn.execute(
                "SELECT room_id, room_name, created_at FROM rooms WHERE room_name = ?",
                (room_name,),
            ).fetchone()
            if existing:
                return dict(existing)

        room_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()
        with self._get_conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO rooms (room_id, room_name, created_at) VALUES (?, ?, ?)",
                (room_id, room_name, created_at),
            )
            conn.commit()
        return {"room_id": room_id, "room_name": room_name, "created_at": created_at}

    def delete_room(self, room_id: str) -> bool:
        """Löscht ein Zimmer aus der Datenbank (inkl. zugehöriger Nachrichten und ACKs)."""
        with self._get_conn() as conn:
            # Nachrichten dieses Zimmers holen
            msg_ids = [
                row[0]
                for row in conn.execute(
                    "SELECT message_id FROM messages WHERE target_room = ? OR sender_room = ?",
                    (room_id, room_id),
                ).fetchall()
            ]
            # ACKs löschen
            if msg_ids:
                placeholders = ",".join("?" * len(msg_ids))
                conn.execute(
                    f"DELETE FROM acknowledgments WHERE message_id IN ({placeholders})",
                    msg_ids,
                )
                conn.execute(
                    f"DELETE FROM messages WHERE message_id IN ({placeholders})",
                    msg_ids,
                )
            # Zimmer löschen
            result = conn.execute("DELETE FROM rooms WHERE room_id = ?", (room_id,))
            conn.commit()
            return result.rowcount > 0

    def get_room_by_id(self, room_id: str):
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT room_id, room_name FROM rooms WHERE room_id = ?", (room_id,)
            ).fetchone()
        return dict(row) if row else None

    # ──────────────────────────── MESSAGES ────────────────────────────

    def save_message(
        self, sender_room: str, target_room: str, message_text: str, is_broadcast=False
    ) -> str:
        message_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()
        with self._get_conn() as conn:
            conn.execute(
                """INSERT INTO messages
                   (message_id, sender_room, target_room, message_text, timestamp, is_broadcast)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (message_id, sender_room, target_room, message_text, timestamp, 1 if is_broadcast else 0),
            )
            conn.commit()
        return message_id

    def get_pending_messages(self, room_id: str) -> list:
        """
        Gibt alle Nachrichten zurück, die an dieses Zimmer adressiert sind
        und noch NICHT von ihm bestätigt wurden.
        """
        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT m.message_id, m.sender_room, m.message_text, m.timestamp
                FROM messages m
                WHERE m.target_room = ?
                  AND m.message_id NOT IN (
                      SELECT a.message_id FROM acknowledgments a
                      WHERE a.ack_by_room = ?
                  )
                ORDER BY m.timestamp ASC
                """,
                (room_id, room_id),
            ).fetchall()
        return [
            {
                "type": "new_message",
                "message_id": r["message_id"],
                "sender_name": r["sender_room"],
                "sender_room": r["sender_room"],
                "message_text": r["message_text"],
                "timestamp": r["timestamp"],
                "requires_ack": True,
            }
            for r in rows
        ]

    # ──────────────────────────── ACKNOWLEDGMENTS ────────────────────────────

    def acknowledge_message(self, message_id: str, ack_by_room: str):
        ack_timestamp = datetime.now(timezone.utc).isoformat()
        with self._get_conn() as conn:
            conn.execute(
                """INSERT OR IGNORE INTO acknowledgments (message_id, ack_by_room, ack_timestamp)
                   VALUES (?, ?, ?)""",
                (message_id, ack_by_room, ack_timestamp),
            )
            conn.commit()

    def get_sent_messages(self, sender_room: str, limit: int = 5) -> list:
        """
        Gibt die letzten N gesendeten Nachrichten dieses Zimmers zurück,
        inkl. ob sie von der jeweiligen Zielstube bestätigt wurden.
        """
        with self._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT
                    m.message_id,
                    m.target_room,
                    m.message_text,
                    m.timestamp,
                    m.is_broadcast,
                    CASE WHEN a.message_id IS NOT NULL THEN 1 ELSE 0 END AS acknowledged
                FROM messages m
                LEFT JOIN acknowledgments a
                    ON a.message_id = m.message_id AND a.ack_by_room = m.target_room
                WHERE m.sender_room = ?
                ORDER BY m.timestamp DESC
                LIMIT ?
                """,
                (sender_room, limit),
            ).fetchall()
        return [
            {
                "message_id": r["message_id"],
                "target_room":  r["target_room"],
                "message_text": r["message_text"],
                "timestamp":    r["timestamp"],
                "is_broadcast": bool(r["is_broadcast"]),
                "acknowledged": bool(r["acknowledged"]),
            }
            for r in rows
        ]
