# -*- coding: utf-8 -*-
"""미번역 텍스처를 '인덱스 그레이스케일'로 렌더해 일본어 판독(팔레트 무시, 4bpp 인덱스=밝기)."""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tex_lib as TX
from PIL import Image, ImageDraw

BASE = os.path.join(HERE, '..', 'files')

def align(n, a): return (n + a - 1) // a * a

def decode_index_gray(b, off):
    hd = TX.parse_header(b, off)
    w, h, palcnt = hd['w'], hd['h'], hd['palcnt']
    raw = b[hd['img_off']: hd['img_off'] + hd['imgsize']]
    img = Image.new('RGB', (w, h), (10, 10, 20))
    px = img.load()
    pw, ph = align(w, 8), align(h, 8)
    p = 0
    maxidx = palcnt - 1
    if palcnt == 16:
        for ty in range(0, ph, 8):
            for tx in range(0, pw, 8):
                for y in range(8):
                    for x in range(0, 8, 2):
                        byte = raw[p]; p += 1
                        for nib, dx in ((byte >> 4, x), (byte & 0xF, x + 1)):
                            X, Y = tx + dx, ty + y
                            if X < w and Y < h:
                                g = int(nib * 255 / maxidx)
                                px[X, Y] = (g, g, g)
    return img

GROUPS = {
    'bank102map': ('Info/arc/bank102.arc', [0x309A0, 0x36E40, 0x3D2E0, 0x43780, 0x4A3A0,
                                            0x840A0, 0x8B440, 0x927E0, 0x99B80, 0xA0F20]),
    'bank102unk': ('Info/arc/bank102.arc', [0x51740, 0x58AE0, 0x5FE80, 0x67220, 0x6E5C0, 0x75960, 0x7CD00]),
    'bank108': ('Info/arc/bank108.arc', [0x14B40, 0x1BEE0, 0x23280, 0x2A620, 0x319C0, 0x38D60, 0x40100]),
}
for name, (rel, offs) in GROUPS.items():
    b = open(os.path.join(BASE, rel.replace('/', os.sep)), 'rb').read()
    imgs = [(o, decode_index_gray(b, o)) for o in offs]
    W = max(i.width for _, i in imgs) * 2 + 90
    H = sum(i.height for _, i in imgs) * 2 + len(imgs) * 12
    m = Image.new('RGB', (W, H), (10, 10, 20)); d = ImageDraw.Draw(m); y = 6
    for o, img in imgs:
        big = img.resize((img.width * 2, img.height * 2), Image.NEAREST)
        m.paste(big, (80, y)); d.text((4, y + 4), '0x%X' % o, fill=(0, 255, 0)); y += big.height + 12
    m.save(os.path.join(HERE, 'idx_%s.png' % name))
    print('idx_%s.png' % name)
