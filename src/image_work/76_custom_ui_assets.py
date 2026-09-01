# -*- coding: utf-8 -*-
"""타이틀 로고와 전투 조작설명 텍스처를 한글로 재작화한다.

둘 다 일반 @Texture 아카이브가 아니라 고정 레이아웃의 GameCube 리소스다.
demo_title.dat의 RGB5A3 로고와 Info/tpl/con_img.tpl의 C8 컨트롤러 그림에서
이미지 바이트만 교체하며, TPL/DAT 헤더와 파일 길이는 유지한다.

사용:
  python 76_custom_ui_assets.py --preview
  python 76_custom_ui_assets.py --apply
"""
import argparse
import os
import struct
import sys

sys.stdout = __import__("io").TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

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


def read_source(rel):
    patched = os.path.join(PATCHED, rel)
    source = patched if os.path.exists(patched) else os.path.join(BASE, rel)
    if not os.path.exists(source):
        raise FileNotFoundError(source)
    return source, bytearray(open(source, "rb").read())


def decode_rgb5a3(raw, width, height):
    if len(raw) < width * height * 2:
        raise ValueError("RGB5A3 raw 데이터가 짧습니다")
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    px = image.load()
    p = 0
    for ty in range(0, height, 4):
        for tx in range(0, width, 4):
            for y in range(ty, ty + 4):
                for x in range(tx, tx + 4):
                    value = struct.unpack_from(">H", raw, p)[0]
                    p += 2
                    if x < width and y < height:
                        px[x, y] = TX.rgb5a3(value)
    return image


def encode_rgb5a3(image, width, height):
    image = image.convert("RGBA")
    px = image.load()
    out = bytearray()
    for ty in range(0, height, 4):
        for tx in range(0, width, 4):
            for y in range(ty, ty + 4):
                for x in range(tx, tx + 4):
                    r, g, b, a = px[x, y] if x < width and y < height else (0, 0, 0, 0)
                    if a < 255:
                        value = ((a // 32) << 12) | ((r // 16) << 8) | ((g // 16) << 4) | (b // 16)
                    else:
                        value = 0x8000 | ((r // 8) << 10) | ((g // 8) << 5) | (b // 8)
                    out.extend(struct.pack(">H", value))
    return bytes(out)


def decode_tpl_c8(data, width, height, palette_offset, image_offset):
    palette = []
    for i in range(256):
        value = struct.unpack_from(">H", data, palette_offset + i * 2)[0]
        palette.append(TX.rgb5a3(value))
    pw = (width + 7) // 8 * 8
    ph = (height + 7) // 8 * 8
    expected = pw * ph
    raw = data[image_offset:image_offset + expected]
    if len(raw) != expected:
        raise ValueError("C8 raw 크기 불일치")
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    px = image.load()
    p = 0
    for ty in range(0, ph, 8):
        for tx in range(0, pw, 8):
            for y in range(8):
                for x in range(8):
                    if tx + x < width and ty + y < height:
                        px[tx + x, ty + y] = palette[raw[p]]
                    p += 1
    return image, palette, expected


def fit_font(draw, text, box, max_size=18, min_size=6, stroke=1):
    left, top, right, bottom = box
    width, height = right - left, bottom - top
    for size in range(max_size, min_size - 1, -1):
        font = ImageFont.truetype(FONT, size)
        bb = draw.textbbox((0, 0), text, font=font, stroke_width=stroke)
        if bb[2] - bb[0] <= width and bb[3] - bb[1] <= height:
            x = left + (width - (bb[2] - bb[0])) // 2 - bb[0]
            y = top + (height - (bb[3] - bb[1])) // 2 - bb[1]
            return font, (x, y)
    raise ValueError("텍스트가 UI 박스에 들어가지 않습니다: %s" % text)


def draw_logo(image):
    """기존 일본어 로고 영역을 비우고 같은 영역에 한국어 로고를 그린다."""
    image = image.copy()
    image.paste((0, 0, 0, 0), (0, 0, image.width, 88))
    draw = ImageDraw.Draw(image)

    def draw_layer(text, box, fill, inner_stroke, outer_stroke=4, max_size=40):
        font, pos = fit_font(draw, text, box, max_size=max_size, min_size=8, stroke=outer_stroke)
        draw.text(pos, text, font=font, fill=fill,
                  stroke_width=outer_stroke, stroke_fill=(255, 255, 255, 255))
        draw.text(pos, text, font=font, fill=fill,
                  stroke_width=inner_stroke, stroke_fill=(24, 35, 116, 255))

    # 상단 SD 로고와 중앙 한국어 제목은 원본의 색감(금색/적색/청색)을 따른다.
    draw_layer("SD 건담", (28, 0, 145, 31), (242, 192, 61, 255), 2, outer_stroke=3, max_size=25)
    draw_layer("가샤폰 워즈", (4, 31, 256, 86), (226, 39, 49, 255), 2, outer_stroke=5, max_size=44)
    return image


# con_img.tpl은 두 개의 동일한 조작 도식을 가로로 보관한 334x182 C8 TPL이다.
# 같은 도식이 액션 배틀용 Effect 아카이브에도 3개 복제되어 있으므로 함께 패치한다.
HELP_ARC_RELS = [
    "Effect/Arc/bank0.arc",
    "Effect/Arc/bank1.arc",
    "Effect/Arc/bank2.arc",
]
HELP_TEXT = [
    # 원본 일본어의 실제 픽셀 범위를 덮되, 말풍선 외곽선은 건드리지 않는다.
    ("가드", (4, 6, 53, 27)),
    ("특수", (104, 6, 165, 27)),
    ("격투 공격", (108, 57, 166, 80)),
    ("이동", (0, 84, 56, 106)),
    ("메인 공격", (14, 133, 84, 158)),
    ("점프", (98, 159, 156, 181)),
    ("태클", (128, 115, 166, 140)),
]
BUBBLE = (66, 132, 115, 255)


def draw_help(image):
    image = image.copy()
    draw = ImageDraw.Draw(image)
    for shift in (0, 167):
        for text, box in HELP_TEXT:
            left, top, right, bottom = box
            box = (left + shift, top, right + shift, bottom)
            # 일본어 글자는 흰색/회색/검정 계열이다. 해당 픽셀만 말풍선 색으로
            # 지워 둥근 테두리와 연결선이 사각형으로 끊기지 않게 한다.
            for y in range(top, bottom):
                for x in range(left + shift, right + shift):
                    r, g, b, a = image.getpixel((x, y))
                    if a and max(r, g, b) - min(r, g, b) <= 8:
                        image.putpixel((x, y), BUBBLE)
            font, pos = fit_font(draw, text, box, max_size=14, min_size=6, stroke=1)
            draw.text(pos, text, font=font, fill=(255, 255, 255, 255),
                      stroke_width=1, stroke_fill=(33, 33, 33, 255))
    return image


def patch_help_arc(rel, preview_image=None):
    """Effect/Arc의 복제 C8 텍스처 한 개를 찾아 같은 도움말을 주입한다."""
    _, buf = read_source(rel)
    candidates = []
    for off in TX.find_blocks(buf):
        try:
            hd = TX.parse_header(buf, off)
        except (IndexError, struct.error):
            continue
        if (hd["w"], hd["h"], hd["palcnt"]) == (334, 182, 256):
            candidates.append((off, hd))
    if len(candidates) != 1:
        raise ValueError("도움말 C8 텍스처 수가 예상과 다릅니다: %s (%d)" %
                         (rel, len(candidates)))
    off, hd = candidates[0]
    image = TX.decode(buf, off)
    if image is None:
        raise ValueError("도움말 C8 디코드 실패: %s @0x%X" % (rel, off))
    patched = draw_help(image)
    palette = TX.read_palette(buf, hd["pal_off"], hd["palcnt"])
    raw = TX.encode_c8(patched, palette, hd["w"], hd["h"])
    if len(raw) != hd["imgsize"]:
        raise AssertionError("Effect 도움말 C8 길이 변경: %s" % rel)
    if preview_image is not None:
        preview_image.append(patched)
    if args.apply:
        buf[hd["img_off"]:hd["img_off"] + hd["imgsize"]] = raw
        dst = os.path.join(PATCHED, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, "wb").write(buf)
        assert os.path.getsize(dst) == len(buf)
        print("APPLIED battle help:", rel, "@0x%X C8" % off)


def preview_pair(title, help_image):
    out_dir = os.path.join(HERE, "out")
    os.makedirs(out_dir, exist_ok=True)
    def on_bg(image, scale=3):
        bg = Image.new("RGB", image.size, (45, 45, 45))
        bg.paste(image, (0, 0), image)
        return bg.resize((image.width * scale, image.height * scale), Image.Resampling.NEAREST)
    title_bg = on_bg(title, 3)
    help_bg = on_bg(help_image, 3)
    canvas = Image.new("RGB", (max(title_bg.width, help_bg.width), title_bg.height + help_bg.height + 16), (25, 27, 35))
    canvas.paste(title_bg, (0, 0)); canvas.paste(help_bg, (0, title_bg.height + 16))
    canvas.save(os.path.join(out_dir, "custom_ui_assets_preview.png"))
    title.save(os.path.join(out_dir, "title_logo_preview.png"))
    help_image.save(os.path.join(out_dir, "battle_help_preview.png"))
    print("preview saved:", os.path.join(out_dir, "custom_ui_assets_preview.png"))


def main():
    if not args.apply and not args.preview:
        ap.error("--apply 또는 --preview를 지정하세요")
    if not os.path.exists(FONT):
        raise FileNotFoundError(FONT)

    _, title_buf = read_source("demo_title.dat")
    title_raw = title_buf[0x700:0x700 + 260 * 108 * 2]
    title = decode_rgb5a3(title_raw, 260, 108)
    patched_title = draw_logo(title)
    new_title_raw = encode_rgb5a3(patched_title, 260, 108)
    if len(new_title_raw) != len(title_raw):
        raise AssertionError("타이틀 RGB5A3 길이 변경")

    _, help_buf = read_source("Info/tpl/con_img.tpl")
    if struct.unpack_from(">I", help_buf, 0x224)[0] != 9:
        raise ValueError("con_img.tpl이 C8 텍스처가 아닙니다")
    help_image, palette, help_size = decode_tpl_c8(help_buf, 334, 182, 0x20, 0x260)
    patched_help = draw_help(help_image)
    new_help_raw = TX.encode_c8(patched_help, palette, 334, 182)
    if len(new_help_raw) != help_size:
        raise AssertionError("전투 도움말 C8 길이 변경")

    if args.preview:
        preview_pair(patched_title, patched_help)
    if args.apply:
        title_buf[0x700:0x700 + len(new_title_raw)] = new_title_raw
        title_dst = os.path.join(PATCHED, "demo_title.dat")
        os.makedirs(os.path.dirname(title_dst), exist_ok=True)
        open(title_dst, "wb").write(title_buf)
        assert os.path.getsize(title_dst) == len(title_buf)

        help_buf[0x260:0x260 + len(new_help_raw)] = new_help_raw
        help_dst = os.path.join(PATCHED, "Info/tpl/con_img.tpl")
        os.makedirs(os.path.dirname(help_dst), exist_ok=True)
        open(help_dst, "wb").write(help_buf)
        assert os.path.getsize(help_dst) == len(help_buf)
        print("APPLIED title logo: demo_title.dat 260x108 RGB5A3")
        print("APPLIED battle help: Info/tpl/con_img.tpl 334x182 C8")

    arc_previews = []
    for rel in HELP_ARC_RELS:
        patch_help_arc(rel, arc_previews if args.preview else None)


if __name__ == "__main__":
    main()
