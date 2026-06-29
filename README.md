# monogram-voiceink

Direkte Ansteuerung von **Monogram**-Hardware (ehemals Palette Gear) — Tasten, LEDs
und das 240×240-Display — **direkt über USB-Seriell, komplett ohne die (eingestellte)
Monogram-Software**. Inklusive eines freihändigen **VoiceInk-Sprachcontrollers**.

Das Protokoll wurde selbst reverse-engineered. Das Gerät spricht **MessagePack** in
**HDLC-Frames (0x7e)** über eine USB-CDC-Serielle Verbindung.

## Stand

| Funktion | Status |
|---|---|
| Tasten lesen (Eingabe) | ✅ |
| LED-Farben setzen | ✅ |
| 240×240-Display bespielen (RGB565) | ✅ |
| VoiceInk-Controller (Push-to-Talk/Toggle + Display-Status) | ✅ |

## Protokoll (selbst ermittelt)

```
Wire:   0x7e <payload> 0x7e        HDLC-Framing, Escape 0x7d (Byte XOR 0x20)
Payload: MessagePack, jede Nachricht ein eigener Frame

Eingang:  {"in": [ {"i": <slot>, "v": [v0..v7]}, ... ]}
          2-Tasten-Modul: v[0] = Bitmaske (1=Taste1, 2=Taste2, 3=beide)
LED:      {"set_module": [id, 0x02, r|g<<8|b<<16]}  + Commit {"set_module":[id,0x05,0x7f<<24]}
Helligkeit: {"set_brightness": [moduleLed, displayBacklight]}
Display:  {"invoke_display":0x03}  (aus)
          je 4 Zeilen: {"write_display_slow":[true,0,y0,240,y1,chunk]}   (240×240 RGB565, 1920 B/Paket)
          {"invoke_display":0x04}  (an)
```

Gerät: „Monogram Core Module", USB-CDC (`/dev/cu.usbmodem*`), VID `0x0483` (STM32).

## Voraussetzungen

- macOS, Python 3
- Der Monogram-Hintergrunddienst darf **nicht** laufen (er belegt den seriellen Port):
  ```sh
  killall "Monogram Creator Internal" "Monogram Service Helper" "Monogram Workspace Helper"
  ```

## Einrichtung

```sh
python3 -m venv .venv
.venv/bin/python -m pip install pyserial msgpack websocket-client
```

## Werkzeuge

| Datei | Zweck |
|---|---|
| `monogram_core.py` | Protokoll-Bibliothek (Framing, MessagePack, `MonogramDevice`: `button_events`, `set_led`, `write_display`) |
| `display.py` | Reiner-Python RGB565-Framebuffer + 7-Segment-Renderer + Formen |
| `monitor.py` | Live-Tasten-Übersicht |
| `monogram.py` | Tastendruck → frei definierbare Aktionen |
| `clock.py` | Live-Uhr auf dem Display |
| `voiceink_ctl.py` | VoiceInk-Controller (Taste 1 = Push-to-Talk/Toggle, Taste 2 = Modus, Display = REC/READY + Timer, LED-Feedback) |
| `vimodes.py` | Liest VoiceInks konfigurierte Modi + Shortcuts dynamisch aus den UserDefaults |
| `led_colors.py`, `led_test.py`, `display_test.py` | Hardware-Tests |
| `listen.py`, `send.py`, `experiment.py` | Debugging/Erkundung |

## Schnellstart

```sh
.venv/bin/python clock.py          # Live-Uhr aufs Display
.venv/bin/python voiceink_ctl.py   # Sprach-Controller
```

## Hinweis

Der Ordner `reference/` (Monograms proprietärer Installer/Binärdateien, die beim
Reverse-Engineering genutzt wurden) ist **bewusst nicht** Teil dieses Repos — wegen
Dateigröße und Urheberrecht. Die obige Protokoll-Beschreibung genügt zur Nutzung.

---

*Prototyp.* Direkte, eigenständige Hardware-Steuerung ohne Abhängigkeit von der
Original-Software.
