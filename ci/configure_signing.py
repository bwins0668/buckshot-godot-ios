#!/usr/bin/env python3
"""Patch a Godot-generated Xcode project for manual distribution signing.

Godot 4.1.1's iOS exporter writes a project.pbxproj with several defaults
that conflict with our setup (Distribution cert + manual signing + iOS 12
deployment target). xcodebuild refuses to build with:

  error: buckshot has conflicting provisioning settings.
         buckshot is automatically signed for development,
         but a conflicting code signing identity iPhone Distribution
         has been manually specified.

We rewrite four fields (in both Project-level and Target-level sections,
since pbxproj duplicates them):

  CODE_SIGN_STYLE                  "Automatic"    -> "Manual"
  ProvisioningStyle                 Automatic     -> Manual
  CODE_SIGN_IDENTITY (any sdk=)    "iPhone Distribution" -> "Apple Distribution"
  IPHONEOS_DEPLOYMENT_TARGET        11.0          -> 12.0

Usage: python3 configure_signing.py <path-to-pbxproj>
"""
import re
import sys
import pathlib


# Order matters: replace identity first so the style rewrite doesn't see
# the original value being half-matched.
PAIRS = [
    # Strip any [sdk=...] qualifier and rewrite to Manual + Apple Distribution.
    # Targets both
    #   CODE_SIGN_IDENTITY = "iPhone Distribution";
    #   CODE_SIGN_IDENTITY[sdk=iphoneos*] = "iPhone Distribution";
    (r'CODE_SIGN_IDENTITY(\[[^\]]*\])? = "iPhone Distribution";',
     r'CODE_SIGN_IDENTITY\1 = "Apple Distribution";'),
    (r'CODE_SIGN_STYLE = "Automatic";',
     'CODE_SIGN_STYLE = "Manual";'),
    (r'ProvisioningStyle = Automatic;',
     'ProvisioningStyle = Manual;'),
    (r'IPHONEOS_DEPLOYMENT_TARGET = 11\.0;',
     'IPHONEOS_DEPLOYMENT_TARGET = 12.0;'),
]


def patch(text: str) -> tuple[str, dict[str, int]]:
    counts = {}
    for pattern, replacement in PAIRS:
        text, n = re.subn(pattern, replacement, text)
        # Record by leading token of the pattern for visibility.
        label = pattern.split()[0]
        counts[label] = counts.get(label, 0) + n
    return text, counts


def main(path: pathlib.Path) -> int:
    src = path.read_text(encoding="utf-8")
    out, counts = patch(src)
    if out == src:
        print(f"No changes made to {path}")
        return 0
    path.write_text(out, encoding="utf-8")
    for label, n in counts.items():
        if n:
            print(f"  {label}: {n} replacement(s)")
    total = sum(counts.values())
    print(f"Patched {total} signing/deployment fields in {path}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(pathlib.Path(sys.argv[1])))