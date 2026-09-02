# -*- coding: utf-8 -*-
"""메뉴 타이틀의 C4/CMP 겹침 레이어를 한 쌍으로 한글 재작화한다.

메인 메뉴는 같은 문구를 담은 C4 하이라이트와 CMP 색상 레이어를 겹쳐
그리는 구조다. 두 레이어를 서로 다른 글꼴 크기/바운딩으로 만들면 한쪽에
일본어 잔상이나 한글 잘림이 남으므로, 이 스크립트는 한 타이틀마다 하나의
공통 ``TextLayout``을 계산하고 두 레이어에 같은 글꼴과 원점을 사용한다.

bank102와 bank108은 메인 메뉴의 중복 리소스이고, bank113은 멀티플레이
대전 방식 선택 화면의 타이틀이다. 모두 같은 방식으로 처리하되, 원본의
색상 계열과 bank113의 블루/레드/VS 색상은 별도 설정으로 보존한다.
"""
import sys, io, os, argparse, struct

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tex_lib as TX
from PIL import Image, ImageFont, ImageDraw
from PIL import ImageChops

BASE = os.path.join(HERE, "..", "files")
PATCHED = os.path.join(HERE, "..", "text_patch_work", "patched_files")
FONT = os.path.join(HERE, "..", "fonts", "NanumSquareNeocBd.ttf")
OUT_DIR = os.path.join(HERE, "out")

ap = argparse.ArgumentParser()
ap.add_argument("--apply", action="store_true")
ap.add_argument("--preview", action="store_true")
args = ap.parse_args()

WHITE = (255, 255, 255, 255)
BLACK = (38, 38, 38, 255)
LAYOUT_STROKE = 3


def pair(c4, cmp, text, color, segments=None):
    return {
        "c4": c4,
        "cmp": cmp,
        "text": text,
        "color": color,
        "segments": segments,
    }


# C4 offset, CMP/CMPR offset, and the phrase shown by both layers.
# bank102's last seven offsets were previously shifted by one entry in v2.16;
# keep this table in visual order as verified against the original composites.
RESOURCES = {
    "Info/arc/bank102.arc": [
        pair(0x309A0, 0x2D760, "모드 선택", (166, 151, 47, 255)),
        pair(0x36E40, 0x33C00, "싱글 플레이", (10, 150, 125, 255)),
        pair(0x3D2E0, 0x3A0A0, "멀티 플레이", (230, 135, 35, 255)),
        pair(0x43780, 0x40540, "옵션", (142, 92, 176, 255)),
        pair(0x4A3A0, 0x469E0, "시나리오 게임", (20, 150, 125, 255)),
        pair(0x51740, 0x4DD80, "캡슐 워즈", (35, 198, 160, 255)),
        pair(0x58AE0, 0x55120, "100문 배틀", (35, 198, 160, 255)),
        pair(0x5FE80, 0x5C4C0, "맵 대전", (240, 180, 55, 255)),
        pair(0x67220, 0x63860, "액션 대전", (225, 185, 55, 255)),
        pair(0x6E5C0, 0x6AC00, "서바이벌", (235, 125, 155, 255)),
        pair(0x75960, 0x71FA0, "캡슐 편집", (195, 105, 225, 255)),
        pair(0x7CD00, 0x79340, "갤러리", (195, 105, 225, 255)),
        pair(0x840A0, 0x806E0, "도움말", (210, 185, 55, 255)),
        pair(0x8B440, 0x87A80, "사운드 플레이어", (237, 128, 150, 255)),
        pair(0x927E0, 0x8EE20, "진동", (170, 90, 210, 255)),
        pair(0x99B80, 0x961C0, "사운드 설정", (80, 140, 210, 255)),
        pair(0xA0F20, 0x9D560, "메모리 카드", (145, 105, 190, 255)),
    ],
    "Info/arc/bank108.arc": [
        pair(0x14B40, 0x11180, "캡슐 워즈", (35, 198, 160, 255)),
        pair(0x1BEE0, 0x18520, "100문 배틀", (35, 198, 160, 255)),
        pair(0x23280, 0x1F8C0, "맵 대전", (100, 180, 230, 255)),
        pair(0x2A620, 0x26C60, "액션 대전", (240, 230, 75, 255)),
        pair(0x319C0, 0x2E000, "서바이벌", (245, 120, 160, 255)),
        pair(0x38D60, 0x353A0, "캡슐 편집", (205, 100, 230, 255)),
    ],
    "Info/arc/bank113.arc": [
        pair(
            0x52F00,
            0x4FCC0,
            "블루사이드 VS 레드사이드",
            (72, 174, 238, 255),
            segments=[
                ("블루사이드 ", (72, 174, 238, 255)),
                ("VS", (245, 196, 42, 255)),
                (" 레드사이드", (246, 102, 118, 255)),
            ],
        ),
        pair(0x593A0, 0x56160, "배틀 로얄", (248, 205, 56, 255)),
    ],
}


def read_base(rel):
    # bank102에는 60_label_inject.py의 소형 헤더 패치가 먼저 들어간다.
    # 다른 리소스도 반복 실행 시에는 직전 결과를 읽되, 타이틀은 항상 같은
    # layout으로 다시 렌더링하므로 누적 오차가 생기지 않는다.
    patched = os.path.join(PATCHED, rel)
    if os.path.exists(patched):
        with open(patched, "rb") as f:
            return f.read()
    with open(os.path.join(BASE, rel), "rb") as f:
        return f.read()


def cmp_header(data, off):
    """CMP/CMPR 블록의 예외적인 이미지 위치를 읽는다.

    이 프로젝트의 palcnt=1 CMP 블록은 일반 @Texture 파서처럼 +0x42가
    아니라 헤더 직후 +0x40부터 CMPR raw가 시작한다.
    """
    fmt = struct.unpack_from(">I", data, off + 0x08)[0]
    w = struct.unpack_from(">I", data, off + 0x10)[0]
    h = struct.unpack_from(">I", data, off + 0x14)[0]
    imgsize = struct.unpack_from(">I", data, off + 0x38)[0]
    if fmt != 0x0E:
        raise ValueError("CMP 블록이 아닙니다: 0x%X (format=0x%X)" % (off, fmt))
    return {"w": w, "h": h, "imgsize": imgsize, "img_off": off + 0x40}


def make_layout(text, w, h):
    """두 레이어가 공유할 font/position을 계산한다."""
    probe = ImageDraw.Draw(Image.new("L", (1, 1)))
    for size in range(min(h, 96), 6, -1):
        font = ImageFont.truetype(FONT, size)
        bb = probe.textbbox((0, 0), text, font=font, stroke_width=LAYOUT_STROKE)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
        if tw <= w - 10 and th <= h - 4:
            x = (w - tw) // 2 - bb[0]
            y = (h - th) // 2 - bb[1]
            return font, (x, y), size, (tw, th)
    raise ValueError("타이틀이 캔버스에 들어가지 않습니다: %s (%dx%d)" % (text, w, h))


def draw_white(text, w, h, layout):
    """C4 하이라이트/실루엣 레이어."""
    font, pos, _, _ = layout
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(img).text(
        pos,
        text,
        font=font,
        fill=WHITE,
        stroke_width=LAYOUT_STROKE,
        stroke_fill=WHITE,
    )
    return img


def draw_cmp(text, w, h, color, layout, segments=None):
    """CMP 색상 레이어. C4와 같은 font/position을 반드시 사용한다."""
    font, pos, _, _ = layout
    img = Image.new("RGBA", (w, h), WHITE)
    d = ImageDraw.Draw(img)
    if not segments:
        d.text(pos, text, font=font, fill=color, stroke_width=LAYOUT_STROKE,
               stroke_fill=BLACK)
        return img

    # segment를 각각 text()로 그리면 경계의 kerning/advance가 달라져
    # C4 하이라이트와 색상 레이어의 글자 위치가 미세하게 어긋날 수 있다.
    # 전체 문장을 한 번만 래스터화하고, 글자 내부만 색상별로 잘라 칠한다.
    d.text(pos, text, font=font, fill=BLACK, stroke_width=LAYOUT_STROKE,
           stroke_fill=BLACK)
    fill_mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(fill_mask).text(pos, text, font=font, fill=255)
    prefix = ""
    for segment, segment_color in segments:
        start = pos[0] + d.textlength(prefix, font=font)
        end = start + d.textlength(segment, font=font)
        band = Image.new("L", img.size, 0)
        ImageDraw.Draw(band).rectangle(
            (int(start), 0, int(end), img.height), fill=255)
        mask = ImageChops.multiply(fill_mask, band)
        img.paste(Image.new("RGBA", img.size, segment_color), (0, 0), mask)
        prefix += segment
    return img


def paste_on_bg(dst, img, xy):
    bg = Image.new("RGB", img.size, (62, 62, 72))
    bg.paste(img, (0, 0), img)
    dst.paste(bg, xy)


def make_preview(rel, preview_rows):
    """C4/CMP 두 레이어를 같은 행에 나란히 놓은 검수용 PNG."""
    if not preview_rows:
        return None
    gap = 18
    label_h = 22
    cell_w = max(max(row[1].width, row[2].width) for row in preview_rows)
    row_h = max(max(r[1].height, r[2].height) for r in preview_rows) + label_h + 8
    width = cell_w * 2 + gap * 3
    height = row_h * len(preview_rows) + 12
    sheet = Image.new("RGB", (width, height), (30, 30, 38))
    d = ImageDraw.Draw(sheet)
    caption_font = ImageFont.truetype(FONT, 13)
    for i, (title, c4_img, cmp_img) in enumerate(preview_rows):
        y = 6 + i * row_h
        d.text((gap, y), "%s  C4 하이라이트" % title,
               font=caption_font, fill=(255, 255, 100))
        d.text((gap * 2 + cell_w, y), "%s  CMP 색상" % title,
               font=caption_font, fill=(255, 255, 100))
        paste_on_bg(sheet, c4_img, (gap, y + label_h))
        paste_on_bg(sheet, cmp_img, (gap * 2 + cell_w, y + label_h))
    os.makedirs(OUT_DIR, exist_ok=True)
    names = {
        "Info/arc/bank102.arc": "menu_titles_preview.png",
        "Info/arc/bank108.arc": "bank108_menu_titles_preview.png",
        "Info/arc/bank113.arc": "bank113_battle_titles_preview.png",
    }
    path = os.path.join(OUT_DIR, names[rel])
    sheet.save(path)
    return path


all_preview = []

for rel, pairs in RESOURCES.items():
    b = read_base(rel)
    patches = []
    preview_rows = []
    for p in pairs:
        c4 = TX.parse_header(b, p["c4"])
        c4_fmt = struct.unpack_from(">I", b, p["c4"] + 0x08)[0]
        if c4_fmt != 0x08:
            raise ValueError("C4 블록이 아닙니다: %s 0x%X (format=0x%X)" %
                             (rel, p["c4"], c4_fmt))
        cmp = cmp_header(b, p["cmp"])
        if (c4["w"], c4["h"]) != (cmp["w"], cmp["h"]):
            raise ValueError("C4/CMP 캔버스 불일치: %s 0x%X / 0x%X" %
                             (rel, p["c4"], p["cmp"]))

        layout = make_layout(p["text"], c4["w"], c4["h"])
        c4_img = draw_white(p["text"], c4["w"], c4["h"], layout)
        cmp_img = draw_cmp(p["text"], cmp["w"], cmp["h"], p["color"], layout,
                           p["segments"])
        c4_raw = TX.encode_c4(c4_img, TX.read_palette(b, c4["pal_off"], c4["palcnt"]),
                              c4["w"], c4["h"])
        cmp_raw = TX.encode_cmp(cmp_img, cmp["w"], cmp["h"])
        if len(c4_raw) != c4["imgsize"] or len(cmp_raw) != cmp["imgsize"]:
            raise ValueError("인코딩 크기 불일치: %s 0x%X/0x%X" %
                             (rel, p["c4"], p["cmp"]))
        patches.append((c4["img_off"], c4["imgsize"], c4_raw))
        patches.append((cmp["img_off"], cmp["imgsize"], cmp_raw))
        preview_rows.append(("0x%X" % p["c4"], c4_img, cmp_img))
        all_preview.append((rel, p["c4"], p["text"], c4_img, cmp_img))

    if args.preview:
        path = make_preview(rel, preview_rows)
        print("preview saved:", path, "pairs:", len(preview_rows))

    if args.apply:
        bb = bytearray(b)
        for off, size, raw in patches:
            if len(raw) != size:
                raise AssertionError((rel, hex(off), len(raw), size))
            bb[off:off + size] = raw
        dst = os.path.join(PATCHED, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, "wb") as f:
            f.write(bb)
        if os.path.getsize(dst) != len(b):
            raise AssertionError("파일 크기 변경: %s" % rel)
        print("APPLIED", rel, "C4/CMP pairs:", len(pairs))

if args.preview and all_preview:
    # release note에 한 장으로 전체 처리 범위를 확인할 수 있는 합본도 남긴다.
    rows = [("%s 0x%X %s" % (rel.rsplit('/', 1)[-1], off, text), c4, cmp)
            for rel, off, text, c4, cmp in all_preview]
    gap = 18
    label_h = 22
    cell_w = max(max(r[1].width, r[2].width) for r in rows)
    row_h = max(max(r[1].height, r[2].height) for r in rows) + label_h + 8
    sheet = Image.new("RGB", (cell_w * 2 + gap * 3, row_h * len(rows) + 12), (30, 30, 38))
    d = ImageDraw.Draw(sheet)
    caption_font = ImageFont.truetype(FONT, 13)
    for i, (title, c4_img, cmp_img) in enumerate(rows):
        y = 6 + i * row_h
        d.text((gap, y), title + "  C4", font=caption_font, fill=(255, 255, 100))
        d.text((gap * 2 + cell_w, y), title + "  CMP",
               font=caption_font, fill=(255, 255, 100))
        paste_on_bg(sheet, c4_img, (gap, y + label_h))
        paste_on_bg(sheet, cmp_img, (gap * 2 + cell_w, y + label_h))
    path = os.path.join(OUT_DIR, "menu_titles_all_layers_preview.png")
    sheet.save(path)
    print("preview saved:", path, "pairs:", len(rows))

print("total title pairs:", sum(len(v) for v in RESOURCES.values()))
