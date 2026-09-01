# -*- coding: utf-8 -*-
"""타이틀 로고와 전투 조작설명 텍스처를 한글로 재작화한다.

둘 다 일반 @Texture 아카이브가 아니라 고정 레이아웃의 GameCube 리소스다.
demo_title.dat의 RGB5A3 로고와 Info/tpl/con_img.tpl의 C8 컨트롤러 그림에서
일본어 글리프와 한글 오버레이 픽셀만 교체하며, 나머지 원본 raw·TPL/DAT 헤더·파일 길이는 유지한다.

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
from PIL import Image, ImageChops, ImageDraw, ImageFont

ap = argparse.ArgumentParser()
ap.add_argument("--apply", action="store_true", help="patched_files에 바이너리 패치 저장")
ap.add_argument("--preview", action="store_true", help="작화 결과 미리보기 저장")
args = ap.parse_args()


def read_source(rel):
    # 항상 추출된 원본에서 시작해야 빌드를 여러 번 실행해도 작화가 누적되지 않는다.
    source = os.path.join(BASE, rel)
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
    # GameCube C8은 8x4 texel tile(32 bytes)이다. 8x8로 읽으면 4행마다
    # 다음 타일 데이터가 섞여 원본 도식이 가로로 분할되고 줄이 밀린다.
    pw = (width + 7) // 8 * 8
    ph = (height + 3) // 4 * 4
    expected = pw * ph
    raw = data[image_offset:image_offset + expected]
    if len(raw) != expected:
        raise ValueError("C8 raw 크기 불일치")
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    px = image.load()
    p = 0
    for ty in range(0, ph, 4):
        for tx in range(0, pw, 8):
            for y in range(4):
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


# con_img.tpl은 하나의 완전한 조작 도식을 보관한 334x182 C8 TPL이다.
# 같은 도식이 액션 배틀용 Effect 아카이브에도 3개 복제되어 있으므로 함께 패치한다.
HELP_ARC_RELS = [
    "Effect/Arc/bank0.arc",
    "Effect/Arc/bank1.arc",
    "Effect/Arc/bank2.arc",
]
HELP_TEXT = [
    # 전체 334x182 도식 기준 (그리기 영역, 일본어만 지울 내부 글리프 영역).
    ("가드", (39, 4, 102, 27), (42, 4, 102, 27)),
    ("특수", (235, 4, 314, 27), (237, 4, 314, 27)),
    ("격투 공격", (255, 53, 334, 80), (257, 56, 334, 79)),
    ("이동", (28, 79, 84, 106), (30, 83, 84, 105)),
    ("메인 공격", (76, 130, 155, 156), (70, 132, 155, 155)),
    ("점프", (188, 152, 264, 182), (190, 154, 264, 180)),
    ("태클", (249, 113, 323, 142), (248, 115, 323, 140)),
]
# 원문에 붙은 후리가나(읽기 표기)는 큰 라벨 박스보다 위에 있으므로
# 별도 내부 영역으로 지운다. 말풍선 테두리와 연결선은 이 범위 밖에 둔다.
HELP_FURIGANA_CLEAR = [
    (119, 129, 150, 136),  # こうげき
    (263, 53, 333, 56),    # かくとうこうげき
    (44, 80, 84, 83),      # いどう
]
BUBBLE = (66, 132, 115, 255)


def draw_help(image):
    image = image.copy()
    # Pillow의 RGBA ImageDraw는 안티앨리어싱 글자 가장자리를 부분 알파로
    # 남긴다. 이 값을 그대로 C8 팔레트에 양자화하면 투명 팔레트 색이
    # 선택되어 게임에서 글자 가장자리가 톱니처럼 끊어진다. 먼저 투명
    # 레이어에 글자를 그리고 불투명한 말풍선/배경 위에 합성한다.
    text_layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    text_draw = ImageDraw.Draw(text_layer)
    def clear_region(clear_box):
        cl, ct, cr, cb = clear_box
        # 일본어 글자는 흰색/회색/검정 계열이다. 해당 픽셀만 말풍선 색으로
        # 지운다. 글리프 내부 영역만 검사해 말풍선 외곽선·도식을 보존한다.
        for y in range(ct, cb):
            for x in range(cl, cr):
                r, g, b, a = image.getpixel((x, y))
                # 일본어 글리프의 반투명 가장자리는 녹색으로 혼합되어
                # 중성색 판정만으로는 남는다. 원본 말풍선 내부 전체를
                # 말풍선 색으로 복원하되, 완전 투명 픽셀은 보존한다.
                if a:
                    image.putpixel((x, y), BUBBLE)

    for _, _, clear_box in HELP_TEXT:
        clear_region(clear_box)
    for clear_box in HELP_FURIGANA_CLEAR:
        clear_region(clear_box)

    for text, box, _ in HELP_TEXT:
        font, pos = fit_font(text_draw, text, box, max_size=14, min_size=6, stroke=1)
        text_draw.text(pos, text, font=font, fill=(255, 255, 255, 255),
                       stroke_width=1, stroke_fill=(33, 33, 33, 255))
    # 글리프 영역 밖의 완전 투명 픽셀에는 텍스트를 쓰지 않는다. 이 마스크를
    # 적용하면 C8 팔레트의 투명 흰색(인덱스 248~254)이 한글 가장자리에
    # 들어가지 않고, 실제 표시되는 픽셀은 모두 불투명 배경 위에 합성된다.
    visible = image.getchannel("A").point(lambda a: 255 if a else 0)
    text_alpha = ImageChops.multiply(text_layer.getchannel("A"), visible)
    text_layer.putalpha(text_alpha)
    return Image.alpha_composite(image, text_layer)


def encode_c8_overlay(raw, original, image, palette, width, height):
    """C8 raw는 그대로 두고 원본과 달라진 글자 픽셀만 팔레트 인덱스로 교체한다."""
    if len(raw) != ((width + 7) // 8 * 8) * ((height + 3) // 4 * 4):
        raise ValueError("C8 raw 크기 불일치")
    out = bytearray(raw)
    before = original.load()
    after = image.load()
    tiles_w = (width + 7) // 8
    cache = {}
    for y in range(height):
        for x in range(width):
            if before[x, y] == after[x, y]:
                continue
            color = after[x, y]
            if color[3] != 255:
                raise ValueError("C8 변경 픽셀에 부분 알파가 남았습니다: %s" % (color,))
            if color not in cache:
                cache[color] = TX._nearest(palette, color)
                if palette[cache[color]][3] != 255:
                    raise ValueError("C8 변경 픽셀이 투명 팔레트로 매핑됐습니다: %s -> %d" %
                                     (color, cache[color]))
            tile_offset = ((y // 4) * tiles_w + (x // 8)) * 32
            out[tile_offset + (y % 4) * 8 + (x % 8)] = cache[color]
    return bytes(out)


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
    original = image.copy()
    patched = draw_help(image)
    palette = TX.read_palette(buf, hd["pal_off"], hd["palcnt"])
    original_raw = bytes(buf[hd["img_off"]:hd["img_off"] + hd["imgsize"]])
    raw = encode_c8_overlay(original_raw, original, patched, palette, hd["w"], hd["h"])
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
    help_raw = bytes(help_buf[0x260:0x260 + help_size])
    patched_help = draw_help(help_image)
    new_help_raw = encode_c8_overlay(help_raw, help_image, patched_help, palette, 334, 182)
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
