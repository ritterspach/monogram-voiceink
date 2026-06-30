import Foundation
import CoreGraphics

/// Ein VoiceInk-Modus. `shortcut` ist das in VoiceInk hinterlegte
/// „in diesem Modus aufnehmen"-Kürzel (nil, wenn keins gesetzt ist).
struct VIMode {
    let name: String
    let id: String
    let shortcut: (CGKeyCode, CGEventFlags)?
}

/// Liest VoiceInks Modi + Shortcuts dynamisch aus den UserDefaults und sendet
/// Tastenkürzel via CGEvent.
enum VoiceInk {
    static let suite = "com.prakashjoshipax.VoiceInk"

    private static func defaults() -> UserDefaults? { UserDefaults(suiteName: suite) }

    private static func flags(fromNSEventRaw raw: Int) -> CGEventFlags {
        var f: CGEventFlags = []
        if raw & (1 << 17) != 0 { f.insert(.maskShift) }
        if raw & (1 << 18) != 0 { f.insert(.maskControl) }
        if raw & (1 << 19) != 0 { f.insert(.maskAlternate) }   // Option
        if raw & (1 << 20) != 0 { f.insert(.maskCommand) }
        return f
    }

    private static func shortcut(_ d: UserDefaults, _ key: String) -> (CGKeyCode, CGEventFlags)? {
        guard let data = d.data(forKey: key),
              let obj = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any],
              (obj["kind"] as? String) == "key",
              let kc = obj["keyCode"] as? Int else { return nil }
        return (CGKeyCode(kc), flags(fromNSEventRaw: obj["modifierFlagsRawValue"] as? Int ?? 0))
    }

    static func modes() -> [VIMode] {
        guard let d = defaults(),
              let data = d.data(forKey: "modeConfigurationsV2"),
              let arr = (try? JSONSerialization.jsonObject(with: data)) as? [[String: Any]] else { return [] }
        var out: [VIMode] = []
        for m in arr {
            if let enabled = m["isEnabled"] as? Bool, !enabled { continue }
            guard let id = m["id"] as? String, let name = m["name"] as? String else { continue }
            out.append(VIMode(name: name, id: id, shortcut: shortcut(d, "Shortcut_mode_\(id)")))
        }
        return out
    }

    static func activeModeId() -> String? {
        defaults()?.string(forKey: "activeConfigurationId")
    }

    /// Schaltet VoiceInks aktiven Modus, indem `activeConfigurationId` in dessen
    /// Defaults geschrieben wird. `CFPreferencesAppSynchronize` flusht die Domain,
    /// damit cfprefsd die Änderung an die laufende App weiterreicht. Ob VoiceInk
    /// sie live in der Menübar übernimmt, hängt davon ab, ob es externe
    /// Defaults-Änderungen beobachtet (am Gerät zu verifizieren).
    static func setActiveMode(_ id: String) {
        guard let d = defaults() else { return }
        d.set(id, forKey: "activeConfigurationId")
        CFPreferencesAppSynchronize(suite as CFString)
    }

    /// Globaler Aufnahme-Toggle-Hotkey (sekundärer, sonst primärer Recording-Shortcut).
    static func recordingToggle() -> (CGKeyCode, CGEventFlags)? {
        guard let d = defaults() else { return nil }
        return shortcut(d, "Shortcut_secondaryRecording") ?? shortcut(d, "Shortcut_primaryRecording")
    }

    static func send(keyCode: CGKeyCode, flags: CGEventFlags) {
        let src = CGEventSource(stateID: .hidSystemState)
        if let down = CGEvent(keyboardEventSource: src, virtualKey: keyCode, keyDown: true) {
            down.flags = flags
            down.post(tap: .cghidEventTap)
        }
        if let up = CGEvent(keyboardEventSource: src, virtualKey: keyCode, keyDown: false) {
            up.flags = flags
            up.post(tap: .cghidEventTap)
        }
    }

    static func diagnose() {
        for m in modes() {
            if let sc = m.shortcut {
                print("Modus: \(m.name) | keyCode \(sc.0) | flags 0x\(String(sc.1.rawValue, radix: 16))")
            } else {
                print("Modus: \(m.name) | KEIN eigener Shortcut")
            }
        }
        print("aktiver Modus:", activeModeId() ?? "nil")
        if let t = recordingToggle() {
            print("Aufnahme-Hotkey: keyCode \(t.0) | flags 0x\(String(t.1.rawValue, radix: 16))")
        } else {
            print("Aufnahme-Hotkey: fehlt")
        }
        // alle relevanten Roh-Keys zeigen
        if let d = defaults() {
            let keys = d.dictionaryRepresentation().keys.filter { $0.hasPrefix("Shortcut_mode") }.sorted()
            print("Roh-Keys:", keys)
        }
    }
}
