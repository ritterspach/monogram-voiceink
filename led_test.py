#!/usr/bin/env python3
"""LED-Test über das ECHTE Geräteprotokoll (aus dem Dienst-Quellcode extrahiert).

WICHTIG: Die Monogram-Software muss BEENDET sein – sonst belegt sie den
seriellen Port und dieses Skript bekommt ihn nicht.

Protokoll (aus @monogramcc service.ts, CoreV2Protocol):
  Jede Nachricht = eigener 0x7E-Frame mit msgpack-Payload.
  LED setzen:  {"set_module": [id, ledKey, configByte]}
      ledKey 0x02 = Modul-LED;  0x05 = Submodul (configByte |= submoduleIndex<<24)
      configByte = r | g<<8 | b<<16
  Commit:      {"set_module": [id, 0x05, 0x7f<<24]}

Aufruf:
    .venv/bin/python led_test.py
"""
import sys, time
sys.path.insert(0, "/Users/ritterspach/Development/monogram-diy")
from monogram_core import MonogramDevice


def config_byte(r, g, b, sub=None):
    c = (r & 0xFF) | ((g & 0xFF) << 8) | ((b & 0xFF) << 16)
    if sub is not None:
        c |= (sub & 0xFF) << 24
    return c


def set_color(dev, mid, r, g, b, sub=None):
    key = 0x02 if sub is None else 0x05
    dev.send({"set_module": [mid, key, config_byte(r, g, b, sub)]})


def commit(dev, mid):
    dev.send({"set_module": [mid, 0x05, 0x7F << 24]})


def main():
    with MonogramDevice() as dev:
        print(f"Port offen: {dev.port}\n")

        print("== Phase 1: Modul-LED (parent), je Modul-ID 0..3 -> ROT ==")
        for mid in range(4):
            print(f"  id={mid}: parent ROT")
            set_color(dev, mid, 255, 0, 0)
            commit(dev, mid)
            time.sleep(2.5)

        print("== Phase 2: Submodule (2 Tasten), je ID -> Taste0=ROT, Taste1=BLAU ==")
        for mid in range(4):
            print(f"  id={mid}: sub0 ROT, sub1 BLAU")
            set_color(dev, mid, 255, 0, 0, sub=0)
            set_color(dev, mid, 0, 0, 255, sub=1)
            commit(dev, mid)
            time.sleep(2.5)

        print("\nfertig. Welche Phase/ID hat die Tasten-LEDs gefärbt?")


if __name__ == "__main__":
    main()
