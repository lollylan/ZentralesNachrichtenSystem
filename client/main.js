/**
 * ZNS – Zentrales Nachrichten-System
 * main.js – Electron-Hauptprozess
 *
 * Aufgaben:
 *  - Hauptfenster (Chat) und Overlay-Fenster verwalten
 *  - Verbindung zum Server halten, inkl. automatischer Serversuche
 *  - Eingehende Nachrichten als Vollbild-Overlay anzeigen
 */

const { app, BrowserWindow, ipcMain, screen, Tray, Menu, nativeImage } = require('electron')
const path = require('path')
const fs = require('fs')
const crypto = require('crypto')
const WebSocket = require('ws')

const { findeServer } = require('./server-finder')

// ──────────────────────────── Zustand ────────────────────────────

let mainWindow = null
let overlayWindow = null
let tray = null
let ws = null

let reconnectTimer = null
let sucheLaeuft = false
let beendenErlaubt = false

let nachrichtenSchlange = []   // wartende Nachrichten fürs Overlay
let overlayAktiv = false

let config = {}

const CONFIG_PATH = () => path.join(app.getPath('userData'), 'config.json')

// ──────────────────────────── Konfiguration ────────────────────────────

const STANDARD_CONFIG = {
    server_host: '',
    server_port: 8765,
    room_id: null,
    room_name: null,
}

function ladeConfig() {
    try {
        if (fs.existsSync(CONFIG_PATH())) {
            config = { ...STANDARD_CONFIG, ...JSON.parse(fs.readFileSync(CONFIG_PATH(), 'utf8')) }
        } else {
            config = { ...STANDARD_CONFIG }
        }
    } catch (e) {
        console.error('[Config] Konnte nicht gelesen werden:', e.message)
        config = { ...STANDARD_CONFIG }
    }

    // Jeder Arbeitsplatz bekommt einmalig eine feste Kennung
    if (!config.room_id) {
        config.room_id = crypto.randomUUID()
        speichereConfig()
    }
}

function speichereConfig() {
    try {
        fs.writeFileSync(CONFIG_PATH(), JSON.stringify(config, null, 2), 'utf8')
    } catch (e) {
        console.error('[Config] Konnte nicht gespeichert werden:', e.message)
    }
}

// ──────────────────────────── Nachrichten an die Oberfläche ────────────────────────────

function anHauptfenster(kanal, daten) {
    if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send(kanal, daten)
    }
}

function statusMelden(status, text = '') {
    anHauptfenster('verbindungs-status', { status, text })
}

// ──────────────────────────── Fenster ────────────────────────────

function erstelleHauptfenster() {
    mainWindow = new BrowserWindow({
        width: 1040,
        height: 700,
        minWidth: 780,
        minHeight: 540,
        title: 'ZNS – Zentrales Nachrichten-System',
        backgroundColor: '#0d1117',
        show: false,
        icon: path.join(__dirname, 'assets', 'icon.png'),
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'),
            contextIsolation: true,
            nodeIntegration: false,
        },
    })

    mainWindow.setMenuBarVisibility(false)
    mainWindow.loadFile(path.join(__dirname, 'renderer', 'index.html'))
    mainWindow.once('ready-to-show', () => mainWindow.show())

    // Schliessen minimiert nur – die App muss im Hintergrund erreichbar bleiben
    mainWindow.on('close', (e) => {
        if (!beendenErlaubt) {
            e.preventDefault()
            mainWindow.hide()
        }
    })
}

function erstelleOverlayFenster() {
    const { bounds } = screen.getPrimaryDisplay()

    overlayWindow = new BrowserWindow({
        x: bounds.x,
        y: bounds.y,
        width: bounds.width,
        height: bounds.height,
        frame: false,
        resizable: false,
        movable: false,
        minimizable: false,
        closable: false,
        alwaysOnTop: true,
        skipTaskbar: true,
        show: false,
        backgroundColor: '#000000',
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'),
            contextIsolation: true,
            nodeIntegration: false,
        },
    })

    overlayWindow.setMenuBarVisibility(false)
    overlayWindow.loadFile(path.join(__dirname, 'renderer', 'overlay.html'))
    overlayWindow.setAlwaysOnTop(true, 'screen-saver', 1)
    overlayWindow.setVisibleOnAllWorkspaces(true)
}

function erstelleTray() {
    const iconPfad = path.join(__dirname, 'assets', 'icon.png')
    let bild = nativeImage.createFromPath(iconPfad)
    if (bild.isEmpty()) bild = nativeImage.createEmpty()

    tray = new Tray(bild)
    tray.setToolTip('ZNS – Zentrales Nachrichten-System')
    tray.setContextMenu(Menu.buildFromTemplate([
        { label: 'Fenster öffnen', click: () => { mainWindow?.show(); mainWindow?.focus() } },
        { type: 'separator' },
        {
            label: 'ZNS beenden',
            click: () => { beendenErlaubt = true; app.quit() },
        },
    ]))
    tray.on('double-click', () => { mainWindow?.show(); mainWindow?.focus() })
}

// ──────────────────────────── Overlay-Steuerung ────────────────────────────

function zeigeNaechsteNachricht() {
    if (nachrichtenSchlange.length === 0) {
        overlayAktiv = false
        if (overlayWindow && !overlayWindow.isDestroyed()) overlayWindow.hide()
        return
    }

    overlayAktiv = true
    const nachricht = nachrichtenSchlange.shift()
    nachricht.wartend = nachrichtenSchlange.length

    overlayWindow.webContents.send('zeige-nachricht', nachricht)
    overlayWindow.show()
    overlayWindow.focus()
    overlayWindow.setAlwaysOnTop(true, 'screen-saver', 1)
}

function nachrichtEinreihen(nachricht) {
    // Notfälle werden vorgezogen
    if (nachricht.is_emergency) {
        nachrichtenSchlange.unshift(nachricht)
    } else {
        nachrichtenSchlange.push(nachricht)
    }
    if (!overlayAktiv) zeigeNaechsteNachricht()
}

// ──────────────────────────── Verbindung ────────────────────────────

function sende(payload) {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(payload))
        return true
    }
    return false
}

/** Steht bereits eine nutzbare Verbindung? */
function istVerbunden() {
    return ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)
}

async function verbinde() {
    // Doppelte Suchläufe und überflüssige Verbindungsversuche vermeiden –
    // sonst prüft der Client den Server im Sekundentakt an, obwohl alles läuft.
    if (sucheLaeuft || istVerbunden()) return
    sucheLaeuft = true

    try {
        const gefunden = await findeServer(config, (text) => statusMelden('suche', text))

        if (!gefunden) {
            statusMelden('getrennt', 'Server nicht gefunden')
            planeNeuverbindung()
            return
        }

        // Neue Adresse gefunden? Dann dauerhaft merken.
        if (gefunden.host !== config.server_host) {
            console.log(`[Server] Neue Adresse gefunden: ${gefunden.host} (${gefunden.quelle})`)
            config.server_host = gefunden.host
            config.server_port = gefunden.port
            speichereConfig()
            anHauptfenster('server-adresse-geaendert', {
                host: gefunden.host,
                quelle: gefunden.quelle,
            })
        }

        oeffneVerbindung(gefunden.host, gefunden.port)
    } catch (e) {
        console.error('[Verbindung] Fehler:', e.message)
        planeNeuverbindung()
    } finally {
        sucheLaeuft = false
    }
}

/**
 * Baut eine bestehende Verbindung sauber ab.
 * Die Ereignisbehandlung wird vorher entfernt, damit eine sterbende
 * Verbindung nicht nachträglich einen Neuaufbau auslöst.
 */
function schliesseVerbindung() {
    if (!ws) return
    const alt = ws
    ws = null
    try {
        alt.removeAllListeners()
        alt.terminate()
    } catch (_) { }
}

function oeffneVerbindung(host, port) {
    // Reste einer früheren Verbindung zuerst entfernen
    schliesseVerbindung()

    const url = `ws://${host}:${port}`
    console.log(`[WS] Verbinde mit ${url}`)

    let socket
    try {
        socket = new WebSocket(url, { handshakeTimeout: 4000 })
    } catch (e) {
        console.error('[WS] Konnte nicht verbinden:', e.message)
        planeNeuverbindung()
        return
    }

    ws = socket

    // Jeder Handler arbeitet ausschliesslich mit seinem eigenen Socket und
    // prüft, ob dieser noch der aktuelle ist. Ohne diese Prüfung kann ein
    // veraltetes Ereignis eine frisch aufgebaute Verbindung wieder zerstören.
    const istAktuell = () => ws === socket

    socket.on('open', () => {
        if (!istAktuell()) return
        console.log('[WS] Verbunden')
        if (reconnectTimer) { clearTimeout(reconnectTimer); reconnectTimer = null }
        versuchZaehler = 0   // nach Erfolg wieder mit kurzen Abständen beginnen

        if (config.room_name) {
            sende({ type: 'register', room_id: config.room_id, room_name: config.room_name })
            statusMelden('verbunden', `${config.server_host}`)
        } else {
            statusMelden('einrichtung', 'Bitte Zimmernamen festlegen')
        }
    })

    socket.on('message', (roh) => {
        if (!istAktuell()) return
        let daten
        try {
            daten = JSON.parse(roh.toString())
        } catch (e) {
            return console.error('[WS] Ungültige Antwort:', e.message)
        }
        verarbeiteServerNachricht(daten)
    })

    socket.on('close', () => {
        if (!istAktuell()) return   // veraltete Verbindung – ignorieren
        console.log('[WS] Verbindung beendet')
        ws = null
        statusMelden('getrennt', 'Verbindung unterbrochen')
        planeNeuverbindung()
    })

    socket.on('error', (fehler) => {
        console.error('[WS] Fehler:', fehler.message)
        // Nur den eigenen Socket beenden, niemals die globale Verbindung
        try { socket.terminate() } catch (_) { }
    })
}

function verarbeiteServerNachricht(daten) {
    switch (daten.type) {
        case 'registered':
            statusMelden('verbunden', `${config.server_host}`)
            sende({ type: 'get_rooms' })
            break

        case 'new_message':
            // Jede eingehende Nachricht übernimmt den Bildschirm –
            // auch Antworten, damit sie garantiert gesehen werden.
            nachrichtEinreihen(daten.message)
            anHauptfenster('neue-nachricht', daten.message)
            break

        case 'messages_sent':
            anHauptfenster('eigene-nachrichten', daten.messages)
            break

        case 'read_receipt':
            anHauptfenster('lesebestaetigung', daten)
            break

        case 'rooms_update':
            anHauptfenster('zimmer-liste', { rooms: daten.rooms, unread: daten.unread || {} })
            if (overlayWindow && !overlayWindow.isDestroyed()) {
                overlayWindow.webContents.send('zimmer-liste', { rooms: daten.rooms })
            }
            break

        case 'conversation':
            anHauptfenster('verlauf', daten)
            break

        case 'error':
            anHauptfenster('server-fehler', daten.message)
            break

        default:
            break
    }
}

// Abstände zwischen den Verbindungsversuchen. Anfangs schnell, damit kurze
// Aussetzer sofort überbrückt werden; danach ruhiger, damit ein abgeschalteter
// Server nicht die ganze Nacht im Sekundentakt angefragt wird. Bei 15 Sekunden
// gedeckelt: Startet der Server im laufenden Betrieb neu, sollen die
// Arbeitsplätze nicht spürbar lange warten.
const WARTEZEITEN = [3000, 3000, 5000, 10000, 15000]
let versuchZaehler = 0

function planeNeuverbindung() {
    if (reconnectTimer || istVerbunden()) return

    const wartezeit = WARTEZEITEN[Math.min(versuchZaehler, WARTEZEITEN.length - 1)]
    versuchZaehler++

    reconnectTimer = setTimeout(() => {
        reconnectTimer = null
        verbinde()
    }, wartezeit)
}

// ──────────────────────────── Schnittstelle zur Oberfläche ────────────────────────────

ipcMain.handle('hole-config', () => ({ ...config }))

ipcMain.handle('speichere-einrichtung', async (_, daten) => {
    if (daten.room_name) config.room_name = daten.room_name.trim()
    if (daten.server_host !== undefined) config.server_host = daten.server_host.trim()
    if (daten.server_port) config.server_port = parseInt(daten.server_port, 10) || 8765
    speichereConfig()

    // Verbindung neu aufbauen, damit der Name sofort greift
    if (reconnectTimer) { clearTimeout(reconnectTimer); reconnectTimer = null }
    versuchZaehler = 0
    schliesseVerbindung()
    await verbinde()

    return { erfolg: true, config: { ...config } }
})

ipcMain.handle('sende-nachricht', (_, daten) => {
    const ok = sende({
        type: 'send_message',
        target_id: daten.target_id,
        message_text: daten.message_text,
    })
    return ok ? { erfolg: true } : { erfolg: false, fehler: 'Keine Verbindung zum Server' }
})

ipcMain.handle('sende-notfall', () => {
    const ok = sende({ type: 'emergency' })
    return ok ? { erfolg: true } : { erfolg: false, fehler: 'Keine Verbindung zum Server' }
})

ipcMain.handle('bestaetige-nachricht', (_, messageId) => {
    sende({ type: 'mark_read', message_id: messageId })
    return { erfolg: true }
})

// Overlay: bestätigen und danach die nächste Nachricht zeigen
ipcMain.handle('overlay-erledigt', (_, daten) => {
    if (daten?.message_id) {
        sende({ type: 'mark_read', message_id: daten.message_id })
    }
    if (daten?.antwort && daten.antwort.trim() && daten.sender_id) {
        sende({
            type: 'send_message',
            target_id: daten.sender_id,
            message_text: daten.antwort.trim(),
        })
    }
    zeigeNaechsteNachricht()
    return { erfolg: true }
})

ipcMain.handle('hole-verlauf', (_, partnerId) => {
    sende({ type: 'get_conversation', partner_id: partnerId })
    return { erfolg: true }
})

ipcMain.handle('hole-zimmer', () => {
    sende({ type: 'get_rooms' })
    return { erfolg: true }
})

ipcMain.handle('loesche-zimmer', (_, roomId) => {
    const ok = sende({ type: 'delete_room', room_id: roomId })
    return ok ? { erfolg: true } : { erfolg: false, fehler: 'Keine Verbindung zum Server' }
})

ipcMain.handle('benenne-zimmer-um', (_, neuerName) => {
    const name = (neuerName || '').trim()
    if (!name) return { erfolg: false, fehler: 'Kein Name angegeben' }
    config.room_name = name
    speichereConfig()
    sende({ type: 'rename_room', room_name: name })
    return { erfolg: true }
})

ipcMain.handle('suche-server-neu', async () => {
    // Erzwingt eine vollständige Suche, auch wenn eine Verbindung besteht
    if (reconnectTimer) { clearTimeout(reconnectTimer); reconnectTimer = null }
    versuchZaehler = 0
    schliesseVerbindung()
    await verbinde()
    return { erfolg: true, host: config.server_host }
})

// ──────────────────────────── App-Start ────────────────────────────

// Nur eine Instanz zulassen – sonst doppelte Overlays
const einzelInstanz = app.requestSingleInstanceLock()
if (!einzelInstanz) {
    app.quit()
} else {
    app.on('second-instance', () => {
        mainWindow?.show()
        mainWindow?.focus()
    })

    app.whenReady().then(() => {
        ladeConfig()
        erstelleHauptfenster()
        erstelleOverlayFenster()
        erstelleTray()
        verbinde()

        if (app.isPackaged) {
            app.setLoginItemSettings({ openAtLogin: true, openAsHidden: false })
        }
    })
}

app.on('window-all-closed', () => {
    // Absichtlich leer: die App läuft im Hintergrund weiter
})

app.on('before-quit', () => {
    beendenErlaubt = true
    try { ws?.close() } catch (_) { }
})
