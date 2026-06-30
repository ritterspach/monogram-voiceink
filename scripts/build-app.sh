#!/bin/bash
# Baut MonogramVoiceInk.app (Release), verpackt es als .app-Bundle und signiert es.
#
#   ./scripts/build-app.sh
#
# Signatur-Identität über Umgebungsvariable wählen (Standard: ad-hoc):
#   MONOGRAM_SIGN_ID="Monogram Self-Signed" ./scripts/build-app.sh
#
# Ad-hoc reicht zum Testen, verliert aber das Bedienungshilfen-Recht bei jedem
# Rebuild. Für stabilen Betrieb ein selbstsigniertes Codesignatur-Zertifikat
# anlegen und dessen Namen als MONOGRAM_SIGN_ID setzen.
set -euo pipefail
cd "$(dirname "$0")/.."

APP_NAME="MonogramVoiceInk"
BUNDLE_ID="com.monogram.voiceink"
DEST="${1:-$HOME/Applications}"
SIGN_ID="${MONOGRAM_SIGN_ID:--}"   # "-" = ad-hoc

echo "→ Release-Build …"
swift build -c release --product "$APP_NAME"
BIN=".build/release/$APP_NAME"

APP="$DEST/$APP_NAME.app"
echo "→ Bundle zusammenbauen: $APP"
mkdir -p "$DEST"
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS"
cp "$BIN" "$APP/Contents/MacOS/$APP_NAME"
cp packaging/Info.plist "$APP/Contents/Info.plist"

echo "→ Signieren mit Identität: $SIGN_ID"
codesign --force --sign "$SIGN_ID" --identifier "$BUNDLE_ID" "$APP"
codesign --verify --verbose=2 "$APP"

echo "✅ Fertig: $APP"
if [ "$SIGN_ID" = "-" ]; then
	echo "⚠️  Ad-hoc signiert – Bedienungshilfen-Recht muss nach jedem Rebuild neu erteilt werden."
fi
