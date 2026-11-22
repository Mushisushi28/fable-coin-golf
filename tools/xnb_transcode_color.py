#!/usr/bin/env python3
"""Transcode a DXT5 XNB texture to uncompressed SurfaceFormat.Color (RGBA),
preserving the XNB envelope (header, reader table incl. any appended
readers) byte-for-byte outside the texture payload.

Usage: xnb_transcode_color.py in.xnb out.xnb
Pure stdlib. DXT5 decode follows the format spec (4-colour palette always).
"""
import struct, sys

def r7(buf, pos):
    v = 0; s = 0
    while True:
        b = buf[pos]; pos += 1
        v |= (b & 0x7F) << s; s += 7
        if not (b & 0x80):
            return v, pos

def expand565(c):
    r = (c >> 11) & 0x1F; g = (c >> 5) & 0x3F; b = c & 0x1F
    return ((r << 3) | (r >> 2), (g << 2) | (g >> 4), (b << 3) | (b >> 2))

def decode_dxt5(data, w, h):
    out = bytearray(w * h * 4)
    bw, bh = w // 4, h // 4
    for byi in range(bh):
        for bxi in range(bw):
            off = (byi * bw + bxi) * 16
            blk = data[off:off+16]
            a0, a1 = blk[0], blk[1]
            if a0 > a1:
                atab = [a0, a1] + [((7 - i) * a0 + i * a1) // 7 for i in range(1, 7)]
            else:
                atab = [a0, a1] + [((5 - i) * a0 + i * a1) // 5 for i in range(1, 5)] + [0, 255]
            abits = int.from_bytes(blk[2:8], 'little')
            c0, c1 = struct.unpack_from('<HH', blk, 8)
            p0 = expand565(c0); p1 = expand565(c1)
            pal = [p0, p1,
                   tuple((2 * p0[k] + p1[k]) // 3 for k in range(3)),
                   tuple((p0[k] + 2 * p1[k]) // 3 for k in range(3))]
            idx = struct.unpack_from('<I', blk, 12)[0]
            for i in range(16):
                px, py = bxi * 4 + (i % 4), byi * 4 + (i // 4)
                o = (py * w + px) * 4
                rgb = pal[(idx >> (2 * i)) & 0x3]
                out[o:o + 3] = bytes(rgb)
                out[o + 3] = atab[(abits >> (3 * i)) & 0x7]
    return bytes(out)

def main(inp, outp):
    buf = open(inp, 'rb').read()
    assert buf[:3] == b'XNB' and buf[5] == 0, "expected uncompressed XNB"
    pos = 10
    n, pos = r7(buf, pos)
    readers = []
    for _ in range(n):
        ln, pos = r7(buf, pos)
        readers.append(buf[pos:pos + ln].decode('utf-8')); pos += ln + 4
    shared, pos = r7(buf, pos)
    assert shared == 0, "texture XNB should have no shared resources"
    payload_start = pos
    rid, pos = r7(buf, pos)
    assert 'Texture2DReader' in readers[rid - 1], readers[rid - 1]
    fmt, w, h, mips = struct.unpack_from('<iiii', buf, pos); pos += 16
    assert fmt == 6, f"expected Dxt5 (6), got {fmt}"
    levels = []
    for _ in range(mips):
        ln, = struct.unpack_from('<i', buf, pos); pos += 4
        levels.append(buf[pos:pos + ln]); pos += ln
    assert pos == len(buf), "trailing bytes after texture payload"

    new_payload = bytearray()
    new_payload += struct.pack('<iiii', 0, w, h, mips)  # SurfaceFormat.Color
    lw, lh = w, h
    for data in levels:
        rgba = decode_dxt5(data, lw, lh)
        assert len(rgba) == lw * lh * 4
        new_payload += struct.pack('<i', len(rgba)) + rgba
        lw = max(1, lw // 2); lh = max(1, lh // 2)

    out = bytearray()
    out += buf[:payload_start]               # header + reader table + shared count
    out += buf[payload_start:pos - 0]        # placeholder, replaced below
    # rebuild properly: header/table/shared + reader-index varint + payload
    out = bytearray(buf[:payload_start])
    # re-emit the reader-index varint exactly as in the source
    p2 = payload_start
    _, p2 = r7(buf, p2)
    out += buf[payload_start:p2]
    out += new_payload
    struct.pack_into('<i', out, 6, len(out))
    open(outp, 'wb').write(bytes(out))
    print(f"{inp}: Dxt5 {w}x{h} mips={mips} {len(buf)}B -> Color {len(out)}B")

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
