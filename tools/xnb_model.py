#!/usr/bin/env python3
"""Walk this game's CustomModelSet XNBs (XNA reflective serialization).

Extracts per model: name, parts (transparent tag, counts), each part's
serialized BasicEffect (external texture ref, DiffuseColor, EmissiveColor,
SpecularColor/Power, Alpha, VertexColorEnabled), and vertex-colour stats
for every vertex array. Validates by exact stream consumption.
"""
import struct
import sys


class XNB:
    def __init__(self, path):
        self.buf = open(path, "rb").read()
        assert self.buf[:3] == b"XNB", "not an XNB"
        self.platform = chr(self.buf[3])
        self.pos = 10
        n = self.u7()
        self.readers = []
        for _ in range(n):
            s = self.string()
            ver = struct.unpack("<i", self.buf[self.pos:self.pos + 4])[0]
            self.pos += 4
            self.readers.append(s)
        self.nshared = self.u7()
        self.shared = [None] * self.nshared
        self.extrefs = []

    # ---- primitives ----
    def u7(self):
        result = 0
        shift = 0
        while True:
            b = self.buf[self.pos]
            self.pos += 1
            result |= (b & 0x7F) << shift
            if not (b & 0x80):
                return result
            shift += 7

    def string(self):
        ln = self.u7()
        s = self.buf[self.pos:self.pos + ln].decode("utf-8", "replace")
        self.pos += ln
        return s

    def i32(self):
        v = struct.unpack("<i", self.buf[self.pos:self.pos + 4])[0]
        self.pos += 4
        return v

    def f32(self):
        v = struct.unpack("<f", self.buf[self.pos:self.pos + 4])[0]
        self.pos += 4
        return v

    def boolean(self):
        v = self.buf[self.pos]
        self.pos += 1
        return v != 0

    def byte(self):
        v = self.buf[self.pos]
        self.pos += 1
        return v

    def vec3(self):
        return (self.f32(), self.f32(), self.f32())

    def vec2(self):
        return (self.f32(), self.f32())

    def vec4(self):
        return (self.f32(), self.f32(), self.f32(), self.f32())

    def color(self):
        r, g, b, a = self.buf[self.pos:self.pos + 4]
        self.pos += 4
        return (r, g, b, a)

    def matrix(self):
        return [self.f32() for _ in range(16)]

    # ---- object plumbing ----
    def obj(self):
        idx = self.u7()
        if idx == 0:
            return None
        return self.body(self.readers[idx - 1])

    def shared_ref(self):
        idx = self.u7()
        if idx == 0:
            return None
        return ("shared", idx)

    def body(self, rname):
        short = rname.split("[[")[0].split(",")[0]
        fn = getattr(self, "read_" + short.split(".")[-1].replace("`1", "").replace("`2", ""), None)
        if fn is None:
            raise ValueError(f"no reader impl for {rname} at pos {self.pos}")
        return fn(rname)

    # ---- readers ----
    def read_ReflectiveReader(self, rname):
        inner = rname.split("[[")[1].split(",")[0].split("]]")[0]
        tname = inner.split(".")[-1]
        fn = getattr(self, "obj_" + tname, None)
        if fn is None:
            raise ValueError(f"no reflective impl for {tname} at pos {self.pos}")
        return fn()

    def read_DictionaryReader(self, rname):
        count = self.i32()
        out = {}
        for _ in range(count):
            k = self.obj()
            v = self.obj()
            out[k] = v
        return out

    def read_ListReader(self, rname):
        inner = rname.split("[[")[1].split(",")[0].split("]]")[0]
        count = self.i32()
        items = []
        for _ in range(count):
            if inner in ("Microsoft.Xna.Framework.Matrix",):
                items.append(self.matrix())
            elif inner in ("System.Int32",):
                items.append(self.i32())
            else:
                items.append(self.obj())
        return items

    def read_ArrayReader(self, rname):
        inner = rname.split("[[")[1].split(",")[0].split("]]")[0]
        count = self.i32()
        tname = inner.split(".")[-1]
        fn = getattr(self, "elem_" + tname)
        return [fn() for _ in range(count)]

    def read_StringReader(self, rname):
        return self.string()

    def read_Int32Reader(self, rname):
        return self.i32()

    def read_BooleanReader(self, rname):
        return self.boolean()

    def read_BoundingSphereReader(self, rname):
        return (self.vec3(), self.f32())

    def read_IndexBufferReader(self, rname):
        sixteen = self.boolean()
        data_len = self.i32()
        esz = 2 if sixteen else 4
        data = self.buf[self.pos:self.pos + data_len]
        self.pos += data_len
        return {"index16": sixteen, "count": data_len // esz}

    def read_EffectReader(self, rname):
        raise ValueError("EffectReader used directly (unexpected)")

    def read_BasicEffectReader(self, rname):
        # Texture: external reference, stored inline as a string
        # (verified byte-exact on coin_sngl: '..\..\coin_single_64_0').
        kind = "string"
        tex = self.string()
        diffuse = self.vec3()
        emissive = self.vec3()
        specular = self.vec3()
        spec_pow = self.f32()
        alpha = self.f32()
        vce = self.boolean()
        return {"tex_kind": kind, "texture": tex, "diffuse": diffuse,
                "emissive": emissive, "specular": specular,
                "specularPower": spec_pow, "alpha": alpha,
                "vertexColorEnabled": vce}

    # ---- reflective object bodies ----
    def obj_CustomModelSet(self):
        return {"meshes": self.obj()}

    def obj_CustomModel(self):
        m = {}
        m["name"] = self.obj()
        m["parts"] = self.obj()
        m["skin"] = self.obj()
        m["bounds"] = (self.vec3(), self.f32())
        m["vertsVPCT"] = self.obj()
        m["vertsVPCT2"] = self.obj()
        m["vertsVPCNT"] = self.obj()
        m["weights"] = self.obj()
        return m

    def obj_CustomModelPart(self):
        p = {}
        p["tag"] = self.obj()
        p["transparent"] = self.obj()
        p["primitiveCount"] = self.i32()
        p["numVertices"] = self.i32()
        p["vertexOffset"] = self.i32()
        p["startIndex"] = self.i32()
        p["indexBuffer"] = self.obj()
        p["effect"] = self.shared_ref()
        return p

    def obj_CIwSkinData(self):
        return {"bindPose": self.obj(), "invBindPose": self.obj(),
                "hierarchy": self.obj(), "alpha": self.boolean()}

    # ---- array element layouts (field order per decompiled structs) ----
    def elem_VertexPositionColorTexture(self):
        pos = self.vec3()
        col = self.color()
        tc = self.vec2()
        return (pos, col, tc)

    def elem_VertexPositionColorTexture2(self):
        col = self.color()
        pos = self.vec3()
        tc = self.vec2()
        tc2 = self.vec2()
        return (pos, col, tc, tc2)

    def elem_VertexPositionColorNormalTexture(self):
        col = self.color()
        pos = self.vec3()
        nrm = self.vec3()
        tc = self.vec2()
        return (pos, col, tc, nrm)

    def elem_CustomVertexWeights(self):
        idx = (self.byte(), self.byte(), self.byte(), self.byte())
        w = self.vec4()
        return (idx, w)

    # ---- top level ----
    def parse(self):
        primary = self.obj()
        for i in range(self.nshared):
            idx = self.u7()
            if idx == 0:
                self.shared[i] = None
            else:
                self.shared[i] = self.body(self.readers[idx - 1])
        # trailing external-reference table
        try:
            n = self.u7()
            if 0 <= n <= 256 and self.pos < len(self.buf):
                self.extrefs = [self.string() for _ in range(n)]
        except Exception:
            pass
        return primary


def colour_stats(verts, label):
    if not verts:
        print(f"    {label}: null")
        return
    cols = [v[1] for v in verts]
    n = len(cols)
    rs = sum(c[0] for c in cols) / n
    gs = sum(c[1] for c in cols) / n
    bs = sum(c[2] for c in cols) / n
    as_ = sum(c[3] for c in cols) / n
    uniq = sorted(set(cols))
    print(f"    {label}: n={n} mean RGBA=({rs:.1f},{gs:.1f},{bs:.1f},{as_:.1f}) distinct={len(uniq)}")
    for u in uniq[:12]:
        print(f"        colour {u} x{cols.count(u)}")


def main():
    for path in sys.argv[1:]:
        print(f"===== {path}")
        x = XNB(path)
        try:
            root = x.parse()
        except Exception as e:
            print(f"  PARSE FAIL: {e} (pos {x.pos}/{len(x.buf)})")
            continue
        print(f"  consumed {x.pos}/{len(x.buf)} bytes; shared={x.nshared}; extrefs={x.extrefs}")
        meshes = root["meshes"]
        for name, m in meshes.items():
            print(f"  model {name!r} (obj name {m['name']!r}) skin={'yes' if m['skin'] else 'no'}")
            if m["skin"]:
                print(f"    skin alpha={m['skin']['alpha']}")
            for pi, p in enumerate(m["parts"] or []):
                eff = None
                if p["effect"]:
                    eff = x.shared[p["effect"][1] - 1]
                print(f"    part {pi}: transparent={p['transparent']!r} prims={p['primitiveCount']} "
                      f"verts={p['numVertices']} vOff={p['vertexOffset']} startIdx={p['startIndex']} "
                      f"tag={p['tag']}")
                print(f"      effectRef={p['effect']}")
                if eff:
                    print(f"      effect: tex={eff['texture']} ({eff['tex_kind']}) diffuse={tuple(round(v,4) for v in eff['diffuse'])} "
                          f"emissive={tuple(round(v,4) for v in eff['emissive'])} specular={tuple(round(v,4) for v in eff['specular'])} "
                          f"specPow={eff['specularPower']} alpha={eff['alpha']} vertexColorEnabled={eff['vertexColorEnabled']}")
                else:
                    print("      effect: None")
            colour_stats(m["vertsVPCT"], "VPCT")
            colour_stats(m["vertsVPCT2"], "VPCT2")
            colour_stats(m["vertsVPCNT"], "VPCNT")
            if m["weights"]:
                print(f"    weights: n={len(m['weights'])}")


if __name__ == "__main__":
    main()
