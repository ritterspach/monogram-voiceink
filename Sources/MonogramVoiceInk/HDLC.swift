import Foundation

/// HDLC-Framing wie vom Monogram-Gerät verwendet: 0x7e als Flag, 0x7d als Escape (Byte XOR 0x20).
enum HDLC {
    static let flag: UInt8 = 0x7E
    static let esc: UInt8 = 0x7D

    static func encode(_ payload: Data) -> Data {
        var out = [UInt8]()
        out.reserveCapacity(payload.count + (payload.count >> 3) + 2)
        out.append(flag)
        for b in payload {
            if b == flag || b == esc {
                out.append(esc)
                out.append(b ^ 0x20)
            } else {
                out.append(b)
            }
        }
        out.append(flag)
        return Data(out)
    }

    static func decode(_ frame: Data) -> Data {
        var out = Data()
        var escNext = false
        for b in frame {
            if escNext {
                out.append(b ^ 0x20)
                escNext = false
            } else if b == esc {
                escNext = true
            } else {
                out.append(b)
            }
        }
        return out
    }
}
