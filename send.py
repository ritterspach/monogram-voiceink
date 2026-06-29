#!/usr/bin/env python3
"""Monogram – ein JSON-Objekt als Frame senden (MessagePack + 0x7e-Framing).

Beispiel (Output-Envelope – Schema noch experimentell):
    .venv/bin/python send.py '{"out":[{"i":0,"led":[255,0,0]},null,null,null]}'
"""
import json
import sys

from monogram_core import MonogramDevice


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("Aufruf:  python send.py '<json>'  [PORT]")
    obj = json.loads(sys.argv[1])
    port = sys.argv[2] if len(sys.argv) > 2 else None
    with MonogramDevice(port) as dev:
        frame = dev.send(obj)
        print(f"gesendet an {dev.port}: {obj}")
        print(f"bytes: {frame.hex()}")
        resp = dev.read_raw(1.0)
        if resp:
            print(f"antwort: {resp.hex()}")


if __name__ == "__main__":
    main()
