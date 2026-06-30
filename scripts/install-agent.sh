#!/bin/bash
# Installiert MonogramVoiceInk als launchd-Hintergrundagent (Start bei Anmeldung,
# Neustart bei Absturz). Erwartet, dass ./scripts/build-app.sh schon gelaufen ist.
#
#   ./scripts/install-agent.sh        # installieren/aktualisieren
#   ./scripts/install-agent.sh stop   # entfernen
set -euo pipefail

LABEL="com.monogram.voiceink"
APP="$HOME/Applications/MonogramVoiceInk.app"
BIN="$APP/Contents/MacOS/MonogramVoiceInk"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
LOGDIR="$HOME/Library/Logs"
DOMAIN="gui/$(id -u)"

if [ "${1:-}" = "stop" ]; then
	launchctl bootout "$DOMAIN/$LABEL" 2>/dev/null || true
	rm -f "$PLIST"
	echo "✅ Agent entfernt."
	exit 0
fi

[ -x "$BIN" ] || { echo "❌ Binary fehlt: $BIN — zuerst ./scripts/build-app.sh ausführen."; exit 1; }
mkdir -p "$HOME/Library/LaunchAgents" "$LOGDIR"

cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>Label</key><string>$LABEL</string>
	<key>ProgramArguments</key><array><string>$BIN</string></array>
	<key>RunAtLoad</key><true/>
	<key>KeepAlive</key><true/>
	<key>ThrottleInterval</key><integer>10</integer>
	<key>ProcessType</key><string>Interactive</string>
	<key>StandardOutPath</key><string>$LOGDIR/MonogramVoiceInk.out.log</string>
	<key>StandardErrorPath</key><string>$LOGDIR/MonogramVoiceInk.err.log</string>
</dict>
</plist>
EOF

launchctl bootout "$DOMAIN/$LABEL" 2>/dev/null || true   # falls schon geladen
launchctl bootstrap "$DOMAIN" "$PLIST"
launchctl enable "$DOMAIN/$LABEL"
echo "✅ Agent geladen: $LABEL"
echo "   Logs:  $LOGDIR/MonogramVoiceInk.{out,err}.log"
echo "   Live:  /usr/bin/log stream --predicate 'subsystem == \"com.monogram.voiceink\"'"
