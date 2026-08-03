/**
 * ZNS – Zentrales Nachrichten-System
 * preload.js – Sichere Brücke zwischen Oberfläche und Hauptprozess
 *
 * Die Oberfläche hat keinen direkten Zugriff auf Node.js.
 * Nur die hier aufgeführten Funktionen stehen ihr zur Verfügung.
 */

const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('zns', {

    // ── Einrichtung ────────────────────────────────────────────
    holeConfig: () => ipcRenderer.invoke('hole-config'),
    speichereEinrichtung: (daten) => ipcRenderer.invoke('speichere-einrichtung', daten),
    benenneZimmerUm: (name) => ipcRenderer.invoke('benenne-zimmer-um', name),
    sucheServerNeu: () => ipcRenderer.invoke('suche-server-neu'),

    // ── Nachrichten ────────────────────────────────────────────
    sendeNachricht: (daten) => ipcRenderer.invoke('sende-nachricht', daten),
    sendeNotfall: () => ipcRenderer.invoke('sende-notfall'),
    bestaetigeNachricht: (id) => ipcRenderer.invoke('bestaetige-nachricht', id),
    holeVerlauf: (partnerId) => ipcRenderer.invoke('hole-verlauf', partnerId),

    // ── Zimmer ─────────────────────────────────────────────────
    holeZimmer: () => ipcRenderer.invoke('hole-zimmer'),
    loescheZimmer: (id) => ipcRenderer.invoke('loesche-zimmer', id),

    // ── Overlay ────────────────────────────────────────────────
    overlayErledigt: (daten) => ipcRenderer.invoke('overlay-erledigt', daten),

    // ── Ereignisse vom Server ──────────────────────────────────
    beiVerbindungsStatus: (cb) =>
        ipcRenderer.on('verbindungs-status', (_, d) => cb(d)),

    beiNeuerNachricht: (cb) =>
        ipcRenderer.on('neue-nachricht', (_, d) => cb(d)),

    beiEigenenNachrichten: (cb) =>
        ipcRenderer.on('eigene-nachrichten', (_, d) => cb(d)),

    beiLesebestaetigung: (cb) =>
        ipcRenderer.on('lesebestaetigung', (_, d) => cb(d)),

    beiZimmerListe: (cb) =>
        ipcRenderer.on('zimmer-liste', (_, d) => cb(d)),

    beiVerlauf: (cb) =>
        ipcRenderer.on('verlauf', (_, d) => cb(d)),

    beiServerFehler: (cb) =>
        ipcRenderer.on('server-fehler', (_, d) => cb(d)),

    beiServerAdresseGeaendert: (cb) =>
        ipcRenderer.on('server-adresse-geaendert', (_, d) => cb(d)),

    // ── Overlay-Ereignisse ─────────────────────────────────────
    beiZeigeNachricht: (cb) =>
        ipcRenderer.on('zeige-nachricht', (_, d) => cb(d)),
})
