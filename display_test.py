#!/usr/bin/env python3
"""Display-Test: füllt das 240x240-Display mit drei Farbbalken (RGB565).

WICHTIG: Monogram-Software muss BEENDET sein.
    .venv/bin/python display_test.py

Protokoll (aus service.ts -> CoreV2Protocol.encodeWriteDisplay):
  {invoke_display: 0x03}                                  -> Display aus
  je 4 Zeilen:  {write_display_slow: [true,0,y0,240,y1,chunk]}
  {invoke_display: 0x04}                                  -> Display an
  Bild = 240x240, 2 Byte/Pixel RGB565, Paketgröße 240*4*2 = 1920 Byte.
"""
import sys
sys.path.insert(0, "/Users/ritterspach/Development/monogram-diy")
from monogram_core import MonogramDevice

W = 240
ROWS = 4
BPP = 2
PACKET = W * ROWS * BPP  # 1920


def rgb565(r, g, b, big_endian=True):
    v = ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)
    hi, lo = (v >> 8) & 0xFF, v & 0xFF
    return bytes([hi, lo]) if big_endian else bytes([lo, hi])


def build_bars(big_endian=True):
    """Oben ROT, Mitte GRÜN, unten BLAU – zum Prüfen von Funktion + Byte-Reihenfolge."""
    buf = bytearray()
    for y in range(W):
        if y < 80:
            px = rgb565(255, 0, 0, big_endian)
        elif y < 160:
            px = rgb565(0, 255, 0, big_endian)
        else:
            px = rgb565(0, 0, 255, big_endian)
        buf += px * W
    return bytes(buf)


def main():
    big_endian = "--le" not in sys.argv  # mit --le auf Little-Endian umschalten
    img = build_bars(big_endian)
    assert len(img) == W * W * BPP, len(img)

    try:
        dev = MonogramDevice().open()
    except Exception as e:
        sys.exit(f"Port nicht offen ({e}). Läuft noch Monogram-Software? Erst beenden:\n"
                 '  killall "Monogram Creator Internal" "Monogram Service Helper" "Monogram Workspace Helper"')
    with dev:
        print(f"Port: {dev.port} – Bild {len(img)} Bytes, {'big' if big_endian else 'little'}-endian")
        dev.send({"set_brightness": [128, 255]})   # Display-Backlight hoch
        dev.send({"invoke_display": 0x03})          # aus
        n = 0
        for i in range(0, len(img), PACKET):
            idx = i // PACKET
            chunk = img[i:i + PACKET]
            dev.send({"write_display_slow": [True, 0, idx * ROWS, W, (idx + 1) * ROWS, chunk]})
            n += 1
        dev.send({"invoke_display": 0x04})          # an
        print(f"fertig: {n} Pakete gesendet. Display sollte 3 Farbbalken zeigen.")
        print("Falls die Farben vertauscht sind, nochmal mit:  .venv/bin/python display_test.py --le")


if __name__ == "__main__":
    main()
