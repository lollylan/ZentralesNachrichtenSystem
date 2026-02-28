# database_sop.md — Datenbank-SOP: SQLite

## Zweck
SQLite-Datenbank auf dem Server speichert Zimmer, Nachrichten und Bestätigungen persistent.

## Datei
`server/zns.db` (wird automatisch erstellt)

## Tabellen-Schema

### `rooms`
| Spalte | Typ | Beschreibung |
|---|---|---|
| `room_id` | TEXT PK | UUID |
| `room_name` | TEXT UNIQUE | Anzeigename |
| `created_at` | TEXT | ISO8601 Zeitstempel |

### `messages`
| Spalte | Typ | Beschreibung |
|---|---|---|
| `message_id` | TEXT PK | UUID |
| `sender_room` | TEXT | Name des Senders |
| `target_room` | TEXT | room_id des Empfängers |
| `message_text` | TEXT | Nachrichteninhalt |
| `timestamp` | TEXT | ISO8601 Zeitstempel |
| `is_broadcast` | INTEGER | 1 = Broadcast |

### `acknowledgments`
| Spalte | Typ | Beschreibung |
|---|---|---|
| `message_id` | TEXT | Verweis auf messages |
| `ack_by_room` | TEXT | room_id des Bestätigers |
| `ack_timestamp` | TEXT | ISO8601 Zeitstempel |
| PK | | (message_id, ack_by_room) |

## Schlüssel-Query: Ausstehende Nachrichten
```sql
SELECT m.message_id, m.sender_room, m.message_text, m.timestamp
FROM messages m
WHERE m.target_room = :room_id
  AND m.message_id NOT IN (
      SELECT a.message_id FROM acknowledgments a
      WHERE a.ack_by_room = :room_id
  )
ORDER BY m.timestamp ASC;
```

## Regeln
1. Nachrichten werden NIEMALS gelöscht – nur als "bestätigt" markiert (ACK-Eintrag).
2. `room_name` ist UNIQUE: Doppeltes Anlegen eines Zimmers ist sicher (IGNORE-Strategie).
3. Backup: `server/zns.db` regelmäßig sichern (einfache Datei-Kopie reicht).
