#!/usr/bin/env python3
"""
Patch the bundled .app/Info.plist after `xcodebuild archive` to:

  (1) inject `godot_cmdline` cmdline args that force Godot 4.1.1's iOS
      renderer into OpenGL ES + gl_compatibility (Candidate A — the
      cheapest possible forcing function for the v0.5/v0.6 black screen)
  (2) bump MinimumOSVersion to 13.0, since Godot 4.1.1's exporter emits
      12.0 regardless of `application/minimum_os_version="13.0"` in
      export_presets.cfg, and the post-export pbxproj patcher rewrites
      IPHONEOS_DEPLOYMENT_TARGET but Xcode's Info.plist generator picks
      the older 12.0 default when the value isn't propagated.

Why this is Candidate A of v0.7:
  - Godot 4.1.1 iOS has NO native Metal backend (libgodot.a has 0 hits
    on MTLDevice). Its main path is MoltenVK/Vulkan, which silently
    fails on iPad M2 + iOS 27 (the v0.5/v0.6 root cause). The fallback
    is OpenGL ES, but in 4.1.1 the OpenGL ES path uses hardcoded FBO 0
    instead of the system FBO, which fails on iOS where system_fbo != 0
    (Godot issue #86830, fix PR #88745 — Godot 4.3+).
  - This patch is the cheapest possible forcing-function. On iOS 27 +
    M2 we expect OpenGL ES to still be removed/unusable, but it forces
    a definitive answer: sim either goes non-magenta (great) or stays
    magenta (expected, see SKILL.md#sim-never-trust).

Idempotent: re-running replaces the keys in place.

Usage:
  python3 ci/patch_info_plist.py <Info.plist> [<Info.plist> ...]

Tested against Godot 4.1.1 export's actual Info.plist schema (verified
on dist/v0.6/artifacts/buckshot-ios/_temp/Buckshot.xcarchive/Products/
Applications/buckshot.app/Info.plist — see HANDOVER §6).
"""
from __future__ import annotations

import plistlib
import sys
from pathlib import Path
from typing import Iterable

# Candidate A — force Godot into the OpenGL ES + gl_compatibility path.
GODOT_CMDLINE: list[str] = [
    "--rendering-driver", "opengl3",
    "--rendering-method", "gl_compatibility",
]

# Xcode 15.4 SDK's IPHONEOS_DEPLOYMENT_TARGET must be >= 12.0, but Godot
# 4.1.1's exporter ignores `application/minimum_os_version` and emits
# 12.0 in pbxproj. Bumping to 13.0 here keeps the install gate clean on
# iOS 26+ where Apple may begin enforcing a higher floor.
MINIMUM_OS_VERSION: str = "13.0"


def patch_one(plist_path: Path) -> None:
    if not plist_path.exists():
        raise SystemExit(f"[patch_info_plist] not found: {plist_path}")
    with plist_path.open("rb") as f:
        data = plistlib.load(f)

    before_cmdline = data.get("godot_cmdline")
    data["godot_cmdline"] = list(GODOT_CMDLINE)

    before_minos = data.get("MinimumOSVersion")
    data["MinimumOSVersion"] = MINIMUM_OS_VERSION

    with plist_path.open("wb") as f:
        plistlib.dump(data, f)

    print(f"[patch_info_plist] {plist_path}")
    print(f"  godot_cmdline:  {before_cmdline!r} -> {data['godot_cmdline']!r}")
    print(f"  MinimumOSVersion: {before_minos!r} -> {data['MinimumOSVersion']!r}")


def main(args: Iterable[str]) -> int:
    paths = list(args)
    if not paths:
        raise SystemExit("usage: patch_info_plist.py <Info.plist> [<Info.plist> ...]")
    for p in paths:
        patch_one(Path(p))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
