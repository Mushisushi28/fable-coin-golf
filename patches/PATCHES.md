# Patches — every change the pipeline makes

The port never modifies the decompiled tree in place. Every change
is either (a) an original scaffold file that *replaces* a decompiled
file via a project-file exclusion, (b) a unified-diff patch in
`patches/files/` that the patcher applies to your own decompiled
files at build time — generating the replacement copy into the
project, or patching your work copy of the decompiled tree in place —
or (c) a build-copy data patch. This file is the complete inventory.
**There are no manual steps**: a full pipeline run produces the
newest development build (`fable-ui-fixes-2026-11-18` lineage) from
your XAP.

## Source patches (`patcher/apply_patches.py` + `patch_manifest.json`)

Each `.patch` is a minimal unified diff (changed hunks only, 3 lines
of context) against the pristine ILSpy output for v1.0.8.10. The
patcher verifies every hunk against your files exactly and refuses
on any mismatch — a different game build or decompiler output stops
the build instead of producing a wrong tree.

### Replacement patches (patched copy generated into the project;
the decompiled original is excluded in the .csproj)

| Patch | File | What it fixes |
|---|---|---|
| `Game.cs.patch` | `FabMob/Game.cs` → `GamePatched.cs` | The entry point: OnExiting de-overridden + DeviceType qualified (the original two fixes), plus the whole presentation layer — HD render target, dynamic-aspect design window (480 × design-height), viewport pinning in Update, touch display size, fixed-30 Hz logic dispatch with puck interpolation (120 Hz presentation), splash/cover handling |
| `CFabMobGame.cs.patch` | `Tech/CFabMobGame.cs` | **Startup hang (M4):** pre-caches the splash font on the main thread before the load thread starts, and moves `LoadComplete()` after `Preload()` — together they close the AB–BA content-lock deadlock |
| `CIwAnimPlayer.cs.patch` | `Tech/CIwAnimPlayer.cs` | Animation timing: playback advances by the engine-clock delta instead of per-draw real time, decoupling animation speed from the (up to 4×) presentation rate |
| `CIwCamera.cs.patch` | `Tech/CIwCamera.cs` | Dynamic-aspect projection: FOV widens on taller-than-design screens so horizontal framing is preserved |
| `CIwDecoratedText.cs.patch` | `Tech/CIwDecoratedText.cs` | **Menu caps (M3)** + plaque correction: end caps scale by `viewport.Width / 480` like the text path, and plaque height/centre follow the width scale so text stays centred on its plaque at any aspect |
| `CIwRenderableModel.cs.patch` | `Tech/CIwRenderableModel.cs` | **Coin rendering (M1):** transparent parts are ordered explicitly — shadow-textured parts composite before/under face parts (`OrderAlphaParts`), so gold pickups render gold instead of black |
| `CIwRenderableText.cs.patch` | `Tech/CIwRenderableText.cs` | Text renders at the render-target scale: glyph size/advances scale by `viewport.Width / 480`, and the design-viewport clip correction for the scaled path |
| `CIwRenderableTexture.cs.patch` | `Tech/CIwRenderableTexture.cs` | Full-aspect texture correction: framed textures keep authored proportions (height follows the width scale, centred in the slot); fullscreen backgrounds draw COVER |
| `CIwRenderableTextureSpec.cs.patch` | `Tech/CIwRenderableTextureSpec.cs` | **Dialogue wrap (M2):** texture specs bake their scale against the fixed design viewport (480×800) instead of the live viewport read on the background load thread — the race that collapsed dialogue to one word per line |
| `CIwSplashScreens.cs.patch` | `Tech/CIwSplashScreens.cs` | Splash screens draw COVER at the dynamic design window; the prompt position follows the design height |
| `CGameOverState.cs.patch` | `Tech/CGameOverState.cs` | Cover/game-over screens draw to the full current viewport instead of native texture pixels |

### In-place patches (your work copy of the decompiled tree is
patched; the files compile from there, as in the development builds)

| Patch | File | What it does |
|---|---|---|
| `CLeaderBoardMenuSubstate.cs.patch` | `Tech/CLeaderBoardMenuSubstate.cs` | Global boards: reads go straight to the leaderboard service (no sign-in — boards are public), per-board error state instead of the dead SYNCING hang, the entry-name top-margin fix (`SetTextTopMargin`, 42 → 34) from the UI-fix release. The Xbox Live avatar machinery is removed |
| `CLevelEndSubstate.cs.patch` | `Tech/CLevelEndSubstate.cs` | Level end submits level/chapter/overall scores and reads back the level's global top-3 + own rank via the service |
| `CMainMenuSubState.cs.patch` | `Tech/CMainMenuSubState.cs` | UI-fix release: chapter-select heading/medal-number margins lifted (33 → 21, 132 → 120) and the top-strip totals re-set in Charlemagne 10pt, re-centred (`SetTopStripText`) |
| `COptionsMenuSubState.cs.patch` | `Tech/COptionsMenuSubState.cs` | Settings gains the username item: shows the claimed name, opens the native username dialog via the service, refreshes when a claim lands |
| `fabmob.cs.patch` | `Tech/Tech/localisation/fabmob.cs` | Adds the strongly-typed accessors for the 11 username strings the resx patch adds |

### Resource patch (`patcher/patch_resx.py`)

Programmatic, verified replacements on your
`Tech.localisation.fabmob.resx`: the two `sent_gold` strings are
reworded for the local banking semantics, and the port's 11 username
strings are inserted after `OPTIONS_MENU_RESET_DATA`. See
`docs/LEADERBOARDS.md`.

## Scaffold replacements (original files, no patch needed)

- **Cloud connectivity:** `Tech/CCloudConnectivity.cs` is excluded
  and replaced by `src/scaffold/compat/CCloudConnectivity.cs` (same
  public signatures, zero network — the Fable III service is gone).
- **Xbox Live wrapper:** only the two data types compile from your
  decompiled `XBOXLiveConnectivity`; the wrapper is
  `src/scaffold/compat/XboxLiveStub.cs` + `LocalLeaderboards.cs`.
- **Global leaderboard client:** `src/scaffold/CLeaderboardService.cs`
  (the port's own code) + `LeaderboardConfig.cs` (generated from your
  `leaderboard.config.json`; empty = local fallback). The username
  dialog lives in `src/scaffold/Activity1.cs` with
  `src/resources/layout/dialog_username.xml`.

## Data patches (build copies only)

- **XNB reader tables** (`tools/patch_xnb_readers.py`): custom-assembly
  reader strings rewritten to the scaffold's single assembly name.
- **Music (M7's other half):** your WMA tracks convert to OGG with
  ffmpeg and each Song XNB is byte-patched (`.wma` → `.ogg`, exactly
  3 bytes differ — `tools/patch_song_xnbs.py` verifies). The sound
  manager itself needs no patch: the decompiled original already
  loads and plays the converted tracks (Variant B).
- **Case-fix duplicates** (`tools/fix_case_pass.py` +
  `tools/inject_dupes.py` + `CaseFixContentManager`, whose installation
  in the entry point is part of `Game.cs.patch` — **M5**): WP7's
  case-insensitive content lookup emulated on Android's
  case-sensitive asset system.
- **Object-typed XNB members:** `ObjectFallbackReader.cs` (scaffold)
  fills the reflective-reader slot MonoGame otherwise refuses.

## Generated art

The development builds' dialog button/flourish art and adaptive-icon
art were derived from game art, so they are not distributed.
`tools/generate_dialog_art.py` draws original substitutes at build
time (same parchment/gold palette, same pixel sizes, a true 9-patch
button), and the launcher icons are generated from your own XAP's
thumbnail (legacy + adaptive foreground; generated parchment
background). The username dialog's font is Cinzel (SIL OFL 1.1,
`src/assets/fonts/`), as in the development builds.

## Never patched

Save format, level data, physics, scoring, achievement thresholds,
and all gameplay logic compile from your decompiled tree exactly as
decompiled.
