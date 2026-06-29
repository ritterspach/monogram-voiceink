import Foundation
import AppKit

/// Fertige Display-Bilder (240x240 RGB565) für die Zustände des Controllers.
enum Screens {
    private static let teal = NSColor(red: 0.0, green: 0.72, blue: 0.62, alpha: 1)

    static func ready(mode: String) -> Data {
        let r = DisplayRenderer()
        r.fill(NSColor(red: 0.03, green: 0.05, blue: 0.07, alpha: 1))
        r.symbol("mic.fill", centerY: 92, size: 78, color: teal)
        r.text("READY", centerY: 168, size: 30, color: NSColor(white: 0.92, alpha: 1), weight: .heavy)
        r.text(mode.uppercased(), centerY: 206, size: 18, color: teal, weight: .semibold)
        return r.rgb565()
    }

    static func rec(elapsed: Int, mode: String) -> Data {
        let r = DisplayRenderer()
        r.fill(NSColor(red: 0.07, green: 0.0, blue: 0.0, alpha: 1))
        r.disc(cx: 120, cy: 48, r: 17, color: .systemRed)
        r.text("REC", centerY: 90, size: 26, color: .systemRed, weight: .heavy)
        let mm = elapsed / 60, ss = elapsed % 60
        r.text(String(format: "%02d:%02d", mm, ss), centerY: 150, size: 54,
               color: .white, weight: .bold, mono: true)
        r.text(mode.uppercased(), centerY: 206, size: 18, color: NSColor(white: 0.6, alpha: 1), weight: .semibold)
        return r.rgb565()
    }

    static func mode(_ name: String) -> Data {
        let r = DisplayRenderer()
        r.fill(NSColor(red: 0.05, green: 0.04, blue: 0.0, alpha: 1))
        r.text("MODE", centerY: 78, size: 22, color: NSColor(white: 0.5, alpha: 1), weight: .semibold)
        r.text(name.uppercased(), centerY: 134, size: 38, color: .systemOrange, weight: .heavy)
        return r.rgb565()
    }
}
