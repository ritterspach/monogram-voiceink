#!/usr/bin/env python3
"""Monogram – Live-Anzeige aller dekodierten Frames (Debugging / Erkundung).

Zeigt jedes vom Gerät empfangene MessagePack-Objekt. Praktisch, um neue Module
oder Eingänge zu erkunden.

    .venv/bin/python listen.py [PORT]
"""
import sys

from monogram_core import MonogramDevice


def main() -> None:
    port = sys.argv[1] if len(sys.argv) > 1 else None
    with MonogramDevice(port) as dev:
        print(f"Lese {dev.port}. Tasten/Regler betätigen. Strg+C beendet.")
        for obj in dev.frames():
            print(obj)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
