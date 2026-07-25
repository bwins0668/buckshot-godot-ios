"""Full byte-level MD5 comparison between the **original PCK** (unpacked
from `G:\\BDDL\\Buckshot.Roulette.Build.16627782`) and the **decompiled
source** (`G:\\BDDL\\Buckshot_decompiled`).

Goal of "一比一复刻贴图": every byte of every .ctex/.scn/.oggvorbisstr
in the original PCK must be byte-identical to the corresponding file in
the source tree, otherwise the iOS export will produce visually different
textures from the original game.

Run:  python ci/full_byte_diff.py
"""
import os, sys, hashlib, pathlib, time

ORIG = pathlib.Path(r'G:\BDDL\Buckshot_original_assets')
SRC  = pathlib.Path(r'G:\BDDL\Buckshot_decompiled')
EXTS = ('.ctex', '.scn', '.oggvorbisstr', '.gdshader', '.gd', '.tres', '.tscn', '.png', '.jpg')
CHUNK = 1 << 16


def md5(p: pathlib.Path) -> str:
    h = hashlib.md5()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(CHUNK), b''):
            h.update(chunk)
    return h.hexdigest()


def index(root: pathlib.Path):
    idx = {}
    for p in root.rglob('*'):
        if p.is_file() and p.suffix.lower() in EXTS:
            idx[str(p.relative_to(root)).lower()] = p
    return idx


def banner(s):
    print(f'\n=== {s} ===')


print('Indexing original (from original PCK) ...')
t = time.time()
orig = index(ORIG)
print(f'  {len(orig):,} files in {time.time()-t:.1f}s')

print('Indexing source (decompiled project) ...')
t = time.time()
src = index(SRC)
print(f'  {len(src):,} files in {time.time()-t:.1f}s')

both = sorted(set(orig) & set(src))
only_orig = sorted(set(orig) - set(src))
only_src  = sorted(set(src)  - set(orig))

print(f'\nFiles in both:     {len(both):,}')
print(f'Files only in orig:{len(only_orig):,}')
print(f'Files only in src: {len(only_src):,}')

# Full-byte MD5 over the intersection
match = mismatch = err = 0
mismatches = []
errs = []
t0 = time.time()
N = len(both)
for i, rel in enumerate(both):
    if i and i % 500 == 0:
        dt = time.time() - t0
        rate = i / dt if dt else 0
        eta = (N - i) / rate if rate else 0
        print(f'  [{i:6,}/{N:,}] match={match:,} mismatch={mismatch:,} ({rate:.0f} files/s, eta {eta:.0f}s)')
    try:
        if md5(orig[rel]) == md5(src[rel]):
            match += 1
        else:
            mismatch += 1
            mismatches.append(rel)
    except Exception as e:
        err += 1
        if len(errs) < 10:
            errs.append((rel, str(e)))

dt = time.time() - t0
print(f'\nFull MD5 done in {dt:.1f}s: {match:,} match, {mismatch:,} mismatch, {err:,} err')

# Bucket mismatches by extension + first folder
def bucket(rel):
    parts = rel.replace('\\','/').split('/')
    if len(parts) >= 2:
        return parts[1] if parts[0] == '.godot' else parts[0]
    return parts[0]

buckets = {}
for rel in mismatches:
    ext = pathlib.PurePath(rel).suffix.lower()
    b = bucket(rel)
    key = f'{ext}\t{bucket(rel)}'
    buckets[key] = buckets.get(key, 0) + 1

print('\nMismatch buckets (ext\tdir):')
for k, n in sorted(buckets.items(), key=lambda kv: -kv[1]):
    print(f'  {n:5,}  {k}')

print('\nFirst 30 mismatches:')
for rel in mismatches[:30]:
    print(f'  {rel}')

if errs:
    print('\nFirst 10 errors:')
    for rel, e in errs:
        print(f'  {rel}: {e}')

# Per-extension tallies for the intersection
# by_ext[ext] = [mismatch, total]
print('\nPer-extension match summary (intersection only):')
by_ext = {}
for rel in both:
    ext = pathlib.PurePath(rel).suffix.lower()
    by_ext.setdefault(ext, [0, 0])  # [mismatch, total]
for rel in both:
    ext = pathlib.PurePath(rel).suffix.lower()
    by_ext[ext][1] += 1
for rel in mismatches:
    ext = pathlib.PurePath(rel).suffix.lower()
    by_ext[ext][0] += 1
for ext in sorted(by_ext):
    mm, t = by_ext[ext]
    m = t - mm
    pct = (m / t * 100) if t else 0
    print(f'  {ext:18s}  {m:6,}/{t:6,}  match  ({mm} mismatch, {pct:.2f}%)')# Verdict
verdict = 'PASS' if mismatch == 0 and err == 0 else 'FAIL'
print(f'\nVERDICT: {verdict}')
sys.exit(0 if verdict == 'PASS' else 1)
