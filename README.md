# Fable: Coin Golf — Android Recompilation

A recompilation-style preservation port of **Fable: Coin Golf**
(2011, Windows Phone 7) for modern Android, in the spirit of the
N64 / Xbox 360 recompilation projects: **this repository contains no
game code and no game assets.** You supply your own legally obtained
copy of the game; the patcher in this repo transforms *your* copy —
locally, on your machine — into a working Android build.

When Windows Phone and Xbox Live for WP7 shut down, Coin Golf became
unplayable on any current device: no store, no sign-in, no
leaderboards. This project brings it back as a native MonoGame port —
not an emulator wrapper — with HD presentation at up to 120 fps, the
original music restored, and working leaderboards standing in for the
dead Xbox Live service.

> **Status, honestly:** the pipeline below reproduces the playable
> port — full game, local leaderboards and achievements, restored
> music. Several later polish fixes from the development builds are
> included as precise patch *descriptions* (`patches/PATCHES.md`,
> items M1–M7) rather than automation. There is no one-click
> installer; if a prerequisite is missing, the pipeline stops and
> tells you exactly what to install or run. Nothing here is
> fire-and-forget, and nothing is uploaded anywhere.

## You need

| | |
|---|---|
| **Your own game** | Fable: Coin Golf **v1.0.8.10** XAP — see verification below |
| **.NET SDK** | 8.0.x, plus `dotnet workload install android` |
| **ILSpy** | `ilspycmd` **8.2.0.7535** (`dotnet tool install --global ilspycmd --version 8.2.0.7535`) |
| **Android SDK** | platforms 34–36, build-tools 34/35 |
| **JDK** | 17 (a JRE is not enough) |
| **Python** | 3.x (patcher + tools) |
| **ffmpeg** | any recent build (music conversion) |

## Verify your XAP

The pipeline targets exactly one build of the game. Check yours
before anything else:

```
File:    Fable Coin Golf v1.0.8.10.xap
SHA-256: 3492b72f93cb8308917db8bb68738df2532742fc7afa9a65d25096b5214a3f73
```

```
python3 tools/verify_xap.py "input/Fable Coin Golf v1.0.8.10.xap"
```

A different version is unsupported — not out of fussiness, but
because every patch in the pipeline was developed and verified
against this build, and a different build will fail later in more
confusing places.

## Build it

1. Drop your XAP into `input/` (see `input/PUT-YOUR-XAP-HERE.txt`).
2. Run the pipeline:

   ```
   python3 patcher/build.py --application-id com.yourname.fablecoingolf
   ```

   Use your own application id — do not ship builds under anyone
   else's.
3. Install the result:

   ```
   adb install -r output/FableCoinGolf.apk
   ```

   Always `install -r` over an existing install; uninstalling first
   erases the save.

### What the patcher does

```
verify     SHA-256-checks your XAP
extract    unzips it (a XAP is a ZIP: 4 DLLs + Content/)
decompile  ILSpy-decompiles the 4 DLLs on YOUR machine
assemble   scaffold + project template + your localisation file +
           GamePatched.cs generated from YOUR Game.cs +
           the game's own thumbnail as the app icon
content    stages Content/, patches XNB reader tables,
           converts the music WMA→OGG and byte-patches the Song XNBs,
           plans duplicate-case assets (Android is case-sensitive,
           WP7 was not)
build      dotnet build -c Release (MonoGame, net8.0-android)
package    injects the duplicate-case assets, zipaligns, re-signs
```

Full longhand instructions, per-step commands, and troubleshooting:
`docs/BUILDING.md`. The complete list of every change the pipeline
makes — and everything it deliberately does not change — is
`patches/PATCHES.md`.

### What you get

- The full game, playable start to finish on modern Android.
- HD rendering; up to **120 fps** presentation on supported displays
  (the engine logic is fixed 30 Hz; the puck is interpolated —
  `src/scaffold/FcgInterp.cs`).
- The **original music**, working again (WMA is undecodable on
  Android; the build converts your tracks to OGG).
- **Achievements and leaderboards without Xbox Live**: a local
  backend synthesises personal-best boards from your own save and
  commits achievements locally (`src/scaffold/compat/`). An optional
  global backend against your own hosted database is specified in
  `docs/LEADERBOARDS.md` — no hosted project, endpoint, or key is
  included in this repo.
- Touch mapped the way the WP7 original felt.

## FAQ

**Is this piracy?** No. The repo ships no game code, no assets, and
no way to obtain them. Without your own XAP it is documentation and
tooling. This is the same model as the established recompilation
projects: the user provides the game; the project provides the
transformation.

**Where do I get a XAP?** From your own Windows Phone backup /
purchase history. We can't help you find one, and links to game files
will be removed.

**Why only v1.0.8.10?** It's the build the patches were developed
against. See "Verify your XAP" above.

**Does it need internet?** The build downloads NuGet packages and
tooling. The game itself, with the included local backend, is fully
offline.

**My save from WP7?** Not transferable — different storage, different
era. The Android build keeps its own save; `install -r` preserves it
across updates.

**The build stopped at the decompile/build stage.** That's by
design: a missing prerequisite stops the pipeline with the exact
install command instead of skipping a step silently. `docs/BUILDING.md`
walks each stage by hand.

**Dialogue text looks wrong / a menu plaque is offset.** Known
defects with precisely described fixes — `patches/PATCHES.md` M2/M3.
They are the main gap between this pipeline and the later development
builds, and automating them is the project's top TODO.

## Project layout

```
input/      your XAP goes here (git-ignored)
patcher/    the pipeline: build.py + the Game.cs transformer
src/        the scaffold (all original code) + project/manifest templates
tools/      XNB / packaging utilities (all original code)
patches/    PATCHES.md — every change, automated or described
docs/       architecture, building, fixes, leaderboards
work/       everything generated from your XAP (git-ignored)
output/     your APK (git-ignored)
```

## Legal

**Fable, Fable: Coin Golf, Xbox, and Windows Phone are trademarks of
Microsoft.** This is an unofficial, non-commercial fan preservation
project, not affiliated with or endorsed by Microsoft, Lionhead
Studios, or Ideaworks3D. No Microsoft or Ideaworks code or assets are
distributed in this repository; the game code and assets used at build
time come solely from the copy you supply. For preservation and
personal use with a legally obtained copy of the game. Rights holders
with concerns: please open an issue.

The port's own code (scaffold, patcher, tools, docs) is **MIT** —
see `LICENSE`. That licence covers only the port's own code; it
grants no rights in the underlying game.

## Support the work

Free, and staying free. If Coin Golf coming back put a smile on your
face and you'd like to buy the maintainer a coffee, that's here —
completely optional, nothing is paywalled:

**Ko-fi: https://ko-fi.com/<your-ko-fi-username>** *(placeholder —
replace with the project's Ko-fi page before publishing)*
