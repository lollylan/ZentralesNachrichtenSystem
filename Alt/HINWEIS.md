# Archiv – alte Fassung (Version 1.2.0)

Dieser Ordner enthält die **vorherige Fassung** von ZNS und wird nicht mehr
gepflegt. Er liegt nur zum Nachschlagen hier.

**Nichts aus diesem Ordner starten oder verteilen.** Die aktuelle Fassung liegt
im übergeordneten Verzeichnis in `server/` und `client/`.

Archiviert am: 3. August 2026

---

## Warum abgelöst

| Punkt | Alte Fassung | Neue Fassung |
|---|---|---|
| Verschlüsselung | TLS/WSS mit selbst-signiertem Zertifikat | Bewusst keine – reines Praxisnetz, keine Zertifikatswarnungen mehr |
| Server-IP ändert sich | Musste an jedem PC von Hand korrigiert werden | Wird automatisch gefunden (Rundruf + Nachbarsuche) |
| Nachrichten | Einzelne Meldungen ohne Zusammenhang | Fortlaufender Chat-Verlauf je Zimmer |
| Antworten | Nicht möglich | Direkt in der Vollbild-Meldung |
| Lesestatus | Nur „bestätigt / nicht bestätigt" | Gesendet · zugestellt · gelesen |
| Zimmer-Kennung | `room_name` und `room_id` vermischt | Durchgängig `room_id` |

## Zur Datenbank

Die alte `zns.db` ist mit der neuen Fassung **nicht kompatibel** – das
Tabellenschema hat sich geändert. Die neue Fassung legt beim ersten Start
automatisch eine frische Datenbank an.

Falls noch eine alte `zns.db` im Ordner `server/` liegt: vor dem ersten Start
löschen oder umbenennen.
