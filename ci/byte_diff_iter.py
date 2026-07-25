#!/usr/bin/env python3
"""
Wrapper for ci/full_byte_diff.py that supports CLI args + JSON output.

Used by ci/self_heal.sh to get a machine-readable list of files that
exist in the original PCK but not in the dev project. The full script
is parameter-driven via --orig/--repo/--output.

Usage: python3 ci/byte_diff_iter.py --orig <orig_pck_or_dir> --repo <repo_root> --output <json>
"""
import argparse
import hashlib
import json
import pathlib
import re
import struct
import sys


ORIG_EXE = r'G:\BDDL\Buckshot.Roulette.Build.16627782\Buckshot Roulette_windows\Buckshot Roulette.exe'
PCK_MAGIC = b'GDPC'

CHUNK = 1 << 20


def md5_file(p):
    h = hashlib.md5()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(CHUNK), b''):
            h.update(chunk)
    return h.hexdigest()


def find_pck_in_exe(exe_path):
    data = exe_path.read_bytes()
    best = None
    for m in re.finditer(PCK_MAGIC, data):
        off = m.start()
        if off + 0x70 > len(data):
            continue
        fc = struct.unpack_from('<I', data, off + 0x60)[0]
        fmt = struct.unpack_from('<I', data, off + 0x04)[0]
        if fmt == 2 and 1000 <= fc <= 100000:
            if best is None or fc > best[0]:
                best = (fc, off)
    if best is None:
        raise SystemExit(f"no valid PCK found in {exe_path}")
    return best[1], best[0]


def parse_pck_entries(exe_path, pck_off):
    data = exe_path.read_bytes()
    file_count = struct.unpack_from('<I', data, pck_off + 0x60)[0]
    file_base = struct.unpack_from('<Q', data, pck_off + 0x18)[0]
    dir_start = pck_off + 0x64
    entries = {}
    pos = dir_start
    for _ in range(file_count):
        if pos + 4 > len(data):
            break
        pl = struct.unpack_from('<I', data, pos)[0]; pos += 4
        if pl > 4096 or pos + pl > len(data):
            break
        path = data[pos:pos + pl].rstrip(b'\x00').decode('utf-8', errors='replace')
        pos += pl
        ofs, sz = struct.unpack_from('<QQ', data, pos); pos += 16
        md5 = data[pos:pos + 16]; pos += 16
        fl = struct.unpack_from('<I', data, pos)[0]; pos += 4
        body_start = file_base + ofs
        entries[path] = {
            'path': path,
            'offset': ofs,
            'size': sz,
            'md5_in_pck': md5.hex(),
            'body_start': body_start,
            'flags': fl,
        }
    return entries, file_count


def project_index(repo_root):
    idx = {}
    for p in pathlib.Path(repo_root).rglob('*'):
        if p.is_file():
            try:
                rel = str(p.relative_to(repo_root)).replace('\\', '/')
            except ValueError:
                continue
            idx[rel.lower()] = str(p)
    return idx


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--orig', required=True)
    ap.add_argument('--repo', required=True)
    ap.add_argument('--output', required=True)
    args = ap.parse_args()
    orig_path = pathlib.Path(args.orig)
    repo_root = pathlib.Path(args.repo).resolve()
    if not orig_path.exists():
        raise SystemExit(f"--orig not found: {orig_path}")
    if orig_path.is_file() and orig_path.suffix.lower() == '.exe':
        pck_off, _ = find_pck_in_exe(orig_path)
        entries, fc = parse_pck_entries(orig_path, pck_off)
        orig_paths = {e['path'] for e in entries.values()}
    elif orig_path.is_dir():
        orig_paths = set()
        for p in orig_path.rglob('*'):
            if p.is_file():
                try:
                    rel = str(p.relative_to(orig_path)).replace('\\', '/')
                    orig_paths.add('res://' + rel)
                except ValueError:
                    pass
    else:
        raise SystemExit(f"unsupported --orig type: {orig_path}")
    proj = project_index(repo_root)
    proj_stripped = set()
    for k in proj.keys():
        proj_stripped.add('res://' + k)
    only_orig = sorted(orig_paths - proj_stripped)
    both = orig_paths & proj_stripped
    out = {
        'orig_path': str(orig_path),
        'repo_root': str(repo_root),
        'orig_count': len(orig_paths),
        'proj_count': len(proj),
        'both': len(both),
        'only_orig_count': len(only_orig),
        'only_orig': only_orig[:500],
    }
    pathlib.Path(args.output).write_text(json.dumps(out, indent=2))
    print(f"[byte_diff_iter] orig={len(orig_paths)} proj={len(proj)} "
          f"only_orig={len(only_orig)} -> {args.output}")


if __name__ == '__main__':
    main()