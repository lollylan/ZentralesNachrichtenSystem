# ZNS – Zentrales Nachrichten-System

**Internes Nachrichtensystem für die Praxis.**
Von jedem Zimmer aus jedes andere erreichen – mit Vollbild-Meldung, die bestätigt werden muss.

---

## Was es kann

| Funktion | Beschreibung |
|---|---|
| **Chat pro Zimmer** | Jedes Zimmerpaar hat einen fortlaufenden Verlauf zum Nachlesen |
| **Vollbild-Meldung** | Jede eingehende Nachricht übernimmt den Bildschirm – unübersehbar |
| **Antworten** | Direkt in der Vollbild-Meldung antworten, ohne das Fenster zu wechseln |
| **Lesestatus** | ✓ gesendet · ✓✓ zugestellt · ✓✓ blau = gelesen – aktualisiert sich von selbst |
| **Notfallknopf** | Alarmiert alle Arbeitsplätze und ruft sie zu deinem Zimmer |
| **Server wird selbst gefunden** | Ändert sich die Server-IP, sucht der Client sie automatisch |
| **Nichts geht verloren** | Nachrichten an ausgeschaltete PCs werden beim nächsten Start zugestellt |
| **Autostart** | Der Client startet automatisch mit Windows |

Das System läuft **ausschliesslich im Praxisnetz** – keine Cloud, kein Internet.

---

## Aufbau

```
┌─────────────────┐                    ┌──────────────────┐
│  Praxis-PC      │                    │  Praxis-Server   │
│  ZNS.exe        │◄── Praxisnetz ────►│  server.py       │
│  (jedes Zimmer) │                    │  + Datenbank     │
└─────────────────┘                    └──────────────────┘
```

| Teil | Technik | Aufgabe |
|---|---|---|
| Server | Python + `websockets` | Verteilt Nachrichten, speichert alles |
| Datenbank | SQLite (`zns.db`) | Zimmer, Nachrichten, Lesestatus |
| Client | Electron | Fenster, Vollbild-Meldung, Autostart |

---

## Einrichtung

### Schritt 1 – Server auf dem Praxisserver starten

Voraussetzung: **Python 3.9 oder neuer** ([python.org](https://www.python.org/downloads/) – beim Installieren *„Add Python to PATH"* ankreuzen).

```
server\start_server.bat  doppelklicken
```

Beim ersten Start richtet sich alles selbst ein. Danach zeigt das Fenster:

```
  Server-Adresse für die Clients:  192.168.10.51
  Port:                            8765
```

Dieses Fenster muss offen bleiben, solange ZNS genutzt wird.

> **Tipp:** Damit der Server nach einem Neustart des Praxisservers automatisch
> wieder läuft, eine Verknüpfung zu `start_server.bat` in den Autostart-Ordner
> legen: `Win + R` → `shell:startup` → Verknüpfung hineinziehen.

### Schritt 2 – Client einmalig bauen

Voraussetzung: **Node.js LTS** ([nodejs.org](https://nodejs.org)) – nur auf dem PC, auf dem gebaut wird.

```
client\build_exe.bat  doppelklicken
```

Ergebnis: der Ordner `client\dist\ZNS-win32-x64\`

### Schritt 3 – Auf die Praxis-PCs verteilen

1. Den Ordner `ZNS-win32-x64` auf den PC kopieren (z.B. nach `C:\ZNS\`)
2. `ZNS.exe` starten
3. Zimmernamen eingeben, z.B. *Empfang* oder *Zimmer 3*
4. Server-Adresse eintragen – **oder leer lassen**, dann sucht ZNS ihn selbst

Fertig. Keine Installation, keine Adminrechte nötig.

---

## Bedienung

**Nachricht schreiben** – links das Zimmer anklicken, Text eingeben, `Enter`.

**Nachricht empfangen** – der Bildschirm wird übernommen. Zwei Möglichkeiten:
- **Gelesen** – bestätigt die Nachricht, Meldung verschwindet
- **Antwort senden** – Text eingeben (`Strg + Enter`), antwortet und bestätigt in einem Schritt

**An alle** – links *„📢 Alle Zimmer"* wählen.

**Notfall** – roter Knopf links unten. Nach einer Sicherheitsabfrage erscheint auf
allen Bildschirmen ein roter Vollbild-Alarm mit der Aufforderung, zu dir zu kommen.

**Lesestatus** – an den Haken unter der eigenen Nachricht:

| Zeichen | Bedeutung |
|---|---|
| ✓ | gesendet, Empfänger-PC ist noch aus |
| ✓✓ grau | auf dem Bildschirm angekommen |
| ✓✓ blau | gelesen und bestätigt |

---

## Wenn sich die Server-IP ändert

Das ist der häufigste Störfall im Praxisnetz: Der Server bekommt vom Router
eine neue Adresse, z.B. `…51` wird zu `…52`. **Der Client löst das selbst.**

Er sucht in drei Stufen:

| Stufe | Vorgehen | Dauer |
|---|---|---|
| 1 | Die zuletzt bekannte Adresse probieren | ~0,3 s |
| 2 | Rundruf ins Netz – der Server meldet sich mit seiner neuen Adresse | ~1,5 s |
| 3 | Nachbaradressen durchprobieren: `…51` → `…50`, `…52`, `…49`, `…53` … bis ±10 | ~2 s |

Sobald der Server gefunden ist, merkt sich der Client die neue Adresse dauerhaft
und meldet kurz: *„Server unter neuer Adresse gefunden"*.

Die Suche läuft automatisch bei jedem Verbindungsverlust. Über den Knopf
**„Server suchen"** oben rechts lässt sie sich jederzeit von Hand anstossen.

> Damit das Problem gar nicht erst auftritt, ist eine **feste IP-Adresse** für den
> Praxisserver die sauberste Lösung – meist im Router unter *DHCP-Reservierung*
> einstellbar. Die automatische Suche ist das Sicherheitsnetz, falls das nicht möglich ist.

---

## Ports

| Port | Art | Wofür |
|---|---|---|
| 8765 | TCP | Nachrichten (WebSocket) |
| 8766 | UDP | Automatische Serversuche |

Beide müssen in der Windows-Firewall des **Servers** für das lokale Netz freigegeben
sein. Beim ersten Start fragt Windows danach – hier *„Privates Netzwerk zulassen"* wählen.

---

## Häufige Fragen

**Der Client findet den Server nicht.**
Läuft `start_server.bat` auf dem Praxisserver? Sind beide PCs im selben Netz?
Firewall auf dem Server für Port 8765 (TCP) und 8766 (UDP) freigegeben?

**Ein Zimmer wird als offline angezeigt.**
Der PC ist aus oder ZNS läuft dort nicht. Nachrichten dorthin gehen trotzdem raus
und werden beim nächsten Start des PCs sofort angezeigt.

**Zimmername ändern.**
Oben rechts *„Umbenennen"*. Der Verlauf bleibt erhalten.

**Nachrichten sind nicht verschlüsselt.**
Bewusst so: Das System läuft nur im internen Praxisnetz und hat keine Verbindung
nach aussen. Verschlüsselung würde nur Zertifikatswarnungen und Fehlerquellen
schaffen, ohne im abgeschlossenen Netz Sicherheit hinzuzugewinnen.

**Warum gibt es den Server nicht als EXE?**
Wurde ausprobiert und wieder verworfen. Eine mit PyInstaller gebaute EXE wird
von Windows Defender blockiert – sie ist unsigniert und nutzt einen generischen
Bootloader, den auch Schadsoftware verwendet. Man müsste auf dem Server eine
Virenschutz-Ausnahme eintragen, und nach jedem neuen Build erneut, weil sich die
Prüfsumme ändert. Ein Signaturzertifikat kostet 250–400 € im Jahr.

Da der Server auf genau einem Rechner läuft, ist Python dort einmal zu
installieren der deutlich kleinere Aufwand. `python.exe` ist signiert, damit
entfällt das Problem vollständig. Für die Clients bleibt es bei der EXE – die
werden auf viele PCs verteilt, und Electron bringt einen signierten Starter mit.

**Wo liegen die Daten?**
Alle Nachrichten liegen in `server\zns.db` auf dem Praxisserver. Diese Datei
gehört in die Datensicherung – und niemals in ein öffentliches Repository.

---

## Projektstruktur

```
ZNS/
├── server/
│   ├── server.py           Der Server
│   ├── database.py         Datenbank
│   ├── requirements.txt    Python-Pakete
│   └── start_server.bat    Server starten
├── client/
│   ├── main.js             Hauptprozess, Verbindung, Overlay-Steuerung
│   ├── server-finder.js    Automatische Serversuche
│   ├── preload.js          Brücke zur Oberfläche
│   ├── build_exe.bat       EXE bauen
│   └── renderer/
│       ├── index.html      Hauptfenster (Chat)
│       ├── overlay.html    Vollbild-Meldung
│       └── style.css       Gestaltung
└── Alt/                    Vorherige Fassung (Archiv)
```

---

## Lizenz

MIT
