/**
 * ZNS – Zentrales Nachrichten-System
 * preload.js – Sicherer IPC-Bridge zwischen Main und Renderer
 *
 * contextBridge stellt nur explizit freigegebene Methoden bereit.
 * nodeIntegration ist DEAKTIVIERT (contextIsolation: true).
 */

const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('zns', {

  // ── Konfiguration ────────────────────────────────────────────
  getConfig: () =>
    ipcRenderer.invoke('get-config'),

  saveConfig: (config) =>
    ipcRenderer.invoke('save-config', config),

  // ── Verbindung & Registrierung ───────────────────────────────
  connect: (serverConfig) =>
    ipcRenderer.invoke('connect', serverConfig),

  registerRoom: (roomData) =>
    ipcRenderer.invoke('register-room', roomData),

  // ── Nachrichten senden ───────────────────────────────────────
  sendMessage: (data) =>
    ipcRenderer.invoke('send-message', data),

  sendEmergency: () =>
    ipcRenderer.invoke('send-emergency'),

  // ── Bestätigung ──────────────────────────────────────────────
  acknowledgeMessage: (messageId) =>
    ipcRenderer.invoke('acknowledge-message', messageId),

  // ── Zimmer verwalten ────────────────────────────────────────
  createRoom: (roomName) =>
    ipcRenderer.invoke('create-room', roomName),

  deleteRoom: (roomId) =>
    ipcRenderer.invoke('delete-room', roomId),

  getRooms: () =>
    ipcRenderer.invoke('get-rooms'),

  getSentMessages: () =>
    ipcRenderer.invoke('get-sent-messages'),

  // ── Eingehende Events (Server → Main → Renderer) ─────────────
  onConnectionStatus: (cb) =>
    ipcRenderer.on('connection-status', (_, status) => cb(status)),

  onRoomsUpdate: (cb) =>
    ipcRenderer.on('rooms-update', (_, rooms) => cb(rooms)),

  onShowMessage: (cb) =>
    ipcRenderer.on('show-message', (_, message) => cb(message)),

  onServerError: (cb) =>
    ipcRenderer.on('server-error', (_, msg) => cb(msg)),

  onSentMessages: (cb) =>
    ipcRenderer.on('sent-messages', (_, msgs) => cb(msgs)),

  // ── Cleanup ──────────────────────────────────────────────────
  removeAllListeners: (channel) =>
    ipcRenderer.removeAllListeners(channel),
})
