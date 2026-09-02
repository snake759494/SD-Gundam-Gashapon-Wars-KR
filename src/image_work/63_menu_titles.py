# -*- coding: utf-8 -*-
"""bank102 대형 메뉴 타이틀(368/316x74) 한글 재작화.

각 타이틀은 같은 위치의 C4 하이라이트와 CMP 색상 레이어가 한 쌍이다.
C4만 바꾸면 일본어 색상 레이어가 남아 한글 글자가 잘려 보이므로 두 레이어를
동일한 작화에서 함께 교체한다. 레이아웃과 각 블록의 길이는 유지한다."""
import sys, io, os, argparse
import struct
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tex_lib as TX
from PIL import Image, ImageFont, ImageDraw

BASE = os.path.join(HERE, '..', 'files')
PATCHED = os.path.join(HERE, '..', 'text_patch_work', 'patched_files')
FONT = os.path.join(HERE, '..', 'fonts', 'NanumSquareNeocBd.ttf')
ap = argparse.ArgumentParser()
ap.add_argument('--apply', action='store_true')
ap.add_argument('--preview', action='store_true')
args = ap.parse_args()

REL = 'Info/arc/bank102.arc'
# bank102의 대형 타이틀. 앞의 10종은 메인 메뉴이고 뒤의 7종은
# 싱글/멀티 선택 후 표시되는 세부 모드다. Issue #12 캡처에서 확인된
# 일본어 잔상(특히 アクション対戦)을 포함해 모두 같은 C4/CMP 쌍으로 교체한다.
TITLES = {
    0x309A0: '모드 선택', 0x36E40: '싱글 플레이', 0x3D2E0: '멀티 플레이',
    0x43780: '옵션', 0x4A3A0: '시나리오 게임', 0x840A0: '도움말',
    0x8B440: '사운드 플레이어', 0x927E0: '진동', 0x99B80: '사운드 설정',
    0xA0F20: '메모리 카드',
    0x51740: '캡슐 워즈', 0x58AE0: '100문 배틀', 0x5FE80: '캡슐 편집',
    0x67220: '맵 대전', 0x6E5C0: '액션 대전', 0x75960: '서바이벌',
    0x7CD00: '배틀로얄',
}
MASKS = {
    0x309A0: 0x2D760, 0x36E40: 0x33C00, 0x3D2E0: 0x3A0A0,
    0x43780: 0x40540, 0x4A3A0: 0x469E0, 0x51740: 0x4DD80,
    0x58AE0: 0x55120, 0x5FE80: 0x5C4C0, 0x67220: 0x63860,
    0x6E5C0: 0x6AC00, 0x75960: 0x71FA0, 0x7CD00: 0x79340,
    0x840A0: 0x806E0, 0x8B440: 0x87A80, 0x927E0: 0x8EE20,
    0x99B80: 0x961C0, 0xA0F20: 0x9D560, 0xA82C0: 0xA4900,
}
# 원본 CMP 레이어의 색상 계열을 유지하되, 글자 자체는 한글이 잘 읽히도록 단순화한다.
CMP_COLORS = {
    0x309A0: (166, 151, 47, 255), 0x36E40: (10, 150, 125, 255),
    0x3D2E0: (230, 135, 35, 255), 0x43780: (142, 92, 176, 255),
    0x4A3A0: (20, 150, 125, 255), 0x840A0: (210, 185, 55, 255),
    0x8B440: (237, 128, 150, 255), 0x927E0: (170, 90, 210, 255),
    0x99B80: (80, 140, 210, 255), 0xA0F20: (145, 105, 190, 255),
}
WHITE = (255, 255, 255, 255)


def read_base(rel):
    # 60_label_inject.py가 먼저 만든 소형 헤더를 보존한다. 이 스크립트는
    # 타이틀 영역을 매번 원본 작화로 다시 만들기 때문에 반복 실행해도 누적되지 않는다.
    patched = os.path.join(PATCHED, rel)
    return open(patched if os.path.exists(patched) else os.path.join(BASE, rel), 'rb').read()


def draw_white(text, w, ht, sw=3):
    """흰색 굵은 글자(버블 느낌), 투명 배경."""
    img = Image.new('RGBA', (w, ht), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for size in range(ht, 6, -1):
        f = ImageFont.truetype(FONT, size)
        bb = d.textbbox((0, 0), text, font=f, stroke_width=sw)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
        if tw <= w - 10 and th <= ht - 4:
            x = (w - tw) // 2 - bb[0]; y = (ht - th) // 2 - bb[1]
            d.text((x, y), text, font=f, fill=WHITE, stroke_width=sw, stroke_fill=WHITE)
            return img
    return img


def draw_cmp(text, w, ht, color, sw=2):
    """불투명한 흰 바탕 위에 CMP 색상 타이틀을 그린다."""
    img = Image.new('RGBA', (w, ht), WHITE)
    d = ImageDraw.Draw(img)
    stroke = (38, 38, 38, 255)
    for size in range(ht, 6, -1):
        f = ImageFont.truetype(FONT, size)
        bb = d.textbbox((0, 0), text, font=f, stroke_width=sw)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
        if tw <= w - 10 and th <= ht - 4:
            x = (w - tw) // 2 - bb[0]; y = (ht - th) // 2 - bb[1]
            d.text((x, y), text, font=f, fill=color,
                   stroke_width=sw, stroke_fill=stroke)
            return img
    return img


def cmp_header(data, off):
    """bank102의 CMP 블록은 일반 @Texture 파서의 팔레트 위치 예외다."""
    fmt = struct.unpack_from('>I', data, off + 0x08)[0]
    w = struct.unpack_from('>I', data, off + 0x10)[0]
    h = struct.unpack_from('>I', data, off + 0x14)[0]
    imgsize = struct.unpack_from('>I', data, off + 0x38)[0]
    if fmt != 0x0E:
        raise ValueError("CMP 블록이 아닙니다: 0x%X (format=0x%X)" % (off, fmt))
    return {'w': w, 'h': h, 'imgsize': imgsize, 'img_off': off + 0x40}


b = read_base(REL)
out = {}; cmp_out = {}; prev = []
for o, ko in TITLES.items():
    hd = TX.parse_header(b, o)
    pal = TX.read_palette(b, hd['pal_off'], hd['palcnt'])
    orig = TX.decode(b, o)
    img = draw_white(ko, orig.width, orig.height, sw=3)
    out[o] = TX.encode_c4(img, pal, hd['w'], hd['h'])
    mo = MASKS[o]
    mh = cmp_header(b, mo)
    if (mh['w'], mh['h']) != (hd['w'], hd['h']):
        raise ValueError("C4/CMP 크기 불일치: 0x%X / 0x%X" % (o, mo))
    cmp_img = draw_cmp(ko, mh['w'], mh['h'], CMP_COLORS.get(o, (120, 150, 190, 255)))
    cmp_out[mo] = TX.encode_cmp(cmp_img, mh['w'], mh['h'])
    prev.append((o, img, ko))
    prev.append((mo, cmp_img, ko + " / CMP"))

if args.preview:
    os.makedirs(os.path.join(HERE, 'out'), exist_ok=True)
    W = max(i.width for _, i, _ in prev)
    H = sum(i.height for _, i, _ in prev) + len(prev) * 6
    m = Image.new('RGB', (W, H), (60, 60, 70)); d = ImageDraw.Draw(m); y = 0
    for o, img, ko in prev:
        bg = Image.new('RGB', img.size, (60, 60, 70)); bg.paste(img, (0, 0), img)
        m.paste(bg, (0, y)); d.text((2, y + 1), f"{o:X}", fill=(0, 255, 0)); y += img.height + 6
    m.save(os.path.join(HERE, 'out', 'menu_titles_preview.png'))
    print("preview saved:", len(prev))

if args.apply:
    bb = bytearray(b)
    for o, data in out.items():
        hd = TX.parse_header(b, o)
        assert len(data) == hd['imgsize'], (hex(o), len(data), hd['imgsize'])
        bb[hd['img_off']: hd['img_off'] + hd['imgsize']] = data
    for o, data in cmp_out.items():
        hd = cmp_header(b, o)
        assert len(data) == hd['imgsize'], (hex(o), len(data), hd['imgsize'])
        bb[hd['img_off']: hd['img_off'] + hd['imgsize']] = data
    dst = os.path.join(PATCHED, REL)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    open(dst, 'wb').write(bb)
    assert os.path.getsize(dst) == len(b)
    print("APPLIED", REL, "C4 titles:", len(out), "CMP titles:", len(cmp_out))
print("total title pairs:", len(out))
