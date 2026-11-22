# Building — the full manual version

`patcher/build.py` chains the steps below and stops honestly at any
missing prerequisite. This document is the same pipeline written out
longhand, for when you want to run (or debug) a step yourself.

## 0. Prerequisites

| Tool | Version used | Why |
|---|---|---|
| Your own XAP | Fable: Coin Golf **v1.0.8.10**, SHA-256 `3492b72f93cb8308917db8bb68738df2532742fc7afa9a65d25096b5214a3f73` | the game itself — not included in this repo |
| Python | 3.x | patcher + tools |
| .NET SDK | 8.0.x, with `dotnet workload install android` | builds the MonoGame Android project |
| ILSpy `ilspycmd` | **8.2.0.7535** (`dotnet tool install --global ilspycmd --version 8.2.0.7535`) | decompiles your XAP's DLLs. Newer ilspycmd releases need a newer SDK tool runner than SDK 8.0.101 ships; the pinned version is the one known to work |
| Android SDK | platforms 34–36, build-tools 34/35 | APK packaging |
| JDK | 17 | required by the Android SDK tooling (a JRE is not enough) |
| ffmpeg | any recent | WMA → OGG music conversion (libvorbis) |

## 1. Verify your XAP

```
python3 tools/verify_xap.py "input/Fable Coin Golf v1.0.8.10.xap"
```

Hash must match. A different build is a different game as far as this
pipeline is concerned.

## 2. Extract

A XAP is a ZIP. Extract it to `work/extracted/`. You should see
`FabMob.dll`, `Tech.dll`, `ModelData.dll`, `XBOXLiveConnectivity.dll`,
`Content/`, and `GameThumbnail.png`.

## 3. Decompile (your machine, your copy)

```
ilspycmd -p --nested-directories --disable-updatecheck -o work/decompiled/FabMob work/extracted/FabMob.dll
ilspycmd -p --nested-directories --disable-updatecheck -o work/decompiled/Tech work/extracted/Tech.dll
ilspycmd -p --nested-directories --disable-updatecheck -o work/decompiled/ModelData work/extracted/ModelData.dll
ilspycmd -p --nested-directories --disable-updatecheck -o work/decompiled/XBOXLiveConnectivity work/extracted/XBOXLiveConnectivity.dll
```

Expected yield: ~380 `.cs` files (~37k lines). All gameplay lives in
Tech; FabMob is a thin entry-point shell.

## 4. Assemble the project

```
python3 patcher/build.py --stage assemble --application-id com.yourname.fablecoingolf
```

This creates `work/src/FableCoinGolf.Android/` containing: every
scaffold `.cs` from `src/scaffold/` (flattened, including `compat/`),
the project file generated from `src/FableCoinGolf.Android.csproj.template`,
`Properties/AndroidManifest.xml` from the template, your
`Tech.localisation.fabmob.resx` copied from your decompiled tree,
`GamePatched.cs` generated from your `decompiled/FabMob/Game.cs`, and
the game's own thumbnail as `Resources/mipmap-hdpi/icon.png`.

## 5. Stage + patch the content

```
python3 patcher/build.py --stage content
```

Copies your `Content/` to `Assets/Content`, then, on that build copy
only: patches XNB reader tables (`tools/patch_xnb_readers.py`),
converts the three music tracks to OGG and byte-patches their Song
XNBs, and runs the case-fix pass, writing `work/case_pairs.txt`.

## 6. Compile

```
dotnet build -c Release work/src/FableCoinGolf.Android
```

(Or `--stage build`.) The project links your decompiled sources; the
only decompiled files excluded are `Game.cs` (replaced by
`GamePatched.cs`), the `AssemblyInfo.cs` files, and
`Tech/CCloudConnectivity.cs` (replaced by the local backend). First
build restores `MonoGame.Framework.Android 3.8.2.1105` from NuGet.

## 7. Package

```
python3 patcher/build.py --stage package
```

Injects the duplicate-case assets from `case_pairs.txt` into the
built `*-Signed.apk`, zipaligns, and re-signs with the standard
Xamarin debug keystore, writing `output/FableCoinGolf.apk`. To sign
with your own keystore instead, run `tools/inject_dupes.py` and
`zipalign` manually, then `apksigner sign --ks <your keystore>`.

Install with `adb install -r output/FableCoinGolf.apk`. Always use
`install -r` over an existing install — uninstalling first erases the
game's save.

## Troubleshooting notes from the original port

- **"SYNCING…" forever on leaderboard screens** — that was the old
  no-op Live stub never invoking its sign-in callback. The included
  local backend completes every call synchronously; if you see it,
  you built without `compat/`.
- **Dialogue collapses to one word per line** — known defect, fix
  described in `patches/PATCHES.md` (M2); not yet automated.
- **Music silent** — check the APK actually contains `.ogg` files
  under `assets/Content/data/music/` and no `.wma`, and that each Song
  XNB references its `.ogg`.
- **A build that differs from a known-good APK by a few bytes in an
  XNB** — suspect a text-encoding round-trip somewhere in your chain.
  XNBs are binary; patch them with byte tools only.
