"""
ZNS – Zentrales Nachrichten-System
database.py – SQLite-Datenbank

Wichtig: Zimmer werden AUSSCHLIESSLICH über room_id referenziert.
Der room_name ist nur ein Anzeigename und darf jederzeit geändert werden.
"""

import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent / "zns.db"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Database:
    """SQLite-Wrapper für Zimmer, Nachrichten und Lesebestätigungen."""

    def __init__(self):
        self._init_db()

    def _conn(self):
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS rooms (
                    room_id    TEXT PRIMARY KEY,
                    room_name  TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_seen  TEXT
                );

                CREATE TABLE IF NOT EXISTS messages (
                    message_id   TEXT PRIMARY KEY,
                    sender_id    TEXT NOT NULL,
                    target_id    TEXT NOT NULL,
                    message_text TEXT NOT NULL,
                    created_at   TEXT NOT NULL,
                    is_emergency INTEGER DEFAULT 0,
                    delivered_at TEXT,
                    read_at      TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_msg_target
                    ON messages (target_id, read_at);
                CREATE INDEX IF NOT EXISTS idx_msg_pair
                    ON messages (sender_id, target_id, created_at);
            """)
            conn.commit()

    # ──────────────────────────── ZIMMER ────────────────────────────

    def ensure_room(self, room_id: str, room_name: str) -> dict:
        """
        Trägt ein Zimmer ein oder aktualisiert seinen Namen.
        Die room_id kommt immer vom Client und ist führend – dadurch
        stimmen die Server-Verbindungsliste und die Datenbank überein.
        """
        with self._conn() as conn:
            row = conn.execute(
                "SELECT room_id, room_name FROM rooms WHERE room_id = ?", (room_id,)
            ).fetchone()

            if row:
                # Zimmer umbenannt? Dann Namen aktualisieren.
                if row["room_name"] != room_name:
                    conn.execute(
                        "UPDATE rooms SET room_name = ? WHERE room_id = ?",
                        (room_name, room_id),
                    )
                conn.execute(
                    "UPDATE rooms SET last_seen = ? WHERE room_id = ?", (_now(), room_id)
                )
            else:
                conn.execute(
                    "INSERT INTO rooms (room_id, room_name, created_at, last_seen) "
                    "VALUES (?, ?, ?, ?)",
                    (room_id, room_name, _now(), _now()),
                )
            conn.commit()

        return {"room_id": room_id, "room_name": room_name}

    def get_all_rooms(self) -> list:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT room_id, room_name, created_at, last_seen "
                "FROM rooms ORDER BY room_name COLLATE NOCASE"
            ).fetchall()
        return [dict(r) for r in rows]

    def rename_room(self, room_id: str, new_name: str) -> bool:
        with self._conn() as conn:
            result = conn.execute(
                "UPDATE rooms SET room_name = ? WHERE room_id = ?", (new_name, room_id)
            )
            conn.commit()
            return result.rowcount > 0

    def delete_room(self, room_id: str) -> bool:
        """Löscht ein Zimmer samt aller zugehörigen Nachrichten."""
        with self._conn() as conn:
            conn.execute(
                "DELETE FROM messages WHERE sender_id = ? OR target_id = ?",
                (room_id, room_id),
            )
            result = conn.execute("DELETE FROM rooms WHERE room_id = ?", (room_id,))
            conn.commit()
            return result.rowcount > 0

    def touch_room(self, room_id: str):
        with self._conn() as conn:
            conn.execute(
                "UPDATE rooms SET last_seen = ? WHERE room_id = ?", (_now(), room_id)
            )
            conn.commit()

    # ──────────────────────────── NACHRICHTEN ────────────────────────────

    def save_message(
        self, sender_id: str, target_id: str, text: str, is_emergency: bool = False
    ) -> dict:
        message_id = str(uuid.uuid4())
        created_at = _now()
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO messages "
                "(message_id, sender_id, target_id, message_text, created_at, is_emergency) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (message_id, sender_id, target_id, text, created_at, 1 if is_emergency else 0),
            )
            conn.commit()
        return {
            "message_id": message_id,
            "sender_id": sender_id,
            "target_id": target_id,
            "message_text": text,
            "created_at": created_at,
            "is_emergency": is_emergency,
            "delivered_at": None,
            "read_at": None,
        }

    def mark_delivered(self, message_id: str) -> str | None:
        """Setzt den Zustellzeitpunkt (nur beim ersten Mal)."""
        ts = _now()
        with self._conn() as conn:
            result = conn.execute(
                "UPDATE messages SET delivered_at = ? "
                "WHERE message_id = ? AND delivered_at IS NULL",
                (ts, message_id),
            )
            conn.commit()
            return ts if result.rowcount > 0 else None

    def mark_read(self, message_id: str, reader_id: str) -> dict | None:
        """
        Markiert eine Nachricht als gelesen. Gibt die Absender-ID zurück,
        damit der Server den Absender über den Lesestatus informieren kann.
        """
        ts = _now()
        with self._conn() as conn:
            row = conn.execute(
                "SELECT sender_id, target_id, read_at FROM messages WHERE message_id = ?",
                (message_id,),
            ).fetchone()

            if not row:
                return None
            # Nur der Empfänger darf seine eigene Nachricht als gelesen markieren
            if row["target_id"] != reader_id:
                return None
            if row["read_at"]:
                return {"sender_id": row["sender_id"], "read_at": row["read_at"]}

            conn.execute(
                "UPDATE messages SET read_at = ?, "
                "delivered_at = COALESCE(delivered_at, ?) WHERE message_id = ?",
                (ts, ts, message_id),
            )
            conn.commit()

        return {"sender_id": row["sender_id"], "read_at": ts}

    def get_unread_messages(self, room_id: str) -> list:
        """Alle noch ungelesenen Nachrichten für ein Zimmer (für Reconnect)."""
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT m.*, r.room_name AS sender_name
                FROM messages m
                LEFT JOIN rooms r ON r.room_id = m.sender_id
                WHERE m.target_id = ? AND m.read_at IS NULL
                ORDER BY m.created_at ASC
                """,
                (room_id,),
            ).fetchall()
        return [self._row_to_message(r) for r in rows]

    def get_conversation(self, room_a: str, room_b: str, limit: int = 100) -> list:
        """Der gemeinsame Chat-Verlauf zweier Zimmer, älteste zuerst."""
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT m.*, r.room_name AS sender_name
                FROM messages m
                LEFT JOIN rooms r ON r.room_id = m.sender_id
                WHERE (m.sender_id = ? AND m.target_id = ?)
                   OR (m.sender_id = ? AND m.target_id = ?)
                ORDER BY m.created_at DESC
                LIMIT ?
                """,
                (room_a, room_b, room_b, room_a, limit),
            ).fetchall()
        return [self._row_to_message(r) for r in reversed(rows)]

    def get_unread_counts(self, room_id: str) -> dict:
        """Anzahl ungelesener Nachrichten je Absender – für die Badges in der Zimmerliste."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT sender_id, COUNT(*) AS anzahl FROM messages "
                "WHERE target_id = ? AND read_at IS NULL GROUP BY sender_id",
                (room_id,),
            ).fetchall()
        return {r["sender_id"]: r["anzahl"] for r in rows}

    @staticmethod
    def _row_to_message(r: sqlite3.Row) -> dict:
        return {
            "message_id": r["message_id"],
            "sender_id": r["sender_id"],
            "sender_name": r["sender_name"] or "Unbekannt",
            "target_id": r["target_id"],
            "message_text": r["message_text"],
            "created_at": r["created_at"],
            "is_emergency": bool(r["is_emergency"]),
            "delivered_at": r["delivered_at"],
            "read_at": r["read_at"],
        }
