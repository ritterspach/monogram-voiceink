#!/usr/bin/env python3
"""voiceink_ctl – Monogram 2-Tasten-Modul + Display als VoiceInk-Controller.

  Taste 1  = Kurz tippen schaltet die Aufnahme um (an/aus); gedrückt HALTEN
             = Push-to-Talk (aufnehmen solange gehalten).
  Taste 2  = VoiceInk-Modus wechseln (zykelt Power-/KI-Modi durch).
  Display  = READY (Mikrofon) ⇄ ● REC + laufender Timer.
  LED      = ruhiges Blau im Leerlauf, pulsierendes Rot beim Aufnehmen.

VORAUSSETZUNGEN
  1) Monogram-Software BEENDET (Port frei):
        killall "Monogram Creator Internal" "Monogram Service Helper" "Monogram Workspace Helper"
  2) In VoiceInk → Einstellungen:
        - Recording-Hotkey auf  ⌃⌥⌘ R  legen, Modus = TOGGLE
          (das Skript erkennt Tipp vs. Halten selbst)
        - Für Taste 2: jedem Modus eine globale Tastenkombi geben unter
          VoiceInk → Modes → [Modus] → Shortcut, z. B. ⌃⌥⌘ 1 / ⌃⌥⌘ 2 / ⌃⌥⌘ 3.
          MODE_COUNT unten auf die Anzahl deiner Modi setzen.
  3) Bedienungshilfen-Recht: Systemeinstellungen → Datenschutz & Sicherheit →
     Bedienungshilfen → Terminal (bzw. python) aktivieren.

    .venv/bin/python voiceink_ctl.py
"""
import sys, time, math, queue, threading, subprocess
sys.path.insert(0, "/Users/ritterspach/Development/monogram-diy")
from monogram_core import MonogramDevice
from display import Framebuffer, draw_time, seven_seg

# ----------------------- Konfiguration (anpassbar) ----------------------- #
REC_KEY, REC_MODS = "r", ["control", "option", "command"]   # VoiceInk Recording-Hotkey (Modus: Toggle)
MODE_MODS = ["control", "option", "command"]                 # = ⌃⌥⌘+Zahl; in VoiceInk je Modus als Shortcut belegen
MODE_COUNT = 3
TAP_MAX = 0.35                 # < diese Dauer (s) = kurzer Tipp (Toggle), sonst Halten (PTT)
IDLE_LED = (0, 40, 70)        # ruhiges Blau
# ------------------------------------------------------------------------- #


# Tastendrücke laufen in einem eigenen Thread: nicht-blockierend (verfälscht die
# Dauermessung nicht) und in fester Reihenfolge.
_key_q = queue.Queue()


def _key_worker():
    while True:
        key, mods = _key_q.get()
        using = (" using {" + ", ".join(f"{m} down" for m in mods) + "}") if mods else ""
        subprocess.run(
            ["osascript", "-e", f'tell application "System Events" to keystroke "{key}"{using}'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


threading.Thread(target=_key_worker, daemon=True).start()


def osa_keystroke(key, mods):
    _key_q.put((key, mods))      # nicht-blockierend


def screen_ready():
    fb = Framebuffer(); fb.fill(0, 0, 0)
    c = (0, 180, 150)
    cx = 120
    fb.disc(cx, 55, 20, *c)               # Kapsel oben
    fb.disc(cx, 115, 20, *c)              # Kapsel unten
    fb.rect(cx - 20, 55, 40, 60, *c)      # Kapsel-Körper
    fb.rect(cx - 2, 135, 4, 24, *c)       # Stativ
    fb.rect(cx - 26, 159, 52, 5, *c)      # Standfuß
    return fb.to_bytes()


def screen_rec(elapsed, pulse):
    fb = Framebuffer(); fb.fill(0, 0, 0)
    fb.disc(120, 60, 22 + int(8 * pulse), 255, 0, 0)     # Record-Punkt
    mm, ss = divmod(int(elapsed), 60)
    draw_time(fb, f"{mm:02d}:{ss:02d}", 255, 50, 50, dw=30, dh=70, y=128)
    return fb.to_bytes()


def screen_mode(n):
    fb = Framebuffer(); fb.fill(0, 0, 0)
    fb.ring(120, 120, 72, 5, 255, 160, 0)
    seven_seg(fb, 95, 75, 50, 90, str(n), 255, 160, 0)
    return fb.to_bytes()


class Controller:
    def __init__(self, dev):
        self.dev = dev
        self.recording = False
        self.latched = False          # True = per kurzem Tipp eingerastet
        self.press_time = 0.0
        self._down_stopped = False    # dieser Tastendruck hat bereits gestoppt
        self.rec_start = 0.0
        self.last_sec = -1
        self.mode = 1
        self.overlay_until = 0.0

    def show_idle(self):
        self.dev.write_display(screen_ready())
        self.dev.set_led(*IDLE_LED)

    def on_event(self, ev, ts):
        if ev.slot != 0:
            return
        if ev.button == 1:
            self.btn1_down(ts) if ev.pressed else self.btn1_up(ts)
        elif ev.button == 2 and ev.pressed:
            self.next_mode()

    def btn1_down(self, ts):
        self.press_time = ts             # echter Empfangs-Zeitstempel
        if self.recording and self.latched:
            self._stop()                 # zweiter Tipp -> Aufnahme aus
            self._down_stopped = True
        else:
            self._start()                # startet (Tipp-Toggle ODER Halten-PTT)
            self._down_stopped = False

    def btn1_up(self, ts):
        if self._down_stopped:           # dieser Druck hatte schon gestoppt
            self._down_stopped = False
            return
        held = ts - self.press_time      # wahre Druckdauer (latenzunabhängig)
        if held < TAP_MAX:
            self.latched = True          # kurzer Tipp -> Aufnahme bleibt an
        else:
            self._stop()                 # gehalten -> Push-to-Talk -> stoppen

    def _start(self):
        if self.recording:
            return
        osa_keystroke(REC_KEY, REC_MODS)
        self.recording = True
        self.latched = False
        self.rec_start = time.monotonic()
        self.last_sec = -1
        self.dev.set_led(255, 0, 0)
        self.dev.write_display(screen_rec(0, 1.0))

    def _stop(self):
        if not self.recording:
            return
        osa_keystroke(REC_KEY, REC_MODS)
        self.recording = False
        self.latched = False
        self.show_idle()

    def next_mode(self):
        self.mode = self.mode % MODE_COUNT + 1
        osa_keystroke(str(self.mode), MODE_MODS)
        self.dev.write_display(screen_mode(self.mode))
        self.overlay_until = time.monotonic() + 1.0

    def tick(self):
        now = time.monotonic()
        if now < self.overlay_until:
            return
        if self.overlay_until:                 # Overlay gerade abgelaufen → zurück
            self.overlay_until = 0.0
            self.last_sec = -1
            if not self.recording:
                self.show_idle()
        if self.recording:
            pulse = 0.5 * (1 + math.sin(now * 8))
            self.dev.set_led(int(80 + 175 * pulse), 0, 0)     # pulsierendes Rot
            sec = int(now - self.rec_start)
            if sec != self.last_sec:                          # Timer 1x/Sekunde
                self.last_sec = sec
                self.dev.write_display(screen_rec(sec, pulse), live_refresh=True)


def main():
    try:
        dev = MonogramDevice().open()
    except Exception as e:
        sys.exit(f"Port nicht offen ({e}). Läuft noch Monogram-Software? Erst beenden:\n"
                 '  killall "Monogram Creator Internal" "Monogram Service Helper" "Monogram Workspace Helper"')

    q = queue.Queue()

    def reader():
        try:
            for ev in dev.button_events():
                q.put((ev, time.monotonic()))      # Zeitstempel beim Empfang
        except Exception:
            pass

    threading.Thread(target=reader, daemon=True).start()

    with dev:
        dev.set_brightness(128, 255)
        ctl = Controller(dev)
        ctl.show_idle()
        print(f"VoiceInk-Controller läuft auf {dev.port}.")
        print("Taste 1 HALTEN = sprechen.  Taste 2 = Modus wechseln.  Strg+C beendet.")
        try:
            while True:
                try:
                    ev, ts = q.get(timeout=0.08)
                    ctl.on_event(ev, ts)
                    while True:
                        ev, ts = q.get_nowait()
                        ctl.on_event(ev, ts)
                except queue.Empty:
                    pass
                ctl.tick()
        except KeyboardInterrupt:
            pass
        finally:
            try:
                dev.set_led(0, 0, 0)
                dev.write_display(Framebuffer().to_bytes())   # Display schwarz
            except Exception:
                pass


if __name__ == "__main__":
    main()
