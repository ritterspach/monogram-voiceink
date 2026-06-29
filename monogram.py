#!/usr/bin/env python3
"""Monogram – Tasten zu Aktionen.

Liest Tastendrücke vom Monogram Core Module und führt pro Taste eine frei
definierbare Aktion aus. Zum Anpassen einfach das ACTIONS-Dictionary unten
bearbeiten.

    .venv/bin/python monogram.py [PORT]
    # PORT optional – Standard: erstes /dev/cu.usbmodem*
"""
import subprocess
import sys

from monogram_core import MonogramDevice


# --------------------------------------------------------------------------- #
#  Aktions-Helfer (macOS-nativ, ohne Zusatzabhängigkeiten)
# --------------------------------------------------------------------------- #
def notify(text: str, title: str = "Monogram") -> None:
    """Sichtbare macOS-Mitteilung (keine Sonderrechte nötig)."""
    subprocess.run(["osascript", "-e",
                    f'display notification "{text}" with title "{title}"'])


def keystroke(key: str, *modifiers: str) -> None:
    """Tastendruck simulieren. modifiers: "command", "shift", "option", "control".
    Benötigt einmalig die Berechtigung „Bedienungshilfen" fürs Terminal.
    Beispiel:  keystroke("space", "command")   # Spotlight
    """
    using = (" using {" + ", ".join(f"{m} down" for m in modifiers) + "}") if modifiers else ""
    subprocess.run(["osascript", "-e",
                    f'tell application "System Events" to keystroke "{key}"{using}'])


def shell(*args: str) -> None:
    """Beliebigen Befehl starten, z.B. shell("open", "-a", "Calculator")."""
    subprocess.run(list(args))


# --------------------------------------------------------------------------- #
#  HIER konfigurieren:  (slot, taste) -> Funktion, die beim DRÜCKEN läuft.
#  slot 0 = das 2-Tasten-Modul.  Falls Taste 1/2 vertauscht wirken: tauschen.
# --------------------------------------------------------------------------- #
ACTIONS = {
    (0, 1): lambda: notify("Taste 1 gedrückt"),
    (0, 2): lambda: notify("Taste 2 gedrückt"),

    # Weitere Beispiele:
    # (0, 1): lambda: keystroke("space", "command"),     # Spotlight
    # (0, 2): lambda: shell("open", "https://monogramcc.com"),
}


def main() -> None:
    port = sys.argv[1] if len(sys.argv) > 1 else None
    with MonogramDevice(port) as dev:
        print(f"Verbunden mit {dev.port}. Tasten betätigen. Strg+C beendet.")
        for ev in dev.button_events():
            print(" ", ev)
            if ev.pressed:
                action = ACTIONS.get((ev.slot, ev.button))
                if action:
                    action()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
