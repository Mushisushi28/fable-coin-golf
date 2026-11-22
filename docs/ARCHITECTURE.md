# Architecture — how the port is put together

## The shape of the thing

The original game is XNA 4.0 / Windows Phone 7: four managed
assemblies inside the XAP.

| Assembly | Contents |
|---|---|
| `FabMob.dll` | Thin shell: the `Game` entry-point class only |
| `Tech.dll` | The actual game + engine (states, menus, physics via a Box2D port, sound, saves) — ~370 files |
| `ModelData.dll` | Content data types and their XNB readers |
| `XBOXLiveConnectivity.dll` | The Xbox Live wrapper (sign-in, achievements, leaderboards) + two data types |

The port does **not** rewrite the game. It compiles the decompiled
sources — generated locally from your own XAP — against
**MonoGame.Framework.Android 3.8.2.1105** (`net8.0-android`), with a
small original scaffold supplying everything WP7 had that Android /
MonoGame does not:

- `Activity1.cs` — the Android entry point (MonoGame
  `AndroidGameActivity`, portrait, fullscreen).
- `Wp7Stubs.cs` — `Microsoft.Phone.Shell.PhoneApplicationService`
  (lifecycle events + state dictionary) and
  `Microsoft.Devices.Environment.DeviceType`, compile-time shims for
  WP7-only APIs the game references.
- `GamerServicesStubs.cs` — the `Microsoft.Xna.Framework.GamerServices`
  surface MonoGame doesn't ship (`Guide`, `SignedInGamer`, leaderboard
  keys, the exception types the game catches), plus the WP7
  marketplace task type as a no-op.
- `CompatStubs.cs` — BCL surface differences (e.g. WP7's
  `Stopwatch.GetRawElapsedTicks()`).
- `CaseFixContentManager.cs` / `ObjectFallbackReader.cs` — content
  pipeline compatibility (case-insensitive lookup; object-typed XNB
  members). See `patches/PATCHES.md` P5/P7.
- `compat/` — replacements for the two dead online services (Xbox
  Live and the Fable III cloud service). See `docs/LEADERBOARDS.md`.

## Data flow at build time

```
your XAP ──extract──> DLLs + Content/
   ├─ DLLs ──ILSpy──> decompiled/ ──linked by .csproj──┐
   ├─ Content/ ──stage + tools──> Assets/Content       ├─> dotnet build
   └─ scaffold (this repo) ────────────────────────────┘        │
                                          duplicate-case injection (zip)
                                                                │
                                                         output/*.apk
```

The decompiled tree is an input, never a deliverable: the project
links it with `Compile Include` globs and per-file exclusions where
the scaffold replaces a file. Nothing in `work/` is committed.

## Runtime notes

- The engine logic runs at a fixed 30 Hz; presentation can run faster.
  `FcgInterp.cs` publishes puck interpolation state so the player puck
  renders smoothly between logic steps at high refresh rates.
- Design resolution is 480×800 (WP7). Everything UI-related is
  authored in fractions of that space; the viewport history of the
  port (and why you must never Y-flip a viewport in it) is in
  `docs/FIXES.md`.
- Saves are the game's own XML format in app-private storage.
  Installing over an existing build (`adb install -r`) preserves
  them; uninstalling does not.
