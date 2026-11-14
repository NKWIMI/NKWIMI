#!/usr/bin/env bash
# Generates the android/ and ios/ platform folders and applies the settings
# this app needs. Run once from the app/ folder:  bash scripts/setup.sh com.yourcompany
set -euo pipefail

ORG="${1:-com.example}"
cd "$(dirname "$0")/.."

flutter create . --project-name ebola_guard --org "$ORG" --platforms android,ios

MANIFEST=android/app/src/main/AndroidManifest.xml
if ! grep -q 'android.permission.INTERNET' "$MANIFEST"; then
  # Release builds need INTERNET to reach the AI backend.
  perl -0pi -e 's#<application#<uses-permission android:name="android.permission.INTERNET"/>\n    <application#' "$MANIFEST"
  echo "Added INTERNET permission to $MANIFEST"
fi

# Allow plain http://10.0.2.2 in DEBUG builds only (local backend on emulator).
DEBUG_MANIFEST=android/app/src/debug/AndroidManifest.xml
if [ -f "$DEBUG_MANIFEST" ] && ! grep -q 'usesCleartextTraffic' "$DEBUG_MANIFEST"; then
  perl -0pi -e 's#</manifest>#    <application android:usesCleartextTraffic="true"/>\n</manifest>#' "$DEBUG_MANIFEST"
  echo "Enabled cleartext HTTP for debug builds only"
fi

flutter pub get
echo
echo "Done. Check android/app/build.gradle(.kts): targetSdk must be 36 or higher for Google Play."
grep -n -E 'targetSdk|compileSdk|minSdk' android/app/build.gradle* || true
