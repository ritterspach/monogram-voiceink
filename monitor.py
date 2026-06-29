#!/usr/bin/env python3
"""Monogram – Live-Tasten-Übersicht in der Konsole.

Zeigt fortlaufend (in einer Zeile, die sich aktualisiert) den Zustand der
Tasten am 2-Tasten-Modul. So siehst du sofort, was gerade gedrückt ist.

    .venv/bin/python monitor.py [PORT]

  ●  = gedrückt        ○  = frei
"""
import sys

from monogram_core import MonogramDevice

ON, OFF = "●", "○"


def slot_masks(obj) -> dict:
    """Aus einem 'in'-Frame die Tasten-Bitmaske je Slot herauslesen."""
    masks = {}
    if isinstance(obj, dict):
        for slot, mod in enumerate(obj.get("in") or []):
            if isinstance(mod, dict):
                v = mod.get("v") or []
                if v and isinstance(v[0], int):
                    masks[slot] = v[0]
    return masks


def main() -> None:
    port = sys.argv[1] if len(sys.argv) > 1 else None
    with MonogramDevice(port) as dev:
        print(f"Verbunden mit {dev.port}. Drücke die Tasten – Strg+C beendet.\n")
        states: dict[int, int] = {}
        for obj in dev.frames():
            states.update(slot_masks(obj))
            cells = [
                f"Slot {slot}:  Taste 1 {ON if m & 1 else OFF}   Taste 2 {ON if m & 2 else OFF}"
                for slot, m in sorted(states.items())
            ]
            sys.stdout.write("\r" + "   |   ".join(cells) + " " * 6)
            sys.stdout.flush()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
