#!/usr/bin/env bash
# Manually package a signed .ipa from a pre-built xcarchive.
#
# exportArchive segfaults on the macos-14 runner (IDEDistribution SIGSEGV
# regardless of method=development/app-store/ad-hoc). We bypass it by:
#   1. Locating the .app inside the archive (or DerivedData if xcodebuild
#      wrote it there instead of the archivePath target)
#   2. Embedding the mobileprovision
#   3. Re-signing with our distribution identity
#   4. Zipping into Payload/<app>.app
#
# Output: a sideload-ready .ipa at $2/buckshot.ipa
set -euo pipefail

ARCHIVE="${1:-$RUNNER_TEMP/Buckshot.xcarchive}"
OUT_DIR="${2:-$RUNNER_TEMP/ipa_out}"
PROFILE_SRC="${3:-$HOME/Library/MobileDevice/Provisioning Profiles/profile.mobileprovision}"
IDENTITY="${4:-}"

if [ -z "$IDENTITY" ]; then
  # Pull from the default keychain if not given.
  if [ -n "${KEYCHAIN_PATH:-}" ]; then
    IDENTITY=$(security find-identity -v -p codesigning "$KEYCHAIN_PATH" | head -1 | sed -n 's/.*"\(.*\)".*/\1/p')
  fi
  IDENTITY="${IDENTITY:-Apple Distribution}"
fi

echo "Archive:  $ARCHIVE"
echo "Out dir:  $OUT_DIR"
echo "Profile:  $PROFILE_SRC"
echo "Identity: $IDENTITY"

# xcodebuild on macos-14 sometimes leaves the xcarchive target dir empty
# and parks the .app under DerivedData instead. Hunt for it.
APP_SRC=""
if [ -d "$ARCHIVE/Products/Applications" ]; then
  APP_SRC="$(ls -d "$ARCHIVE"/Products/Applications/*.app 2>/dev/null | head -1 || true)"
fi
if [ -z "$APP_SRC" ] && [ -d "$ARCHIVE/Products/Application" ]; then
  APP_SRC="$(ls -d "$ARCHIVE"/Products/Application/*.app 2>/dev/null | head -1 || true)"
fi
if [ -z "$APP_SRC" ]; then
  APP_SRC="$(find "$ARCHIVE" -maxdepth 4 -type d -name "*.app" 2>/dev/null | head -1 || true)"
fi
if [ -z "$APP_SRC" ]; then
  # Final fallback: DerivedData.
  DD="$(find ~/Library/Developer/Xcode/DerivedData -maxdepth 6 -path "*ArchiveIntermediates/buckshot/InstallationBuildProductsLocation/Applications/buckshot.app" 2>/dev/null | head -1 || true)"
  if [ -n "$DD" ]; then
    echo "Found .app in DerivedData: $DD"
    APP_SRC="$DD"
  fi
fi
if [ -z "$APP_SRC" ] || [ ! -d "$APP_SRC" ]; then
  echo "No .app found in archive or DerivedData" >&2
  exit 1
fi
echo "Source app: $APP_SRC"

WORK="$RUNNER_TEMP/ipa_work"
rm -rf "$WORK"
mkdir -p "$WORK/Payload"
cp -R "$APP_SRC" "$WORK/Payload/buckshot.app"
# Phase v0.8 Candidate C — Godot 4.3-stable iOS export. The 4.3 Mobile
# renderer uses native Metal on Apple Silicon by default, so we do NOT
# inject `godot_cmdline` (patch_info_plist.py only re-asserts the
# MinimumOSVersion bump). See ci/patch_info_plist.py for the rationale
# and the PATCH_GODOT_CMDLINE=opengl3 opt-in for the legacy fallback.
# Must run BEFORE codesign because Info.plist edits invalidate the
# embedded hash.
PATCHED_PLIST="$WORK/Payload/buckshot.app/Info.plist"
if [ -f "$PATCHED_PLIST" ]; then
  python3 "$GITHUB_WORKSPACE/ci/patch_info_plist.py" "$PATCHED_PLIST"
else
  echo "WARN: no Info.plist at $PATCHED_PLIST -- skipping Info.plist patch"
fi

# Embed provisioning profile (required for distribution-style ipa).
if [ -f "$PROFILE_SRC" ]; then
  cp "$PROFILE_SRC" "$WORK/Payload/buckshot.app/embedded.mobileprovision"
  echo "Embedded profile: $PROFILE_SRC"
else
  echo "WARN: no provisioning profile at $PROFILE_SRC -- skipping embed"
fi

# Locate entitlements file (xcarchive stores it as
# IntermediateBuildFilesPath/<target>.build/Release-iphoneos/<target>.build/<target>.app.xcent).
ENTITLEMENTS="$(find ~/Library/Developer/Xcode/DerivedData -path "*Release-iphoneos*/*.app.xcent" 2>/dev/null | head -1 || true)"
echo "Entitlements: ${ENTITLEMENTS:-<none>}"

echo "Re-signing with: $IDENTITY"
if [ -n "$ENTITLEMENTS" ] && [ -f "$ENTITLEMENTS" ]; then
  codesign --force --sign "$IDENTITY" \
    --entitlements "$ENTITLEMENTS" \
    --generate-entitlement-der \
    --timestamp=none \
    "$WORK/Payload/buckshot.app"
else
  codesign --force --sign "$IDENTITY" \
    --generate-entitlement-der \
    --timestamp=none \
    "$WORK/Payload/buckshot.app"
fi
codesign --verify --deep --strict "$WORK/Payload/buckshot.app" && echo "Signature OK"

mkdir -p "$OUT_DIR"
cd "$WORK"
zip -qr "$OUT_DIR/buckshot.ipa" Payload
echo "Created: $OUT_DIR/buckshot.ipa"
ls -la "$OUT_DIR"
