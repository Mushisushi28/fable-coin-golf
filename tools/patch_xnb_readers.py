#!/usr/bin/env python3
"""Phase 3 XNB reader-table patcher (build copies only).

Rewrites custom-assembly references in XNB type-reader strings from the
original WP7 assembly names (Tech / ModelData) to the scaffold's single
compiled assembly name (FableCoinGolf), stripping the attached
Version/Culture/PublicKeyToken segment for those custom references.
Framework reader strings (Microsoft.Xna.Framework.*) are left untouched —
MonoGame's PrepareType already maps those.

XNBs here are uncompressed (flags=0), so re-serializing the reader table
with different string lengths is safe: everything after the table is
self-delimiting, and the only spanning field is the total file size in
the header, which we recompute.
"""
import os, re, struct, sys

ROOT = sys.argv[1]
NEWASM = "FableCoinGolf"

def r7(buf, pos):
    v = 0; s = 0
    while True:
        b = buf[pos]; pos += 1
        v |= (b & 0x7F) << s; s += 7
        if not (b & 0x80):
            return v, pos

def w7(v):
    out = bytearray()
    while True:
        b = v & 0x7F; v >>= 7
        if v: out.append(b | 0x80)
        else:
            out.append(b); return bytes(out)

def patch_string(s):
    orig = s
    # Custom assembly refs with full version segment -> bare new assembly name
    s = re.sub(r", (?:Tech|ModelData), Version=[^,\]]+(?:, Culture=[^,\]]+)?(?:, PublicKeyToken=[^,\]]+)?",
               f", {NEWASM}", s)
    # Custom assembly refs as bare generic arguments: ", Tech]" / ", ModelData]"
    s = re.sub(r", (?:Tech|ModelData)\]", f", {NEWASM}]", s)
    # Trailing bare assembly ref
    s = re.sub(r", (?:Tech|ModelData)$", f", {NEWASM}", s)
    return s, (s != orig)

changed_files = 0; changed_strings = 0; total = 0; skipped = []
for dp, _, fns in os.walk(ROOT):
    for fn in fns:
        if not fn.lower().endswith(".xnb"):
            continue
        total += 1
        p = os.path.join(dp, fn)
        buf = open(p, "rb").read()
        if buf[:3] != b"XNB" or buf[5] != 0:
            skipped.append(p); continue
        pos = 10
        n, pos = r7(buf, pos)
        readers = []
        for _ in range(n):
            ln, pos = r7(buf, pos)
            s = buf[pos:pos+ln].decode("utf-8"); pos += ln
            ver = buf[pos:pos+4]; pos += 4
            ns, ch = patch_string(s)
            if ch: changed_strings += 1
            readers.append((ns, ver))
        # Phase 3b: guarantee a System.Object reader exists in every asset's
        # table (MonoGame ReflectiveReader throws for object-typed members,
        # e.g. CustomModelPart.Tag). Appending preserves all existing indices.
        if not any("ObjectFallbackReader" in s for s, _ in readers):
            readers.append(("FableCoinGolfCompat.ObjectFallbackReader, FableCoinGolf", b"\x00\x00\x00\x00"))
            changed_strings += 1
        rest = buf[pos:]
        out = bytearray()
        out += buf[:6]              # magic + platform + version + flags
        out += b"\x00\x00\x00\x00"  # size placeholder
        out += w7(len(readers))
        for s, ver in readers:
            b = s.encode("utf-8")
            out += w7(len(b)); out += b; out += ver
        out += rest
        struct.pack_into("<i", out, 6, len(out))
        if bytes(out) != buf:
            open(p, "wb").write(bytes(out))
            changed_files += 1

print(f"total_xnb={total} changed_files={changed_files} changed_reader_strings={changed_strings} skipped={len(skipped)}")
