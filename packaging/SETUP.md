# MonogramVoiceInk – Produktiv-Einrichtung (Hintergrundbetrieb)

Die App läuft als unsichtbarer Hintergrund-Agent (`LSUIElement`), gestartet von
launchd bei der Anmeldung. Sie wartet auf das Monogram-Gerät, verbindet
automatisch und überlebt Ab-/Anstecken sowie Schlaf/Aufwachen.

## Einmalige Einrichtung

### 1. Selbstsigniertes Zertifikat anlegen (für stabile Rechte)
Ohne stabile Signatur muss das Bedienungshilfen-Recht nach jedem Rebuild neu
erteilt werden. Ein selbstsigniertes Zertifikat behebt das – kostenlos, ohne
Apple-Account:

> **Schlüsselbundverwaltung** → *Zertifikatsassistent → Ein Zertifikat erstellen…*
> → Name `Monogram Self-Signed`, Identitätstyp **Selbstsigniertes Stammzert.**,
> Zertifikatstyp **Codesignatur** → erstellen.

Prüfen:
```sh
security find-identity -v -p codesigning      # sollte "Monogram Self-Signed" zeigen
```

### 2. App bauen & signieren
```sh
MONOGRAM_SIGN_ID="Monogram Self-Signed" ./scripts/build-app.sh
# → ~/Applications/MonogramVoiceInk.app
```

### 3. Bedienungshilfen-Recht erteilen (einmalig)
Die App simuliert Tastenkürzel (CGEvent) und braucht dafür das Bedienungshilfen-
Recht. Einmal manuell starten, damit sie im Systemdialog erscheint:
```sh
open ~/Applications/MonogramVoiceInk.app
```
Dann **Systemeinstellungen → Datenschutz & Sicherheit → Bedienungshilfen** →
`MonogramVoiceInk` aktivieren. Dank stabiler Signatur bleibt das Recht über
spätere Rebuilds erhalten.

### 4. Als Hintergrund-Agent installieren
```sh
./scripts/install-agent.sh          # Start bei Anmeldung + Neustart bei Absturz
```

## Betrieb

| Aufgabe | Befehl |
|---|---|
| Live-Logs | `/usr/bin/log stream --predicate 'subsystem == "com.monogram.voiceink"'` |
| Verlauf | `/usr/bin/log show --last 15m --predicate 'subsystem == "com.monogram.voiceink"'` |
| Datei-Logs | `~/Library/Logs/MonogramVoiceInk.{out,err}.log` |
| Neu bauen + übernehmen | `MONOGRAM_SIGN_ID="Monogram Self-Signed" ./scripts/build-app.sh && ./scripts/install-agent.sh` |
| Agent entfernen | `./scripts/install-agent.sh stop` |

## Diagnose-Flags (ohne Agent, im Terminal)
```sh
.build/debug/MonogramVoiceInk --modes                 # VoiceInk-Modi/Shortcuts prüfen
.build/debug/MonogramVoiceInk --set-mode <id>         # aktiven Modus in Defaults setzen
.build/debug/MonogramVoiceInk --switch-menu "<Name>"  # Modus über Statusmenü (AX) testen
```

## Tastenbelegung
- **Taste 1** – Aufnahme: kurz tippen = an/aus (Toggle), halten = Push-to-Talk.
  Nimmt im gewählten Modus auf (sendet dessen Tastenkürzel).
- **Taste 2** – Modus wählen (Anzeige auf dem Geräte-Display; wird bei der
  nächsten Aufnahme über das Modus-Kürzel wirksam).
