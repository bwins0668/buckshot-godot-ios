#!/usr/bin/env python3
"""
CRLF → LF conversion for Godot .import files.

Godot 4.1.1 stable's INI parser (`ResourceFormatImporter::load` →
`_test_for_reimport`) does NOT handle CRLF line endings — it expects LF.
When .import files saved on Windows are committed to the repo with CRLF,
Godot emits:
    ERROR: ResourceFormatImporter::load - '...foo.glb.import:15'
           error 'Expected ','.'

This script rewrites CRLF → LF in every .import / .glb.import / .ctex.import
/ .ogg.import file under the project tree, in place.

Usage: python3 ci/fix_import_crlf.py [--repo-root <path>] [--dry-run]
"""
import argparse
import pathlib
import sys


EXTS = (".import", ".remap")
SKIP_DIRS = {".git", ".godot", "node_modules", ".github"}


def has_crlf(p: pathlib.Path):
    try:
        with open(p, "rb") as f:
            data = f.read()
    except OSError:
        return False
    return b"\r\n" in data


def fix_one(p: pathlib.Path, dry_run=False):
    try:
        with open(p, "rb") as f:
            data = f.read()
    except OSError:
        return False
    if b"\r\n" not in data:
        return False
    fixed = data.replace(b"\r\n", b"\n")
    if not dry_run:
        with open(p, "wb") as f:
            f.write(fixed)
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    root = pathlib.Path(args.repo_root).resolve()
    fixed = 0
    examined = 0
    crlf_files = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        parts = rel.parts
        if any(d in SKIP_DIRS for d in parts):
            continue
        if path.suffix not in EXTS:
            continue
        examined += 1
        if has_crlf(path):
            crlf_files.append(path)
            if fix_one(path, dry_run=args.dry_run):
                fixed += 1
    print(f"[fix_import_crlf] examined={examined} CRLF={len(crlf_files)} "
          f"fixed={fixed} dry_run={args.dry_run}")
    if crlf_files[:5]:
        print("[fix_import_crlf] sample of CRLF files:")
        for p in crlf_files[:5]:
            print(f"  {p}")


if __name__ == "__main__":
    sys.exit(main() or 0)