#!/usr/bin/env python3
"""Verify a Fable: Coin Golf XAP against the known-good release.

The pipeline was developed and tested against exactly one build of the
game. Like other recompilation projects, we pin it by hash so that a
different build fails loudly here instead of mysteriously later.

Usage: verify_xap.py <file.xap>
Exit code 0 = hash matches; 1 = mismatch / not a XAP; 2 = usage error.
"""
import hashlib
import sys
import zipfile

EXPECTED_SHA256 = "3492b72f93cb8308917db8bb68738df2532742fc7afa9a65d25096b5214a3f73"
EXPECTED_VERSION = "1.0.8.10"
# Assemblies that must be inside the XAP for the pipeline to work.
REQUIRED_ENTRIES = ("FabMob.dll", "Tech.dll", "ModelData.dll",
                    "XBOXLiveConnectivity.dll")


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2
    path = argv[1]
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    digest = h.hexdigest()
    print(f"file:    {path}")
    print(f"sha256:  {digest}")
    print(f"expect:  {EXPECTED_SHA256}  (v{EXPECTED_VERSION})")
    if digest != EXPECTED_SHA256:
        print("RESULT:  MISMATCH — this is not the build the pipeline targets.")
        return 1
    if not zipfile.is_zipfile(path):
        print("RESULT:  hash matches but the file is not a ZIP/XAP archive?")
        return 1
    names = set(zipfile.ZipFile(path).namelist())
    missing = [e for e in REQUIRED_ENTRIES if e not in names]
    if missing:
        print(f"RESULT:  archive is missing required entries: {missing}")
        return 1
    print("RESULT:  OK — this is the supported XAP.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
