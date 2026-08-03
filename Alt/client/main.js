/**
 * ZNS – Zentrales Nachrichten-System
 * main.js – Electron Hauptprozess
 *
 * Verantwortlich für:
 *  - Fenster-Management (Hauptfenster + Overlay)
 *  - WebSocket-Verbindung zum Server (via ws-Paket)
 *  - Nachrichten-Queue für mehrere gleichzeitige Overlays
 *  - Reconnect-Logik (alle 3 Sekunden)
 *  - Windows-Autostart
 */

const { app, BrowserWindow, ipcMain, screen } = require('electron')
const path = require('path')
const fs = require('fs')
const WebSocket = require('ws')

// ──────────────────────── Zustand ────────────────────────
let mainWindow = null
let overlayWindow = null
let ws = null
let reconnectTimer = null

let messageQueue = []   // Queue unbestätigter Nachrichten
let overlayShowing = false

let config = {}

const CONFIG_PATH = path.join(app.getPath('userData'), 'config.json')

// ──────────────────────── Konfiguration ───────────────────

function loadConfig() {
    try {
        if (fs.existsSync(CONFIG_PATH)) {
            config = JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf8'))
        } else {
            config = {
                server_host: '192.168.10.51',
                server_port: 8765,
                room_id: null,
                room_name: null,
            }
        }
    } catch (e) {
        config = { server_host: '192.168.10.51', server_port: 8765 }
    }
}

function saveConfig() {
    try {
        fs.writeFileSync(CONFIG_PATH, JSON.stringify(config, null, 2), 'utf8')
    } catch (e) {
        console.error('[Config] Fehler beim Speichern:', e.message)
    }
}

// ──────────────────────── Fenster ─────────────────────────

function createMainWindow() {
    mainWindow = new BrowserWindow({
        width: 900,
        height: 640,
        minWidth: 620,
        minHeight: 480,
        title: 'ZNS – Zentrales Nachrichten-System',
        backgroundColor: '#0d1117',
        show: false,
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'),
            contextIsolation: true,
            nodeIntegration: false,
        },
    })

    mainWindow.loadFile(path.join(__dirname, 'renderer', 'index.html'))
    mainWindow.once('ready-to-show', () => mainWindow.show())

    // Nicht beenden – nur minimieren (App läuft im Hintergrund)
    mainWindow.on('close', (e) => {
        e.preventDefault()
        mainWindow.minimize()
    })
}

function createOverlayWindow() {
    const display = screen.getPrimaryDisplay()
    const { x, y, width, height } = display.bounds

    overlayWindow = new BrowserWindow({
        x, y,
        width, height,
        frame: false,
        resizable: false,
        movable: false,
        focusable: true,
        alwaysOnTop: true,
        skipTaskbar: false,
        show: false,
        backgroundColor: '#000000',
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'),
            contextIsolation: true,
            nodeIntegration: false,
        },
    })

    overlayWindow.loadFile(path.join(__dirname, 'renderer', 'overlay.html'))

    // Höchste Ebene setzen (über UAC-Dialoge hinaus)
    overlayWindow.setAlwaysOnTop(true, 'screen-saver', 1)
}

// ──────────────────────── Overlay-Queue ───────────────────

function showNextOverlay() {
    if (messageQueue.length === 0) {
        overlayShowing = false
        if (overlayWindow) overlayWindow.hide()
        return
    }

    overlayShowing = true
    const msg = messageQueue.shift()

    // Queue-Länge anhängen (damit Overlay "X weitere" anzeigen kann)
    msg.queueRemaining = messageQueue.length

    overlayWindow.webContents.send('show-message', msg)
    overlayWindow.show()
    overlayWindow.focus()
    overlayWindow.setAlwaysOnTop(true, 'screen-saver', 1)
}

// ──────────────────────── WebSocket ───────────────────────

function connectWebSocket() {
    if (!config.server_host || !config.server_port) return

    const url = `wss://${config.server_host}:${config.server_port}`
    console.log(`[WS] Verbinde mit ${url} …`)

    try {
        ws = new WebSocket(url, { rejectUnauthorized: false })
    } catch (e) {
        console.error('[WS] Verbindungsfehler:', e.message)
        scheduleReconnect()
        return
    }

    ws.on('open', () => {
        console.log('[WS] Verbunden!')
        if (reconnectTimer) { clearTimeout(reconnectTimer); reconnectTimer = null }

        // Zimmerliste immer beim Connect anfordern
        wsSend({ type: 'get_rooms' })

        if (config.room_id) {
            // Zimmer registrieren und ausstehende Nachrichten anfragen
            wsSend({ type: 'register', room_id: config.room_id, room_name: config.room_name })
            if (mainWindow) mainWindow.webContents.send('connection-status', 'connected')
        } else {
            if (mainWindow) mainWindow.webContents.send('connection-status', 'setup-required')
        }
    })

    ws.on('message', (raw) => {
        try {
            const msg = JSON.parse(raw.toString())

            switch (msg.type) {
                case 'new_message':
                    // In Queue schieben; Overlay anzeigen falls frei
                    // is_emergency-Flag wird direkt aus dem Server-Payload übernommen
                    messageQueue.push(msg)
                    if (!overlayShowing) showNextOverlay()
                    break

                case 'rooms_update':
                    if (mainWindow) mainWindow.webContents.send('rooms-update', msg.rooms)
                    if (overlayWindow) overlayWindow.webContents.send('rooms-update', msg.rooms)
                    break

                case 'sent_messages':
                    if (mainWindow) mainWindow.webContents.send('sent-messages', msg.messages)
                    break

                case 'error':
                    if (mainWindow) mainWindow.webContents.send('server-error', msg.message)
                    break

                default:
                    break
            }
        } catch (e) {
            console.error('[WS] Parsefehler:', e.message)
        }
    })

    ws.on('close', () => {
        console.log('[WS] Verbindung getrennt.')
        if (mainWindow) mainWindow.webContents.send('connection-status', 'disconnected')
        scheduleReconnect()
    })

    ws.on('error', (err) => {
        console.error('[WS] Fehler:', err.message)
        try { ws.terminate() } catch (_) { }
    })
}

function wsSend(payload) {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(payload))
        return true
    }
    return false
}

function scheduleReconnect() {
    if (reconnectTimer) return
    reconnectTimer = setTimeout(() => {
        reconnectTimer = null
        connectWebSocket()
    }, 3000)
}

// ──────────────────────── IPC Handler ─────────────────────

ipcMain.handle('get-config', () => config)

ipcMain.handle('save-config', (_, newConfig) => {
    config = { ...config, ...newConfig }
    saveConfig()
    return config
})

ipcMain.handle('connect', (_, serverConfig) => {
    config = { ...config, ...serverConfig }
    saveConfig()
    if (reconnectTimer) { clearTimeout(reconnectTimer); reconnectTimer = null }
    try { ws?.terminate() } catch (_) { }
    connectWebSocket()
    return { success: true }
})

ipcMain.handle('register-room', (_, roomData) => {
    config.room_id = roomData.room_id
    config.room_name = roomData.room_name
    saveConfig()

    wsSend({ type: 'register', room_id: config.room_id, room_name: config.room_name })

    if (mainWindow) mainWindow.webContents.send('connection-status', 'connected')
    return { success: true }
})

ipcMain.handle('send-message', (_, data) => {
    const ok = wsSend({
        type: 'send_message',
        sender_id: config.room_id,
        sender_name: config.room_name,
        target_room_id: data.target_room_id,
        message_text: data.message_text,
        timestamp: new Date().toISOString(),
    })
    if (ok) {
        // Sendehistorie nach kurzer Verzögerung automatisch neu laden
        // (Server hat die Nachricht dann bereits gespeichert)
        setTimeout(() => wsSend({ type: 'get_sent_messages' }), 150)
    }
    return ok ? { success: true } : { success: false, error: 'Nicht verbunden' }
})

ipcMain.handle('acknowledge-message', (_, messageId) => {
    wsSend({
        type: 'ack_message',
        message_id: messageId,
        ack_by_room: config.room_id,
        ack_timestamp: new Date().toISOString(),
    })
    // Nächste Nachricht aus der Queue anzeigen
    showNextOverlay()
})

ipcMain.handle('create-room', (_, roomName) => {
    const ok = wsSend({ type: 'create_room', room_name: roomName })
    return ok ? { success: true } : { success: false, error: 'Nicht verbunden' }
})

ipcMain.handle('delete-room', (_, roomId) => {
    const ok = wsSend({ type: 'delete_room', room_id: roomId })
    return ok ? { success: true } : { success: false, error: 'Nicht verbunden' }
})

ipcMain.handle('send-emergency', () => {
    const ok = wsSend({ type: 'emergency_call' })
    return ok ? { success: true } : { success: false, error: 'Nicht verbunden' }
})

ipcMain.handle('get-sent-messages', () => {
    wsSend({ type: 'get_sent_messages' })
    return { success: true }
})

ipcMain.handle('get-rooms', () => {
    wsSend({ type: 'get_rooms' })
    return { success: true }
})

// ──────────────────────── App-Lifecycle ───────────────────

app.whenReady().then(() => {
    loadConfig()
    createMainWindow()
    createOverlayWindow()
    connectWebSocket()

    // Autostart in Windows (nur im gepackten Modus aktiv)
    if (app.isPackaged) {
        app.setLoginItemSettings({ openAtLogin: true, openAsHidden: false })
    }
})

// Verhindert das vollständige Beenden beim letzten Fenster
app.on('window-all-closed', () => { /* absichtlich leer */ })

app.on('before-quit', () => {
    // Sauberes Trennen vom Server
    try { ws?.close() } catch (_) { }
})
