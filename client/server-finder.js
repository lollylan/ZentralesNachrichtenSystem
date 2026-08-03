/**
 * ZNS – Zentrales Nachrichten-System
 * server-finder.js – Automatische Serversuche
 *
 * Hintergrund: Die IP-Adresse des Praxisservers ändert sich gelegentlich
 * (z.B. von ...51 auf ...52). Damit die Clients nicht jedes Mal neu
 * eingerichtet werden müssen, sucht der Client den Server in drei Stufen:
 *
 *   Stufe 1  Die zuletzt bekannte Adresse direkt probieren   (~0,3 s)
 *   Stufe 2  UDP-Rundruf ins Netz – der Server meldet sich   (~1,5 s)
 *   Stufe 3  Nachbar-Adressen durchprobieren (...51 → 50, 52, 49, 53 …)
 *
 * Sobald der Server gefunden ist, wird die neue Adresse gespeichert.
 */

const net = require('net')
const dgram = require('dgram')
const os = require('os')

const DISCOVERY_PORT = 8766
const DISCOVERY_MAGIC = 'ZNS_DISCOVER'

// Wie weit rund um die bekannte Adresse gesucht wird (…51 → …41 bis …61)
const NACHBAR_REICHWEITE = 10

/**
 * Prüft, ob unter host:port ein TCP-Dienst erreichbar ist.
 * Bewusst kurzer Timeout – im LAN antwortet ein laufender Server sofort.
 */
function pruefeAdresse(host, port, timeout = 400) {
    return new Promise((resolve) => {
        const socket = new net.Socket()
        let erledigt = false

        const fertig = (erfolg) => {
            if (erledigt) return
            erledigt = true
            socket.destroy()
            resolve(erfolg)
        }

        socket.setTimeout(timeout)
        socket.once('connect', () => fertig(true))
        socket.once('timeout', () => fertig(false))
        socket.once('error', () => fertig(false))

        try {
            socket.connect(port, host)
        } catch (_) {
            fertig(false)
        }
    })
}

/**
 * Stufe 2: UDP-Rundruf. Der Server antwortet mit seinem Port,
 * die Adresse lesen wir aus dem Absender der Antwort.
 */
function sucheViaRundruf(timeout = 1500) {
    return new Promise((resolve) => {
        let socket
        try {
            socket = dgram.createSocket({ type: 'udp4', reuseAddr: true })
        } catch (_) {
            return resolve(null)
        }

        let erledigt = false
        const fertig = (ergebnis) => {
            if (erledigt) return
            erledigt = true
            try { socket.close() } catch (_) { }
            resolve(ergebnis)
        }

        const timer = setTimeout(() => fertig(null), timeout)

        socket.once('error', () => { clearTimeout(timer); fertig(null) })

        socket.on('message', (daten, absender) => {
            try {
                const antwort = JSON.parse(daten.toString())
                if (antwort.service === 'ZNS') {
                    clearTimeout(timer)
                    fertig({
                        host: absender.address,
                        port: antwort.ws_port || 8765,
                        quelle: 'Rundruf',
                    })
                }
            } catch (_) {
                // Fremdes Paket – ignorieren
            }
        })

        socket.bind(() => {
            try {
                socket.setBroadcast(true)
            } catch (_) { }

            const nachricht = Buffer.from(DISCOVERY_MAGIC)

            // An die allgemeine Broadcast-Adresse …
            const ziele = ['255.255.255.255']

            // … und zusätzlich gezielt an die Broadcast-Adresse jedes
            // Netzwerkadapters. Manche Switches/Firewalls lassen nur diese durch.
            for (const adapter of Object.values(os.networkInterfaces())) {
                for (const adr of adapter || []) {
                    if (adr.family === 'IPv4' && !adr.internal && adr.address && adr.netmask) {
                        const b = broadcastAdresse(adr.address, adr.netmask)
                        if (b && !ziele.includes(b)) ziele.push(b)
                    }
                }
            }

            for (const ziel of ziele) {
                socket.send(nachricht, DISCOVERY_PORT, ziel, () => { })
            }
        })
    })
}

/** Berechnet die Broadcast-Adresse aus IP und Subnetzmaske. */
function broadcastAdresse(ip, maske) {
    const ipTeile = ip.split('.').map(Number)
    const maskeTeile = maske.split('.').map(Number)
    if (ipTeile.length !== 4 || maskeTeile.length !== 4) return null
    return ipTeile
        .map((teil, i) => (teil & maskeTeile[i]) | (~maskeTeile[i] & 255))
        .join('.')
}

/**
 * Stufe 3: Nachbar-Adressen. Ausgehend von der bekannten IP wird das
 * letzte Zahlenfeld abwechselnd nach unten und oben durchprobiert:
 * 51 → 50, 52, 49, 53, 48, 54 …
 * So wird die wahrscheinlichste Adresse zuerst getestet.
 */
function nachbarAdressen(host, reichweite = NACHBAR_REICHWEITE) {
    const teile = host.split('.')
    if (teile.length !== 4) return []

    const basis = teile.slice(0, 3).join('.')
    const start = parseInt(teile[3], 10)
    if (Number.isNaN(start)) return []

    const liste = []
    for (let abstand = 1; abstand <= reichweite; abstand++) {
        for (const richtung of [-1, 1]) {
            const wert = start + abstand * richtung
            if (wert >= 1 && wert <= 254) liste.push(`${basis}.${wert}`)
        }
    }
    return liste
}

/** Testet mehrere Adressen gleichzeitig und liefert die erste Treffer-Adresse. */
async function ersteErreichbare(adressen, port, timeout = 400) {
    if (adressen.length === 0) return null

    const ergebnisse = await Promise.all(
        adressen.map(async (host) => ({
            host,
            erreichbar: await pruefeAdresse(host, port, timeout),
        }))
    )
    // Reihenfolge der Eingabe beibehalten – die wahrscheinlichste zuerst
    const treffer = ergebnisse.find((e) => e.erreichbar)
    return treffer ? treffer.host : null
}

/**
 * Sucht den Server in drei Stufen.
 *
 * @param {object}   config     Aktuelle Konfiguration (server_host, server_port)
 * @param {function} melden     Rückmeldung für die Oberfläche: melden(text)
 * @returns {Promise<{host,port,quelle}|null>}
 */
async function findeServer(config, melden = () => { }) {
    const port = config.server_port || 8765
    const bekannt = config.server_host

    // ── Stufe 1: die bekannte Adresse ───────────────────────────────
    if (bekannt) {
        melden(`Verbinde mit ${bekannt} …`)
        if (await pruefeAdresse(bekannt, port, 600)) {
            return { host: bekannt, port, quelle: 'gespeichert' }
        }
    }

    // ── Stufe 2: Rundruf ins Netz ───────────────────────────────────
    melden('Server nicht erreichbar – suche im Netzwerk …')
    const gefunden = await sucheViaRundruf(1500)
    if (gefunden) return gefunden

    // ── Stufe 3: Nachbar-Adressen ───────────────────────────────────
    if (bekannt) {
        melden('Prüfe benachbarte Adressen …')
        const nachbarn = nachbarAdressen(bekannt)

        // In Blöcken von 6 testen, damit nicht zu viele Verbindungen
        // gleichzeitig offen sind
        for (let i = 0; i < nachbarn.length; i += 6) {
            const block = nachbarn.slice(i, i + 6)
            const treffer = await ersteErreichbare(block, port, 500)
            if (treffer) return { host: treffer, port, quelle: 'Nachbarsuche' }
        }
    }

    melden('Server nicht gefunden')
    return null
}

module.exports = { findeServer, pruefeAdresse, nachbarAdressen }
