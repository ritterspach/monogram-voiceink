import Foundation
import ApplicationServices
import Darwin

/// Single-Instance-Sperre via `flock` auf einer Lock-Datei. Der Deskriptor wird
/// bewusst offen gelassen – das Betriebssystem hält die Sperre für die gesamte
/// Prozesslebensdauer. true = wir haben die Sperre, false = es läuft schon eine Instanz.
func acquireSingleInstanceLock() -> Bool {
    let dir = (NSHomeDirectory() as NSString)
        .appendingPathComponent("Library/Application Support/MonogramVoiceInk")
    try? FileManager.default.createDirectory(atPath: dir, withIntermediateDirectories: true)
    let lockPath = (dir as NSString).appendingPathComponent("instance.lock")
    let fd = open(lockPath, O_CREAT | O_RDWR, 0o644)
    guard fd >= 0 else { return true }                 // im Zweifel starten statt blockieren
    if flock(fd, LOCK_EX | LOCK_NB) != 0 {
        close(fd)
        return false
    }
    return true                                        // fd absichtlich offen lassen
}

// Diagnose-Modus: nur VoiceInk-Modi prüfen, ohne Gerät.
if CommandLine.arguments.contains("--modes") {
    VoiceInk.diagnose()
    exit(0)
}

// Diagnose-Modus: aktiven VoiceInk-Modus setzen (testet den Schreibpfad ohne Gerät).
//   swift run MonogramVoiceInk --set-mode <id>
if let i = CommandLine.arguments.firstIndex(of: "--set-mode"), i + 1 < CommandLine.arguments.count {
    let id = CommandLine.arguments[i + 1]
    print("vorher:  \(VoiceInk.activeModeId() ?? "nil")")
    VoiceInk.setActiveMode(id)
    print("gesetzt: \(id)")
    print("nachher: \(VoiceInk.activeModeId() ?? "nil")")
    exit(0)
}

// Diagnose-Modus: Modus über VoiceInks Statusmenü umschalten (testet AX ohne Gerät).
//   swift run MonogramVoiceInk --switch-menu "<Modusname>"
if let i = CommandLine.arguments.firstIndex(of: "--switch-menu"), i + 1 < CommandLine.arguments.count {
    let name = CommandLine.arguments[i + 1]
    let axOpts = [kAXTrustedCheckOptionPrompt.takeUnretainedValue() as String: true] as CFDictionary
    if !AXIsProcessTrustedWithOptions(axOpts) {
        print("⚠️  Bedienungshilfen-Recht fehlt – bitte erteilen und erneut versuchen.")
    }
    let ok = MenuControl.activateMode(named: name)
    print(ok ? "✅ Modus '\(name)' im Menü geklickt." : "❌ Eintrag '\(name)' nicht gefunden/geklickt.")
    exit(0)
}

// Voller VoiceInk-Controller (Dauerbetrieb).
// Single-Instance-Sperre: ein zweiter Start würde Tastenanschläge doppeln.
guard acquireSingleInstanceLock() else {
    Log.app.error("Andere Instanz läuft bereits – beende.")
    exit(0)
}

// Bedienungshilfen-Recht (für simulierte Tastenkürzel) prüfen/anfordern.
// Fehlt es, läuft die App trotzdem weiter; Kürzel greifen erst nach Erteilung.
let axOpts = [kAXTrustedCheckOptionPrompt.takeUnretainedValue() as String: true] as CFDictionary
if !AXIsProcessTrustedWithOptions(axOpts) {
    Log.app.warning("Bedienungshilfen-Recht fehlt – VoiceInk-Tastenkürzel werden erst gesendet, wenn es erteilt ist.")
}

Log.app.notice("MonogramVoiceInk gestartet – warte auf Gerät.")
let supervisor = Supervisor()
supervisor.start()
RunLoop.main.run()
