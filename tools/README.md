# Tools — XNB and packaging utilities

All tools are original, pure-stdlib Python 3 unless noted. They only
ever run on **your** files, inside your work tree.

| Tool | What it does |
|---|---|
| `verify_xap.py` | SHA-256-verifies your XAP against the supported v1.0.8.10 build and checks the required assemblies are inside |
| `patch_xnb_readers.py` | Rewrites custom-assembly references in XNB type-reader strings (WP7 assembly names → the scaffold's single assembly name) on build copies |
| `patch_song_xnbs.py` | Byte-level Song XNB patch: `.wma` → `.ogg` in the embedded filename; verifies exactly 3 bytes differ and refuses anything else |
| `fix_case_pass.py` | Scans your staged Content (and optionally your decompiled sources) for every requested asset spelling and plans duplicate-case copies into a pairs file. Paths are arguments — no machine-specific paths are baked in |
| `stage_extref_copies.py` | Applies a pairs file inside a Content tree (filesystem-level variant) |
| `inject_dupes.py` | Injects the planned duplicate-case entries directly into a built APK (zip entries are case-sensitive), ready for zipalign + re-signing |
| `xnb_model.py` | Read-only inspector: walks this game's model XNBs and reports parts, effects, and vertex-colour stats |
| `xnb_texture.py` | Read-only inspector: parses an uncompressed Texture2D XNB and decodes DXT1/DXT5 to an image + JSON stats |
| `xnb_transcode_color.py` | Transcodes a DXT5 XNB texture to uncompressed RGBA, preserving the XNB envelope byte-for-byte outside the texture payload |
