"""monogram_core – Protokoll & Geräte-Zugriff für das Monogram Core Module.

Reverse-engineertes Wire-Protokoll (selbst ermittelt, bestätigt):

    Frame:   0x7e <payload> 0x7e        HDLC-Framing, Escape 0x7d (Byte XOR 0x20)
    Payload: MessagePack
    Eingang: {"in": [ {"i": <slot>, "v": [v0..v7]}, ... ]}
             Beim 2-Tasten-Modul ist v[0] eine Bitmaske:
                 Bit 0 (1) = Taste 1,  Bit 1 (2) = Taste 2

Diese Bibliothek kapselt Framing, MessagePack und die serielle Verbindung,
damit die CLIs (monogram.py, listen.py, send.py, experiment.py) schlank bleiben.
"""
from __future__ import annotations

import glob
import time
from dataclasses import dataclass
from typing import Iterator, Optional

try:
    import serial          # pyserial
    import msgpack
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "Fehlende Abhängigkeit – bitte installieren:\n"
        "    python -m pip install pyserial msgpack"
    ) from exc

FLAG = 0x7E          # HDLC-Flag (Frame-Begrenzer)
ESC = 0x7D           # HDLC-Escape
DEFAULT_BAUD = 115200
DEFAULT_GLOB = "/dev/cu.usbmodem*"


# --------------------------------------------------------------------------- #
#  Low-Level: Port-Suche & HDLC-Framing
# --------------------------------------------------------------------------- #
def find_port(pattern: str = DEFAULT_GLOB) -> Optional[str]:
    """Ersten passenden seriellen Port liefern (oder None)."""
    hits = sorted(glob.glob(pattern))
    return hits[0] if hits else None


def hdlc_encode(payload: bytes) -> bytes:
    """payload -> 0x7e <gestopfter payload> 0x7e."""
    out = bytearray([FLAG])
    for b in payload:
        if b in (FLAG, ESC):
            out += bytes([ESC, b ^ 0x20])
        else:
            out.append(b)
    out.append(FLAG)
    return bytes(out)


def hdlc_decode(frame: bytes) -> bytes:
    """Inhalt zwischen zwei Flags entstopfen (0x7d <b> -> b XOR 0x20)."""
    out = bytearray()
    esc = False
    for b in frame:
        if esc:
            out.append(b ^ 0x20)
            esc = False
        elif b == ESC:
            esc = True
        else:
            out.append(b)
    return bytes(out)


def pack(obj) -> bytes:
    """JSON-artiges Objekt -> sendefertiger Frame (MessagePack + HDLC)."""
    return hdlc_encode(msgpack.packb(obj, use_bin_type=True))


# --------------------------------------------------------------------------- #
#  High-Level: Event-Modell
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class ButtonEvent:
    slot: int       # Modul-Port am Core (0..3)
    button: int     # Tastennummer, 1-basiert
    pressed: bool   # True = gedrückt, False = losgelassen

    def __str__(self) -> str:
        arrow = "↓ gedrückt" if self.pressed else "↑ losgelassen"
        return f"Slot {self.slot} · Taste {self.button} · {arrow}"


# --------------------------------------------------------------------------- #
#  Geräte-Abstraktion
# --------------------------------------------------------------------------- #
class MonogramDevice:
    """Serielle Verbindung zum Monogram Core Module.

    Beispiel:
        with MonogramDevice() as dev:
            for ev in dev.button_events():
                print(ev)
    """

    def __init__(self, port: Optional[str] = None, baud: int = DEFAULT_BAUD):
        self.port = port or find_port()
        if not self.port:
            raise SystemExit(
                "Kein Monogram-Port gefunden.\n"
                "  • Datenkabel (kein Ladekabel) verwenden\n"
                "  • möglichst direkt am Mac statt am Hub/Dock\n"
                "  • prüfen mit:  ls /dev/cu.*"
            )
        self.baud = baud
        self._ser: Optional[serial.Serial] = None
        self._buf = bytearray()
        self._state: dict[int, int] = {}   # slot -> letzte Tasten-Bitmaske

    # -- Lebenszyklus ------------------------------------------------------- #
    def open(self) -> "MonogramDevice":
        self._ser = serial.Serial(self.port, self.baud, timeout=0.1)
        self._ser.dtr = True
        self._ser.rts = True
        return self

    def close(self) -> None:
        if self._ser:
            self._ser.close()
            self._ser = None

    def __enter__(self) -> "MonogramDevice":
        return self.open()

    def __exit__(self, *exc) -> None:
        self.close()

    # -- Senden ------------------------------------------------------------- #
    def send(self, obj) -> bytes:
        """Objekt als MessagePack-Frame senden. Gibt die gesendeten Bytes zurück."""
        frame = pack(obj)
        self._ser.write(frame)
        self._ser.flush()
        return frame

    # -- Geräte-Output: LED & Display ------------------------------------- #
    #  Protokoll aus dem Dienst-Quellcode (CoreV2Protocol). Jede Nachricht ist
    #  ein eigener Frame. Setzt voraus, dass die Monogram-Software NICHT läuft
    #  (sonst belegt sie den seriellen Port).
    DISPLAY_SIZE = 240        # Display: 240x240, RGB565 (2 Byte/Pixel)

    def set_brightness(self, module_led: int = 128, display_backlight: int = 255) -> None:
        self.send({"set_brightness": [module_led, display_backlight]})

    def set_led(self, r: int, g: int, b: int, module_id: int = 0) -> None:
        """Setzt die Modul-LED auf eine Farbe (0..255 je Kanal) und übernimmt sie."""
        cfg = (r & 0xFF) | ((g & 0xFF) << 8) | ((b & 0xFF) << 16)
        self.send({"set_module": [module_id, 0x02, cfg]})
        self.send({"set_module": [module_id, 0x05, 0x7F << 24]})   # commit

    def write_display(self, rgb565: bytes, live_refresh: bool = False) -> None:
        """Schreibt ein 240x240-RGB565-Bild (115200 Bytes) aufs Display.
        live_refresh=True schaltet das Display beim Aktualisieren nicht ab
        (flackerfrei für Animationen/Uhr)."""
        w, rows, bpp = self.DISPLAY_SIZE, 4, 2
        packet = w * rows * bpp
        if len(rgb565) != w * w * bpp:
            raise ValueError(f"Bild muss {w*w*bpp} Bytes sein, ist {len(rgb565)}")
        if not live_refresh:
            self.send({"invoke_display": 0x03})           # aus
        for idx, i in enumerate(range(0, len(rgb565), packet)):
            self.send({"write_display_slow": [True, 0, idx * rows, w, (idx + 1) * rows, rgb565[i:i + packet]]})
        self.send({"invoke_display": 0x04})               # an

    # -- Empfangen ---------------------------------------------------------- #
    def frames(self) -> Iterator[dict]:
        """Blockierender Generator über alle dekodierten MessagePack-Objekte."""
        while True:
            chunk = self._ser.read(256)
            if chunk:
                self._buf += chunk
                yield from self._drain()

    def _drain(self) -> Iterator[dict]:
        while True:
            i = self._buf.find(FLAG)
            if i < 0:
                if len(self._buf) > 4096:      # Schutz gegen Müll-Aufstau
                    del self._buf[:-2]
                return
            j = self._buf.find(FLAG, i + 1)
            if j < 0:
                if i > 0:
                    del self._buf[:i]          # Müll vor dem ersten Flag verwerfen
                return
            raw = bytes(self._buf[i + 1:j])
            del self._buf[:j]                  # Schluss-Flag als nächstes Start-Flag behalten
            if not raw:
                continue
            try:
                yield msgpack.unpackb(hdlc_decode(raw), raw=False)
            except Exception:
                continue

    def button_events(self) -> Iterator[ButtonEvent]:
        """Höhere Ebene: nur Flankenwechsel der Tasten als ButtonEvent."""
        for obj in self.frames():
            if not isinstance(obj, dict):
                continue
            for slot, mod in enumerate(obj.get("in") or []):
                if not isinstance(mod, dict):
                    continue
                vals = mod.get("v") or []
                if not vals or not isinstance(vals[0], int):
                    continue
                mask, old = vals[0], self._state.get(slot, 0)
                if mask == old:
                    continue
                changed = mask ^ old
                bit, btn = 1, 1
                while bit <= max(mask, old):
                    if changed & bit:
                        yield ButtonEvent(slot, btn, bool(mask & bit))
                    bit <<= 1
                    btn += 1
                self._state[slot] = mask

    # -- Roh-Zugriff (für Experimente) ------------------------------------- #
    def reset_input(self) -> None:
        self._ser.reset_input_buffer()

    def read_raw(self, seconds: float) -> bytes:
        """Für `seconds` lauschen und alle Rohbytes sammeln."""
        end = time.monotonic() + seconds
        out = bytearray()
        while time.monotonic() < end:
            d = self._ser.read(256)
            if d:
                out += d
        return bytes(out)
