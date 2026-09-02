# -*- coding: utf-8 -*-
"""중첩 U8/HSD 메뉴 이미지의 한글 재작화.

Issue #14의 대전 방식 선택 화면은 일반 ``@Texture`` 블록이 아니라
``Info/arc/bank113.arc/scen/usel_mode.dat`` 안에 들어 있는 HSD 이미지다.
각 문구는 C4 하이라이트와 CMP/CI8 색상 이미지가 겹쳐지는 구조이므로,
두 레이어에 반드시 같은 TextLayout을 사용한다. 원본 HSD/U8 컨테이너의
파일 크기와 오프셋은 유지하고, 이미지 버퍼만 같은 길이로 교체한다.

같은 방식으로 캡슐 편집기의 중첩 메뉴 제목(ce_menu_title.dat)도 처리한다.
이 파일은 HSDLib로 원본 구조를 확인한 뒤 이미지 버퍼 오프셋을 고정해
재현 가능하게 패치한다. 빌드에는 HSDLib 런타임이 필요하지 않다.
"""
import argparse
import hashlib
import io
import os
import struct
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tex_lib as TX
from PIL import Image, ImageDraw, ImageFont
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
BLACK = (20, 20, 24, 255)
PROMPT_GOLD = (232, 170, 42, 255)
LAYOUT_STROKE = 3
MODE_TEXT_BOTTOM = 37
SECONDARY_FONT_SIZE = 10
SECONDARY_STROKE = 1


def u32(data, off):
    return struct.unpack_from(">I", data, off)[0]


def u16(data, off):
    return struct.unpack_from(">H", data, off)[0]


def u8_entries(data):
    """Nintendo U8 파일 시스템의 파일 경로/오프셋/크기 목록을 반환한다."""
    if u32(data, 0) != 0x55AA382D:
        raise ValueError("Nintendo U8 매직이 아닙니다")
    root = u32(data, 4)
    count = u32(data, root + 8)
    string_base = root + count * 12
    out = []
    stack = []
    for i in range(1, count):
        node = root + i * 12
        raw_name = u32(data, node)
        kind = raw_name >> 24
        name_off = raw_name & 0xFFFFFF
        end = data.index(b"\0", string_base + name_off)
        name = data[string_base + name_off:end].decode("cp932", "replace")
        a = u32(data, node + 4)
        c = u32(data, node + 8)
        while stack and i >= stack[-1][1]:
            stack.pop()
        if kind == 1:
            stack.append((name, c))
        else:
            out.append(("/".join(x[0] for x in stack + [(name, c)]), a, c))
    return out


def get_u8_entry(data, wanted):
    for name, off, size in u8_entries(data):
        if name == wanted:
            return off, size
    raise KeyError("U8 내부 파일을 찾지 못했습니다: %s" % wanted)


def read_file(rel, prefer_patched=False):
    path = os.path.join(PATCHED if prefer_patched else BASE, rel)
    if not os.path.exists(path) and prefer_patched:
        path = os.path.join(BASE, rel)
    with open(path, "rb") as f:
        return f.read()


def palette(data, off, count):
    return [TX.rgb5a3(u16(data, off + i * 2)) for i in range(count)]


def make_layout(text, w, h, top=0, bottom=None, stroke=LAYOUT_STROKE):
    """두 레이어가 공유할 글꼴, 원점, 바운딩을 계산한다."""
    if bottom is None:
        bottom = h
    probe = ImageDraw.Draw(Image.new("L", (1, 1)))
    target_h = bottom - top
    for size in range(min(target_h, 96), 5, -1):
        font = ImageFont.truetype(FONT, size)
        bb = probe.textbbox((0, 0), text, font=font, stroke_width=stroke)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
        if tw <= w - 8 and th <= target_h:
            x = (w - tw) // 2 - bb[0]
            y = top + (target_h - th) // 2 - bb[1]
            return font, (x, y), size, (tw, th)
    raise ValueError("타이틀이 캔버스에 들어가지 않습니다: %s (%dx%d)" %
                     (text, w, h))


def draw_segments(img, text, layout, color, segments=None, stroke=LAYOUT_STROKE):
    font, pos, _, _ = layout
    d = ImageDraw.Draw(img)
    if not segments:
        d.text(pos, text, font=font, fill=color, stroke_width=stroke,
               stroke_fill=BLACK)
        return

    # 전체 문장을 한 번만 래스터화한다. segment를 각각 text()로 그리면
    # 경계의 kerning/advance가 달라져 C4 하이라이트와 색상 레이어의
    # 글자 위치가 미세하게 어긋날 수 있다.
    d.text(pos, text, font=font, fill=BLACK, stroke_width=stroke,
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


def draw_mask(text, w, h, layout):
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    font, pos, _, _ = layout
    ImageDraw.Draw(img).text(pos, text, font=font, fill=WHITE,
                             stroke_width=LAYOUT_STROKE, stroke_fill=WHITE)
    return img


def draw_cmp_prompt(text, w, h, layout):
    img = Image.new("RGBA", (w, h), WHITE)
    draw_segments(img, text, layout, PROMPT_GOLD, stroke=LAYOUT_STROKE)
    return img


def draw_secondary(img, segments, y):
    """영문 보조 라인을 깨끗하게 다시 그린다.

    일본어 대형 제목과 영문 라인이 한 CI8 이미지에서 겹쳐 있어 원본
    하단을 잘라 붙이면 일본어 획의 잔상이 남는다. 영문은 의미를
    보존하면서 별도 라인으로 재작성해 잔상을 원천적으로 제거한다.
    """
    font = ImageFont.truetype(FONT, SECONDARY_FONT_SIZE)
    d = ImageDraw.Draw(img)
    total = sum(d.textlength(text, font=font) for text, _ in segments)
    x = (img.width - total) / 2
    for text, color in segments:
        d.text((x, y), text, font=font, fill=color,
               stroke_width=SECONDARY_STROKE, stroke_fill=BLACK)
        x += d.textlength(text, font=font)


def draw_mode_color(text, w, h, layout, color, segments, secondary):
    """일본어 대형 제목과 잔상을 지우고 한국어/영문을 다시 그린다."""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw_segments(img, text, layout, color, segments=segments)
    draw_secondary(img, secondary, MODE_TEXT_BOTTOM)
    return img


def encode_hsd(img, spec, data):
    if spec["fmt"] == 8:
        pal = palette(data, spec["pal_off"], spec["pal_count"])
        raw = TX.encode_c4(img, pal, spec["w"], spec["h"])
    elif spec["fmt"] == 9:
        pal = palette(data, spec["pal_off"], spec["pal_count"])
        raw = TX.encode_c8(img, pal, spec["w"], spec["h"])
    elif spec["fmt"] == 14:
        raw = TX.encode_cmp(img, spec["w"], spec["h"])
    else:
        raise ValueError("지원하지 않는 HSD 이미지 포맷: %s" % spec["fmt"])
    if len(raw) != spec["size"]:
        raise ValueError("HSD 이미지 크기 불일치: %s != %s" %
                         (hex(len(raw)), hex(spec["size"])))
    return raw


def validate_spec(data, spec):
    if spec.get("struct_off") is not None:
        w = u16(data, spec["struct_off"] + 4)
        h = u16(data, spec["struct_off"] + 6)
        fmt = u32(data, spec["struct_off"] + 8)
        if (w, h, fmt) != (spec["w"], spec["h"], spec["fmt"]):
            raise ValueError("HSD 구조 변경: %s, 실제 %sx%s/f%s" %
                             (hex(spec["struct_off"]), w, h, fmt))
    if spec["img_off"] < 0 or spec["img_off"] + spec["size"] > len(data):
        raise ValueError("HSD 이미지 버퍼가 파일 밖입니다: %s" % hex(spec["img_off"]))
    if spec.get("sha256"):
        actual = hashlib.sha256(data[spec["img_off"]:spec["img_off"] + spec["size"]]).hexdigest()
        if actual != spec["sha256"]:
            raise ValueError("원본 이미지 버퍼가 예상과 다릅니다: %s" % hex(spec["img_off"]))
    if "pal_off" in spec:
        pal_bytes = spec["pal_count"] * 2
        if len(data[spec["pal_off"]:spec["pal_off"] + pal_bytes]) != pal_bytes:
            raise ValueError("HSD 팔레트 버퍼가 파일 밖입니다: %s" % hex(spec["pal_off"]))


def spec(struct_off, img_off, w, h, fmt, pal_off=None, pal_count=None):
    out = {"struct_off": struct_off, "img_off": img_off, "w": w,
           "h": h, "fmt": fmt, "size": (
               TX.cmp_size(w, h) if fmt == 14 else (
                   ((w + 7) // 8 * 8) * ((h + 7) // 8 * 8) // 2
                   if fmt == 8 else
                   ((w + 7) // 8 * 8) * ((h + 3) // 4 * 4)
               )
           )}
    if pal_off is not None:
        out["pal_off"] = pal_off
        out["pal_count"] = pal_count
    return out


def raw_spec(img_off, w, h, fmt, pal_off=None, pal_count=None, sha256=None):
    """HSD 이미지 구조체 없이 공유되는 제자리 raw 버퍼 사양."""
    out = spec(None, img_off, w, h, fmt, pal_off, pal_count)
    if sha256:
        out["sha256"] = sha256
    return out


# Offsets were read from the original HSD relocation graph and are validated
# against width/height/format before any bytes are written.
NESTED = {
    "Info/arc/bank113.arc": {
        "entry": "scen/usel_mode.dat",
        "pairs": [
            {"name": "대전 형식을 선택하세요",
             "mask": spec(0x2C30, 0x620E0, 424, 76, 8, 0x7D0C0, 8),
             "color": spec(0x2BBC, 0x5DEA0, 424, 76, 14),
             "kind": "prompt"},
            {"name": "필드를 선택하세요",
             "mask": spec(0x2D50, 0x6A1A0, 400, 74, 8, 0x7D100, 8),
             "color": spec(0x2CDC, 0x66320, 400, 74, 14),
             "kind": "prompt"},
            {"name": "배틀 로얄",
             "mask": spec(0x3158, 0x6E260, 286, 50, 8, 0x7D180, 8),
             "color": spec(0x3204, 0x701E0, 286, 50, 9, 0x7D1C0, 183),
             "kind": "mode", "color_value": (232, 184, 50, 255),
             "secondary": [("BATTLE ROYAL", (222, 238, 246, 255))]},
            {"name": "블루사이드 VS 레드사이드",
             "mask": spec(0x335C, 0x73E60, 286, 50, 8, 0x7D3A0, 8),
             "color": spec(0x3408, 0x75DE0, 286, 50, 9, 0x7D3E0, 220),
             "kind": "mode", "color_value": (72, 174, 238, 255),
             "segments": [
                 ("블루사이드 ", (72, 174, 238, 255)),
                 ("VS", (245, 196, 42, 255)),
                 (" 레드사이드", (246, 102, 118, 255)),
             ],
             "secondary": [
                 ("BLUE SIDE ", (255, 246, 184, 255)),
                 ("VS", (35, 184, 232, 255)),
                 (" RED SIDE", (198, 198, 255, 255)),
             ]},
        ],
    },
    "Info/arc/bank101.arc": {
        "entry": "scen/ce_menu_title.dat",
        "singles": [
            {"name": "캡슐 박스 편집",
             "image": spec(0x214, 0x920, 184, 26, 8, 0x1520, 16),
             "kind": "single"},
        ],
    },
}

# usel_base.dat에도 같은 대전 방식 안내 이미지가 공유 데이터로 한 벌
# 존재한다. 이 영역은 별도 HSD 이미지 구조체가 아니라 공통 raw 버퍼로
# 참조되므로, 원본 SHA-256과 크기를 함께 검증하고 두 레이어를 같이
# 교체한다. 이 버퍼를 빼먹으면 일부 진입 경로에서 일본어 안내가 남는다.
RAW_NESTED = {
    "Info/arc/bank113.arc": {
        "entry": "scen/usel_base.dat",
        "pairs": [
            {"name": "대전 형식을 선택하세요",
             "mask": raw_spec(
                 0x64E0, 424, 76, 8, 0xD040, 16,
                 "385418126ae0c6847c3b0c2fab7a67cafec5a88f13e01249c33f6b8c7254be00"),
             "color": raw_spec(
                 0x22A0, 424, 76, 14, None, None,
                 "40c852973b4bb09c17fb7eefc3be014fdd29dcd9b2f4c078c706b6afedcdbedb"),
             "kind": "prompt"},
        ],
    },
}


def process_pair(source_hsd, work_hsd, pair):
    mask = pair["mask"]
    color = pair["color"]
    validate_spec(source_hsd, mask)
    validate_spec(source_hsd, color)
    if (mask["w"], mask["h"]) != (color["w"], color["h"]):
        raise ValueError("중첩 레이어 캔버스 불일치: %s" % pair["name"])
    if pair["kind"] == "mode":
        layout = make_layout(pair["name"], mask["w"], mask["h"],
                             0, MODE_TEXT_BOTTOM)
        mask_img = draw_mask(pair["name"], mask["w"], mask["h"], layout)
        color_img = draw_mode_color(
            pair["name"], color["w"], color["h"], layout,
            pair["color_value"], pair.get("segments"), pair["secondary"])
    else:
        layout = make_layout(pair["name"], mask["w"], mask["h"])
        mask_img = draw_mask(pair["name"], mask["w"], mask["h"], layout)
        color_img = draw_cmp_prompt(pair["name"], color["w"], color["h"], layout)
    mask_raw = encode_hsd(mask_img, mask, source_hsd)
    color_raw = encode_hsd(color_img, color, source_hsd)
    if args.apply:
        work_hsd[mask["img_off"]:mask["img_off"] + mask["size"]] = mask_raw
        work_hsd[color["img_off"]:color["img_off"] + color["size"]] = color_raw
    composite = Image.alpha_composite(mask_img, color_img)
    return mask_img, color_img, composite


def process_single(source_hsd, work_hsd, item):
    image = item["image"]
    validate_spec(source_hsd, image)
    layout = make_layout(item["name"], image["w"], image["h"], stroke=1)
    img = Image.new("RGBA", (image["w"], image["h"]), (0, 0, 0, 0))
    font, pos, _, _ = layout
    ImageDraw.Draw(img).text(pos, item["name"], font=font,
                             fill=(74, 74, 74, 255), stroke_width=1,
                             stroke_fill=(74, 74, 74, 255))
    raw = encode_hsd(img, image, source_hsd)
    if args.apply:
        work_hsd[image["img_off"]:image["img_off"] + image["size"]] = raw
    return img


def preview_cell(sheet, img, x, y, width, label, caption_font):
    bg = Image.new("RGB", img.size, (52, 52, 62))
    bg.paste(img, (0, 0), img)
    sheet.paste(bg, (x, y + 22))
    ImageDraw.Draw(sheet).text((x, y), label, font=caption_font,
                               fill=(255, 255, 100))


def save_preview(rows, filename):
    if not rows:
        return None
    gap = 18
    label_h = 22
    caption_font = ImageFont.truetype(FONT, 13)
    cell_w = max(max(img.width for img in imgs) for _, imgs in rows)
    row_h = max(max(img.height for img in imgs) for _, imgs in rows) + label_h + 8
    sheet = Image.new("RGB", (cell_w * 3 + gap * 4, row_h * len(rows) + 12),
                      (30, 30, 38))
    for i, (label, imgs) in enumerate(rows):
        y = 6 + i * row_h
        labels = ["C4/CI4 하이라이트", "색상 레이어", "겹침 결과"]
        for j, img in enumerate(imgs):
            preview_cell(sheet, img, gap + j * (cell_w + gap), y, cell_w,
                         "%s  %s" % (label, labels[j]), caption_font)
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, filename)
    sheet.save(path)
    return path


all_rows = []
single_rows = []

for rel, group in list(NESTED.items()) + list(RAW_NESTED.items()):
    source_container = read_file(rel, prefer_patched=False)
    work_container = bytearray(read_file(rel, prefer_patched=True))
    entry_path = group["entry"]
    source_off, source_size = get_u8_entry(source_container, entry_path)
    work_off, work_size = get_u8_entry(work_container, entry_path)
    if source_size != work_size:
        raise ValueError("U8 내부 파일 크기가 변경됨: %s" % entry_path)
    source_hsd = source_container[source_off:source_off + source_size]
    work_hsd = bytearray(work_container[work_off:work_off + work_size])
    if len(source_hsd) != source_size or len(work_hsd) != work_size:
        raise ValueError("U8 내부 HSD 범위가 잘못됨: %s" % entry_path)

    rows = []
    for pair in group.get("pairs", []):
        mask_img, color_img, composite = process_pair(source_hsd, work_hsd, pair)
        rows.append((pair["name"], [mask_img, color_img, composite]))
        all_rows.append((pair["name"], [mask_img, color_img, composite]))
    for item in group.get("singles", []):
        single_rows.append((item["name"], process_single(source_hsd, work_hsd, item)))

    if args.apply:
        work_container[work_off:work_off + work_size] = work_hsd
        dst = os.path.join(PATCHED, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, "wb") as f:
            f.write(work_container)
        if os.path.getsize(dst) != len(work_container):
            raise AssertionError("U8 컨테이너 크기 변경: %s" % rel)
        print("APPLIED", rel, entry_path,
              "pairs:", len(group.get("pairs", [])),
              "singles:", len(group.get("singles", [])))

if args.preview:
    path = save_preview(all_rows, "nested_menu_titles_preview.png")
    print("preview saved:", path, "pairs:", len(all_rows))
    if single_rows:
        gap = 18
        caption_font = ImageFont.truetype(FONT, 13)
        cell_w = max(img.width for _, img in single_rows)
        cell_h = max(img.height for _, img in single_rows)
        sheet = Image.new("RGB", (cell_w + gap * 2, cell_h + 38), (30, 30, 38))
        for i, (label, img) in enumerate(single_rows):
            preview_cell(sheet, img, gap, 6, cell_w, label, caption_font)
        path = os.path.join(OUT_DIR, "nested_capsule_menu_title_preview.png")
        sheet.save(path)
        print("preview saved:", path, "singles:", len(single_rows))

print("nested menu title pairs:", len(all_rows), "singles:", len(single_rows))
