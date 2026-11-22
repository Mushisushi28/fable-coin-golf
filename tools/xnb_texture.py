#!/usr/bin/env python3
"""Parse an uncompressed XNB (v5) whose primary object is a Texture2D.
Decode DXT1/DXT5 (reference algorithm) or Color/Bgr565 to RGBA pixels.
Usage: xnb_texture.py <file.xnb> <out.png>  -> prints JSON stats."""
import json, struct, sys
from PIL import Image

def read_7bit(buf, pos):
    result = 0; shift = 0
    while True:
        b = buf[pos]; pos += 1
        result |= (b & 0x7F) << shift; shift += 7
        if not (b & 0x80):
            return result, pos

def read_string(buf, pos):
    n, pos = read_7bit(buf, pos)
    s = buf[pos:pos+n].decode('utf-8', 'replace'); pos += n
    return s, pos

def parse_texture(path):
    buf = open(path, 'rb').read()
    assert buf[:3] == b'XNB', 'not XNB'
    platform = chr(buf[3]); version = buf[4]; flags = buf[5]
    total = struct.unpack_from('<i', buf, 6)[0]
    assert flags & 0x80 == 0, 'compressed XNB not supported'
    pos = 10
    nreaders, pos = read_7bit(buf, pos)
    readers = []
    for _ in range(nreaders):
        name, pos = read_string(buf, pos)
        ver = struct.unpack_from('<i', buf, pos)[0]; pos += 4
        readers.append((name, ver))
    nshared, pos = read_7bit(buf, pos)
    tidx, pos = read_7bit(buf, pos)
    rname = readers[tidx-1][0] if tidx else 'null'
    fmt, w, h, mips = struct.unpack_from('<iiii', buf, pos); pos += 16
    levels = []
    for _ in range(mips):
        dlen = struct.unpack_from('<i', buf, pos)[0]; pos += 4
        levels.append(buf[pos:pos+dlen]); pos += dlen
    return dict(platform=platform, version=version, reader=rname,
                format=fmt, width=w, height=h, mips=mips, levels=levels,
                readers=[r[0] for r in readers], shared=nshared)

def expand565(c):
    r = (c >> 11) & 0x1F; g = (c >> 5) & 0x3F; b = c & 0x1F
    return ((r << 3) | (r >> 2), (g << 2) | (g >> 4), (b << 3) | (b >> 2))

def decode_dxt(data, w, h, alpha_mode):
    """alpha_mode: 'dxt1' (1-bit/punchthrough or opaque), 'dxt5'."""
    out = bytearray(w * h * 4)
    bx = (w + 3) // 4; by = (h + 3) // 4
    blocksize = 16 if alpha_mode == 'dxt5' else 8
    for byi in range(by):
        for bxi in range(bx):
            off = (byi * bx + bxi) * blocksize
            blk = data[off:off+blocksize]
            alphas = [255] * 16
            coff = 0
            if alpha_mode == 'dxt5':
                a0, a1 = blk[0], blk[1]
                if a0 > a1:
                    atab = [a0, a1] + [((7 - i) * a0 + i * a1) // 7 for i in range(1, 7)]
                else:
                    atab = [a0, a1] + [((5 - i) * a0 + i * a1) // 5 for i in range(1, 5)] + [0, 255]
                bits = int.from_bytes(blk[2:8], 'little')
                alphas = [atab[(bits >> (3 * i)) & 0x7] for i in range(16)]
                coff = 8
            c0, c1 = struct.unpack_from('<HH', blk, coff)
            p0 = expand565(c0); p1 = expand565(c1)
            if c0 > c1 or alpha_mode == 'dxt5':
                pal = [p0, p1,
                       tuple((2 * p0[k] + p1[k]) // 3 for k in range(3)),
                       tuple((p0[k] + 2 * p1[k]) // 3 for k in range(3))]
                palpha = alphas
            else:
                pal = [p0, p1, tuple((p0[k] + p1[k]) // 2 for k in range(3)), (0, 0, 0)]
                palpha = [alphas[i] if i != 3 else 0 for i in range(16)]
                if alpha_mode == 'dxt1_opaque':
                    pal[3] = (0, 0, 0); palpha = [255] * 16
            idx = struct.unpack_from('<I', blk, coff + 4)[0]
            for i in range(16):
                px = bxi * 4 + (i % 4); py = byi * 4 + (i // 4)
                if px >= w or py >= h:
                    continue
                ci = (idx >> (2 * i)) & 0x3
                o = (py * w + px) * 4
                out[o:o+3] = bytes(pal[ci])
                out[o+3] = palpha[i] if alpha_mode == 'dxt5' else (palpha[ci] if False else (0 if (alpha_mode == 'dxt1' and c0 <= c1 and ci == 3) else 255))
    return bytes(out)

def main():
    path, outpng = sys.argv[1], sys.argv[2]
    t = parse_texture(path)
    fmtmap = {0: 'Color', 1: 'Bgr565', 4: 'Dxt1', 5: 'Dxt3', 6: 'Dxt5'}
    fmtname = fmtmap.get(t['format'], str(t['format']))
    data = t['levels'][0]; w, h = t['width'], t['height']
    if t['format'] == 6:
        px = decode_dxt(data, w, h, 'dxt5')
    elif t['format'] == 4:
        px = decode_dxt(data, w, h, 'dxt1')
    elif t['format'] == 0:
        px = data[:w*h*4]
    elif t['format'] == 1:
        outb = bytearray(w*h*4)
        for i in range(w*h):
            c = struct.unpack_from('<H', data, i*2)[0]
            r, g, b = expand565(c)
            outb[i*4:i*4+4] = bytes((r, g, b, 255))
        px = bytes(outb)
    else:
        print(json.dumps({'error': 'unhandled format', 'format': t['format']})); return
    img = Image.frombytes('RGBA', (w, h), px)
    img.save(outpng)
    import numpy as np
    a = np.frombuffer(px, dtype=np.uint8).reshape(h, w, 4).astype(int)
    opaque = a[a[:, :, 3] > 200]
    semi = a[(a[:, :, 3] > 10) & (a[:, :, 3] <= 200)]
    stats = dict(file=path.split('/')[-1], platform=t['platform'], reader=t['reader'],
                 format=fmtname, size=f'{w}x{h}', mips=t['mips'],
                 opaque_mean=[round(float(x), 1) for x in opaque[:, :3].mean(axis=0)] if len(opaque) else None,
                 opaque_count=int(len(opaque)),
                 semi_mean=[round(float(x), 1) for x in semi[:, :3].mean(axis=0)] if len(semi) else None,
                 semi_count=int(len(semi)),
                 transparent_count=int((a[:, :, 3] <= 10).sum()))
    print(json.dumps(stats, indent=1))

if __name__ == '__main__':
    main()
