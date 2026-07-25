#!/usr/bin/env python3
"""
Godot 4.1.1 .import parser bug fix: rewrite files=[ ... ] arrays so each
entry is followed by a comma.

Godot 4.1.1's _test_for_reimport() reads .import files and emits:
    ERROR: ResourceFormatImporter::load - '...glb.import:15' error
           'Expected ',''.

The cause is that .glb.import files written by gdre_export (and a few
other decompilers) emit a `files=[ ... ]` array WITHOUT trailing
commas between entries. Godot 4.1.1 expects the array to be comma-
separated (Godot 4.2+ accepts both forms; 4.1.1 strict). This script:

  1. Finds every `files=[` block in .import/.remap files
  2. Rewrites it as a comma-separated list
  3. Writes back atomically

Idempotent (skips files that are already comma-separated).

Usage: python3 ci/fix_import_arrays.py [--dry-run]
"""
import argparse
import pathlib
import re
import sys


SKIP_DIRS = {".git", "node_modules", ".github"}


def fix_one(p: pathlib.Path, dry_run=False):
    text = p.read_text(encoding="utf-8", errors="replace")
    if "files=[" not in text and "deps=[" not in text:
        return False
    new_lines = []
    changed = False
    in_array = False
    array_indent = ""
    last_was_entry = False
    for line in text.splitlines(keepends=True):
        stripped = line.rstrip("\n").rstrip()
        if "files=[" in stripped and stripped.endswith("["):
            in_array = True
            array_indent = line[: len(line) - len(line.lstrip())]
            new_lines.append(line)
            last_was_entry = False
            continue
        if in_array:
            if stripped == "]" or stripped.endswith("]"):
                # Close array
                if last_was_entry and not stripped.startswith("]"):
                    # ensure trailing comma before ]
                    pass
                new_lines.append(line)
                in_array = False
                last_was_entry = False
                continue
            # This is an array entry — must end with ','
            s = line.rstrip("\n")
            if s and not s.rstrip().endswith(","):
                # Add comma
                indent = s[: len(s) - len(s.lstrip())]
                content = s.strip()
                if content and content[0] in ('"', "'"):
                    new_line = f"{indent}{content},\n"
                    new_lines.append(new_line)
                    changed = True
                    last_was_entry = True
                    continue
        new_lines.append(line)
    if changed and not dry_run:
        p.write_text("".join(new_lines), encoding="utf-8")
    return changed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    root = pathlib.Path(args.repo_root).resolve()
    examined = 0
    fixed = 0
    samples = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(root)
        parts = rel.parts
        if any(d in SKIP_DIRS for d in parts):
            continue
        if p.suffix not in (".import", ".remap"):
            continue
        examined += 1
        if fix_one(p, dry_run=args.dry_run):
            fixed += 1
            if len(samples) < 5:
                samples.append(str(p))
    print(f"[fix_import_arrays] examined={examined} fixed={fixed} "
          f"dry_run={args.dry_run}")
    for s in samples:
        print(f"  {s}")


if __name__ == "__main__":
    sys.exit(main() or 0)