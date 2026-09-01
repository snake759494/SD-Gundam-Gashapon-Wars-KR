# -*- coding: utf-8 -*-
"""@Texture(GameCube) 블록 파서 + 디코더. C4/C8 팔레트(RGB5A3/RGB565) 지원."""
import struct
from PIL import Image

MAGIC = b'@Texture'


def find_blocks(data):
    out = []
    i = 0
    while True:
        i = data.find(MAGIC, i)
        if i < 0:
            break
        out.append(i)
        i += 1
    return out


def rgb5a3(v):
    # GameCube RGB5A3: bit15=1 -> RGB555(opaque); bit15=0 -> ARGB3444
    if v & 0x8000:
        r = (v >> 10) & 0x1F; g = (v >> 5) & 0x1F; b = v & 0x1F
        return (r << 3 | r >> 2, g << 3 | g >> 2, b << 3 | b >> 2, 255)
    else:
        a = (v >> 12) & 0x7; r = (v >> 8) & 0xF; g = (v >> 4) & 0xF; b = v & 0xF
        return (r << 4 | r, g << 4 | g, b << 4 | b, (a << 5 | a << 2 | a >> 1))


def parse_header(data, off):
    w = struct.unpack_from('>I', data, off + 0x10)[0]
    h = struct.unpack_from('>I', data, off + 0x14)[0]
    palcnt = struct.unpack_from('>I', data, off + 0x18)[0]
    imgsize = struct.unpack_from('>I', data, off + 0x38)[0]
    pal_off = off + 0x40
    img_off = pal_off + palcnt * 2
    return {'w': w, 'h': h, 'palcnt': palcnt, 'imgsize': imgsize,
            'pal_off': pal_off, 'img_off': img_off}


def read_palette(data, pal_off, palcnt):
    pal = []
    for i in range(palcnt):
        v = struct.unpack_from('>H', data, pal_off + i * 2)[0]
        pal.append(rgb5a3(v))
    return pal


def _nearest(pal, rgba):
    # 알파 우선(투명/불투명 구분) 후 RGB 거리
    r, g, b, a = rgba
    best = 0; bestd = 1 << 30
    for i, (pr, pg, pb, pa) in enumerate(pal):
        d = (pr - r) ** 2 + (pg - g) ** 2 + (pb - b) ** 2 + 3 * (pa - a) ** 2
        if d < bestd:
            bestd = d; best = i
    return best


def encode_c4(img, pal, w, h):
    """PIL RGBA 이미지를 팔레트 최근접 인덱스로 C4(4bpp,8x8타일) 바이트로 인코딩."""
    img = img.convert('RGBA')
    px = img.load()
    # 픽셀->인덱스 (캐시)
    cache = {}
    def idx(x, y):
        if x >= w or y >= h:
            return 0
        c = px[x, y]
        if c not in cache:
            cache[c] = _nearest(pal, c)
        return cache[c]
    def align(n, a): return (n + a - 1) // a * a
    pw, ph = align(w, 8), align(h, 8)
    out = bytearray()
    for ty in range(0, ph, 8):
        for tx in range(0, pw, 8):
            for y in range(8):
                for x in range(0, 8, 2):
                    hi = idx(tx + x, ty + y)
                    lo = idx(tx + x + 1, ty + y)
                    out.append(((hi & 0xF) << 4) | (lo & 0xF))
    return bytes(out)


def encode_c8(img, pal, w, h):
    """PIL RGBA 이미지를 C8(8bpp,8x8타일) 바이트로 인코딩한다."""
    img = img.convert('RGBA')
    px = img.load()
    cache = {}

    def idx(x, y):
        if x >= w or y >= h:
            return 0
        c = px[x, y]
        if c not in cache:
            cache[c] = _nearest(pal, c)
        return cache[c]

    def align(n, a):
        return (n + a - 1) // a * a

    pw, ph = align(w, 8), align(h, 8)
    out = bytearray()
    for ty in range(0, ph, 8):
        for tx in range(0, pw, 8):
            for y in range(8):
                for x in range(8):
                    out.append(idx(tx + x, ty + y))
    return bytes(out)


def cmp_size(width, height):
    """GameCube CMP/CMPR 이미지의 8x8 매크로블록 기준 바이트 수."""
    return ((width + 7) // 8 * 8) * ((height + 7) // 8 * 8) // 2


def _rgb565(v):
    r = (v >> 11) & 0x1F
    g = (v >> 5) & 0x3F
    b = v & 0x1F
    return (r << 3 | r >> 2, g << 2 | g >> 4, b << 3 | b >> 2)


def decode_cmp_raw(raw, w, h):
    """GameCube CMP raw image를 PIL RGBA로 디코드한다."""
    if len(raw) < cmp_size(w, h):
        raise ValueError("CMP raw 데이터가 짧습니다")
    pw = (w + 7) // 8 * 8
    img = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    px = img.load()
    for y in range(h):
        for x in range(w):
            x0 = x & 3
            x1 = (x >> 2) & 1
            x2 = x >> 3
            y0 = y & 3
            y1 = (y >> 2) & 1
            y2 = y >> 3
            off = 8 * x1 + 16 * y1 + 32 * x2 + 4 * pw * y2
            c0v = (raw[off] << 8) | raw[off + 1]
            c1v = (raw[off + 2] << 8) | raw[off + 3]
            c0 = _rgb565(c0v)
            c1 = _rgb565(c1v)
            mode = c0v > c1v
            if mode:
                c2 = tuple((2 * c0[i] + c1[i]) // 3 for i in range(3))
                c3 = tuple((c0[i] + 2 * c1[i]) // 3 for i in range(3))
            else:
                c2 = tuple((c0[i] + c1[i]) // 2 for i in range(3))
                c3 = (0, 0, 0)
            bits = int.from_bytes(raw[off + 4:off + 8], 'big')
            ix = x0 + 4 * y0
            ci = (bits >> (30 - 2 * ix)) & 3
            color = (c0, c1, c2, c3)[ci]
            alpha = 0 if ci == 3 and not mode else 255
            px[x, y] = color + (alpha,)
    return img


def encode_cmp(img, w, h):
    """PIL RGBA 이미지를 GameCube CMP(DXT1)로 인코딩한다."""
    img = img.convert('RGBA')
    px = img.load()
    pw, ph = (w + 7) // 8 * 8, (h + 7) // 8 * 8
    out = bytearray(cmp_size(w, h))

    def pack565(c):
        r, g, b = c
        return ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)

    def unpack565(v):
        return _rgb565(v)

    def distance(a, b):
        return sum((a[i] - b[i]) ** 2 for i in range(3))

    def block_encode(colors):
        opaque = [c[:3] for c in colors if c[3] >= 32]
        has_alpha = len(opaque) != len(colors)
        if not opaque:
            # 3-color mode + index 3 gives an entirely transparent block.
            return b'\x00\x00\xff\xff\xff\xff\xff\xff'

        # Pick the two farthest source colors, as in the reference encoder.
        best_pair = (opaque[0], opaque[0])
        best_distance = -1
        for i, a in enumerate(opaque):
            for b in opaque[i + 1:]:
                d = distance(a, b)
                if d > best_distance:
                    best_distance = d
                    best_pair = (a, b)
        c0v, c1v = pack565(best_pair[0]), pack565(best_pair[1])
        if has_alpha:
            if c0v > c1v:
                c0v, c1v = c1v, c0v
            if c0v == c1v:
                c0v, c1v = 0, 0xFFFF
        else:
            if c0v <= c1v:
                c0v, c1v = c1v, c0v
            if c0v == c1v:
                c0v, c1v = 0xFFFF, 0

        c0, c1 = unpack565(c0v), unpack565(c1v)
        if c0v > c1v:
            palette = [c0, c1,
                       tuple((2 * c0[i] + c1[i]) // 3 for i in range(3)),
                       tuple((c0[i] + 2 * c1[i]) // 3 for i in range(3))]
            usable = range(4)
        else:
            palette = [c0, c1,
                       tuple((c0[i] + c1[i]) // 2 for i in range(3)),
                       (0, 0, 0)]
            usable = range(3)

        bits = 0
        for c in colors:
            if c[3] < 32 and c0v <= c1v:
                ci = 3
            else:
                ci = min(usable, key=lambda j: distance(c[:3], palette[j]))
            bits = (bits << 2) | ci
        return c0v.to_bytes(2, 'big') + c1v.to_bytes(2, 'big') + bits.to_bytes(4, 'big')

    for ty in range(0, ph, 8):
        for tx in range(0, pw, 8):
            for sy in range(0, 8, 4):
                for sx in range(0, 8, 4):
                    x1 = sx // 4
                    y1 = sy // 4
                    off = 32 * (tx // 8) + 4 * pw * (ty // 8) + 8 * x1 + 16 * y1
                    colors = []
                    for yy in range(4):
                        for xx in range(4):
                            x, y = tx + sx + xx, ty + sy + yy
                            colors.append(px[x, y] if x < w and y < h else (0, 0, 0, 0))
                    out[off:off + 8] = block_encode(colors)
    return bytes(out)


def decode(data, off):
    """@Texture 블록 -> PIL RGBA Image (실패시 None)."""
    hd = parse_header(data, off)
    w, h, palcnt = hd['w'], hd['h'], hd['palcnt']
    if w <= 0 or h <= 0 or w > 1024 or h > 1024:
        return None
    if palcnt not in (16, 256):
        return None
    pal = read_palette(data, hd['pal_off'], palcnt)
    img = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    px = img.load()
    raw = data[hd['img_off']: hd['img_off'] + hd['imgsize']]
    bpp4 = (palcnt == 16)
    # 8x8 타일
    p = 0
    def align(n, a): return (n + a - 1) // a * a
    pw = align(w, 8); ph = align(h, 8)
    try:
        if bpp4:
            for ty in range(0, ph, 8):
                for tx in range(0, pw, 8):
                    for y in range(8):
                        for x in range(0, 8, 2):
                            byte = raw[p]; p += 1
                            for nib, dx in ((byte >> 4, x), (byte & 0xF, x + 1)):
                                X, Y = tx + dx, ty + y
                                if X < w and Y < h:
                                    px[X, Y] = pal[nib]
        else:  # C8
            for ty in range(0, ph, 8):
                for tx in range(0, pw, 8):
                    for y in range(8):
                        for x in range(8):
                            idx = raw[p]; p += 1
                            X, Y = tx + x, ty + y
                            if X < w and Y < h and idx < len(pal):
                                px[X, Y] = pal[idx]
    except IndexError:
        return None
    return img
