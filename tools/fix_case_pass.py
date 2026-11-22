#!/usr/bin/env python3
"""Case-fix pass for WP7 -> Android content packaging.

WP7/Windows content lookup is case-insensitive; Android's AssetManager is
case-sensitive. The game's data was authored case-insensitively, so asset
requests arrive in spellings that match neither the file's case nor
all-lowercase. This tool scans your extracted Content tree (and, optionally,
your local decompiled sources) for every requested spelling and plans
duplicate-case copies. Because NTFS is case-insensitive, the duplicates
cannot coexist in the build tree, so the plan is written as a pairs file
for inject_dupes.py, which injects them directly into the built APK
(zip entries ARE case-sensitive).

Usage:
    fix_case_pass.py <content-dir> [decompiled-dir] [work-dir]

    <content-dir>     your extracted Assets/Content directory
    [decompiled-dir]  optional local decompiled source tree (string literals)
    [work-dir]        where case_pairs.txt + case_pass_report.txt go
                      (default: current directory)

No paths from the original development machine are baked in.
"""
import os, re, sys

CONTENT = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.abspath("Content")
DECOMPILED = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else None
WORK = os.path.abspath(sys.argv[3]) if len(sys.argv) > 3 else os.path.abspath(".")
OUT = os.path.join(WORK, "case_pass_report.txt")
PAIRS = os.path.join(WORK, "case_pairs.txt")


def relposix(p):
    return os.path.relpath(p, CONTENT).replace(os.sep, '/')


packaged = []
for dp, dn, fn in os.walk(CONTENT):
    for f in fn:
        packaged.append(relposix(os.path.join(dp, f)))
lower_map = {}
for p in packaged:
    lower_map.setdefault(p.lower(), p)
basenames = set()
for p in packaged:
    b = p.split('/')[-1]
    if '.' in b:
        basenames.add(b.rsplit('.', 1)[0].lower())
    else:
        basenames.add(b.lower())

RUN = re.compile(rb'[\x20-\x7e]{4,140}')
LIT = re.compile(rb'"([^"\r\n]{2,140})"')


def pathlike(s):
    if '\\' in s or '/' in s:
        return True
    base = s.replace('\\', '/').split('/')[-1]
    if '.' in base:
        base = base.rsplit('.', 1)[0]
    return base.lower() in basenames


candidates = set()
# 1) strings inside every packaged XNB (string tables, design specs, level data)
for p in packaged:
    if not p.lower().endswith('.xnb'):
        continue
    data = open(os.path.join(CONTENT, p.replace('/', os.sep)), 'rb').read()
    for m in RUN.finditer(data):
        s = m.group().decode('ascii', 'replace')
        for part in s.split('"'):
            part = part.strip()
            if pathlike(part):
                candidates.add(part)
# 2) string literals in decompiled sources (your local copy only)
if DECOMPILED and os.path.isdir(DECOMPILED):
    for dp, dn, fn in os.walk(DECOMPILED):
        for f in fn:
            if not f.endswith('.cs'):
                continue
            data = open(os.path.join(dp, f), 'rb').read()
            for m in LIT.finditer(data):
                s = m.group(1).decode('utf-8', 'replace')
                if pathlike(s):
                    candidates.add(s)

copies = []   # (src_rel, dst_rel)


def stage(src_rel, dst_rel):
    if src_rel == dst_rel:
        return
    if dst_rel in packaged or dst_rel.lower() in [c[1].lower() for c in copies]:
        return
    copies.append((src_rel, dst_rel))


# A1: blanket lowercase duplicates for every packaged path containing uppercase
exact = set(packaged)
for p in packaged:
    lp = p.lower()
    if lp != p and lp not in exact:
        stage(p, lp)

# A2: exact requested spellings from the candidate universe
unresolved = []
for cand in sorted(candidates):
    r = cand.replace('\\', '/').strip()
    while r.startswith('./'):
        r = r[2:]
    if not r or r.startswith('/') or '://' in r or r.endswith('.cs'):
        continue
    rf = r if r.lower().endswith('.xnb') else r + '.xnb'
    matched = False
    for root in ('data/', ''):
        full = root + rf
        hit = lower_map.get(full.lower())
        if hit:
            matched = True
            if hit != full:
                stage(hit, full)
    if not matched and ('\\' in cand or '/' in cand):
        unresolved.append(cand)

made = 0
total_bytes = 0
with open(PAIRS, 'w', encoding='utf-8') as pf:
    for src_rel, dst_rel in copies:
        pf.write(dst_rel + '\t' + src_rel + '\n')
        made += 1
        total_bytes += os.path.getsize(os.path.join(CONTENT, src_rel.replace('/', os.sep)))

with open(OUT, 'w', encoding='utf-8') as fh:
    fh.write(f'packaged_before={len(packaged)} candidates={len(candidates)} copies_planned={len(copies)} copies_made={made} bytes={total_bytes}\n')
    fh.write('--- unresolved candidates (separator-bearing, no case-insensitive match):\n')
    for u in unresolved:
        fh.write(u + '\n')
print(f'packaged={len(packaged)} candidates={len(candidates)} copies={made} bytes={total_bytes} unresolved={len(unresolved)}')
