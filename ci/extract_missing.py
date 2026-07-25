#!/usr/bin/env python3
"""
Selective PCK extractor — extracts only files listed in a filter file
into the project tree. Used by self_heal.sh to recover only the
778 missing-from-dev files identified by ci/byte_diff_iter.py, not the
full 3572-file unpack (which would clobber the curated source project).

Usage: ci/extract_missing.py <orig_exe_or_pck> <filter_file> <project_root>
   filter_file: one res:// path per line; lines starting with '#' are comments
"""
import os
import pathlib
import re
import struct
import sys


PCK_MAGIC = b'GDPC'


def find_pck(buf):
    best = None
    for m in re.finditer(re.escape(PCK_MAGIC), buf):
        off = m.start()
        if off + 0x70 > len(buf):
            continue
        fc = struct.unpack_from('<I', buf, off + 0x60)[0]
        fmt = struct.unpack_from('<I', buf, off + 0x04)[0]
        if fmt == 2 and 1000 <= fc <= 100000:
            if best is None or fc > best[0]:
                best = (fc, off)
    return best


def parse_entries(buf, pck_off):
    file_count = struct.unpack_from('<I', buf, pck_off + 0x60)[0]
    file_base = struct.unpack_from('<Q', buf, pck_off + 0x18)[0]
    dir_start = pck_off + 0x64
    pos = dir_start
    entries = []
    for _ in range(file_count):
        if pos + 4 > len(buf):
            break
        pl = struct.unpack_from('<I', buf, pos)[0]; pos += 4
        if pl > 4096 or pos + pl > len(buf):
            break
        path = buf[pos:pos + pl].rstrip(b'\x00').decode('utf-8', errors='replace')
        pos += pl
        ofs, sz = struct.unpack_from('<QQ', buf, pos); pos += 16
        md5 = buf[pos:pos + 16]; pos += 16
        fl = struct.unpack_from('<I', buf, pos)[0]; pos += 4
        entries.append({'path': path, 'offset': ofs, 'size': sz,
                        'md5': md5, 'flags': fl})
    return entries, file_base


def main():
    if len(sys.argv) != 4:
        print(__doc__); return 2
    src = pathlib.Path(sys.argv[1])
    flt = pathlib.Path(sys.argv[2])
    root = pathlib.Path(sys.argv[3])
    wanted = set()
    for line in flt.read_text(errors='ignore').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        wanted.add(line)
    print(f'[extract_missing] filter: {len(wanted)} paths')
    data = src.read_bytes()
    found = find_pck(data)
    if found is None:
        print('[extract_missing] no PCK in source'); return 1
    fc, pck_off = found
    entries, file_base = parse_entries(data, pck_off)
    by_path = {e['path']: e for e in entries}
    written = 0
    for w in wanted:
        e = by_path.get(w)
        if not e:
            print(f'  skip (not in PCK): {w}')
            continue
        rel = w.replace('res://', '')
        rel = rel.replace(':', '_').replace('*', '_').replace('?', '_')\
                .replace('"', '_').replace('<', '_').replace('>', '_')\
                .replace('|', '_')
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        abs_off = file_base + e['offset']
        chunk = data[abs_off:abs_off + e['size']]
        target.write_bytes(chunk)
        written += 1
    print(f'[extract_missing] wrote {written} files into {root}')
    return 0


if __name__ == '__main__':
    sys.exit(main())