"""Diff: which resources differ between the original PCK and the
decompiled source project?

Goal: prove 'one-to-one texture replication' — i.e. every original
asset is present in the decompiled source, byte-identical.
"""
import os, sys, hashlib, pathlib

ORIG = pathlib.Path(r'G:\BDDL\Buckshot_original_assets')
SRC  = pathlib.Path(r'G:\BDDL\Buckshot_decompiled')


def md5(p: pathlib.Path) -> str:
    h = hashlib.md5()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()


def index(root: pathlib.Path):
    """Index all files under root by their relative path."""
    idx = {}
    for p in root.rglob('*'):
        if p.is_file():
            idx[str(p.relative_to(root))] = p
    return idx


print('Indexing original...')
orig = index(ORIG)
print(f'  {len(orig):5d} files')

print('Indexing source...')
src = index(SRC)
print(f'  {len(src):5d} files')

# Files unique to each side
only_orig = set(orig) - set(src)
only_src  = set(src)  - set(orig)
both = set(orig) & set(src)

print(f'\nFiles only in original: {len(only_orig)}')
print(f'Files only in source:   {len(only_src)}')
print(f'Files in both:          {len(both)}')

# Sample a few of each
def sample(s, n=15):
    for p in sorted(s)[:n]:
        print(f'  {p}')

print('\nSamples (only_orig):')
sample(only_orig)
print('\nSamples (only_src):')
sample(only_src)

# Hash-compare the common files
print('\nHash comparison on common files (sampled):')
sample_both = sorted(both)
import random
random.seed(42)
random_sample = random.sample(sample_both, min(50, len(sample_both)))
match, mismatch, err = 0, 0, 0
for rel in random_sample:
    try:
        if md5(orig[rel]) == md5(src[rel]):
            match += 1
        else:
            mismatch += 1
            print(f'  MISMATCH: {rel}')
    except Exception as e:
        err += 1
        print(f'  ERROR: {rel}: {e}')
print(f'\nRandom sample of {len(random_sample)}: {match} match, {mismatch} mismatch, {err} err')

# Now do the full check on category files
def category_count(p):
    n = 0
    for ext in ('.ctex', '.scn', '.oggvorbisstr', '.gd', '.gdshader'):
        n += sum(1 for _ in p.rglob(f'*{ext}'))
    return n

print(f'\nOriginal key-extension file count: {category_count(ORIG)}')
print(f'Source   key-extension file count: {category_count(SRC)}')

# Detailed mismatch count
print('\nFull hash comparison on .ctex files...')
ctex_match = ctex_mis = 0
for rel in [r for r in both if r.endswith('.ctex')]:
    try:
        if md5(orig[rel]) == md5(src[rel]):
            ctex_match += 1
        else:
            ctex_mis += 1
    except Exception:
        pass
print(f'  .ctex: {ctex_match} match, {ctex_mis} mismatch')