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

# v0.8.3: split sim vs device cmdline override.
#
# Real iOS device: --rendering-driver omitted → Godot 4.3 default is
# `vulkan` which routes through MoltenVK to Apple Metal on iPad M2 +
# iOS 27. The MoltenVK layer's AGXMetalG14G.dlopen was confirmed in
# the v0.8 iPad syslog, so the device path works.
#
# iOS Simulator: --rendering-driver opengl3 → OpenGL ES, which is
# natively supported by the Simulator runtime. Godot 4.3 iOS export
# template has NO "metal" driver option; the only valid options are
# vulkan / opengl3 / dummy. Forcing "metal" causes
#   "Unknown rendering driver 'metal', aborting." (v0.8.2 sim.log).
# Forcing vulkan on sim crashes at
#   drivers/vulkan/rendering_device_driver_vulkan.cpp:1195
#   (v0.8 sim-syslog.txt). opengl3 is the only viable sim fallback.
#
# Env var precedence:
#   PATCH_GODOT_CMDLINE  → legacy, used by both sim and device
#   PATCH_GODOT_CMDLINE_SIM / PATCH_GODOT_CMDLINE_DEVICE  → split
#   Either may be empty/unset to mean "no override" (let Godot auto-pick).
#
# Allowed values per side: "opengl3" | "vulkan" | "metal" | "" (empty)
GODOT_CMDLINE_SIM: list[str] | None = None
GODOT_CMDLINE_DEVICE: list[str] | None = None

_LEGACY = os.environ.get("PATCH_GODOT_CMDLINE", "").strip().lower()
_SIM = os.environ.get("PATCH_GODOT_CMDLINE_SIM", "").strip().lower()
_DEV = os.environ.get("PATCH_GODOT_CMDLINE_DEVICE", "").strip().lower()


def _parse_cmd(val: str, side: str) -> list[str] | None:
    """Translate env-var string to a Godot cmdline list."""
    if val == "":
        return None
    if val == "opengl3":
        return ["--rendering-driver", "opengl3", "--rendering-method", "gl_compatibility"]
    if val == "vulkan":
        return ["--rendering-driver", "vulkan", "--rendering-method", "mobile"]
    if val == "metal":
        return ["--rendering-driver", "metal", "--rendering-method", "mobile"]
    raise SystemExit(f"[patch_info_plist] unknown PATCH_GODOT_CMDLINE_{side}={val!r}")


if _LEGACY and (_SIM or _DEV):
    raise SystemExit(
        "[patch_info_plist] both PATCH_GODOT_CMDLINE and PATCH_GODOT_CMDLINE_{SIM|DEVICE} "
        "are set; use only one scheme"
    )
if _LEGACY:
    # Legacy mode: apply same override to both sim and device.
    GODOT_CMDLINE_SIM = _parse_cmd(_LEGACY, "SIM/DEVICE")
    GODOT_CMDLINE_DEVICE = _parse_cmd(_LEGACY, "SIM/DEVICE")
else:
    GODOT_CMDLINE_SIM = _parse_cmd(_SIM, "SIM")
    GODOT_CMDLINE_DEVICE = _parse_cmd(_DEV, "DEVICE")


def cmdline_for_target(target: str) -> list[str] | None:
    """Return cmdline for the named target ('sim' or 'device')."""
    if target == "sim":
        return GODOT_CMDLINE_SIM
    if target == "device":
        return GODOT_CMDLINE_DEVICE
    raise SystemExit(f"[patch_info_plist] unknown target {target!r}; use 'sim' or 'device'")


# Back-compat: preserve the old module-level `GODOT_CMDLINE` for any
# caller that hasn't migrated yet. Falls back to the sim value if set,
# else the device value, else None. Prefer `cmdline_for_target()`.
GODOT_CMDLINE: list[str] | None = GODOT_CMDLINE_SIM if GODOT_CMDLINE_SIM is not None else GODOT_CMDLINE_DEVICE

# Godot 4.3 iOS exporter emits MinimumOSVersion following
# application/minimum_os_version in export_presets.cfg, which we already
# set to "13.0" — but we re-assert it here defensively, since prior 4.1.1
# versions ignored the preset and shipped 12.0 (Xcode 15.4 SDK floor is
# 12.0, but iOS 26+ begins enforcing a higher floor).
MINIMUM_OS_VERSION: str = "13.0"


def patch_one(plist_path: Path, target: str = "device") -> None:
    """Patch one Info.plist with cmdline override for the named target.

    target ∈ {"sim", "device"}. Defaults to "device" for back-compat with
    callers that haven't been updated yet (e.g. package_ipa.sh).
    """
    if not plist_path.exists():
        raise SystemExit(f"[patch_info_plist] not found: {plist_path}")
    with plist_path.open("rb") as f:
        data = plistlib.load(f)

    cmdline = cmdline_for_target(target)
    before_cmdline = data.get("godot_cmdline")
    if cmdline is not None:
        data["godot_cmdline"] = list(cmdline)
        cmdline_after = data["godot_cmdline"]
    else:
        cmdline_after = before_cmdline  # unchanged

    before_minos = data.get("MinimumOSVersion")
    data["MinimumOSVersion"] = MINIMUM_OS_VERSION

    with plist_path.open("wb") as f:
        plistlib.dump(data, f)

    print(f"[patch_info_plist] {plist_path} (target={target})")
    print(f"  godot_cmdline:  {before_cmdline!r} -> {cmdline_after!r}")
    print(f"  MinimumOSVersion: {before_minos!r} -> {data['MinimumOSVersion']!r}")


def main(args: Iterable[str]) -> int:
    """
    Back-compat CLI: each path arg is treated as a device Info.plist.
    Pass --sim before a path to mark it as a sim plist instead.
    """
    args = list(args)
    target = "device"
    paths: list[str] = []
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--sim":
            target = "sim"
            i += 1
        elif a == "--device":
            target = "device"
            i += 1
        else:
            paths.append(a)
            i += 1
    if not paths:
        raise SystemExit("usage: patch_info_plist.py [--sim|--device] <Info.plist> [<Info.plist> ...]")
    for p in paths:
        patch_one(Path(p), target=target)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
