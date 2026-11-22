#!/usr/bin/env python3
"""Patch YOUR decompiled localisation .resx for the port.

The .resx is a game resource, so the modified file is never shipped.
This script makes exactly the port's changes to your own copy, and
verifies each one landed (it refuses if the expected original text is
not found exactly once):

1. Two strings for the `sent_gold` achievement are reworded. The
   achievement originally meant sending gold to Fable III over a
   service that no longer exists; the port's local backend earns it
   by banking gold at level end instead (see docs/LEADERBOARDS.md),
   so the text says that.
2. Eleven strings for the username dialog / leaderboard identity UI
   are added after the OPTIONS_MENU_RESET_DATA entry. These strings
   are the port's own text, written for the global-leaderboard
   feature; they exist in no original resource.

Usage: patch_resx.py <your Tech.localisation.fabmob.resx> <output .resx>
"""
import sys

REWORDS = [
    ('<data name="ACHIEVEMENT10_HOWTO" xml:space="preserve">'
     '<value>Send gold from Coin Golf to Fable III 5G</value></data>',
     '<data name="ACHIEVEMENT10_HOWTO" xml:space="preserve">'
     '<value>Bank gold from a Coin Golf level</value></data>'),
    ('<data name="ACHIEVEMENT10_DESCRIPTION" xml:space="preserve">'
     '<value>You sent gold to Fable III!</value></data>',
     '<data name="ACHIEVEMENT10_DESCRIPTION" xml:space="preserve">'
     '<value>You banked gold in Coin Golf!</value></data>'),
]

ANCHOR = ('<data name="OPTIONS_MENU_RESET_DATA" xml:space="preserve">'
          '<value>Reset Data</value></data>')

NEW_ENTRIES = [
    '<data name="OPTIONS_MENU_USERNAME" xml:space="preserve"><value>Set Username</value></data>',
    '<data name="OPTIONS_MENU_USERNAME_SET" xml:space="preserve"><value>Username: {0}</value></data>',
    '<data name="USERNAME_DIALOG_TITLE" xml:space="preserve"><value>Username</value></data>',
    '<data name="USERNAME_DIALOG_MESSAGE" xml:space="preserve"><value>Enter a username for the leaderboards. Other players will see this name.</value></data>',
    '<data name="USERNAME_DIALOG_HINT" xml:space="preserve"><value>Username</value></data>',
    '<data name="USERNAME_DIALOG_SAVE" xml:space="preserve"><value>Save</value></data>',
    '<data name="USERNAME_DIALOG_CANCEL" xml:space="preserve"><value>Cancel</value></data>',
    '<data name="USERNAME_TAKEN" xml:space="preserve"><value>That username is taken. Try another one.</value></data>',
    '<data name="USERNAME_INVALID" xml:space="preserve"><value>Usernames are 3 to 16 letters, numbers or _.</value></data>',
    '<data name="USERNAME_CHECKING" xml:space="preserve"><value>Checking...</value></data>',
    '<data name="USERNAME_NO_CONNECTION" xml:space="preserve"><value>Could not reach the leaderboards. Check your connection and try again.</value></data>',
]


def main(argv):
    if len(argv) != 3:
        print(__doc__)
        return 2
    src_path, out_path = argv[1], argv[2]
    text = open(src_path, encoding="utf-8-sig").read()
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")

    for old, new in REWORDS:
        hits = [i for i, ln in enumerate(lines) if old in ln]
        if len(hits) != 1:
            print(f"STOP: expected exactly one line containing "
                  f"{old[:60]}..., found {len(hits)}. Different game "
                  f"build? See patches/PATCHES.md.")
            return 1
        lines[hits[0]] = lines[hits[0]].replace(old, new)

    if any("OPTIONS_MENU_USERNAME" in ln for ln in lines):
        print("STOP: username strings already present — this .resx "
              "looks already patched; start from a fresh decompile.")
        return 1
    hits = [i for i, ln in enumerate(lines) if ANCHOR in ln]
    if len(hits) != 1:
        print(f"STOP: expected exactly one OPTIONS_MENU_RESET_DATA "
              f"anchor line, found {len(hits)}.")
        return 1
    indent = lines[hits[0]][:len(lines[hits[0]]) - len(lines[hits[0]].lstrip())]
    lines[hits[0] + 1:hits[0] + 1] = [indent + e for e in NEW_ENTRIES]

    with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines))
    print(f"patched resx -> {out_path} "
          f"(2 strings reworded, {len(NEW_ENTRIES)} username strings added)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
