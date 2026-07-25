#!/usr/bin/env python3
"""Repair PBXFileReference indentation in a Godot 4.1.1-generated project.pbxproj.

Godot 4.1.1 iOS exporter emits PBXFileReference entries for InfoPlist .lproj
files *without* the leading tabs the rest of the section has, which breaks
Xcode's OpenStep plist parser. We re-indent any 24-hex-character UID line
that sits inside the PBXFileReference section and lacks a leading tab.

Usage: python3 repair_pbxproj.py <path-to-pbxproj>
"""
import re
import sys
import pathlib


def repair(path: pathlib.Path) -> int:
    src = path.read_text(encoding="utf-8")
    lines = src.splitlines(keepends=True)
    fixed = []
    in_section = False
    repaired_count = 0

    uid_re = re.compile(r"^[A-Z0-9]{24} /\*")
    for line in lines:
        if "Begin PBXFileReference section" in line:
            in_section = True
        elif "End PBXFileReference section" in line:
            in_section = False

        if in_section and uid_re.match(line) and not line.startswith("\t"):
            fixed.append("\t\t" + line)
            repaired_count += 1
        else:
            fixed.append(line)

    path.write_text("".join(fixed), encoding="utf-8")
    print(f"Repaired {repaired_count} PBXFileReference entries in {path}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(repair(pathlib.Path(sys.argv[1])))
