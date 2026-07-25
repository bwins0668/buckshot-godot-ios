#!/usr/bin/env python3
"""
Patch the bundled .app/Info.plist after `xcodebuild archive` to:

  (1) Optionally inject `godot_cmdline` cmdline args to force a specific
      renderer. DEFAULT in v0.8 Candidate C is no injection — Godot 4.3's
      Mobile renderer uses native Metal on Apple Silicon by default, which
      fixes the v0.5/v0.6/v0.7 black screen on iPad M2 + iOS 27.
      Set env var `PATCH_GODOT_CMDLINE=opengl3` to force the legacy OpenGL
      ES + gl_compatibility fallback (Candidate A retry).
  (2) bump MinimumOSVersion to 13.0, keeping the install gate clean on
      iOS 26+ where Apple may begin enforcing a higher floor.

Why Candidate C supersedes Candidate A (v0.7):
  - Godot 4.1.1 iOS has NO native Metal backend (libgodot.a has 0 hits
    on MTLDevice). Its main path is MoltenVK/Vulkan, which silently
    fails on iPad M2 + iOS 27. The OpenGL ES fallback uses hardcoded
    FBO 0 instead of the system FBO, which fails on iOS where
    system_fbo != 0 (Godot issue #86830, fix PR #88745 — Godot 4.3+).
  - v0.7 verified that forcing OpenGL ES via godot_cmdline patch DOES
    enter the Info.plist correctly, yet the iPad M2 + iOS 27 screen
    remained black. iOS 27 has removed OpenGL ES entirely, so the
    legacy path cannot succeed on this device. Candidate C upgrades
    Godot to 4.3-stable, whose Mobile renderer uses native Metal on
    Apple Silicon — bypassing both MoltenVK and OpenGL ES entirely.

Idempotent: re-running replaces the keys in place.

Usage:
  python3 ci/patch_info_plist.py <Info.plist> [<Info.plist> ...]

Tested against Godot 4.3-stable export's Info.plist schema.
"""
from __future__ import annotations

import os
import plistlib
import sys
from pathlib import Path
from typing import Iterable

# Candidate C (Godot 4.3) — let the engine pick its native Metal path.
# Default: do NOT inject godot_cmdline. To force the legacy OpenGL ES
# fallback (regression test only), set env var PATCH_GODOT_CMDLINE=opengl3.
GODOT_CMDLINE: list[str] | None = None
if os.environ.get("PATCH_GODOT_CMDLINE") == "opengl3":
    GODOT_CMDLINE = [
        "--rendering-driver", "opengl3",
        "--rendering-method", "gl_compatibility",
    ]

# Godot 4.3 iOS exporter emits MinimumOSVersion following
# application/minimum_os_version in export_presets.cfg, which we already
# set to "13.0" — but we re-assert it here defensively, since prior 4.1.1
# versions ignored the preset and shipped 12.0 (Xcode 15.4 SDK floor is
# 12.0, but iOS 26+ begins enforcing a higher floor).
MINIMUM_OS_VERSION: str = "13.0"


def patch_one(plist_path: Path) -> None:
    if not plist_path.exists():
        raise SystemExit(f"[patch_info_plist] not found: {plist_path}")
    with plist_path.open("rb") as f:
        data = plistlib.load(f)

    before_cmdline = data.get("godot_cmdline")
    if GODOT_CMDLINE is not None:
        data["godot_cmdline"] = list(GODOT_CMDLINE)
        cmdline_after = data["godot_cmdline"]
    else:
        cmdline_after = before_cmdline  # unchanged

    before_minos = data.get("MinimumOSVersion")
    data["MinimumOSVersion"] = MINIMUM_OS_VERSION

    with plist_path.open("wb") as f:
        plistlib.dump(data, f)

    print(f"[patch_info_plist] {plist_path}")
    print(f"  godot_cmdline:  {before_cmdline!r} -> {cmdline_after!r}")
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
