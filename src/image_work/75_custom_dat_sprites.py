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


def align(n, a):
    return (n + a - 1) // a * a


def c4_size(width, height):
    return align(width, 8) * align(height, 8) // 2


def read_palette(data, offset, count):
    if offset < 0 or offset + count * 2 > len(data):
        raise ValueError("palette 범위가 DAT 파일 밖입니다: 0x%X" % offset)
    return [TX.rgb5a3(struct.unpack_from(">H", data, offset + i * 2)[0])
            for i in range(count)]


def read_base(rel):
    patched = os.path.join(PATCHED, rel)
    source = patched if os.path.exists(patched) else os.path.join(BASE, rel)
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

    if args.preview:
        make_preview(preview)
    if args.apply:
        print("APPLIED custom DAT sprites:", changed, "files")
    else:
        print("preview only:", changed, "files")


if __name__ == "__main__":
    main()
