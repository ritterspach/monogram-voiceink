import Foundation
import CoreGraphics
import AppKit

/// Zeichnet auf eine 240x240-Leinwand mit Core Graphics (echte Schrift, SF-Symbole,
/// Formen) und liefert das Ergebnis als RGB565-Buffer fürs Monogram-Display.
final class DisplayRenderer {
    static let size = 240
    private let ctx: CGContext

    init() {
        let cs = CGColorSpaceCreateDeviceRGB()
        ctx = CGContext(data: nil, width: 240, height: 240, bitsPerComponent: 8,
                        bytesPerRow: 240 * 4, space: cs,
                        bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
        // Ursprung oben-links (wie das Display), damit y nach unten wächst und Text aufrecht ist.
        ctx.translateBy(x: 0, y: 240)
        ctx.scaleBy(x: 1, y: -1)
    }

    private func withAppKit(_ body: () -> Void) {
        let ns = NSGraphicsContext(cgContext: ctx, flipped: true)
        NSGraphicsContext.saveGraphicsState()
        NSGraphicsContext.current = ns
        body()
        NSGraphicsContext.restoreGraphicsState()
    }

    func fill(_ color: NSColor) {
        ctx.setFillColor(color.cgColor)
        ctx.fill(CGRect(x: 0, y: 0, width: 240, height: 240))
    }

    func disc(cx: CGFloat, cy: CGFloat, r: CGFloat, color: NSColor) {
        ctx.setFillColor(color.cgColor)
        ctx.fillEllipse(in: CGRect(x: cx - r, y: cy - r, width: 2 * r, height: 2 * r))
    }

    /// Horizontal zentrierter Text, vertikal zentriert um `centerY` (oben = 0).
    func text(_ s: String, centerY: CGFloat, size: CGFloat, color: NSColor,
              weight: NSFont.Weight = .bold, mono: Bool = false) {
        let font = mono ? NSFont.monospacedDigitSystemFont(ofSize: size, weight: weight)
                        : NSFont.systemFont(ofSize: size, weight: weight)
        let attrs: [NSAttributedString.Key: Any] = [.font: font, .foregroundColor: color]
        let str = NSAttributedString(string: s, attributes: attrs)
        let b = str.size()
        let x = (240 - b.width) / 2
        let y = centerY - b.height / 2
        withAppKit { str.draw(at: CGPoint(x: x, y: y)) }
    }

    /// SF-Symbol, eingefärbt, zentriert um `centerY`.
    func symbol(_ name: String, centerY: CGFloat, size: CGFloat, color: NSColor) {
        let cfg = NSImage.SymbolConfiguration(pointSize: size, weight: .bold)
        guard let base = NSImage(systemSymbolName: name, accessibilityDescription: nil)?
            .withSymbolConfiguration(cfg) else { return }
        let sz = base.size
        let tinted = NSImage(size: sz)
        tinted.lockFocus()
        color.set()
        let rr = NSRect(origin: .zero, size: sz)
        base.draw(in: rr)
        rr.fill(using: .sourceAtop)
        tinted.unlockFocus()
        let rect = CGRect(x: (240 - sz.width) / 2, y: centerY - sz.height / 2,
                          width: sz.width, height: sz.height)
        withAppKit { tinted.draw(in: rect) }
    }

    /// 240x240 RGB565 (big-endian), Zeile 0 = oben.
    func rgb565() -> Data {
        guard let base = ctx.data else { return Data(count: 240 * 240 * 2) }
        let px = base.bindMemory(to: UInt8.self, capacity: 240 * 240 * 4)
        var out = Data(count: 240 * 240 * 2)
        out.withUnsafeMutableBytes { raw in
            let dst = raw.bindMemory(to: UInt8.self).baseAddress!
            var di = 0
            var i = 0
            let n = 240 * 240 * 4
            while i < n {
                let v = (UInt16(px[i] >> 3) << 11) | (UInt16(px[i + 1] >> 2) << 5) | UInt16(px[i + 2] >> 3)
                dst[di] = UInt8(v >> 8)
                dst[di + 1] = UInt8(v & 0xFF)
                di += 2
                i += 4
            }
        }
        return out
    }
}
