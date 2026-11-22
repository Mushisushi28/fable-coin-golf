#!/usr/bin/env python3
"""Byte-level Song XNB patcher for the music fix.

Each music track in the XAP exists twice: a loose .wma file and a
compiled Song .xnb whose embedded filename string still points at the
.wma. MonoGame on Android resolves that filename next to the XNB and
hands it to the Android media player, which cannot decode WMA — so the
build converts the .wma files to .ogg (ffmpeg, libvorbis) and rewrites
the filename inside each Song XNB from ".wma" to ".ogg".

The patch is done on raw bytes, never through a text encoding: an
earlier attempt that round-tripped XNBs as text silently corrupted
binary bytes. This tool verifies its own work — after patching, the
file must differ from the original in EXACTLY the bytes of the
extension (".wma" -> ".ogg" is 3 differing bytes: w->o, m->g, a->g at
the same length), and the tool refuses to write anything else.

Usage: patch_song_xnbs.py <music-dir>
       (patches every *.xnb in the directory that references a .wma)
"""
import os
import sys

OLD = b".wma"
NEW = b".ogg"


def patch_file(path):
    data = open(path, "rb").read()
    count = data.count(OLD)
    if count == 0:
        return "skip (no .wma reference)"
    if count != 1:
        return f"REFUSED ({count} .wma references; expected exactly 1)"
    patched = data.replace(OLD, NEW)
    if len(patched) != len(data):
        return "REFUSED (length changed)"
    diff = sum(1 for a, b in zip(data, patched) if a != b)
    if diff != 3:
        return f"REFUSED ({diff} bytes differ; expected exactly 3)"
    with open(path, "wb") as fh:
        fh.write(patched)
    return "patched (3 bytes: .wma -> .ogg)"


def main(argv):
    if len(argv) != 2 or not os.path.isdir(argv[1]):
        print(__doc__)
        return 2
    results = {}
    for name in sorted(os.listdir(argv[1])):
        if name.lower().endswith(".xnb"):
            results[name] = patch_file(os.path.join(argv[1], name))
    for name, result in results.items():
        print(f"{name}: {result}")
    if any(r.startswith("REFUSED") for r in results.values()):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
