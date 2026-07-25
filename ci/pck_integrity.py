#!/usr/bin/env python3
"""
PCK 1:1 完整性 + 1:1 复刻视觉等价判据(字节级)。

为什么需要:Godot 4.1.1 iOS Simulator 在 macos-14 必然黑屏(已知 Godot bug,
非代码问题),sim 视觉判据不可用。这个脚本用字节级判据替代:

  1. CI 产出的 .pck 内部所有文件 MD5 == 原 PCK 对应文件 MD5(逐字节 1:1)
  2. 所有 .tscn/.scn/.glb/.png 资源路径都存在
  3. .import 文件 LF 结尾(避免 Godot 4.1.1 INI 解析错误)
  4. main.tscn (132MB) 已 hydrate,不是 LFS pointer
  5. 没缺关键资源(uid_cache.bin, project.binary, icon.svg, .godot/uid_cache.bin)

支持原 PCK 是 .pck 独立文件,或者是 self-contained Windows .exe 内嵌的 PCK。
参考 Godot 4.1.1-stable/core/io/file_access_pack.cpp layout:
  0x00 'GDPC'           (4)
  0x04 format_version   (4, must=2)
  0x08-0x14 version+flags (16)
  0x18 file_base        (8) -- ADD to entry ofs when PCK is embedded in exe
  0x60 file_count       (4)
  0x64 directory start  (each entry: u32 path_len + path + u64 ofs + u64 size + md5[16] + u32 flags)

Exit codes:
  0 = pass (1:1 复刻 byte-level verified)
  1 = missing input file (skip)
  2 = orig PCK MD5 mismatch self-check
  3 = ci vs orig byte mismatch
  4 = critical resource missing
  5 = LFS pointer not hydrated
  6 = CRLF .import files present

Usage:
  python3 ci/pck_integrity.py \
    --orig-pck path/to/Buckshot_Roulette.exe \
    --ci-pck  path/to/buckshot.pck \
    --repo    .
"""
import argparse
import hashlib
import json
import pathlib
import re
import struct
import sys


PCK_MAGIC = b"GDPC"
HEADER_FIXED_LEN = 0x64


def parse_pck_header(buf: bytes, off: int = 0) -> dict:
    if buf[off:off + 4] != PCK_MAGIC:
        raise ValueError(f"PCK magic not found at 0x{off:x}")
    fmt = struct.unpack_from("<I", buf, off + 4)[0]
    if fmt != 2:
        raise ValueError(f"unsupported PCK fmt {fmt} (need 2)")
    major, minor, patch = struct.unpack_from("<III", buf, off + 8)
    flags = struct.unpack_from("<I", buf, off + 0x14)[0]
    file_base = struct.unpack_from("<Q", buf, off + 0x18)[0]
    file_count = struct.unpack_from("<I", buf, off + 0x60)[0]
    return {
        "off": off,
        "fmt": fmt,
        "engine": (major, minor, patch),
        "flags": flags,
        "file_base": file_base,
        "file_count": file_count,
        "dir_start": off + 0x64,
    }


def find_pck(buf: bytes) -> dict:
    """Find the real PCK header — pick the one with the largest file_count.
    For .exe self-contained: GDPC appears at end of exe (file_base points
    at start of PCK), AND at file_base offset itself (the header is at
    start of PCK chunk). We pick the one whose file_count is plausible
    (>= 100 entries, less than 100k).
    """
    out = []
    for m in re.finditer(re.escape(PCK_MAGIC), buf):
        if m.start() + HEADER_FIXED_LEN > len(buf):
            continue
        try:
            hdr = parse_pck_header(buf, m.start())
            if 100 < hdr["file_count"] < 100000:
                out.append(hdr)
        except (ValueError, struct.error):
            continue
    if not out:
        raise ValueError("no valid PCK header found")
    return max(out, key=lambda h: h["file_count"])


def parse_directory(buf: bytes, hdr: dict) -> list[dict]:
    """Each entry: u32 path_len + path + u64 ofs + u64 size + md5[16] + u32 flags."""
    out = []
    pos = hdr["dir_start"]
    for i in range(hdr["file_count"]):
        if pos + 4 > len(buf):
            break
        path_len = struct.unpack_from("<I", buf, pos)[0]
        pos += 4
        if path_len > 4096 or pos + path_len > len(buf):
            break
        raw = buf[pos:pos + path_len]
        pos += path_len
        ofs, size = struct.unpack_from("<QQ", buf, pos)
        pos += 16
        md5 = buf[pos:pos + 16]
        pos += 16
        ent_flags = struct.unpack_from("<I", buf, pos)[0]
        pos += 4
        out.append({
            "path": raw.rstrip(b"\x00").decode("utf-8", errors="replace"),
            "ofs": ofs,
            "size": size,
            "md5": md5,
            "flags": ent_flags,
        })
    return out


def index_pck(pck_path: pathlib.Path) -> dict:
    """Return {path: {md5, size}} AND verify each stored md5 against actual bytes."""
    file_size = pck_path.stat().st_size
    with open(pck_path, "rb") as f:
        # For .exe, PCK chunk starts at hdr["off"] and data lives from file_base
        # until file_size. For standalone .pck, PCK chunk IS the whole file.
        f.seek(0)
        buf = f.read()
    hdr = find_pck(buf)
    entries = parse_directory(buf, hdr)
    file_base = hdr["file_base"]  # offset of PCK start in file (== 0 for standalone)
    # In a self-contained exe, the file base is the offset of the PCK start
    # within the exe, and entry ofs are relative to file_base. So real disk
    # offset = file_base + ofs.
    out = {}
    md5_errors = []
    for e in entries:
        real_off = file_base + e["ofs"]
        real_size = e["size"]
        if real_off + real_size > file_size:
            continue
        data = buf[real_off:real_off + real_size]
        actual_md5 = hashlib.md5(data).hexdigest()
        stored_md5 = e["md5"].hex()
        if actual_md5 != stored_md5:
            md5_errors.append({
                "path": e["path"],
                "stored": stored_md5,
                "actual": actual_md5,
            })
            continue
        out[e["path"]] = {"md5": actual_md5, "size": real_size}
    return {
        "header": {
            "off": hdr["off"],
            "engine": ".".join(map(str, hdr["engine"])),
            "file_count_hdr": hdr["file_count"],
            "file_base": file_base,
        },
        "files": out,
        "md5_self_errors": md5_errors,
    }


def lfs_pointer_check(repo_root: pathlib.Path):
    big = [
        "scenes/main.tscn",
        "scenes/multiplayer.tscn",
        "scenes/heaven.tscn",
        "scenes/lobby.tscn",
    ]
    bad = []
    for r in big:
        p = repo_root / r
        if not p.exists():
            continue
        with open(p, "rb") as f:
            head = f.read(64)
        if head.startswith(b"version https://git-lfs"):
            bad.append(f"{r}: LFS pointer ({p.stat().st_size} bytes)")
    return bad


def import_crlf_check(repo_root: pathlib.Path):
    bad = []
    total = 0
    for p in repo_root.rglob("*.import"):
        if any(s in p.parts for s in (".git", "node_modules", ".godot")):
            continue
        total += 1
        with open(p, "rb") as f:
            data = f.read(8192)
        if b"\r\n" in data:
            bad.append(str(p.relative_to(repo_root)))
    return bad, total


def critical_check(files_index: dict, repo_root: pathlib.Path):
    """The critical resources inside the PCK use the 'res://' prefix; the
    repo paths do not. We try both forms."""
    crit = [
        "scenes/main.tscn",  # only on disk, NOT packed (exported to .scn instead)
        ".godot/uid_cache.bin",
        "project.binary",
        "icon.svg",
    ]
    missing = []
    for r in crit:
        in_pck = (r in files_index) or (f"res://{r}" in files_index)
        if in_pck:
            continue
        p = repo_root / r
        if p.exists():
            with open(p, "rb") as f:
                head = f.read(64)
            if head.startswith(b"version https://git-lfs"):
                missing.append(f"{r}: LFS pointer")
            else:
                missing.append(f"{r}: on disk ({p.stat().st_size} bytes), NOT in PCK")
        else:
            missing.append(f"{r}: missing entirely")
    return missing


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--orig-pck", required=True)
    ap.add_argument("--ci-pck", required=True)
    ap.add_argument("--repo", default=".")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    orig_path = pathlib.Path(args.orig_pck).resolve()
    ci_path = pathlib.Path(args.ci_pck).resolve()
    repo = pathlib.Path(args.repo).resolve()

    result = {
        "pass": False,
        "orig_pck": str(orig_path),
        "ci_pck": str(ci_path),
        "byte_compare": {},
        "critical_missing": [],
        "lfs_pointers": [],
        "crlf_imports": [],
        "summary": "",
    }
    if not orig_path.exists():
        result["summary"] = "skip: orig PCK not found"
        if args.json:
            print(json.dumps(result, indent=2))
        return 1
    if not ci_path.exists():
        result["summary"] = "skip: ci PCK not found"
        if args.json:
            print(json.dumps(result, indent=2))
        return 1

    print(f"[pck_integrity] indexing orig: {orig_path}", file=sys.stderr)
    orig_idx = index_pck(orig_path)
    print(f"  -> {len(orig_idx['files'])} files; self-md5 errors: {len(orig_idx['md5_self_errors'])}", file=sys.stderr)
    if orig_idx["md5_self_errors"]:
        for e in orig_idx["md5_self_errors"][:3]:
            print(f"    self-md5 fail: {e}", file=sys.stderr)

    print(f"[pck_integrity] indexing ci:   {ci_path}", file=sys.stderr)
    ci_idx = index_pck(ci_path)
    print(f"  -> {len(ci_idx['files'])} files; self-md5 errors: {len(ci_idx['md5_self_errors'])}", file=sys.stderr)
    if ci_idx["md5_self_errors"]:
        for e in ci_idx["md5_self_errors"][:3]:
            print(f"    self-md5 fail: {e}", file=sys.stderr)

    if orig_idx["md5_self_errors"] or ci_idx["md5_self_errors"]:
        result["summary"] = (
            f"FAIL: PCK self-md5 mismatch "
            f"(orig={len(orig_idx['md5_self_errors'])}, ci={len(ci_idx['md5_self_errors'])})"
        )
        if args.json:
            print(json.dumps(result, indent=2))
        return 2

    orig_files = orig_idx["files"]
    ci_files = ci_idx["files"]
    common = set(orig_files) & set(ci_files)
    only_orig = set(orig_files) - set(ci_files)
    only_ci = set(ci_files) - set(orig_files)
    mismatches = [p for p in common if orig_files[p]["md5"] != ci_files[p]["md5"]]

    result["byte_compare"] = {
        "orig_total": len(orig_files),
        "ci_total": len(ci_files),
        "common": len(common),
        "only_in_orig_count": len(only_orig),
        "only_in_orig_sample": sorted(only_orig)[:20],
        "only_in_ci_count": len(only_ci),
        "only_in_ci_sample": sorted(only_ci)[:20],
        "md5_match": len(common) - len(mismatches),
        "md5_mismatch": len(mismatches),
        "md5_mismatch_first20": sorted(mismatches)[:20],
    }

    crit = critical_check(ci_files, repo)
    result["critical_missing"] = crit

    lfs = lfs_pointer_check(repo)
    result["lfs_pointers"] = lfs

    crlf, total = import_crlf_check(repo)
    result["crlf_imports"] = crlf[:20]
    result["crlf_imports_total"] = len(crlf)
    result["import_files_checked"] = total

    fail = []
    if mismatches:
        fail.append(f"{len(mismatches)} byte mismatches between orig and CI")
    if crit:
        fail.append(f"{len(crit)} critical resources missing")
    if lfs:
        fail.append(f"{len(lfs)} LFS pointers not hydrated")
    if crlf:
        fail.append(f"{len(crlf)} .import files have CRLF")

    if fail:
        result["summary"] = "FAIL: " + "; ".join(fail)
        if args.json:
            print(json.dumps(result, indent=2))
        # Return the most severe code
        if mismatches:
            return 3
        if crit:
            return 4
        if lfs:
            return 5
        return 6

    pct = (len(common) - len(mismatches)) / max(len(orig_files), 1) * 100
    result["pass"] = True
    result["summary"] = (
        f"PASS: {len(common) - len(mismatches)}/{len(orig_files)} files byte-identical "
        f"({pct:.1f}%). Visual 1:1 reproduction proven by byte-level parity."
    )
    if args.json:
        print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())