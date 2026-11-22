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

`apply_patches.py` is the source-transformation engine: it applies
the 16 unified diffs in `patches/files/` (listed in
`patch_manifest.json`) to your own decompiled files — 11 replacement
files generated into the project, 5 leaderboard/localisation files
patched in place in your work copy of the decompiled tree. Every hunk
is verified against your files exactly; a mismatch refuses the build
with the patch and hunk named. `patch_resx.py` does the equivalent
verified edit for your localisation `.resx`. Together they reproduce
the newest development build's source tree from your decompile —
see `patches/PATCHES.md` for the per-file inventory.

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

The chained pipeline reproduces the newest development build
(`fable-ui-fixes-2026-11-18` lineage) end to end: XAP in, that build
out. The only build-time choices are your application id and the
optional leaderboard backend config (`leaderboard.config.json`;
absent = local boards).
