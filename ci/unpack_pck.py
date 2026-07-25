#!/usr/bin/env python3
"""Unpack a Godot 4 PCK file (or one embedded at the end of a Godot 4
self-contained Windows executable) into a flat directory tree.

Layout reference: godotengine/godot/4.1.1-stable/core/io/file_access_pack.cpp
  Header:
    0x00 magic 'GDPC'           (4 bytes)
    0x04 format_version         (4 bytes, must be 2 for Godot 4)
    0x08 major                  (4 bytes)
    0x0c minor                  (4 bytes)
    0x10 patch                  (4 bytes)
    0x14 pack_flags             (4 bytes)
    0x18 file_base              (8 bytes -- ADD to each entry's offset
                                      when the PCK is embedded in exe;
                                      0 for a standalone .pck file)
    0x20 reserved[16]            (64 bytes, zero)
    0x60 file_count             (4 bytes)
  Then 64-byte aligned directory at 0x64 (NOT a counted offset).
  Directory entries (each):
    u32 path_len | path bytes (NO nul terminator on disk)
    u64 ofs | u64 size | u8 md5[16] | u32 flags

The PCK can be standalone (the trailer is the same as the header) or
embedded at the END of a Godot Windows executable. We probe the file's
end for the second 'GDPC' marker -- if found, the directory between
the two 'GDPC' markers is the directory payload, and file_base points
at the first 'GDPC'.

Usage:
    python3 unpack_pck.py <pck_or_exe> <out_dir>
"""
from __future__ import annotations
import os, sys, struct, re, hashlib, pathlib


PCK_MAGIC = b'GDPC'
HEADER_FIXED_LEN = 0x64   # bytes up to (and including) file_count
RESERVED_LEN = 64
ALIGNMENT = 64            # directory start padded to 64-byte boundary


def _align(n: int, a: int) -> int:
    return ((n + a - 1) // a) * a


def parse_header(buf: bytes, off: int) -> dict:
    """Parse one PCK header starting at buf[off]. Returns dict."""
    if buf[off:off + 4] != PCK_MAGIC:
        raise ValueError(f"PCK magic not found at offset 0x{off:x}")
    fmt_version = struct.unpack_from('<I', buf, off + 4)[0]
    if fmt_version != 2:
        raise ValueError(f"Unsupported PCK format version {fmt_version} (need 2)")
    major = struct.unpack_from('<I', buf, off + 8)[0]
    minor = struct.unpack_from('<I', buf, off + 0xc)[0]
    patch = struct.unpack_from('<I', buf, off + 0x10)[0]
    pack_flags = struct.unpack_from('<I', buf, off + 0x14)[0]
    file_base = struct.unpack_from('<Q', buf, off + 0x18)[0]
    file_count = struct.unpack_from('<I', buf, off + 0x60)[0]
    # Per godot source: after reading file_count, position is at 0x64.
    # In Godot 4.1.1 self-contained exe mode the directory starts at
    # file_base (= header offset) + 0x64, NOT aligned.
    return {
        'off': off,
        'fmt_version': fmt_version,
        'engine': (major, minor, patch),
        'pack_flags': pack_flags,
        'file_base': file_base,
        'file_count': file_count,
        'dir_start': off + 0x64,
    }


def find_pcks(buf: bytes) -> list[dict]:
    """Find all valid PCK headers in buf."""
    out = []
    for m in re.finditer(re.escape(PCK_MAGIC), buf):
        # Need at least one full header
        if m.start() + HEADER_FIXED_LEN > len(buf):
            continue
        try:
            hdr = parse_header(buf, m.start())
            # Sanity: file_base should be either 0 (standalone) or
            # near the header offset (embedded-in-exe).
            if hdr['file_base'] in (0, hdr['off']) or hdr['file_base'] > hdr['off']:
                out.append(hdr)
        except (ValueError, struct.error):
            continue
    return out


def parse_directory(buf: bytes, hdr: dict) -> list[dict]:
    """Parse the file_count entries starting at hdr['dir_start'].

    Each entry (Godot 4.1.1 PCK v2):
      u32 path_len | path[path_len]  (NOT nul-terminated on disk)
      u64 ofs       (relative to file_base)
      u64 size
      u8 md5[16]
      u32 flags
    No padding. Total fixed prefix = 40 bytes per entry.
    """
    entries = []
    pos = hdr['dir_start']
    for i in range(hdr['file_count']):
        if pos + 4 > len(buf):
            print(f'  WARN: truncated before entry {i}', file=sys.stderr)
            break
        path_len = struct.unpack_from('<I', buf, pos)[0]
        pos += 4
        if path_len > 4096 or pos + path_len > len(buf):
            print(f'  WARN: entry {i} path_len={path_len} OOB', file=sys.stderr)
            break
        raw = buf[pos:pos + path_len]
        pos += path_len
        ofs, size = struct.unpack_from('<QQ', buf, pos)
        pos += 16
        md5 = buf[pos:pos + 16]; pos += 16
        ent_flags = struct.unpack_from('<I', buf, pos)[0]; pos += 4
        entries.append({
            'path': raw.rstrip(b'\x00').decode('utf-8', errors='replace'),
            'ofs': ofs,
            'size': size,
            'md5': md5,
            'flags': ent_flags,
        })
    return entries


def md5_hex(b: bytes) -> str:
    return hashlib.md5(b).hexdigest()


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__)
        return 2
    src, dst = argv[1], argv[2]
    src_size = os.path.getsize(src)
    with open(src, 'rb') as f:
        buf = f.read()
    print(f'Loaded {src}: {src_size} bytes ({src_size/1024/1024:.1f} MiB)')

    pcks = find_pcks(buf)
    if not pcks:
        print('No valid PCK found', file=sys.stderr)
        return 1
    # Take the one with the largest file_count (the real game PCK, not
    # the embedded trailer or duplicate overlays).
    hdr = max(pcks, key=lambda h: h['file_count'])
    print(f'PCK @ 0x{hdr["off"]:x}: engine={".".join(map(str,hdr["engine"]))} '
          f'files={hdr["file_count"]} file_base=0x{hdr["file_base"]:x} '
          f'flags=0x{hdr["pack_flags"]:x}')

    if hdr['pack_flags'] & 1:  # PACK_DIR_ENCRYPTED
        print('ERROR: PCK directory is encrypted; cannot unpack without key.',
              file=sys.stderr)
        return 3

    entries = parse_directory(buf, hdr)
    print(f'Parsed {len(entries)} directory entries')

    out_root = pathlib.Path(dst)
    out_root.mkdir(parents=True, exist_ok=True)

    skipped, written, bad = 0, 0, 0
    for e in entries:
        # Skip embedded .gd (we already have source) and shaders; keep textures/meshes.
        if e['flags'] & 1:  # PACK_FILE_ENCRYPTED
            skipped += 1
            continue

        rel = e['path']
        if rel.startswith('res://'):
            rel = rel[len('res://'):]
        # Windows-safe path
        rel = rel.replace(':', '_').replace('*', '_').replace('?', '_')\
                 .replace('"', '_').replace('<', '_').replace('>', '_')\
                 .replace('|', '_')
        target = out_root / rel
        # Guard against zip-slip-like traversal
        if not str(target.resolve()).startswith(str(out_root.resolve())):
            bad += 1
            continue
        target.parent.mkdir(parents=True, exist_ok=True)

        abs_off = hdr['file_base'] + e['ofs']
        end = abs_off + e['size']
        if end > src_size:
            print(f'  OOB: {e["path"]} off=0x{abs_off:x}+{e["size"]} > file size',
                  file=sys.stderr)
            bad += 1
            continue
        chunk = buf[abs_off:end]
        # Optional: verify md5
        if e['md5'] and len(e['md5']) == 16:
            calc = hashlib.md5(chunk).digest()
            if calc != e['md5']:
                print(f'  md5 mismatch: {e["path"]} (expected {e["md5"].hex()}, '
                      f'got {calc.hex()})', file=sys.stderr)
        target.write_bytes(chunk)
        written += 1

    print(f'\nWrote {written} files, skipped {skipped}, bad {bad}')
    print(f'Output: {out_root}')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))