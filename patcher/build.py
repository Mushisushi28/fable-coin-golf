#!/usr/bin/env python3
"""Fable: Coin Golf — recomp-style build pipeline.

Takes YOUR OWN legally obtained XAP and produces an Android APK on
YOUR machine. Nothing copyrighted is downloaded or distributed; every
game file the build uses is extracted, decompiled, and patched locally
from the XAP you supply.

Stages (run individually with --stage, or all in order by default):

  verify     SHA-256-check the XAP in input/ (tools/verify_xap.py)
  extract    Unzip the XAP into work/extracted/
  decompile  ilspycmd the 4 game DLLs into work/decompiled/
             (requires ilspycmd 8.2.0.7535 on PATH; if it is missing,
             the exact commands are printed and the stage stops —
             this step is NOT silently skipped)
  assemble   Build the work tree: scaffold + project template +
             manifest + ALL source patches applied to YOUR decompiled
             files (patcher/apply_patches.py + patch_manifest.json:
             the 11 replacement files generated into the project, the
             5 leaderboard/localisation files patched in place) +
             YOUR localisation .resx patched (patcher/patch_resx.py) +
             the username-dialog resources + Cinzel font + generated
             dialog/icon art (tools/generate_dialog_art.py) + the
             game's own thumbnail as the app icon + your leaderboard
             backend config, if any (leaderboard.config.json)
  content    Stage Content/ into the project Assets, patch the XNB
             reader tables, convert the music (ffmpeg: WMA -> OGG),
             patch the Song XNBs, and run the case-fix pass
  build      dotnet build -c Release (requires .NET 8 SDK, the
             Android workload, an Android SDK, and JDK 17)
  package    Inject the duplicate-case assets into the built APK,
             zipalign, and re-sign with the standard debug keystore,
             producing output/FableCoinGolf.apk

Honest status: every stage above is implemented; the pipeline
reproduces the newest development build of the port (the
fable-ui-fixes-2026-11-18 lineage) from your XAP — every source
difference from a fresh decompile is an automated, verified patch in
patches/files/, listed in patches/PATCHES.md. The stages are chained,
but this is not a fire-and-forget one-click installer — if a
prerequisite is missing the pipeline stops at that stage with the
exact command or install step needed. See docs/BUILDING.md.
"""
import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
import zipfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.path.join(REPO, "work")
PROJ = os.path.join(WORK, "src", "FableCoinGolf.Android")
TOOLS = os.path.join(REPO, "tools")
PATCHER = os.path.join(REPO, "patcher")
ASSEMBLIES = ("FabMob", "Tech", "ModelData", "XBOXLiveConnectivity")


def run(cmd, **kw):
    print("+", " ".join(str(c) for c in cmd))
    return subprocess.run([str(c) for c in cmd], **kw).returncode


def die(msg, code=1):
    print(f"\nSTOP: {msg}")
    return code


def find_xap(args):
    if args.xap:
        return args.xap
    hits = sorted(glob.glob(os.path.join(REPO, "input", "*.xap")))
    return hits[0] if hits else None


def stage_verify(args):
    xap = find_xap(args)
    if not xap:
        return die("no .xap found. Put your Fable: Coin Golf v1.0.8.10 XAP "
                   "in the input/ folder (see input/PUT-YOUR-XAP-HERE.txt).")
    rc = run([sys.executable, os.path.join(TOOLS, "verify_xap.py"), xap])
    if rc != 0 and not args.allow_other_version:
        return die("XAP verification failed. The pipeline targets v1.0.8.10 "
                   "only; re-run with --allow-other-version to proceed anyway "
                   "(later stages will likely fail).")
    args.xap = xap
    return 0


def stage_extract(args):
    out = os.path.join(WORK, "extracted")
    os.makedirs(out, exist_ok=True)
    with zipfile.ZipFile(args.xap) as z:
        z.extractall(out)
    print(f"extracted -> {out}")
    return 0


def stage_decompile(args):
    if not shutil.which("ilspycmd"):
        print("ilspycmd not found on PATH. Install the exact version used")
        print("by the original port, then re-run this stage:")
        print("  dotnet tool install --global ilspycmd --version 8.2.0.7535")
        print("Manual equivalent (per assembly):")
        for name in ASSEMBLIES:
            print(f"  ilspycmd -p --nested-directories --disable-updatecheck "
                  f"-o work/decompiled/{name} work/extracted/{name}.dll")
        return die("decompile prerequisite missing (manual step, not skipped).", 2)
    for name in ASSEMBLIES:
        dll = os.path.join(WORK, "extracted", name + ".dll")
        out = os.path.join(WORK, "decompiled", name)
        if run(["ilspycmd", "-p", "--nested-directories",
                "--disable-updatecheck", "-o", out, dll]) != 0:
            return die(f"ilspycmd failed for {name}.dll")
    return 0


def stage_assemble(args):
    os.makedirs(PROJ, exist_ok=True)
    scaffold = os.path.join(REPO, "src", "scaffold")
    for root, _dirs, files in os.walk(scaffold):
        for f in files:
            if f.endswith(".cs"):
                shutil.copyfile(os.path.join(root, f), os.path.join(PROJ, f))
    # Project file from the template, with your application id.
    csproj = open(os.path.join(REPO, "src",
                               "FableCoinGolf.Android.csproj.template"),
                  encoding="utf-8").read()
    if args.application_id:
        csproj = csproj.replace("com.example.fablecoingolf",
                                args.application_id)
    open(os.path.join(PROJ, "FableCoinGolf.Android.csproj"), "w",
         encoding="utf-8").write(csproj)
    # Manifest from the template.
    manifest = open(os.path.join(REPO, "src", "AndroidManifest.template.xml"),
                    encoding="utf-8").read()
    if args.application_id:
        manifest = manifest.replace("com.example.fablecoingolf",
                                    args.application_id)
    props = os.path.join(PROJ, "Properties")
    os.makedirs(props, exist_ok=True)
    open(os.path.join(props, "AndroidManifest.xml"), "w",
         encoding="utf-8").write(manifest)
    # Your localisation resource, from your decompiled tree, patched
    # (achievement rewording + the port's username strings).
    resx = os.path.join(WORK, "decompiled", "Tech",
                        "Tech.localisation.fabmob.resx")
    if not os.path.exists(resx):
        return die(f"missing {resx} — did the decompile stage complete?")
    rc = run([sys.executable, os.path.join(PATCHER, "patch_resx.py"),
              resx, os.path.join(PROJ, "Tech.localisation.fabmob.resx")])
    if rc != 0:
        return die("resx patch failed — see patches/PATCHES.md.")
    # Every source patch: replacement files generated into the project,
    # leaderboard/localisation files patched in place in your work copy
    # of the decompiled tree. Each patch verifies its hunks exactly and
    # refuses on mismatch (wrong build / decompiler output).
    rc = run([sys.executable, os.path.join(PATCHER, "apply_patches.py"),
              "--manifest", os.path.join(PATCHER, "patch_manifest.json"),
              "--decompiled", os.path.join(WORK, "decompiled"),
              "--project", PROJ])
    if rc != 0:
        return die("source patches failed — see patches/PATCHES.md.")
    # The cloud-connectivity replacement is an original scaffold file,
    # not a patch: the csproj excludes the decompiled original and the
    # scaffold copy (already copied above from src/scaffold/compat/)
    # takes its place.
    # Username-dialog resources (layout, theme, parchment drawable,
    # adaptive-icon definition) — the port's own files.
    res_src = os.path.join(REPO, "src", "resources")
    for root, _dirs, files in os.walk(res_src):
        rel = os.path.relpath(root, res_src)
        for f in files:
            dst_dir = os.path.join(PROJ, "Resources", rel)
            os.makedirs(dst_dir, exist_ok=True)
            shutil.copyfile(os.path.join(root, f), os.path.join(dst_dir, f))
    # Cinzel (the dialog font, SIL OFL 1.1 — Assets/fonts/OFL.txt).
    fonts_src = os.path.join(REPO, "src", "assets", "fonts")
    fonts_dst = os.path.join(PROJ, "Assets", "fonts")
    os.makedirs(fonts_dst, exist_ok=True)
    for f in os.listdir(fonts_src):
        shutil.copyfile(os.path.join(fonts_src, f),
                        os.path.join(fonts_dst, f))
    # Generated raster art: dialog button/flourish + adaptive-icon
    # backgrounds (originals drawn by the tool — the development
    # builds' game-derived art is not distributed).
    rc = run([sys.executable, os.path.join(TOOLS, "generate_dialog_art.py"),
              os.path.join(PROJ, "Resources")])
    if rc != 0:
        return die("dialog art generation failed")
    # The game's own thumbnail (from your XAP) as the launcher icon:
    # legacy icon + the adaptive icon's foreground, at every density.
    thumb = os.path.join(WORK, "extracted", "GameThumbnail.png")
    if os.path.exists(thumb):
        for density in ("mdpi", "hdpi", "xhdpi", "xxhdpi", "xxxhdpi"):
            mip = os.path.join(PROJ, "Resources", f"mipmap-{density}")
            os.makedirs(mip, exist_ok=True)
            shutil.copyfile(thumb, os.path.join(mip, "icon.png"))
            shutil.copyfile(thumb, os.path.join(mip, "icon_foreground.png"))
    # Leaderboard backend config (optional): your own project URL +
    # anon key from leaderboard.config.json (or the FCG_SUPABASE_URL /
    # FCG_SUPABASE_ANON_KEY environment variables) become the work
    # tree's LeaderboardConfig.cs. Absent config = local boards only.
    rc = write_leaderboard_config(args)
    if rc != 0:
        return rc
    print(f"assembled project -> {PROJ}")
    return 0


def write_leaderboard_config(args):
    url = os.environ.get("FCG_SUPABASE_URL", "")
    key = os.environ.get("FCG_SUPABASE_ANON_KEY", "")
    cfg = os.path.join(REPO, "leaderboard.config.json")
    if os.path.exists(cfg):
        try:
            data = json.load(open(cfg, encoding="utf-8"))
        except (OSError, ValueError) as exc:
            return die(f"leaderboard.config.json is not valid JSON: {exc}")
        url = data.get("supabase_url", url) or url
        key = data.get("supabase_anon_key", key) or key
    if not url and not key:
        print("leaderboard config: none — local leaderboards only "
              "(see docs/LEADERBOARDS.md to add your own backend)")
        return 0
    if not url or not key:
        return die("leaderboard config needs BOTH supabase_url and "
                   "supabase_anon_key (or neither).")

    def esc(s):
        return s.replace("\\", "\\\\").replace('"', '\\"')

    body = (
        "// LeaderboardConfig - GENERATED by patcher/build.py from your\n"
        "// leaderboard.config.json. Do not commit this generated file\n"
        "// with real values into a public fork.\n"
        "public static class LeaderboardConfig\n"
        "{\n"
        f"\tpublic const string SupabaseUrl = \"{esc(url)}\";\n"
        f"\tpublic const string AnonKey = \"{esc(key)}\";\n"
        "}\n")
    with open(os.path.join(PROJ, "LeaderboardConfig.cs"), "w",
              encoding="utf-8", newline="\n") as fh:
        fh.write(body)
    print("leaderboard config: backend configured from "
          "leaderboard.config.json / environment")
    return 0


def stage_content(args):
    src_content = os.path.join(WORK, "extracted", "Content")
    dst_content = os.path.join(PROJ, "Assets", "Content")
    if os.path.exists(dst_content):
        shutil.rmtree(dst_content)
    shutil.copytree(src_content, dst_content)
    # XNB reader-table patch (build copies only).
    if run([sys.executable, os.path.join(TOOLS, "patch_xnb_readers.py"),
            dst_content]) != 0:
        return die("patch_xnb_readers.py failed")
    # Music: convert WMA -> OGG, drop the WMA from the build copy,
    # then byte-patch the Song XNBs to point at the OGG files.
    music = os.path.join(dst_content, "data", "music")
    wmas = glob.glob(os.path.join(music, "*.wma")) if os.path.isdir(music) else []
    if wmas:
        if not shutil.which("ffmpeg"):
            print("ffmpeg not found. Convert each track manually, e.g.:")
            for w in wmas:
                print(f"  ffmpeg -i \"{w}\" -c:a libvorbis -q:a 6 "
                      f"\"{w[:-4]}.ogg\"")
            return die("music conversion prerequisite missing "
                       "(manual step, not skipped).", 2)
        for w in wmas:
            if run(["ffmpeg", "-y", "-i", w, "-c:a", "libvorbis",
                    "-q:a", "6", w[:-4] + ".ogg"]) != 0:
                return die(f"ffmpeg failed for {w}")
            os.remove(w)
        if run([sys.executable, os.path.join(TOOLS, "patch_song_xnbs.py"),
                music]) != 0:
            return die("patch_song_xnbs.py failed")
    # Case-fix pass: plans duplicate-case assets for the package stage.
    rc = run([sys.executable, os.path.join(TOOLS, "fix_case_pass.py"),
              dst_content, os.path.join(WORK, "decompiled"), WORK])
    if rc != 0:
        return die("fix_case_pass.py failed")
    print(f"content staged -> {dst_content}")
    return 0


def stage_build(args):
    if not shutil.which("dotnet"):
        return die(".NET SDK not found. Install .NET 8 SDK, then:\n"
                   "  dotnet workload install android\n"
                   "and make sure an Android SDK and JDK 17 are installed "
                   "(see docs/BUILDING.md).", 2)
    return run(["dotnet", "build", "-c", "Release", PROJ])


def stage_package(args):
    built = sorted(glob.glob(os.path.join(
        PROJ, "bin", "Release", "net8.0-android", "*-Signed.apk")))
    if not built:
        return die("no built *-Signed.apk found — did the build stage succeed?")
    out_dir = os.path.join(REPO, "output")
    os.makedirs(out_dir, exist_ok=True)
    work_apk = os.path.join(WORK, "work.apk")
    if run([sys.executable, os.path.join(TOOLS, "inject_dupes.py"),
            built[0], os.path.join(WORK, "case_pairs.txt"),
            work_apk]) != 0:
        return die("inject_dupes.py failed")
    sdk = (args.android_sdk or os.environ.get("ANDROID_SDK_ROOT")
           or os.environ.get("ANDROID_HOME")
           or os.path.expandvars(r"%LocalAppData%\Android\Sdk"))
    bt = sorted(glob.glob(os.path.join(sdk, "build-tools", "*")))
    if not bt:
        return die(f"Android build-tools not found under {sdk}. "
                   "Zipalign + sign manually (see docs/BUILDING.md, step 7).", 2)
    bt = bt[-1]
    aligned = os.path.join(WORK, "aligned.apk")
    final = os.path.join(out_dir, "FableCoinGolf.apk")

    def tool(name):
        # Windows SDK ships zipalign.exe but apksigner as a .bat, which
        # CreateProcess cannot start directly — wrap .bat in cmd /c.
        for cand in (name + ".exe", name + ".bat", name):
            p = os.path.join(bt, cand)
            if os.path.exists(p):
                return ["cmd", "/c", p] if cand.endswith(".bat") else [p]
        return [os.path.join(bt, name)]

    if run(tool("zipalign") + ["-f", "-p", "4",
                               work_apk, aligned]) != 0:
        return die("zipalign failed")
    keystore = os.path.expandvars(
        r"%LocalAppData%\Xamarin\Mono for Android\debug.keystore")
    rc = run(tool("apksigner") + ["sign", "--ks", keystore,
              "--ks-key-alias", "androiddebugkey",
              "--ks-pass", "pass:android", "--key-pass", "pass:android",
              "--out", final, aligned])
    if rc != 0:
        return die("apksigner failed — sign with your own keystore instead "
                   "(see docs/BUILDING.md, step 7).")
    print(f"APK -> {final}")
    return 0


STAGES = {"verify": stage_verify, "extract": stage_extract,
          "decompile": stage_decompile, "assemble": stage_assemble,
          "content": stage_content, "build": stage_build,
          "package": stage_package}
ORDER = list(STAGES)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stage", choices=ORDER,
                    help="run only this stage (default: all, in order)")
    ap.add_argument("--xap", help="path to your XAP (default: first *.xap in input/)")
    ap.add_argument("--application-id",
                    help="your own Android application id for the build")
    ap.add_argument("--android-sdk", help="Android SDK path (package stage)")
    ap.add_argument("--allow-other-version", action="store_true",
                    help="proceed even if the XAP hash does not match v1.0.8.10")
    args = ap.parse_args(argv)
    stages = [args.stage] if args.stage else ORDER
    if "verify" not in stages:
        # Later stages need to know which XAP to use.
        args.xap = find_xap(args)
        if not args.xap and any(s in stages for s in ("extract",)):
            return die("no .xap found in input/ (and --xap not given).")
    for name in stages:
        print(f"\n=== stage: {name} ===")
        rc = STAGES[name](args)
        if rc != 0:
            return rc
    print("\nDone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
