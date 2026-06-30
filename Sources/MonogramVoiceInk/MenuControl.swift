import Foundation
import AppKit
import ApplicationServices

/// Schaltet VoiceInks aktiven Modus über dessen Menübar-Statusmenü um – per
/// Accessibility (AXUIElement). Nutzt dasselbe Bedienungshilfen-Recht, das die
/// App für die CGEvent-Tastenkürzel ohnehin anfordert; kein zusätzliches
/// Automations-Recht nötig.
///
/// Menü-Aufbau (ermittelt): Statusmenü → „Modus: <aktiv>" → Untermenü mit den
/// Modusnamen (der aktive trägt ein Häkchen-Suffix).
enum MenuControl {
    private static func copyAttr(_ el: AXUIElement, _ name: String) -> CFTypeRef? {
        var v: CFTypeRef?
        return AXUIElementCopyAttributeValue(el, name as CFString, &v) == .success ? v : nil
    }

    private static func children(_ el: AXUIElement) -> [AXUIElement] {
        (copyAttr(el, kAXChildrenAttribute as String) as? [AXUIElement]) ?? []
    }

    private static func title(_ el: AXUIElement) -> String {
        (copyAttr(el, kAXTitleAttribute as String) as? String) ?? ""
    }

    private static func role(_ el: AXUIElement) -> String {
        (copyAttr(el, kAXRoleAttribute as String) as? String) ?? ""
    }

    /// Öffnet das Menü eines Items (AXPress) und wartet aufs erste AXMenu-Kind.
    private static func openMenu(of item: AXUIElement) -> AXUIElement? {
        AXUIElementPerformAction(item, kAXPressAction as CFString)
        for _ in 0..<30 {
            if let m = children(item).first(where: { role($0) == (kAXMenuRole as String) }) { return m }
            usleep(20_000)   // 20 ms
        }
        return children(item).first { role($0) == (kAXMenuRole as String) }
    }

    private static func voiceInkPID() -> pid_t? {
        NSRunningApplication
            .runningApplications(withBundleIdentifier: VoiceInk.suite)
            .first?.processIdentifier
    }

    /// Schaltet auf den Modus mit Namen `name`. Gibt true zurück, wenn der
    /// Ziel-Eintrag gefunden und geklickt wurde.
    @discardableResult
    static func activateMode(named name: String) -> Bool {
        guard let pid = voiceInkPID() else { return false }
        let app = AXUIElementCreateApplication(pid)
        guard let extras = copyAttr(app, "AXExtrasMenuBar") else { return false }
        let extrasBar = extras as! AXUIElement
        guard let statusItem = children(extrasBar).first else { return false }
        guard let menu = openMenu(of: statusItem) else { return false }
        defer { AXUIElementPerformAction(statusItem, kAXCancelAction as CFString) }

        guard let modeItem = children(menu).first(where: { title($0).hasPrefix("Modus:") }),
              let sub = openMenu(of: modeItem) else { return false }

        // Aktiver Eintrag trägt ein Häkchen-Suffix → auf Präfix prüfen.
        guard let target = children(sub).first(where: {
            let t = title($0); return t == name || t.hasPrefix(name + " ")
        }) else { return false }

        return AXUIElementPerformAction(target, kAXPressAction as CFString) == .success
    }
}
