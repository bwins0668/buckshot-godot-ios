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
#
# pbxproj writes the CODE_SIGN_IDENTITY key in two forms:
#   CODE_SIGN_IDENTITY = "iPhone Distribution";
#   "CODE_SIGN_IDENTITY[sdk=iphoneos*]" = "iPhone Distribution";
# (the second is quoted because the [] would otherwise break the
#  OpenStep parser). We handle both forms with a single regex that
# uses a backreference group to keep the leading (and trailing) quote
# usage symmetric:
#
#   ( " ? )  CODE_SIGN_IDENTITY  ( \[[^\]]*\] )?  \1  = "iPhone Distribution";
#   group 1 captures either a single " or empty;
#   \1 (back-reference) forces the trailing position to use the same
#   choice, so the second form (quoted key) preserves its quotes and
#   the first form (unquoted key) stays unquoted.
#
# IMPORTANT: previous attempts used `r'"?..."?'` directly, which in a
# raw-string regex is _literally_ a `"` followed by `?` quantifier --
# not "optional quote" -- and produced output like
#   "?CODE_SIGN_IDENTITY"? = "Apple Distribution";
# which broke Xcode's plist parser. The backreference construction
# below avoids the `"?` footgun entirely.
PAIRS = [
    (
        r'''("?)CODE_SIGN_IDENTITY(\[[^\]]*\])?\1 = "iPhone Distribution";''',
        r'''\1CODE_SIGN_IDENTITY\2\1 = "Apple Distribution";''',
    ),
    ('CODE_SIGN_STYLE = "Automatic";',
     'CODE_SIGN_STYLE = "Manual";'),
    ('ProvisioningStyle = Automatic;',
     'ProvisioningStyle = Manual;'),
    ('IPHONEOS_DEPLOYMENT_TARGET = 11.0;',
     'IPHONEOS_DEPLOYMENT_TARGET = 12.0;'),
]  # noqa: E501


def patch(text: str) -> tuple[str, dict[str, int]]:
    counts: dict[str, int] = {}
    for pattern, replacement in PAIRS:
        new_text, n = re.subn(pattern, replacement, text)
        text = new_text
        # Record by leading non-whitespace token of the pattern for visibility.
        label = pattern.lstrip('(').split()[0]
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
