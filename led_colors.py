#!/usr/bin/env python3
"""LED-Farbwechsel-Test über die Parent-LED (ledKey 0x02) – der Weg, der Rot
gezeigt hat. Zykelt ROT -> GRÜN -> BLAU je Modul-ID, um zu bestätigen, dass
alle Farben schalten, und um die richtige Modul-ID zu finden.

WICHTIG: Monogram-Software muss BEENDET sein (sonst ist der serielle Port belegt).
    .venv/bin/python led_colors.py
"""
import sys, time
sys.path.insert(0, "/Users/ritterspach/Development/monogram-diy")
from monogram_core import MonogramDevice


def cbyte(r, g, b):
    return (r & 0xFF) | ((g & 0xFF) << 8) | ((b & 0xFF) << 16)


def set_color(dev, mid, r, g, b):
    dev.send({"set_module": [mid, 0x02, cbyte(r, g, b)]})


def commit(dev, mid):
    dev.send({"set_module": [mid, 0x05, 0x7F << 24]})


COLORS = [("ROT", 255, 0, 0), ("GRÜN", 0, 255, 0), ("BLAU", 0, 0, 255)]


def main():
    try:
        dev = MonogramDevice().open()
    except Exception as e:
        sys.exit(f"Port nicht offen ({e}). Läuft noch Monogram-Software? Erst beenden:\n"
                 '  killall "Monogram Creator Internal" "Monogram Service Helper" "Monogram Workspace Helper"')
    with dev:
        print("Port:", dev.port)
        for mid in range(4):
            print(f"\n== Modul-ID {mid}: ROT -> GRÜN -> BLAU ==")
            for name, r, g, b in COLORS:
                print(f"   {name}")
                set_color(dev, mid, r, g, b)
                commit(dev, mid)
                time.sleep(1.3)
        print("\nfertig. Bei welcher ID hast du den Farbwechsel gesehen – und kamen alle 3 Farben (inkl. Blau)?")


if __name__ == "__main__":
    main()
