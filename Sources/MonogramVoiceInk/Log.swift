import os

/// Zentrale Logger fürs Hintergrund-Logging (sichtbar in Console.app, Subsystem
/// „com.monogram.voiceink"). Im Hintergrundbetrieb gibt es kein Terminal, daher
/// statt `print` durchgängig `os_log`.
enum Log {
    static let app    = Logger(subsystem: "com.monogram.voiceink", category: "app")
    static let device = Logger(subsystem: "com.monogram.voiceink", category: "device")
    static let mode   = Logger(subsystem: "com.monogram.voiceink", category: "mode")
}
