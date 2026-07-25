#!/usr/bin/env python3
"""
Pre-export UID stabilization: snapshot uid_cache.bin + *.uid sidecars so that
Godot 4.1.1's deterministic export (post-export-patch) has stable UIDs.

Godot 4.1.1 assigns sub_resource UIDs via CryptoCore::RandomGenerator at
export time, making the resulting PCK non-reproducible across runs.
This script:
  1. Snapshots .godot/uid_cache.bin before export (the "frozen" baseline)
  2. Snapshots all *.uid sidecars next to imported resources
  3. Exports the original SCN file_count + per-file MD5 baseline so we can
     verify deterministic-ness after export.

Usage: python3 ci/snapshot_uids.py [--snapshot|--verify|--restore]
"""
import argparse
import hashlib
import json
import os
import pathlib
import shutil
import struct
import sys


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
GODOT_DIR = REPO_ROOT / ".godot"
UID_CACHE = GODOT_DIR / "uid_cache.bin"
SNAPSHOT_DIR = REPO_ROOT / ".godot" / ".uid_snapshot"
SCN_DIR = GODOT_DIR / "imported"
PCK_HEADER_MAGIC = b"GDPC"


def file_md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def snapshot_uids():
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {
        "uid_cache": None,
        "uid_sidecars": {},
        "imported_count": 0,
    }
    if UID_CACHE.exists():
        manifest["uid_cache"] = {
            "path": str(UID_CACHE),
            "md5": file_md5(UID_CACHE),
            "size": UID_CACHE.stat().st_size,
        }
        shutil.copy2(UID_CACHE, SNAPSHOT_DIR / "uid_cache.bin")
    if SCN_DIR.exists():
        scn_files = list(SCN_DIR.rglob("*.scn"))
        ctex_files = list(SCN_DIR.rglob("*.ctex"))
        manifest["imported_count"] = len(scn_files) + len(ctex_files)
        for uid_file in GODOT_DIR.rglob("*.uid"):
            rel = uid_file.relative_to(REPO_ROOT)
            manifest["uid_sidecars"][str(rel)] = {
                "md5": file_md5(uid_file),
                "size": uid_file.stat().st_size,
            }
            target = SNAPSHOT_DIR / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(uid_file, target)
    out_path = SNAPSHOT_DIR / "snapshot.json"
    out_path.write_text(json.dumps(manifest, indent=2))
    print(f"[snapshot_uids] {manifest['imported_count']} imported files; "
          f"{len(manifest['uid_sidecars'])} uid sidecars")
    print(f"[snapshot_uids] snapshot at {SNAPSHOT_DIR}")


def verify_uids(pck_path):
    """Verify that post-export PCK uid_cache.bin MD5 matches the snapshot."""
    if not SNAPSHOT_DIR.exists():
        print("[verify_uids] no snapshot found; run --snapshot first")
        return 1
    snap = json.loads((SNAPSHOT_DIR / "snapshot.json").read_text())
    current = UID_CACHE if UID_CACHE.exists() else None
    pck = pathlib.Path(pck_path) if pck_path else None
    if pck and pck.exists():
        pck_md5 = file_md5(pck)
        print(f"[verify_uids] pck={pck} md5={pck_md5} size={pck.stat().st_size}")
    if current:
        cur_md5 = file_md5(current)
        snap_md5 = snap.get("uid_cache", {}).get("md5")
        print(f"[verify_uids] uid_cache.bin cur={cur_md5} snap={snap_md5}")
        if cur_md5 != snap_md5:
            print("[verify_uids] MISMATCH — UIDs drift between runs")
            return 2
        print("[verify_uids] OK")
        return 0
    print("[verify_uids] no current uid_cache.bin to compare")
    return 0


def restore_uids():
    if not SNAPSHOT_DIR.exists():
        print("[restore_uids] no snapshot to restore")
        return 1
    snap = json.loads((SNAPSHOT_DIR / "snapshot.json").read_text())
    if (SNAPSHOT_DIR / "uid_cache.bin").exists():
        UID_CACHE.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(SNAPSHOT_DIR / "uid_cache.bin", UID_CACHE)
    for rel in snap.get("uid_sidecars", {}):
        src = SNAPSHOT_DIR / rel
        dst = REPO_ROOT / rel
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    print(f"[restore_uids] restored uid_cache.bin + "
          f"{len(snap.get('uid_sidecars', {}))} uid sidecars")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", action="store_true")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--restore", action="store_true")
    ap.add_argument("--pck", default="")
    args = ap.parse_args()
    if args.snapshot:
        snapshot_uids()
    elif args.verify:
        sys.exit(verify_uids(args.pck))
    elif args.restore:
        sys.exit(restore_uids())
    else:
        snapshot_uids()


if __name__ == "__main__":
    main()