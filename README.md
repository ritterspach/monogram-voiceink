# monogram-voiceink

Native **Swift-App für macOS**, die **Monogram**-Hardware (ehemals Palette Gear) —
Tasten, LEDs und das 240×240-Display — **direkt über USB-Seriell** ansteuert,
komplett ohne die (eingestellte) Monogram-Software. Sie läuft als unsichtbarer
**Hintergrund-Agent** und macht aus dem Gerät einen freihändigen **VoiceInk-
Sprachcontroller**.

Das Wire-Protokoll wurde selbst reverse-engineered: das Gerät spricht **MessagePack**
in **HDLC-Frames (0x7e)** über eine USB-CDC-Serielle Verbindung.

## Funktion

- **Taste 1 – Aufnahme:** kurz tippen = an/aus (Toggle), halten = Push-to-Talk.
  Nimmt im aktuell gewählten Modus auf (sendet dessen VoiceInk-Tastenkürzel).
- **Taste 2 – Modus wählen:** zykelt durch VoiceInks Modi (dynamisch aus dessen
  Einstellungen gelesen) und zeigt den Modus auf dem Display. Der Modus wird beim
  Aufnehmen über das Kürzel wirksam.
- **Display:** Bereitschaft (Mikrofon + Modus), Aufnahme (Timer + Modus), Modus-Overlay.
- **LED:** ruhiges Teal im Leerlauf, pulsierendes Rot während der Aufnahme.
- **Dauerbetrieb:** verbindet automatisch, übersteht Ab-/Anstecken (Hotplug) und
  Schlaf/Aufwachen, startet bei der Anmeldung.

## Aufbau (Swift-Package)

| Datei | Zweck |
|---|---|
| `main.swift` | Einstiegspunkt, Diagnose-Flags, Single-Instance-Sperre, Start des Supervisors |
| `Supervisor.swift` | Geräte-Lebenszyklus: Auto-Connect/Reconnect (Hotplug), nie `exit()` bei fehlendem Gerät |
| `MonogramDevice.swift` | USB-Seriell (ORSSerialPort), Frame-Parsing, Tasten-Events, Display/LED senden |
| `HDLC.swift` | HDLC-Framing (0x7e/0x7d) |
| `Controller.swift` | Tastenlogik (Aufnahme/Modus), Display-Zustände, LED-Feedback |
| `VoiceInk.swift` | VoiceInks Modi/Shortcuts aus den UserDefaults lesen, Tastenkürzel via CGEvent |
| `Screens.swift` / `DisplayRenderer.swift` | Fertige Display-Bilder (READY/REC/MODE) + 240×240-RGB565-Renderer |
| `MenuControl.swift` | (nur Diagnose) Modus über VoiceInks Statusmenü via Accessibility umschalten |
| `Log.swift` | Logging via `os_log` (Subsystem `com.monogram.voiceink`) |

## Schnellstart (Entwicklung)

```sh
swift build
swift run MonogramVoiceInk            # im Vordergrund (Strg+C beendet)
```

Diagnose ohne Gerät:

```sh
swift run MonogramVoiceInk --modes                 # VoiceInk-Modi/Shortcuts prüfen
swift run MonogramVoiceInk --switch-menu "<Name>"  # Modus über Statusmenü (AX) testen
```

## Produktiv (Hintergrund-Agent)

Komplette Einrichtung — selbstsigniertes Zertifikat, Bundle bauen, Bedienungshilfen-
Recht, launchd-Agent — in **[`packaging/SETUP.md`](packaging/SETUP.md)**. Kurz:

```sh
MONOGRAM_SIGN_ID="Monogram Self-Signed" ./scripts/build-app.sh   # → ~/Applications/MonogramVoiceInk.app
./scripts/install-agent.sh                                       # Start bei Anmeldung
/usr/bin/log stream --predicate 'subsystem == "com.monogram.voiceink"'   # Live-Logs
```

Die App braucht nur das **Bedienungshilfen-Recht** (für die simulierten Tastenkürzel).

## Voraussetzungen

- macOS 14+, Swift-Toolchain (Xcode).
- Der Monogram-Hintergrunddienst darf **nicht** laufen (belegt sonst den seriellen Port):
  ```sh
  killall "Monogram Creator Internal" "Monogram Service Helper" "Monogram Workspace Helper"
  ```

## Protokoll (selbst ermittelt)

```
Wire:    0x7e <payload> 0x7e        HDLC-Framing, Escape 0x7d (Byte XOR 0x20)
Payload: MessagePack, jede Nachricht ein eigener Frame

Eingang:    {"in": [ {"i": <slot>, "v": [v0..v7]}, ... ]}
            2-Tasten-Modul: v[0] = Bitmaske (1=Taste1, 2=Taste2, 3=beide)
LED:        {"set_module": [id, 0x02, r|g<<8|b<<16]}  + Commit {"set_module":[id,0x05,0x7f<<24]}
Helligkeit: {"set_brightness": [moduleLed, displayBacklight]}
Display:    {"invoke_display":0x03}  (Frame beginnen)
            je 4 Zeilen: {"write_display_slow":[true,0,y0,240,y1,chunk]}   (240×240 RGB565)
            {"invoke_display":0x04}  (anzeigen)
```

Gerät: „Monogram Core Module", USB-CDC (`/dev/cu.usbmodem*`), VID `0x0483` (STM32).

## Herkunft

Das Protokoll wurde mit einem Python-Prototyp erkundet (`monogram_core.py`,
`monogram.py`, `listen.py`, `experiment.py` …), der zur Referenz im Repo bleibt.
Die produktive Steuerung ist die obige Swift-App.

Der Ordner `reference/` (Monograms proprietärer Installer/Binärdateien aus dem
Reverse-Engineering) ist **bewusst nicht** Teil des Repos — wegen Dateigröße und
Urheberrecht. Die Protokoll-Beschreibung oben genügt zur Nutzung.
