# -*- coding: utf-8 -*-
"""한글패치에서 남은 HAL DAT 내부의 커스텀 텍스트 이미지를 재작화한다.

미션 제목 카드와 성공/실패 화면은 일반 @Texture 파일이 아니라 HAL Laboratory
HSD/DAT 컨테이너 안의 CI4 텍스처다. HSDRaw로 확인한 고정 레이아웃을 검증한 뒤
GameCube 8x8 타일 순서로 이미지만 교체하며, 컨테이너의 포인터/구조체는 건드리지
않는다.

사용:
  python 75_custom_dat_sprites.py --preview
  python 75_custom_dat_sprites.py --apply
"""
import argparse
import io
import os
import struct
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, "..", "files")
PATCHED = os.path.join(HERE, "..", "text_patch_work", "patched_files")
FONT = os.path.join(HERE, "..", "fonts", "NanumSquareNeocBd.ttf")

sys.path.insert(0, HERE)
import tex_lib as TX
from PIL import Image, ImageDraw, ImageFont

ap = argparse.ArgumentParser()
ap.add_argument("--apply", action="store_true", help="patched_files에 바이너리 패치 저장")
ap.add_argument("--preview", action="store_true", help="작화 결과 미리보기 저장")
args = ap.parse_args()


# HSDRaw로 확인한 sub_t01.dat~sub_t14.dat 공통 레이아웃.
SUB_TITLES = {
    "sub_t01.dat": "전투의 시작",
    "sub_t02.dat": "강력한 팀의 힘",
    "sub_t03.dat": "저편에서의 공격",
    "sub_t04.dat": "하늘을 나는 검은 그림자",
    "sub_t05.dat": "수중에 울려 퍼지는 폭음",
    "sub_t06.dat": "거점을 둘러싼 쟁탈전",
    "sub_t07.dat": "우주로 펼쳐지는 전장",
    "sub_t08.dat": "새로운 전술",
    "sub_t09.dat": "가샤 베이스의 사투",
    "sub_t10.dat": "또 하나의 승리",
    "sub_t11.dat": "지켜야 할 요새",
    "sub_t12.dat": "변화하는 전장",
    "sub_t13.dat": "다가오는 공포",
    "sub_t14.dat": "모든 힘을 해방하라",
}

SUB_TITLE = {
    "image_offset": 0x34A0,
    "width": 580,
    "height": 128,
    "palette_offset": 0xD120,
    "palette_count": 16,
}
SUB_NEXT = {
    "image_offset": 0xCE20,
    "width": 42,
    "height": 18,
    "palette_offset": 0xD220,
    "palette_count": 16,
}
MISSION_SUCCESS = {
    "rel": "Info/dat/m_seikou.dat",
    "image_offset": 0x36C0,
    "width": 240,
    "height": 182,
    "palette_offset": 0x8D00,
    "palette_count": 16,
    "text": "미션 클리어",
}
MISSION_FAILURE = {
    "rel": "Info/dat/m_sippai.dat",
    "image_offset": 0x07E0,
    "width": 240,
    "height": 182,
    "palette_offset": 0xB460,
    "palette_count": 8,
    "text": "미션 실패",
}

# The same UI textures are copied into scene-specific HSD files inside U8
# archives. These copies are what the game uses after entering a scenario;
# patching only Info/dat/* leaves the Japanese labels visible in-game.
NESTED_SUCCESS = (
    "Info/arc/bank111.arc",
    "scen/pb_m_cl.dat",
    {
        "image_offset": 0x36C0,
        "width": 240,
        "height": 182,
        "palette_offset": 0x8D00,
        "palette_count": 16,
        "text": "미션 클리어",
    },
)
NESTED_NEXT = (
    ("Info/arc/bank111.arc", "scen/rw_push_a.dat"),
    ("Info/arc/bank120.arc", "scen/rw_push_a.dat"),
)
NESTED_NEXT_SPEC = {
    "image_offset": 0x12E0,
    "width": 42,
    "height": 18,
    "palette_offset": 0x1620,
    "palette_count": 16,
    "text": "다음",
}


def align(n, a):
    return (n + a - 1) // a * a


def c4_size(width, height):
    return align(width, 8) * align(height, 8) // 2


def u32(data, offset):
    return struct.unpack_from(">I", data, offset)[0]


def u8_entries(data):
    """Return (path, offset, size) for files in a Nintendo U8 archive."""
    if u32(data, 0) != 0x55AA382D:
        raise ValueError("Nintendo U8 매직이 아닙니다")
    root = u32(data, 4)
    count = u32(data, root + 8)
    string_base = root + count * 12
    stack = []
    result = []
    for index in range(1, count):
        node = root + index * 12
        raw_name = u32(data, node)
        kind = raw_name >> 24
        name_offset = raw_name & 0xFFFFFF
        end = data.index(b"\0", string_base + name_offset)
        name = data[string_base + name_offset:end].decode("cp932", "replace")
        first = u32(data, node + 4)
        last = u32(data, node + 8)
        while stack and index >= stack[-1][1]:
            stack.pop()
        if kind:
            stack.append((name, last))
        else:
            result.append(("/".join(x[0] for x in stack + [(name, last)]),
                           first, last))
    return result


def find_u8_entry(data, wanted):
    for name, offset, size in u8_entries(data):
        if name == wanted:
            return offset, size
    raise KeyError("U8 내부 파일을 찾지 못했습니다: " + wanted)


def read_palette(data, offset, count):
    if offset < 0 or offset + count * 2 > len(data):
        raise ValueError("palette 범위가 DAT 파일 밖입니다: 0x%X" % offset)
    return [TX.rgb5a3(struct.unpack_from(">H", data, offset + i * 2)[0])
            for i in range(count)]


def read_base(rel):
    # 패치 결과를 다시 읽으면 재빌드 때 작화가 누적될 수 있으므로 항상 원본을 읽는다.
    source = os.path.join(BASE, rel)
    if not os.path.exists(source):
        raise FileNotFoundError(source)
    return source, bytearray(open(source, "rb").read())


def draw_centered(text, width, height, max_size, stroke_width, stroke_fill=(0, 0, 0, 255)):
    """투명 배경에 팔레트로 양자화될 흰색 텍스트를 가운데 그린다."""
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    fill = (255, 255, 255, 255)
    for size in range(max_size, 5, -1):
        font = ImageFont.truetype(FONT, size)
        box = draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
        tw, th = box[2] - box[0], box[3] - box[1]
        if tw <= width - 8 and th <= height - 4:
            x = (width - tw) // 2 - box[0]
            y = (height - th) // 2 - box[1]
            draw.text((x, y), text, font=font, fill=fill,
                      stroke_width=stroke_width, stroke_fill=stroke_fill)
            return img
    raise ValueError("텍스트가 이미지에 들어가지 않습니다: %s" % text)


def replace_c4(buf, spec, image):
    expected = c4_size(spec["width"], spec["height"])
    if image.size != (spec["width"], spec["height"]):
        raise ValueError("이미지 크기 불일치: %s != %s" % (image.size,
                                                    (spec["width"], spec["height"])))
    if spec["image_offset"] < 0 or spec["image_offset"] + expected > len(buf):
        raise ValueError("이미지 범위가 DAT 파일 밖입니다: 0x%X + 0x%X" %
                         (spec["image_offset"], expected))
    palette = read_palette(buf, spec["palette_offset"], spec["palette_count"])
    raw = TX.encode_c4(image, palette, spec["width"], spec["height"])
    if len(raw) != expected:
        raise AssertionError("C4 크기 불일치: %d != %d" % (len(raw), expected))
    start = spec["image_offset"]
    buf[start:start + expected] = raw


_nested_containers = {}


def patch_nested(rel, inner, spec, image, expected_raw=None):
    """Patch one fixed-layout HSD stored as a file in a U8 archive."""
    # Several nested targets share one outer ARC. Keep one in-memory copy per
    # ARC so a later target does not overwrite an earlier target with BASE.
    source_container = Path(BASE, rel).read_bytes()
    existing = Path(PATCHED, rel)
    work_container = _nested_containers.setdefault(
        rel, bytearray(existing.read_bytes() if existing.exists() else source_container)
    )
    offset, size = find_u8_entry(source_container, inner)
    source_hsd = source_container[offset:offset + size]
    raw_size = c4_size(spec["width"], spec["height"])
    if expected_raw is not None:
        actual = source_hsd[spec["image_offset"]:
                            spec["image_offset"] + raw_size]
        if actual != expected_raw:
            raise ValueError("중첩 HSD 원본 raw가 기준 파일과 다릅니다: " +
                             rel + ":" + inner)
    hsd = bytearray(work_container[offset:offset + size])
    replace_c4(hsd, spec, image)
    work_container[offset:offset + size] = hsd
    if len(work_container) != len(source_container):
        raise AssertionError("U8 컨테이너 크기 변경: " + rel)
    if args.apply:
        dst = Path(PATCHED, rel)
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(work_container)
    return image


def make_preview(items):
    out_dir = os.path.join(HERE, "out")
    os.makedirs(out_dir, exist_ok=True)
    gap = 28
    width = max(image.width for _, image, _ in items)
    height = sum(image.height + gap for _, image, _ in items)
    sheet = Image.new("RGB", (width, height), (55, 58, 70))
    draw = ImageDraw.Draw(sheet)
    y = 0
    for label, image, note in items:
        bg = Image.new("RGB", image.size, (18, 20, 28))
        bg.paste(image, (0, 0), image)
        sheet.paste(bg, (0, y))
        draw.text((4, y + image.height + 4), "%s  %s" % (label, note),
                  fill=(230, 235, 245))
        y += image.height + gap
    path = os.path.join(out_dir, "custom_dat_sprites_preview.png")
    sheet.save(path)
    print("preview saved:", path)


def main():
    if not args.apply and not args.preview:
        ap.error("--apply 또는 --preview를 지정하세요")
    if not os.path.exists(FONT):
        raise FileNotFoundError(FONT)

    preview = []
    changed = 0

    for name, ko in SUB_TITLES.items():
        rel = "Info/dat/" + name
        source, buf = read_base(rel)
        title = draw_centered(ko, SUB_TITLE["width"], SUB_TITLE["height"],
                              max_size=104, stroke_width=3)
        next_button = draw_centered("다음", SUB_NEXT["width"], SUB_NEXT["height"],
                                    max_size=15, stroke_width=1)
        replace_c4(buf, SUB_TITLE, title)
        replace_c4(buf, SUB_NEXT, next_button)
        if args.preview and name in ("sub_t01.dat", "sub_t04.dat", "sub_t09.dat", "sub_t14.dat"):
            preview.append((name + " title", title, ko))
            preview.append((name + " next", next_button, "다음"))
        if args.apply:
            dst = os.path.join(PATCHED, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            open(dst, "wb").write(buf)
        changed += 1

    for spec in (MISSION_SUCCESS, MISSION_FAILURE):
        source, buf = read_base(spec["rel"])
        # 성공 텍스처는 흰 글자+검은 외곽선, 실패 텍스처는 흰색 알파 팔레트다.
        stroke = 3 if spec["palette_count"] == 16 else 0
        image = draw_centered(spec["text"], spec["width"], spec["height"],
                              max_size=76, stroke_width=stroke,
                              stroke_fill=(0, 0, 0, 255))
        replace_c4(buf, spec, image)
        if args.preview:
            preview.append((os.path.basename(spec["rel"]), image, spec["text"]))
        if args.apply:
            dst = os.path.join(PATCHED, spec["rel"])
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            open(dst, "wb").write(buf)
        changed += 1

    # The mission-clear HSD is duplicated in bank111's scenario archive.
    # Compare its source pixels with the standalone source before replacing
    # them, so a future layout change fails loudly instead of patching noise.
    standalone_success = Path(BASE, MISSION_SUCCESS["rel"]).read_bytes()
    success_raw_size = c4_size(MISSION_SUCCESS["width"],
                               MISSION_SUCCESS["height"])
    success_raw = standalone_success[MISSION_SUCCESS["image_offset"]:
                                     MISSION_SUCCESS["image_offset"] +
                                     success_raw_size]
    success_image = draw_centered(MISSION_SUCCESS["text"],
                                  MISSION_SUCCESS["width"],
                                  MISSION_SUCCESS["height"],
                                  max_size=76, stroke_width=3)
    rel, inner, nested_spec = NESTED_SUCCESS
    patch_nested(rel, inner, nested_spec, success_image, success_raw)
    if args.preview:
        preview.append((rel + ":" + inner, success_image,
                        MISSION_SUCCESS["text"]))
    changed += 1

    # Both multiplayer next-button HSDs are exact copies of SUB_NEXT's raw
    # buffer, but use a different palette location in their compact layout.
    standalone_subtitle = Path(BASE, "Info/dat/sub_t01.dat").read_bytes()
    next_raw_size = c4_size(SUB_NEXT["width"], SUB_NEXT["height"])
    next_raw = standalone_subtitle[SUB_NEXT["image_offset"]:
                                   SUB_NEXT["image_offset"] + next_raw_size]
    next_image = draw_centered("다음", NESTED_NEXT_SPEC["width"],
                               NESTED_NEXT_SPEC["height"],
                               max_size=15, stroke_width=1)
    for rel, inner in NESTED_NEXT:
        patch_nested(rel, inner, NESTED_NEXT_SPEC, next_image, next_raw)
        if args.preview:
            preview.append((rel + ":" + inner, next_image, "다음"))
        changed += 1

    if args.preview:
        make_preview(preview)
    if args.apply:
        print("APPLIED custom DAT sprites:", changed, "files")
    else:
        print("preview only:", changed, "files")


if __name__ == "__main__":
    main()
