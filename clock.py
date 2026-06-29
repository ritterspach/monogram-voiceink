#!/usr/bin/env python3
"""clock – zeigt die aktuelle Uhrzeit (HH:MM:SS) auf dem Monogram-Display.

Eine echte kleine Display-App, komplett ohne Monogram-Software.
WICHTIG: Die Monogram-Software muss BEENDET sein (sonst ist der Port belegt).

    .venv/bin/python clock.py
"""
import sys
import time
from datetime import datetime

sys.path.insert(0, "/Users/ritterspach/Development/monogram-diy")
from monogram_core import MonogramDevice
from display import Framebuffer, draw_time


def main():
    try:
        dev = MonogramDevice().open()
    except Exception as e:
        sys.exit(f"Port nicht offen ({e}). Läuft noch Monogram-Software? Erst beenden:\n"
                 '  killall "Monogram Creator Internal" "Monogram Service Helper" "Monogram Workspace Helper"')
    with dev:
        print(f"Uhr läuft auf {dev.port}. Strg+C beendet.")
        dev.set_brightness(128, 255)
        dev.set_led(0, 40, 80)          # dezentes Blau an den Tasten
        last = None
        try:
            while True:
                now = datetime.now().strftime("%H:%M:%S")
                if now != last:
                    fb = Framebuffer()
                    fb.fill(0, 0, 0)
                    draw_time(fb, now, 0, 255, 180)
                    dev.write_display(fb.to_bytes(), live_refresh=True)
                    last = now
                time.sleep(0.1)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
