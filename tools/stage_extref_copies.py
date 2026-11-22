#!/usr/bin/env python3
"""Stage external-reference copies in a build Content tree.

Reads a pairs file (tab-separated: destination-relative-path, then
source-relative-path, one pair per line — the format fix_case_pass.py
writes) and copies each source file to its destination inside your
Content tree, creating directories as needed.

Usage:
    stage_extref_copies.py <content-dir> <pairs-file>

No paths from the original development machine are baked in.
"""
import os, shutil, sys

base = os.path.abspath(sys.argv[1])
pairs_file = os.path.abspath(sys.argv[2])
n = 0
total = 0
for line in open(pairs_file, encoding='utf-8'):
    line = line.rstrip('\n')
    if not line:
        continue
    dst, src = line.split('\t')
    s = os.path.join(base, src.replace('/', os.sep))
    d = os.path.join(base, dst.replace('/', os.sep))
    os.makedirs(os.path.dirname(d), exist_ok=True)
    shutil.copyfile(s, d)
    n += 1
    total += os.path.getsize(d)
print(f'staged={n} bytes={total}')
