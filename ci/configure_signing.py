#!/usr/bin/env python3
"""Switch a Godot-generated Xcode project to manual code signing style.

The Godot iOS exporter emits a project.pbxproj with:
    CODE_SIGN_STYLE  = "Automatic"
    ProvisioningStyle = Automatic;

xcodebuild complains about conflicting provisioning settings when we then
override identity / profile manually. Patch the pbxproj in-place to use
Manual style.

Usage: python3 configure_signing.py <path-to-pbxproj>
"""
import re
import sys
import pathlib


def main(path: pathlib.Path) -> int:
    src = path.read_text(encoding="utf-8")
    out = src
    out = re.sub(r'CODE_SIGN_STYLE = "Automatic";', 'CODE_SIGN_STYLE = "Manual";', out)
    out = re.sub(r'ProvisioningStyle = Automatic;', 'ProvisioningStyle = Manual;', out)
    if out == src:
        print(f"No Automatic style fields replaced in {path}")
        return 0
    path.write_text(out, encoding="utf-8")
    print(f"Configured manual signing style in {path}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(pathlib.Path(sys.argv[1])))
