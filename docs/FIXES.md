# Fixes — what was broken, and what the port does about it

A WP7 XNA game does not simply recompile for Android. These are the
defects the port had to solve, in the order they were found. **Every
fix below is automated by the pipeline** — the ones that change
decompiled files ship as verified diffs in `patches/files/` (see
`patches/PATCHES.md` for the per-file inventory).

## Compile surface (automated)
WP7-only APIs (`Microsoft.Phone.Shell`, `Microsoft.Devices`,
GamerServices, WP7 BCL members) don't exist in the Android reference
pack. The scaffold supplies minimal original shims with the same
surface (`Wp7Stubs.cs`, `GamerServicesStubs.cs`, `CompatStubs.cs`),
and one decompiled file — the entry point — gets the two-line-class
patch described as P1 in `patches/PATCHES.md`.

## Content loading (automated)
- **Reader tables.** XNB files name their content readers by the
  original WP7 assembly names. The staged build copies are rewritten
  to the scaffold's single assembly name (P4).
- **Case sensitivity.** WP7 lookup is case-insensitive, Android's
  AssetManager is case-sensitive, and the game asks for assets in
  spellings matching neither the file's case nor lowercase. Fixed at
  build time (duplicate-case injection, P5) and at runtime
  (`CaseFixContentManager`).
- **Object-typed members.** Some XNB data stores values
  polymorphically under `System.Object`; MonoGame's reflective reader
  refuses to initialise without a reader for it. `ObjectFallbackReader`
  fills that slot (P7).

## The dead "SYNCING…" screens (automated)
Both leaderboard surfaces hung forever on "SYNCING…": every Live-gated
flow in the game is callback-driven, and a naive no-op stub accepts
the sign-in callback and never invokes it, parking both screens at
their first step — permanently, because the menu latches its syncing
flag. The included local backend completes every operation
synchronously, in the same call stack, so each surface resolves on the
first frame to real local rows or the game's own built-in empty state.
See `docs/LEADERBOARDS.md`.

## Music (automated)
The soundtrack ships as WMA, which Android's media player cannot
decode. Converted to OGG (libvorbis) with a verified 3-byte Song XNB
patch per track (P6). Lesson recorded from the original work: patch
XNBs as bytes, never as text.

## Coins rendered the wrong colour (automated — `CIwRenderableModel.cs.patch`)
A part-ordering problem in the model renderable: transparent parts
must be ordered explicitly and shadow parts keyed separately
(`OrderAlphaParts`: shadow-textured parts composite before/under
face parts). The patch applies that ordering to your copy of the
renderable.

## Dialogue wrapped to one word per line (automated — `CIwRenderableTextureSpec.cs.patch`)
A creation race: UI texture specs baked their scale from the *live*
viewport on a background load thread, racing the main loop's viewport
cycle (design pin → render target → backbuffer). A bad sample
collapsed the usable text width to a few pixels. On WP7 the viewport
never changed, so the bake cancelled out. Fix: bake against the fixed
design viewport. Fonts were exonerated byte-for-byte before this was
found — the authored wrap was always correct.

## Menu text plaques misregistered (automated — `CIwDecoratedText.cs.patch`)
One draw branch (decorated-text end caps) missed the scale factor the
text path received. The patch scales that branch by the same factor,
and centres the plaque on its text at any aspect (the plaque
correction). A related earlier theory — that render-target
presentation needed a Y-flip correction — was **disproven by
experiment** (it inverted the whole menu stack; those builds were
quarantined). The rule the port now lives by: **never Y-flip any
viewport, clip, or position in this port** — the render-target→
backbuffer blit already supplies the second flip, so orientation and
sub-viewport origin cancel.

## Startup hang (automated — `CFabMobGame.cs.patch`)
A background load thread and the main thread contended over the
content cache lock (an AB–BA deadlock against MonoGame's
BlockOnUIThread), and the load-complete signal could fire before the
level preload finished. Fix: pre-cache the splash font on the main
thread before the load thread starts; reorder the load-phase tail so
preload completes before the signal.

## Presentation: HD + high refresh (automated — `Game.cs.patch` and friends)
Design width stays 480 forever; the design height follows the live
backbuffer aspect, the world renders to a full-resolution render
target, and the player puck is interpolated between the engine's
fixed 30 Hz logic steps (`FcgInterp.cs`), which is what makes 120 Hz
presentation smooth instead of steppy. The camera, texture, text and
splash patches (`CIwCamera`, `CIwRenderableTexture`,
`CIwRenderableText`, `CIwSplashScreens`, `CGameOverState`) carry the
matching per-surface corrections.
