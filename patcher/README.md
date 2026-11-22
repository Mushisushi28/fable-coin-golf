# Patcher — the pipeline

`build.py` is the recomp-style pipeline: your XAP in, an Android APK
out, everything generated locally from your own copy of the game.

```
python3 patcher/build.py [--stage STAGE] [--xap PATH]
                         [--application-id ID] [--android-sdk PATH]
                         [--allow-other-version]
```

Stages, in order: `verify` → `extract` → `decompile` → `assemble` →
`content` → `build` → `package`. Run one at a time with `--stage`
when a prerequisite needs attention; the pipeline stops with the exact
command or install step required rather than skipping silently.

`apply_game_patch.py` is the one source transformation in the
pipeline: it generates the patched entry point (`GamePatched.cs`)
from your own decompiled `Game.cs`, verifies the two documented
changes matched, and refuses — with a pointer to
`patches/PATCHES.md` — if they don't.

What is generated where:

```
input/    your XAP (git-ignored, never committed)
work/     everything the pipeline generates (git-ignored):
  extracted/   your XAP, unzipped
  decompiled/  your DLLs, decompiled by ILSpy on your machine
  src/FableCoinGolf.Android/   the assembled MonoGame project
  case_pairs.txt, work.apk, aligned.apk   packaging intermediates
output/   FableCoinGolf.apk (git-ignored)
```

Honest limits are listed in `docs/BUILDING.md` and
`patches/PATCHES.md`: the chained pipeline reproduces the playable
port with local leaderboards and restored music; several later polish
fixes from the development builds are documented patch descriptions
(M1–M7), not automation.
