import struct, sys, pathlib

orig_exe = r'G:\BDDL\Buckshot.Roulette.Build.16627782\Buckshot Roulette_windows\Buckshot Roulette.exe'
dev_pck  = r'C:\Users\lvgua\AppData\Local\Temp\dev_extract\buckshot-godot-ios\buckshot-godot-ios\builds\buckshot.pck'


def parse_pck_header(path, header_off=0):
    with open(path, 'rb') as f:
        data = f.read()
    fmt_version = struct.unpack_from('<I', data, header_off+4)[0]
    file_base = struct.unpack_from('<Q', data, header_off+0x18)[0]
    file_count = struct.unpack_from('<I', data, header_off+0x60)[0]
    dir_start = header_off + 0x64
    return data, file_count, file_base, dir_start


def parse_entries(data, file_count, dir_start):
    entries = []
    pos = dir_start
    for i in range(file_count):
        if pos + 4 > len(data): break
        pl = struct.unpack_from('<I', data, pos)[0]; pos += 4
        if pl > 4096 or pos + pl > len(data): break
        path = data[pos:pos+pl].rstrip(b'\x00').decode('utf-8', errors='replace')
        pos += pl
        ofs, sz = struct.unpack_from('<QQ', data, pos); pos += 16
        md5 = data[pos:pos+16]; pos += 16
        fl = struct.unpack_from('<I', data, pos)[0]; pos += 4
        entries.append({'path': path, 'ofs': ofs, 'size': sz, 'flags': fl})
    return entries


# Original: scan all GDPC, pick the one with pack_format=2 and fc in plausible range.
# The real PCK of a 3572-file game lives at 0x3725e00 in this exe;
# other GDPC markers are accidental 4-byte matches with garbage file_counts.
import re
orig_data = open(orig_exe, 'rb').read()
candidates = []
for m in re.finditer(b'GDPC', orig_data):
    off = m.start()
    if off + 0x70 > len(orig_data): continue
    fc = struct.unpack_from('<I', orig_data, off+0x60)[0]
    fmt = struct.unpack_from('<I', orig_data, off+0x04)[0]
    candidates.append((off, fc, fmt))

best = None
for off, fc, fmt in candidates:
    if fmt == 2 and 1000 <= fc <= 100000:
        if best is None or fc > best[1]:
            best = (off, fc)
assert best, f'no valid PCK found among {len(candidates)} GDPC candidates'
orig_off, orig_count = best
orig_fb = struct.unpack_from('<Q', orig_data, orig_off+0x18)[0]
orig_dir = orig_off + 0x64
print(f'orig: header @ 0x{orig_off:x} file_count={orig_count} file_base=0x{orig_fb:x}')
orig_entries = parse_entries(orig_data, orig_count, orig_dir)
orig_paths = {e['path']: e for e in orig_entries}
print(f'  parsed {len(orig_entries)} entries')

# Dev
dev_data, dev_count, dev_fb, dev_dir = parse_pck_header(dev_pck)
print(f'dev: file_count={dev_count}')
dev_entries = parse_entries(dev_data, dev_count, dev_dir)
dev_paths = {e['path']: e for e in dev_entries}
print(f'  parsed {len(dev_entries)} entries')

# Diff
only_orig = set(orig_paths) - set(dev_paths)
only_dev  = set(dev_paths) - set(orig_paths)
both = set(orig_paths) & set(dev_paths)
print(f'\nFiles only in orig: {len(only_orig)}')
print(f'Files only in dev:  {len(only_dev)}')
print(f'Files in both:      {len(both)}')

# Bucket only_orig by directory
buckets = {}
for p in only_orig:
    parts = p.replace('res://', '').split('/')
    if len(parts) > 1:
        bucket = parts[1] if parts[0] == '.godot' else parts[0]
    else:
        bucket = parts[0]
    buckets[bucket] = buckets.get(bucket, 0) + 1
print('\nOnly_orig by bucket:')
for b, n in sorted(buckets.items(), key=lambda kv: -kv[1]):
    print(f'  {n:5d}  {b}')

# Sample some
print('\nFirst 20 only_orig paths:')
for p in sorted(only_orig)[:20]:
    print(f'  {p}')