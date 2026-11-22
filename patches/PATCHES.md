# Patches — what the pipeline changes, and what it does not (yet)

The port never modifies the decompiled tree in place. Every change is
either (a) an original scaffold file that *replaces* a decompiled file
via a project-file exclusion, (b) a transformation script in
`patcher/` or `tools/` that runs on your own files, or (c) a build-copy
data patch. This file is the complete inventory.

## Automated by the pipeline

### P1 — `FabMob/Game.cs` → `GamePatched.cs` (entry point)
Tool: `patcher/apply_game_patch.py` (verifies its patterns, refuses on
mismatch). Exactly two changes:
1. `Environment.DeviceType` → `Microsoft.Devices.Environment.DeviceType`
   (bare name is ambiguous under the Android reference pack).
2. `protected override void OnExiting(object sender, EventArgs args)`
   → `protected void OnExiting(...)`, and the
   `base.OnExiting(sender, args);` call inside it is removed
   (MonoGame's Android Game has no such virtual). Body otherwise intact.

### P2 — XBOX Live wrapper replaced (no decompiled file changed)
The project compiles only the two data types (`CAchievement`,
`CLeaderboardEntry`) from your decompiled XBOXLiveConnectivity tree.
The wrapper itself is replaced by the original local backend in
`src/scaffold/compat/XboxLiveStub.cs` + `LocalLeaderboards.cs`:
sign-in completes synchronously with a local profile, achievements are
snapshot reads / commit-on-earn against your own save, leaderboard
reads are synthesised from your own per-level bests. See
`docs/LEADERBOARDS.md`.

### P3 — Cloud connectivity replaced (one exclusion)
`Tech/CCloudConnectivity.cs` is excluded in the project template and
replaced by `src/scaffold/compat/CCloudConnectivity.cs`: same public
signatures, zero network. The original posted to a long-dead web
service for Fable III gold/item transfers; the local version completes
every operation synchronously with local semantics (gold is banked at
level end; item awards retire their retry bookkeeping without granting
anything in Fable III — that service no longer exists).

### P4 — XNB reader tables (build copies only)
Tool: `tools/patch_xnb_readers.py`, run on the staged `Assets/Content`
copy. Rewrites custom-assembly references in XNB type-reader strings
from the original WP7 assembly names to the scaffold's single compiled
assembly name, stripping the version/culture segment for those
references. Framework reader strings are left untouched.

### P5 — Case-fix duplicates (build copies only)
Tools: `tools/fix_case_pass.py` (planning) + `tools/inject_dupes.py`
(APK injection at the package stage) + the runtime half,
`src/scaffold/CaseFixContentManager.cs`. WP7 content lookup is
case-insensitive; Android's is not, and the game requests assets in
spellings that match neither the file's case nor all-lowercase. The
pass plans duplicate-case entries and injects them into the built APK
(zip entries are case-sensitive even though the build filesystem may
not be).

### P6 — Music: WMA → OGG + Song XNB byte patch
Tools: `ffmpeg` (invoked by the pipeline; libvorbis, quality 6) +
`tools/patch_song_xnbs.py`. The three tracks
(`UpbeatChapter_01`, `chapterTwoTheme`, `chapterThreeTheme`) are
converted from your XAP's loose `.wma` files to `.ogg`; each Song XNB
is patched at the byte level — exactly 3 bytes differ (`.wma` → `.ogg`
in the embedded filename). The tool verifies the 3-byte diff and
refuses anything else. Never patch XNBs through a text encoding: a
string round-trip silently corrupts binary bytes (learned the hard
way during the original port; the corrupted build was discarded).

### P7 — Object-typed XNB members
`src/scaffold/ObjectFallbackReader.cs`: a fallback content reader for
object-typed reflective members in the game's XNB data, which
MonoGame's reflective reader otherwise refuses to initialise for.
In the original development builds this reader was appended to the
reader table of packaged XNBs (build copies only).

## Documented but NOT automated (manual steps)

These fixes were part of the original port's later polish builds. They
are scaffold *copies of decompiled files* with small changes, so —
unlike everything above — the fixed files themselves cannot be
distributed, and the pipeline does not yet generate them. Each entry
describes the change precisely enough to reproduce it on your own
decompiled copy. A build without them is the playable Phase-3-level
port; these are quality fixes on top.

- **M1 — Coin rendering (`CIwRenderableModel.cs` copy).** Coins
  rendered with wrong colours: the fix orders transparent model parts
  explicitly and keys shadow parts separately in the renderable's
  part-sorting path. (The diagnostic markers used during development
  are not part of the fix.)
- **M2 — Dialogue wrap (`CIwRenderableTextureSpec.cs` copy).** Texture
  specs baked their scale from the live viewport on a background load
  thread, racing the main loop's viewport cycle and collapsing
  dialogue text to one word per line. The fix bakes against the fixed
  design viewport (480×800) instead of the live one.
- **M3 — Decorated-text end caps (`CIwDecoratedText.cs` copy).** The
  left/right end caps were drawn at native texture scale while the
  text path was scaled; the fix scales only the cap branch by
  `viewport.Width / 480f` (and the right cap's X offset by the same
  factor). Do not Y-flip anything to chase this — see docs/FIXES.md.
- **M4 — Startup hang (`CFabMobGame.cs` copy).** Two changes:
  pre-cache the splash font on the main thread before the background
  load thread starts, and reorder the end of the first load phase so
  the level-manager preload completes before the load-complete signal
  fires.
- **M5 — Case-fix wiring.** Installing `CaseFixContentManager` as the
  game's `Content` (one assignment where the scaffold creates the game)
  activates the runtime half of P5.
- **M6 — Aspect / HD presentation.** The shipped development builds
  render the world to a full-resolution render target, present it
  without letterbox distortion at any aspect, and interpolate the
  player puck between 30 Hz logic steps (`FcgInterp.cs`, included).
  The render-target plumbing lives in the patched game/scaffold files
  covered by M1–M4; reproducing it is manual work guided by
  docs/FIXES.md.
- **M7 — Global leaderboards.** The online backend client from the
  later development builds is not included in this repository (it was
  written against a specific hosted project). `docs/LEADERBOARDS.md`
  specifies the interface so you can implement it against your own
  backend.

## Never patched
Save format, level data, physics, scoring, achievement thresholds, and
all gameplay logic compile from your decompiled tree exactly as
decompiled.
