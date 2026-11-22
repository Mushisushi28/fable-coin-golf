#!/usr/bin/env python3
"""Apply the port's source patches to YOUR OWN decompiled files.

Every fix the port makes to a decompiled game file ships in this
repository as a unified diff (`patches/files/*.patch`) — never as the
patched file itself, because the patched file is still mostly the
game's code. This script applies those diffs to the decompiled tree
you generated locally from your own XAP.

Behaviour:
- Input text is normalised to LF line endings before patching, and
  output is written with LF endings. (The C# compiler is indifferent;
  ILSpy's own output mixes endings between files.)
- Each hunk's old block (context + removed lines) must match the
  input EXACTLY, at exactly one place in the file (searched from the
  hunk's stated position outward). If a hunk does not match — wrong
  game build, different decompiler version/settings — the script
  refuses and names the patch and hunk. Nothing is half-applied:
  a patch is applied to an in-memory copy and only written out when
  every hunk matched.

Usage:
  apply_patches.py --manifest patcher/patch_manifest.json \
      --decompiled work/decompiled --project work/src/FableCoinGolf.Android
  apply_patches.py --patch patches/files/CIwAnimPlayer.cs.patch \
      --input work/decompiled/Tech/CIwAnimPlayer.cs \
      --output work/src/FableCoinGolf.Android/CIwAnimPlayer.cs
"""
import argparse
import json
import os
import re
import sys

HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


def parse_patch(text):
    """Return a list of hunks; each hunk is (old_start, old_lines, new_lines)."""
    hunks = []
    cur = None
    for line in text.splitlines():
        m = HUNK_RE.match(line)
        if m:
            cur = (int(m.group(1)), [], [])
            hunks.append(cur)
            continue
        if cur is None:
            continue  # --- / +++ headers and any preamble
        if line.startswith("\\"):
            continue  # "\ No newline at end of file" — endings are normalised
        tag, body = line[:1], line[1:]
        if tag == " ":
            cur[1].append(body)
            cur[2].append(body)
        elif tag == "-":
            cur[1].append(body)
        elif tag == "+":
            cur[2].append(body)
        elif line == "":
            # A bare empty line in a diff is a context line for an
            # empty source line (some diff writers strip the space).
            cur[1].append("")
            cur[2].append("")
    return hunks


def find_unique(lines, block, hint):
    """Find `block` in `lines`; prefer the match nearest `hint`.
    Return the index, or None if there is no match. Raise on ambiguity
    (two equally near matches)."""
    if not block:
        return hint
    hits = []
    n = len(block)
    for i in range(0, len(lines) - n + 1):
        if lines[i:i + n] == block:
            hits.append(i)
    if not hits:
        return None
    if len(hits) == 1:
        return hits[0]
    hits.sort(key=lambda i: abs(i - hint))
    if abs(hits[0] - hint) == abs(hits[1] - hint) and hits[0] != hits[1]:
        raise ValueError(f"ambiguous hunk position (matches at lines "
                         f"{hits[0] + 1} and {hits[1] + 1})")
    return hits[0]


def apply_patch_text(src_text, patch_text, patch_name):
    lines = src_text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if lines and lines[-1] == "":
        lines.pop()  # trailing newline; re-added on write
    hunks = parse_patch(patch_text)
    if not hunks:
        raise ValueError(f"{patch_name}: no hunks found — corrupt patch file")
    offset = 0
    for idx, (old_start, old_block, new_block) in enumerate(hunks, 1):
        hint = max(0, old_start - 1 + offset)
        try:
            pos = find_unique(lines, old_block, hint)
        except ValueError as exc:
            raise ValueError(f"{patch_name} hunk {idx}: {exc}")
        if pos is None:
            raise ValueError(
                f"{patch_name} hunk {idx}: the expected original code was "
                f"not found. This patch targets the v1.0.8.10 build "
                f"decompiled with ilspycmd 8.2.0.7535 (see docs/BUILDING.md); "
                f"a different build or decompiler output will not match.")
        lines[pos:pos + len(old_block)] = new_block
        offset += len(new_block) - len(old_block)
    return "\n".join(lines) + "\n"


def apply_one(patch_path, input_path, output_path):
    with open(patch_path, encoding="utf-8") as fh:
        patch_text = fh.read()
    with open(input_path, encoding="utf-8-sig") as fh:
        src_text = fh.read()
    out = apply_patch_text(src_text, patch_text, os.path.basename(patch_path))
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(out)
    print(f"patched {os.path.basename(input_path)} -> {output_path}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", help="patch_manifest.json to apply in full")
    ap.add_argument("--patch", help="a single .patch file")
    ap.add_argument("--input", help="input file (single-patch mode)")
    ap.add_argument("--output", help="output file (single-patch mode)")
    ap.add_argument("--decompiled", help="decompiled tree root (manifest mode)")
    ap.add_argument("--project", help="assembled project dir (manifest mode)")
    ap.add_argument("--patch-dir",
                    help="directory holding the .patch files "
                         "(default: patches/files next to the repo root)")
    args = ap.parse_args(argv)
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    patch_dir = args.patch_dir or os.path.join(repo, "patches", "files")
    try:
        if args.manifest:
            with open(args.manifest, encoding="utf-8") as fh:
                entries = json.load(fh)
            for entry in entries:
                src = os.path.join(args.decompiled, entry["input"])
                if entry["mode"] == "replace":
                    dst = os.path.join(args.project, entry["output"])
                elif entry["mode"] == "inplace":
                    dst = src
                else:
                    raise ValueError(f"unknown mode {entry['mode']!r}")
                apply_one(os.path.join(patch_dir, entry["patch"]), src, dst)
        elif args.patch and args.input and args.output:
            apply_one(args.patch, args.input, args.output)
        else:
            ap.print_help()
            return 2
    except (ValueError, OSError) as exc:
        print(f"STOP: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
