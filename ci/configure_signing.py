#!/usr/bin/env python3
"""Patch a Godot-generated Xcode project to match our manual signing setup.

Godot 4.1.1's iOS exporter writes a project.pbxproj that is incompatible
with both xcodebuild manual signing AND iphonesimulator Debug builds:

  CODE_SIGN_STYLE         = "Automatic"
  ProvisioningStyle       = Automatic;
  CODE_SIGN_IDENTITY[sdk=iphoneos*] = "iPhone Distribution"
  IPHONEOS_DEPLOYMENT_TARGET = "11.0"

We rewrite all four to Manual + "Apple Distribution" + 12.0 so that:
  * `xcodebuild archive` with explicit manual flags no longer errors with
    "conflicting provisioning settings: Automatic vs iPhone Distribution"
  * `xcodebuild -sdk iphonesimulator -configuration Debug` (smoke test)
    doesn't reject the embedded iPhone Distribution identity either.

Usage: python3 configure_signing.py <path-to-pbxproj>
"""
import re
import sys
import pathlib


PAIRS = [
    # (pattern, replacement)
    (r'CODE_SIGN_STYLE = "Automatic";',
     'CODE_SIGN_STYLE = "Manual";'),
    (r'ProvisioningStyle = Automatic;',
     'ProvisioningStyle = Manual;'),
    (r'CODE_SIGN_IDENTITY\[sdk=iphoneos\*\] = "iPhone Distribution";',
     'CODE_SIGN_IDENTITY[sdk=iphoneos*] = "Apple Distribution";'),
    (r'IPHONEOS_DEPLOYMENT_TARGET = 11\.0;',
     'IPHONEOS_DEPLOYMENT_TARGET = 12.0;'),
]


def patch(text: str) -> tuple[str, int]:
    hits = 0
    for pattern, replacement in PAIRS:
        text, n = re.subn(pattern, replacement, text)
        hits += n
    return text, hits


def main(path: pathlib.Path) -> int:
    src = path.read_text(encoding="utf-8")
    out, hits = patch(src)
    if out == src:
        print(f"No changes made to {path}")
        return 0
    path.write_text(out, encoding="utf-8")
    print(f"Patched {hits} signing/deployment fields in {path}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(pathlib.Path(sys.argv[1])))