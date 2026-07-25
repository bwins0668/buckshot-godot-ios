#!/usr/bin/env bash
# Manually package a signed .ipa from a pre-built xcarchive.
#
# exportArchive segfaults on the macos-14 runner (IDEDistribution SIGSEGV
# regardless of method=development/app-store/ad-hoc). We bypass it by:
#   1. Copying the .app out of the xcarchive
#   2. Re-signing with our distribution identity (xcarchive's signature
#      uses the embedded provisioning, which is fine, but we also need to
#      embed the mobileprovision for distribution)
#   3. Zipping into Payload/<app>.app
#
# Output: a sideload-ready .ipa at $RUNNER_TEMP/ipa_out/buckshot.ipa
set -euo pipefail

ARCHIVE="${1:-$RUNNER_TEMP/Buckshot.xcarchive}"
OUT_DIR="${2:-$RUNNER_TEMP/ipa_out}"
PROFILE_SRC="${3:-$HOME/Library/MobileDevice/Provisioning Profiles/profile.mobileprovision}"
IDENTITY="${4:-Apple Distribution: ku wushi (WB5752S5M6)}"

if [ ! -d "$ARCHIVE" ]; then
  echo "archive not found: $ARCHIVE" >&2
  exit 1
fi

APP_SRC="$ARCHIVE/Products/Application/buckshot.app"
if [ ! -d "$APP_SRC" ]; then
  # Godot lowercases the bundle; fallback to first .app
  APP_SRC="$(ls -d "$ARCHIVE"/Products/Application/*.app | head -1)"
fi
echo "Source app: $APP_SRC"

WORK="$RUNNER_TEMP/ipa_work"
rm -rf "$WORK"
mkdir -p "$WORK/Payload"
cp -R "$APP_SRC" "$WORK/Payload/buckshot.app"

# Embed provisioning profile (distribution-style). iOS looks for this in
# the bundle root.
if [ -f "$PROFILE_SRC" ]; then
  cp "$PROFILE_SRC" "$WORK/Payload/buckshot.app/embedded.mobileprovision"
  echo "Embedded: $PROFILE_SRC"
else
  echo "WARN: no provisioning profile at $PROFILE_SRC -- install with"
  echo "  ios_port/tools/Sideloadly or copy manually into the app root."
fi

# Re-sign with the matching identity (already signed during archive, but
# the re-sign is needed because we touched the bundle).
echo "Re-signing with: $IDENTITY"
codesign --force --sign "$IDENTITY" \
  --entitlements "$ARCHIVE/Info.plist" 2>/dev/null \
  --generate-entitlement-der \
  "$WORK/Payload/buckshot.app" || \
codesign --force --sign "$IDENTITY" \
  "$WORK/Payload/buckshot.app"

codesign --verify --deep --strict "$WORK/Payload/buckshot.app" && \
  echo "Signature OK"

mkdir -p "$OUT_DIR"
cd "$WORK"
zip -qr "$OUT_DIR/buckshot.ipa" Payload
echo "Created: $OUT_DIR/buckshot.ipa"
ls -la "$OUT_DIR"