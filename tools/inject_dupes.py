import shutil, sys, zipfile, os

# Inject duplicate-case asset entries into a built APK (zip entries are
# case-sensitive even though the NTFS build tree is not), then the caller
# zipaligns + re-signs with the same debug keystore.
in_apk, pairs_file, work_apk = sys.argv[1], sys.argv[2], sys.argv[3]
shutil.copyfile(in_apk, work_apk)
z = zipfile.ZipFile(work_apk, 'a')
names = {}
for info in z.infolist():
    names[info.filename] = info
added = 0
skipped = 0
for line in open(pairs_file, encoding='utf-8'):
    line = line.rstrip('\n')
    if not line:
        continue
    dst_rel, src_rel = line.split('\t')
    src = 'assets/Content/' + src_rel
    dst = 'assets/Content/' + dst_rel
    if dst in names:
        skipped += 1
        continue
    info = names.get(src)
    if info is None:
        print('MISSING SRC ENTRY', src)
        skipped += 1
        continue
    data = z.read(src)
    z.writestr(dst, data, compress_type=info.compress_type)
    names[dst] = None
    added += 1
z.close()
print(f'added={added} skipped={skipped} outsize={os.path.getsize(work_apk)}')
