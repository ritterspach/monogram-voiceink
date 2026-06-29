#!/usr/bin/env python3
"""vimodes – liest die in VoiceInk konfigurierten Modi + ihre Tastenkürzel
direkt aus den macOS-UserDefaults. Damit muss nichts fest verdrahtet werden.

    .venv/bin/python vimodes.py          # zeigt die gefundenen Modi

Quelle: UserDefaults-Domain com.prakashjoshipax.VoiceInk
  modeConfigurationsV2          -> JSON-Array der Modi (name, id, isEnabled, ...)
  Shortcut_mode_<id>            -> {"kind":"key","keyCode":N,"modifierFlagsRawValue":M}
  Shortcut_secondaryRecording   -> Toggle-Hotkey zum Stoppen
"""
import json
import plistlib
import subprocess

DOMAIN = "com.prakashjoshipax.VoiceInk"

# NSEvent.ModifierFlags -> Name für osascript "key code N using {...}"
_FLAGS = [(1 << 17, "shift"), (1 << 18, "control"), (1 << 19, "option"), (1 << 20, "command")]


def read_defaults() -> dict:
    out = subprocess.run(["defaults", "export", DOMAIN, "-"], capture_output=True).stdout
    return plistlib.loads(out)


def _mods(raw: int):
    return [name for bit, name in _FLAGS if raw & bit]


def _shortcut(d: dict, key: str):
    v = d.get(key)
    if not v:
        return None
    try:
        s = json.loads(v)
    except Exception:
        return None
    if s.get("kind") != "key" or "keyCode" not in s:
        return None          # modifier-only Hotkeys lassen sich nicht sauber senden
    return {"key_code": int(s["keyCode"]), "mods": _mods(int(s.get("modifierFlagsRawValue", 0)))}


def read_modes(d: dict = None):
    """Aktive Modi mit zuweisbarem Shortcut: [{name, id, key_code, mods}]."""
    d = d or read_defaults()
    modes = json.loads(d["modeConfigurationsV2"])
    out = []
    for m in modes:
        if not m.get("isEnabled", True):
            continue
        sc = _shortcut(d, "Shortcut_mode_" + str(m.get("id")))
        if sc:
            out.append({"name": m.get("name", "?"), "id": m.get("id"), **sc})
    return out


def stop_shortcut(d: dict = None):
    """Toggle-Hotkey zum Stoppen (sekundärer, sonst primärer Recording-Shortcut)."""
    d = d or read_defaults()
    for key in ("Shortcut_secondaryRecording", "Shortcut_primaryRecording"):
        sc = _shortcut(d, key)
        if sc:
            return sc
    return None


if __name__ == "__main__":
    d = read_defaults()
    print("Gefundene Modi mit Shortcut:")
    for m in read_modes(d):
        print("  %-18s keyCode=%-3s mods=%s" % (m["name"], m["key_code"], m["mods"]))
    print("Stop-Hotkey:", stop_shortcut(d))
