# -*- coding: utf-8 -*-
"""중복 HSD UI 이미지(메뉴 헤더·로고·대형 제목)를 한글로 재작화한다.

Issue #18에서 확인된 화면은 일반 ``@Texture`` 뱅크만으로 완성되지 않는다.
모드 선택/캡슐 워즈/사운드 플레이어가 각각 ``Info/arc`` 안의 HSD 장면에
같은 종류의 제목을 하나씩 더 보관하고 있으며, 사운드 플레이어의 로고는
모드 선택 장면의 188x80 CI8 이미지로 공유된다.

이 스크립트는 HSD/U8 컨테이너의 구조체·팔레트·파일 크기를 유지하고,
검증된 raw 이미지 버퍼만 교체한다. 두 레이어로 겹쳐 그리는 gtitle은
하나의 TextLayout을 공유하므로 C4 하이라이트와 CMP 색상 레이어의
위치/크기가 항상 일치한다.

사용:
  python 77_nested_ui_assets.py --preview
  python 77_nested_ui_assets.py --apply
"""
import argparse
import hashlib
import io
import os
import struct
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, "..", "files")
PATCHED = os.path.join(HERE, "..", "text_patch_work", "patched_files")
FONT = os.path.join(HERE, "..", "fonts", "NanumSquareNeocBd.ttf")
OUT_DIR = os.path.join(HERE, "out")

sys.path.insert(0, HERE)
import tex_lib as TX
from PIL import Image, ImageDraw, ImageFont

ap = argparse.ArgumentParser()
ap.add_argument("--apply", action="store_true", help="patched_files에 바이너리 패치 저장")
ap.add_argument("--preview", action="store_true", help="재작화 결과 PNG 저장")
args = ap.parse_args()

WHITE = (255, 255, 255, 255)
BLACK = (25, 25, 31, 255)
LOGO_RED = (226, 39, 49, 255)
LOGO_BLUE = (42, 122, 221, 255)
LOGO_GOLD = (244, 193, 54, 255)
TITLE_GREEN = (182, 231, 66, 255)
TITLE_BLUE = (78, 170, 239, 255)
TITLE_PINK = (235, 111, 175, 255)
STROKE = 3


def u32(data, off):
    return struct.unpack_from(">I", data, off)[0]


def u16(data, off):
    return struct.unpack_from(">H", data, off)[0]


def u8_entries(data):
    """Nintendo U8 파일 시스템의 파일 경로/오프셋/크기 목록."""
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


def palette(data, off, count):
    return [TX.rgb5a3(u16(data, off + i * 2)) for i in range(count)]


def spec(struct_off, img_off, w, h, fmt, pal_off=None, pal_count=None, sha256=None):
    if fmt == 8:  # CI4: GameCube 8x8 tile
        size = ((w + 7) // 8 * 8) * ((h + 7) // 8 * 8) // 2
    elif fmt == 9:  # CI8: GameCube 8x4 tile
        size = ((w + 7) // 8 * 8) * ((h + 3) // 4 * 4)
    elif fmt == 14:  # CMP/CMPR
        size = TX.cmp_size(w, h)
    else:
        raise ValueError("지원하지 않는 HSD 포맷: %s" % fmt)
    out = {
        "struct_off": struct_off,
        "img_off": img_off,
        "w": w,
        "h": h,
        "fmt": fmt,
        "size": size,
    }
    if pal_off is not None:
        out["pal_off"] = pal_off
        out["pal_count"] = pal_count
    if sha256:
        out["sha256"] = sha256
    return out


def validate(data, item):
    if item.get("struct_off") is not None:
        off = item["struct_off"]
        actual = (u16(data, off + 4), u16(data, off + 6), u32(data, off + 8))
        expected = (item["w"], item["h"], item["fmt"])
        if actual != expected:
            raise ValueError("HSD 구조 변경: %s 실제=%s 예상=%s" %
                             (hex(off), actual, expected))
    off = item["img_off"]
    end = off + item["size"]
    if off < 0 or end > len(data):
        raise ValueError("HSD 이미지 버퍼가 파일 밖입니다: %s" % hex(off))
    if item.get("sha256"):
        actual = hashlib.sha256(data[off:end]).hexdigest()
        if actual != item["sha256"]:
            raise ValueError("원본 HSD 이미지 버퍼가 예상과 다릅니다: %s" % hex(off))
    if "pal_off" in item:
        pal_end = item["pal_off"] + item["pal_count"] * 2
        if pal_end > len(data):
            raise ValueError("HSD 팔레트 버퍼가 파일 밖입니다: %s" % hex(item["pal_off"]))


def encode(data, image, item):
    if item["fmt"] == 8:
        raw = TX.encode_c4(image, palette(data, item["pal_off"], item["pal_count"]),
                           item["w"], item["h"])
    elif item["fmt"] == 9:
        raw = TX.encode_c8(image, palette(data, item["pal_off"], item["pal_count"]),
                           item["w"], item["h"])
    elif item["fmt"] == 14:
        raw = TX.encode_cmp(image, item["w"], item["h"])
    else:
        raise ValueError("지원하지 않는 HSD 포맷: %s" % item["fmt"])
    if len(raw) != item["size"]:
        raise ValueError("HSD raw 크기 불일치: %s != %s" %
                         (hex(len(raw)), hex(item["size"])))
    return raw


def make_layout(text, w, h, top=0, bottom=None, stroke=STROKE):
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
            return font, (x, y)
    raise ValueError("텍스트가 HSD 캔버스에 들어가지 않습니다: %s (%dx%d)" %
                     (text, w, h))


def draw_text(img, text, top, bottom, fill=WHITE, stroke=2):
    font, pos = make_layout(text, img.width, img.height, top, bottom, stroke)
    ImageDraw.Draw(img).text(pos, text, font=font, fill=fill,
                             stroke_width=stroke, stroke_fill=BLACK)


def draw_header(korean, english, w, h):
    """기존 일본어/영문 2행 헤더를 한글/영문 2행으로 통째로 재작화."""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw_text(img, korean, 0, h // 2, WHITE, stroke=2)
    draw_text(img, english, h // 2 - 1, h, WHITE, stroke=1)
    return img


def draw_logo(w=188, h=80):
    """모드/사운드 플레이어가 공유하는 188x80 게임 로고."""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    def layer(text, top, bottom, fill, outer, inner):
        font, pos = make_layout(text, w, h, top, bottom, outer)
        d.text(pos, text, font=font, fill=fill,
               stroke_width=outer, stroke_fill=WHITE)
        d.text(pos, text, font=font, fill=fill,
               stroke_width=inner, stroke_fill=(26, 42, 112, 255))

    layer("SD 건담", 0, 23, LOGO_BLUE, 2, 1)
    layer("가샤폰 워즈", 17, 62, LOGO_RED, 3, 2)
    layer("GASHAPONWARS", 59, 80, LOGO_GOLD, 1, 0)
    return img


def draw_title_pair(text, w, h, color):
    """gtitle HSD의 C4 하이라이트와 CMP 색상 레이어."""
    layout = make_layout(text, w, h, stroke=STROKE)
    font, pos = layout
    mask = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(mask).text(pos, text, font=font, fill=WHITE,
                              stroke_width=STROKE, stroke_fill=WHITE)
    color_img = Image.new("RGBA", (w, h), WHITE)
    ImageDraw.Draw(color_img).text(pos, text, font=font, fill=color,
                                   stroke_width=STROKE, stroke_fill=BLACK)
    return mask, color_img, Image.alpha_composite(mask, color_img)


ASSETS = [
    {
        "rel": "Info/arc/bank102.arc",
        "entry": "scen/msel_base.dat",
        "name": "모드 선택 헤더(중복 HSD)",
        "kind": "header",
        "ko": "모드 선택",
        "en": "MODE SELECT",
        "image": spec(0xF44, 0x12380, 160, 52, 8, 0x13AA0, 16,
                       "54f593add519fc45523e577925acfdcf20626b2978ba13595db37537b63eefee"),
    },
    {
        "rel": "Info/arc/bank102.arc",
        "entry": "scen/msel_base.dat",
        "name": "공유 게임 로고(모드/사운드 플레이어)",
        "kind": "logo",
        "image": spec(0x2A4, 0xA2E0, 188, 80, 9, 0x13500, 256,
                       "1e2d6930b296bd972524d19c746e1cc96689ebdbf96b95d2a7a41302c0a68997"),
    },
    {
        "rel": "Info/arc/bank108.arc",
        "entry": "scen/cap_base.dat",
        "name": "캡슐 워즈 헤더(중복 HSD)",
        "kind": "header",
        "ko": "캡슐 워즈",
        "en": "CAPSULE WARS",
        "image": spec(0x8C4, 0x5F00, 160, 52, 8, 0x7240, 16,
                       "c9137ae839a30caa9e8976d03cc7ac04a3840eeb584ce63e94f4d5431c54ad1e"),
    },
    {
        "rel": "Info/arc/bank119.arc",
        "entry": "scen/osp_base.dat",
        "name": "사운드 플레이어 헤더",
        "kind": "header",
        "ko": "사운드 플레이어",
        "en": "SOUND PLAYER",
        "image": spec(0x3C8, 0x27580, 162, 52, 8, 0x288A0, 16,
                       "a0f256e298664fba8192aeab64e9c9af8407ad305adc9ea9d93adaeaccf1fb92"),
    },
]


_GTITLE_ROWS = [
    (0x688, 0x9A40, 0x614, 0x6840, 0x19500, "멀티 플레이", TITLE_GREEN,
     "8e2e8f41e52230e6b35d10ca8bb509fdd4cadbd9e4237a2c48aa64c8810c183d",
     "cbe05af3357a183b26a62a4b06e84a9ac25f490f44f7db89fd6df5302b1452b2"),
    (0x7A8, 0xFE40, 0x734, 0xCC40, 0x19540, "옵션", TITLE_BLUE,
     "99ed27f06d36193364d4f287b5cf865607fa6ed2a4bc3fbfe562765f2ce01425",
     "6618e1f0b79619e49975346f2486bbc25379f5408911500c0f56c9362e69cacc"),
    (0x8C8, 0x16240, 0x854, 0x13040, 0x19580, "옵션", TITLE_PINK,
     "55c37e65cae873b2e094dcacf82cc5d4b023f61ca5502f202f3b5eb0262bd693",
     "ca32ba28dfe97b8ddf41d0d95af0ad287d8edcec913e6496e9acc6b1fd1e4594"),
    (0x9E8, 0x16240, 0x974, 0x13040, 0x19580, "옵션", TITLE_PINK,
     "55c37e65cae873b2e094dcacf82cc5d4b023f61ca5502f202f3b5eb0262bd693",
     "ca32ba28dfe97b8ddf41d0d95af0ad287d8edcec913e6496e9acc6b1fd1e4594"),
    (0xB08, 0x16240, 0xA94, 0x13040, 0x19580, "옵션", TITLE_PINK,
     "55c37e65cae873b2e094dcacf82cc5d4b023f61ca5502f202f3b5eb0262bd693",
     "ca32ba28dfe97b8ddf41d0d95af0ad287d8edcec913e6496e9acc6b1fd1e4594"),
]


def gtitle_group(rel, entry, shift=0):
    pairs = []
    for mask_struct, mask_raw, color_struct, color_raw, pal, text, color, mask_sha, color_sha in _GTITLE_ROWS:
        pairs.append({
            "name": text,
            "mask": spec(mask_struct, mask_raw + shift, 316, 74, 8,
                          pal + shift, 8, mask_sha),
            "color": spec(color_struct, color_raw + shift, 316, 74, 14,
                           sha256=color_sha),
            "kind": "gtitle",
            "color_value": color,
        })
    return {"rel": rel, "entry": entry, "pairs": pairs}


PAIR_GROUPS = [
    gtitle_group("Info/arc/bank102.arc", "scen/msel_gtitle.dat"),
    gtitle_group("Info/arc/bank108.arc", "scen/cap_gtitle.dat"),
    # bank113은 같은 HSD 그래프를 0x20바이트 앞에서 시작한다.
    gtitle_group("Info/arc/bank113.arc", "scen/usel_gtitle.dat", shift=-0x20),
]


def load_group(rel, entry):
    source_path = os.path.join(BASE, rel)
    work_path = os.path.join(PATCHED, rel)
    source_container = bytearray(open(source_path, "rb").read())
    if os.path.exists(work_path):
        work_container = bytearray(open(work_path, "rb").read())
    else:
        work_container = bytearray(source_container)
    source_off, source_size = get_u8_entry(source_container, entry)
    work_off, work_size = get_u8_entry(work_container, entry)
    if source_size != work_size:
        raise ValueError("U8 내부 파일 크기 변경: %s" % entry)
    return source_container, work_container, source_off, work_off, source_size


def write_group(rel, data):
    dst = os.path.join(PATCHED, rel)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, "wb") as f:
        f.write(data)
    if os.path.getsize(dst) != len(data):
        raise AssertionError("U8 컨테이너 크기 변경: %s" % rel)


def save_pair_preview(rows, filename):
    if not rows:
        return None
    gap = 18
    label_h = 24
    cell_w = max(max(img.width for img in images) for _, images in rows)
    row_h = max(max(img.height for img in images) for _, images in rows) + label_h + 8
    sheet = Image.new("RGB", (cell_w * 3 + gap * 4, row_h * len(rows) + 12),
                      (30, 30, 38))
    d = ImageDraw.Draw(sheet)
    caption = ImageFont.truetype(FONT, 13)
    labels = ["C4 하이라이트", "CMP 색상", "겹침 확인"]
    for i, (name, images) in enumerate(rows):
        y = 6 + i * row_h
        for j, image in enumerate(images):
            x = gap + j * (cell_w + gap)
            d.text((x, y), "%s  %s" % (name, labels[j]), font=caption,
                   fill=(255, 255, 100))
            bg = Image.new("RGB", image.size, (52, 52, 62))
            bg.paste(image, (0, 0), image)
            sheet.paste(bg, (x, y + label_h))
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, filename)
    sheet.save(path)
    return path


def save_asset_preview(rows, filename):
    if not rows:
        return None
    gap = 18
    label_h = 24
    caption = ImageFont.truetype(FONT, 13)
    scale = 3
    cells = []
    for name, image in rows:
        bg = Image.new("RGB", image.size, (52, 52, 62))
        bg.paste(image, (0, 0), image)
        cells.append((name, bg.resize((image.width * scale, image.height * scale),
                                      Image.Resampling.NEAREST)))
    width = max(image.width for _, image in cells) + gap * 2
    row_h = max(image.height for _, image in cells) + label_h + 8
    sheet = Image.new("RGB", (width, row_h * len(cells) + 12), (30, 30, 38))
    d = ImageDraw.Draw(sheet)
    for i, (name, image) in enumerate(cells):
        y = 6 + i * row_h
        d.text((gap, y), name, font=caption, fill=(255, 255, 100))
        sheet.paste(image, (gap, y + label_h))
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, filename)
    sheet.save(path)
    return path


def process_assets(preview_rows):
    grouped = {}
    for item in ASSETS:
        grouped.setdefault((item["rel"], item["entry"]), []).append(item)
    for (rel, entry), items in grouped.items():
        source_container, work_container, source_off, work_off, source_size = load_group(rel, entry)
        source_hsd = source_container[source_off:source_off + source_size]
        work_hsd = bytearray(work_container[work_off:work_off + source_size])
        for item in items:
            image_spec = item["image"]
            validate(source_hsd, image_spec)
            if item["kind"] == "logo":
                image = draw_logo(image_spec["w"], image_spec["h"])
            else:
                image = draw_header(item["ko"], item["en"], image_spec["w"], image_spec["h"])
            raw = encode(source_hsd, image, image_spec)
            if args.apply:
                off = image_spec["img_off"]
                work_hsd[off:off + image_spec["size"]] = raw
            preview_rows.append((item["name"], image))
        if args.apply:
            work_container[work_off:work_off + source_size] = work_hsd
            write_group(rel, work_container)
            print("APPLIED", rel, entry, "assets:", len(items))


def process_pairs(preview_rows):
    for group in PAIR_GROUPS:
        rel, entry = group["rel"], group["entry"]
        source_container, work_container, source_off, work_off, source_size = load_group(rel, entry)
        source_hsd = source_container[source_off:source_off + source_size]
        work_hsd = bytearray(work_container[work_off:work_off + source_size])
        rows = []
        for pair in group["pairs"]:
            mask_spec = pair["mask"]
            color_spec = pair["color"]
            validate(source_hsd, mask_spec)
            validate(source_hsd, color_spec)
            if (mask_spec["w"], mask_spec["h"]) != (color_spec["w"], color_spec["h"]):
                raise ValueError("gtitle 레이어 크기 불일치: %s" % pair["name"])
            mask, color_img, composite = draw_title_pair(
                pair["name"], mask_spec["w"], mask_spec["h"], pair["color_value"])
            mask_raw = encode(source_hsd, mask, mask_spec)
            color_raw = encode(source_hsd, color_img, color_spec)
            if args.apply:
                work_hsd[mask_spec["img_off"]:mask_spec["img_off"] + mask_spec["size"]] = mask_raw
                work_hsd[color_spec["img_off"]:color_spec["img_off"] + color_spec["size"]] = color_raw
            rows.append((pair["name"], [mask, color_img, composite]))
        preview_rows.extend(("%s %s" % (rel.rsplit("/", 1)[-1], name), images)
                            for name, images in rows)
        if args.apply:
            work_container[work_off:work_off + source_size] = work_hsd
            write_group(rel, work_container)
            print("APPLIED", rel, entry, "gtitle pairs:", len(group["pairs"]))


def main():
    if not args.apply and not args.preview:
        ap.error("--apply 또는 --preview를 지정하세요")
    if not os.path.exists(FONT):
        raise FileNotFoundError(FONT)
    asset_rows = []
    pair_rows = []
    process_assets(asset_rows)
    process_pairs(pair_rows)
    if args.preview:
        print("preview saved:", save_asset_preview(asset_rows, "nested_ui_assets_preview.png"))
        print("preview saved:", save_pair_preview(pair_rows, "nested_duplicate_titles_preview.png"))
    print("nested UI assets:", len(asset_rows), "gtitle pairs:", len(pair_rows))


if __name__ == "__main__":
    main()
