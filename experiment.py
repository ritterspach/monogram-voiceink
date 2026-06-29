#!/usr/bin/env python3
"""Monogram – Output-Experiment: Display/LED-Schema finden.

Sendet nacheinander Kandidaten-Frames und liest Antworten. Pacing per [Enter] –
beobachte dabei LEDs + Display und merke dir, welche Nummer eine sichtbare
Reaktion auslöst.

    .venv/bin/python experiment.py
"""
import msgpack

from monogram_core import MonogramDevice, hdlc_decode


def slot(port: int, obj):
    """4-Port-Array mit obj auf Position `port`, Rest null."""
    arr = [None, None, None, None]
    arr[port] = obj
    return arr


# (Label, Objekt)
#   Gruppe A: Output-Envelope an der TASTEN-LED testen (Port 0, sofort sichtbar)
#   Gruppe B: Display-Text auf jedem Port versuchen
CANDIDATES = [
    ("A1 LED 2 Farben (led)", {"out": slot(0, {"i": 0, "led": [[255, 0, 0], [0, 255, 0]]})}),
    ("A2 LED 2 Farben (v)",   {"out": slot(0, {"i": 0, "v":   [[255, 0, 0], [0, 255, 0]]})}),
    ("A3 LED 1 Farbe (led)",  {"out": slot(0, {"i": 0, "led": [255, 0, 0]})}),
    ("A4 LED hex (c)",        {"out": slot(0, {"i": 0, "c":   ["#ff0000", "#00ff00"]})}),
    ("B0 Text @Port0",        {"out": slot(0, {"i": 0, "profileText": "HELLO"})}),
    ("B1 Text @Port1",        {"out": slot(1, {"i": 0, "profileText": "HELLO"})}),
    ("B2 Text @Port2",        {"out": slot(2, {"i": 0, "profileText": "HELLO"})}),
    ("B3 Text @Port3",        {"out": slot(3, {"i": 0, "profileText": "HELLO"})}),
]


def decode_response(raw: bytes):
    """0x7e-getrennte Antwort-Frames dekodieren (best effort)."""
    for part in raw.split(b"\x7e"):
        if not part:
            continue
        try:
            yield msgpack.unpackb(hdlc_decode(part), raw=False)
        except Exception:
            continue


def main() -> None:
    with MonogramDevice() as dev:
        print(f"Verbunden mit {dev.port}. Beobachte LEDs + Display.\n")
        for n, (label, obj) in enumerate(CANDIDATES, 1):
            try:
                input(f"[Enter] → Kandidat {n}/{len(CANDIDATES)}: {label} ")
            except (EOFError, KeyboardInterrupt):
                break
            dev.reset_input()
            frame = dev.send(obj)
            print(f"   gesendet: {obj}")
            print(f"   bytes:    {frame.hex()}")
            raw = dev.read_raw(1.5)
            if raw:
                print(f"   antwort roh: {raw.hex()}")
                for resp in decode_response(raw):
                    print(f"   antwort:     {resp}")
            else:
                print("   (keine Antwort)")
            print()
    print("Fertig. Welche Nummer(n) zeigten eine Reaktion – und was "
          "(LED-Farbe / Display)?")


if __name__ == "__main__":
    main()
