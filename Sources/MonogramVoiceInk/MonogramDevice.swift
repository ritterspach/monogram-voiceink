import Foundation
import ORSSerial
import MessagePack
import QuartzCore

struct ButtonEvent {
    let slot: Int
    let button: Int
    let pressed: Bool
}

/// High-Level-Zugriff auf das Monogram Core Module über USB-Seriell.
/// Eingang: MessagePack {"in": [ {"i": slot, "v": [maske, ...]}, ... ]} in 0x7e-Frames.
/// Ausgang: einzelne Befehls-Frames (set_module, set_brightness, write_display_slow, invoke_display).
final class MonogramDevice: NSObject, ORSSerialPortDelegate {
    private let port: ORSSerialPort
    private var buf: [UInt8] = []
    private var state: [Int: Int] = [:]   // slot -> letzte Tasten-Bitmaske

    /// Wird bei jedem Flankenwechsel aufgerufen (mit monotonem Zeitstempel in Sekunden).
    var onButton: ((ButtonEvent, Double) -> Void)?

    var path: String { port.path }

    init?(path: String) {
        guard let p = ORSSerialPort(path: path) else { return nil }
        port = p
        super.init()
        port.baudRate = NSNumber(value: 115200)   // bei USB-CDC nominal
        port.delegate = self
    }

    static func autodetect() -> MonogramDevice? {
        let paths = ORSSerialPortManager.shared().availablePorts.map { $0.path }
        guard let path = paths.first(where: { $0.contains("usbmodem") }) else { return nil }
        return MonogramDevice(path: path)
    }

    func open() { port.open() }
    func close() { port.close() }

    // MARK: - Senden

    func send(_ value: MessagePackValue) {
        port.send(HDLC.encode(pack(value)))
    }

    func setBrightness(moduleLed: Int = 128, displayBacklight: Int = 255) {
        send(["set_brightness": [.int(Int64(moduleLed)), .int(Int64(displayBacklight))]])
    }

    /// Setzt die Modul-LED auf eine Farbe (0..255 je Kanal) und übernimmt sie.
    func setLED(_ r: Int, _ g: Int, _ b: Int, moduleId: Int = 0) {
        let cfg = UInt64((r & 0xFF) | ((g & 0xFF) << 8) | ((b & 0xFF) << 16))
        send(["set_module": [.int(Int64(moduleId)), .int(0x02), .uint(cfg)]])
        send(["set_module": [.int(Int64(moduleId)), .int(0x05), .uint(0x7F00_0000)]])  // commit
    }

    /// Schreibt ein 240x240-RGB565-Bild (115200 Bytes) aufs Display.
    func writeDisplay(_ rgb565: Data, liveRefresh: Bool = false) {
        let w = 240, rows = 4, bpp = 2
        let packet = w * rows * bpp
        var out = Data()
        if !liveRefresh {
            out.append(HDLC.encode(pack(["invoke_display": .int(0x03)])))
        }
        var idx = 0
        var i = 0
        while i < rgb565.count {
            let chunk = rgb565.subdata(in: i ..< min(i + packet, rgb565.count))
            let msg: MessagePackValue = ["write_display_slow":
                [.bool(true), .int(0), .int(Int64(idx * rows)), .int(Int64(w)), .int(Int64((idx + 1) * rows)), .binary(chunk)]]
            out.append(HDLC.encode(pack(msg)))
            idx += 1
            i += packet
        }
        out.append(HDLC.encode(pack(["invoke_display": .int(0x04)])))
        port.send(out)
    }

    // MARK: - ORSSerialPortDelegate

    func serialPortWasOpened(_ serialPort: ORSSerialPort) {
        serialPort.rts = true
        serialPort.dtr = true
    }

    func serialPort(_ serialPort: ORSSerialPort, didReceive data: Data) {
        let ts = CACurrentMediaTime()
        buf.append(contentsOf: data)
        drain(ts)
    }

    func serialPort(_ serialPort: ORSSerialPort, didEncounterError error: Error) {
        FileHandle.standardError.write(Data("Serial-Fehler: \(error)\n".utf8))
    }

    func serialPortWasRemovedFromSystem(_ serialPort: ORSSerialPort) {
        FileHandle.standardError.write(Data("Gerät entfernt.\n".utf8))
    }

    // MARK: - Frame-Parsing

    private func drain(_ ts: Double) {
        while let i = buf.firstIndex(of: HDLC.flag) {
            guard let j = buf[(i + 1)...].firstIndex(of: HDLC.flag) else {
                if i > 0 { buf.removeFirst(i) }           // Müll vor erstem Flag verwerfen
                if buf.count > 8192 { buf.removeAll(keepingCapacity: true) }
                return
            }
            let frame = Array(buf[(i + 1) ..< j])
            buf.removeFirst(j)                            // Schluss-Flag als nächstes Start-Flag behalten
            if frame.isEmpty { continue }
            handle(frame: frame, ts: ts)
        }
    }

    private func handle(frame: [UInt8], ts: Double) {
        let decoded = HDLC.decode(Data(frame))
        guard let value = try? unpackFirst(decoded),
              let dict = value.dictionaryValue,
              let inArr = dict["in"]?.arrayValue else { return }

        for (slot, modVal) in inArr.enumerated() {
            guard let mod = modVal.dictionaryValue,
                  let vArr = mod["v"]?.arrayValue,
                  let mask64 = vArr.first?.int64Value else { continue }
            let mask = Int(mask64)
            let old = state[slot] ?? 0
            if mask == old { continue }
            let changed = mask ^ old
            var bit = 1, btn = 1
            while bit <= max(mask, old) {
                if changed & bit != 0 {
                    onButton?(ButtonEvent(slot: slot, button: btn, pressed: (mask & bit) != 0), ts)
                }
                bit <<= 1
                btn += 1
            }
            state[slot] = mask
        }
    }
}
