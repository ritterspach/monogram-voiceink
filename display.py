#!/usr/bin/env python3
"""display – kleiner RGB565-Framebuffer für das 240x240-Monogram-Display.

Reines Python, keine Zusatz-Abhängigkeiten. Bietet Flächen/Rechtecke und einen
großen 7-Segment-Renderer für Ziffern + Doppelpunkt (ideal für eine Uhr).

    from display import Framebuffer, draw_time
    fb = Framebuffer(); fb.fill(0,0,0); draw_time(fb, "12:34:56", 0,255,180)
    dev.write_display(fb.to_bytes())
"""

SIZE = 240

# 7-Segment-Belegung je Ziffer: a=oben b=oben-rechts c=unten-rechts d=unten
# e=unten-links f=oben-links g=mitte
_SEG = {
    "0": "abcdef", "1": "bc", "2": "abged", "3": "abgcd", "4": "fgbc",
    "5": "afgcd", "6": "afgedc", "7": "abc", "8": "abcdefg", "9": "abcfgd",
}


class Framebuffer:
    def __init__(self, size=SIZE, big_endian=True):
        self.size = size
        self.big_endian = big_endian
        self.buf = bytearray(size * size * 2)

    def _enc(self, r, g, b):
        v = ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)
        hi, lo = (v >> 8) & 0xFF, v & 0xFF
        return (hi, lo) if self.big_endian else (lo, hi)

    def fill(self, r, g, b):
        hi, lo = self._enc(r, g, b)
        self.buf[:] = bytes([hi, lo]) * (self.size * self.size)

    def pixel(self, x, y, r, g, b):
        if 0 <= x < self.size and 0 <= y < self.size:
            hi, lo = self._enc(r, g, b)
            o = (y * self.size + x) * 2
            self.buf[o] = hi
            self.buf[o + 1] = lo

    def rect(self, x, y, w, h, r, g, b):
        hi, lo = self._enc(r, g, b)
        cell = bytes([hi, lo])
        for yy in range(max(0, y), min(self.size, y + h)):
            x0 = max(0, x)
            x1 = min(self.size, x + w)
            if x1 > x0:
                o = (yy * self.size + x0) * 2
                self.buf[o:o + (x1 - x0) * 2] = cell * (x1 - x0)

    def disc(self, cx, cy, radius, r, g, b):
        """Gefüllter Kreis."""
        rr = radius * radius
        for yy in range(cy - radius, cy + radius + 1):
            dy = yy - cy
            if dy * dy <= rr:
                span = int((rr - dy * dy) ** 0.5)
                self.rect(cx - span, yy, 2 * span + 1, 1, r, g, b)

    def ring(self, cx, cy, radius, thickness, r, g, b):
        """Kreisring (Umriss mit Dicke)."""
        ro2 = radius * radius
        ri = max(0, radius - thickness)
        ri2 = ri * ri
        for yy in range(cy - radius, cy + radius + 1):
            for xx in range(cx - radius, cx + radius + 1):
                d = (xx - cx) ** 2 + (yy - cy) ** 2
                if ri2 <= d <= ro2:
                    self.pixel(xx, yy, r, g, b)

    def to_bytes(self):
        return bytes(self.buf)


def seven_seg(fb, x, y, w, h, ch, r, g, b, t=None):
    """Zeichnet eine Ziffer im Kasten (x,y,w,h)."""
    if t is None:
        t = max(3, w // 6)
    segs = _SEG.get(ch, "")
    midy = y + h // 2
    half = h // 2 - t
    if "a" in segs: fb.rect(x + t, y, w - 2 * t, t, r, g, b)
    if "g" in segs: fb.rect(x + t, midy - t // 2, w - 2 * t, t, r, g, b)
    if "d" in segs: fb.rect(x + t, y + h - t, w - 2 * t, t, r, g, b)
    if "f" in segs: fb.rect(x, y + t, t, half, r, g, b)
    if "b" in segs: fb.rect(x + w - t, y + t, t, half, r, g, b)
    if "e" in segs: fb.rect(x, midy, t, half, r, g, b)
    if "c" in segs: fb.rect(x + w - t, midy, t, half, r, g, b)


def _colon(fb, x, y, h, r, g, b, t):
    fb.rect(x, y + h // 3 - t // 2, t, t, r, g, b)
    fb.rect(x, y + 2 * h // 3 - t // 2, t, t, r, g, b)


def draw_time(fb, text, r=0, g=255, b=180, dw=28, dh=72, gap=6, y=None):
    """Zeichnet z.B. '12:34:56' (Ziffern + Doppelpunkte), horizontal zentriert.
    y=None -> vertikal zentriert; sonst obere Kante bei y."""
    t = max(3, dw // 6)
    colon_w = t
    width = sum((colon_w if c == ":" else dw) for c in text) + gap * (len(text) - 1)
    x = (fb.size - width) // 2
    if y is None:
        y = (fb.size - dh) // 2
    for c in text:
        if c == ":":
            _colon(fb, x, y, dh, r, g, b, t)
            x += colon_w + gap
        else:
            seven_seg(fb, x, y, dw, dh, c, r, g, b, t)
            x += dw + gap
