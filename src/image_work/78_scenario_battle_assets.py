# -*- coding: utf-8 -*-
"""시나리오/공용 전투 화면의 HSD·HLH 텍스트 이미지를 전수 패치한다.

Issue #21에서 확인된 시나리오 전투 화면은 일반 이미지 아카이브가 아니라
bank100의 HLH 압축 HSD와 bank103·107의 중첩 HSD를 함께 사용한다. 이
스크립트는 첨부 캡처에서 확인한 모든 일본어/미번역 그래픽 문구를 고정
목록으로 관리하고, 중복 raw 버퍼는 한 번만 교체한다.

HLH는 복원된 HSD의 이미지 raw만 바꾼 뒤 같은 크기의 압축 슬롯으로 다시
압축한다. 따라서 U8 엔트리의 오프셋·크기와 HSD 구조체는 변하지 않는다.

사용:
  python 78_scenario_battle_assets.py --preview
  python 78_scenario_battle_assets.py --apply --preview
"""

from __future__ import annotations

import argparse
import io
import os
import struct
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / "files"
PATCHED = HERE.parent / "text_patch_work" / "patched_files"
FONT = HERE.parent / "fonts" / "NanumSquareNeocBd.ttf"
OUT_DIR = HERE / "out"

sys.path.insert(0, str(HERE))
import hlh_codec as HLH
import tex_lib as TX
from PIL import Image, ImageDraw, ImageFont


parser = argparse.ArgumentParser()
parser.add_argument("--apply", action="store_true")
parser.add_argument("--preview", action="store_true")
args = parser.parse_args()

WHITE = (255, 255, 255, 255)
BLACK = (24, 24, 30, 255)
GOLD = (238, 186, 48, 255)
BLUE = (54, 177, 238, 255)
GREEN = (76, 218, 96, 255)


def u16(data: bytes, offset: int) -> int:
    return struct.unpack_from(">H", data, offset)[0]


def u32(data: bytes, offset: int) -> int:
    return struct.unpack_from(">I", data, offset)[0]


def hsd_size(width: int, height: int, fmt: int) -> int:
    if fmt == 8:
        return ((width + 7) // 8 * 8) * ((height + 7) // 8 * 8) // 2
    if fmt == 9:
        return ((width + 7) // 8 * 8) * ((height + 3) // 4 * 4)
    if fmt == 14:
        return TX.cmp_size(width, height)
    raise ValueError("지원하지 않는 HSD 포맷: %s" % fmt)


def image_spec(struct_off, image_off, width, height, fmt, palette_off,
               palette_count, text, fill=None, stroke=None, background=None):
    return {
        "struct_off": struct_off,
        "image_off": image_off,
        "width": width,
        "height": height,
        "fmt": fmt,
        "palette_off": palette_off,
        "palette_count": palette_count,
        "size": hsd_size(width, height, fmt),
        "text": text,
        "fill": fill,
        "stroke": stroke,
        "background": background,
    }


def entries(data: bytes):
    """Nintendo U8 파일의 내부 경로/offset/size 목록."""
    if u32(data, 0) != 0x55AA382D:
        raise ValueError("Nintendo U8 매직이 아닙니다")
    root = u32(data, 4)
    count = u32(data, root + 8)
    string_base = root + count * 12
    result = []
    stack = []
    for index in range(1, count):
        node = root + index * 12
        raw_name = u32(data, node)
        kind = raw_name >> 24
        name_offset = raw_name & 0xFFFFFF
        end = data.index(b"\x00", string_base + name_offset)
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


def find_entry(data: bytes, wanted: str):
    for name, offset, size in entries(data):
        if name == wanted:
            return offset, size
    raise KeyError("U8 내부 파일을 찾지 못했습니다: %s" % wanted)


def read_palette(data: bytes, offset: int, count: int):
    if offset is None:
        return None
    end = offset + count * 2
    if offset < 0 or end > len(data):
        raise ValueError("팔레트 범위가 HSD 밖입니다: 0x%X" % offset)
    return [TX.rgb5a3(u16(data, offset + index * 2))
            for index in range(count)]


def validate_spec(data: bytes, item) -> None:
    struct_off = item["struct_off"]
    actual = (u16(data, struct_off + 4),
              u16(data, struct_off + 6),
              u32(data, struct_off + 8))
    expected = (item["width"], item["height"], item["fmt"])
    if actual != expected:
        raise ValueError("HSD 구조 불일치: 0x%X 실제=%s 예상=%s" %
                         (struct_off, actual, expected))
    start = item["image_off"]
    end = start + item["size"]
    if start < 0 or end > len(data):
        raise ValueError("HSD raw 범위가 파일 밖입니다: 0x%X" % start)


def render_text(item):
    width = item["width"]
    height = item["height"]
    background = item["background"]
    if background is None:
        background = WHITE if item["fmt"] == 14 else (0, 0, 0, 0)
    image = Image.new("RGBA", (width, height), background)
    draw = ImageDraw.Draw(image)
    stroke = item["stroke"]
    if stroke is None:
        stroke = 2 if height >= 28 else (1 if height >= 12 else 0)
    fill = item["fill"] or WHITE

    def draw_fitted(text, top, bottom, text_stroke):
        # Short labels need a little extra horizontal room because Korean
        # syllables are wider than the original half-width kana.
        box_height = bottom - top
        margin = 4 if box_height >= 16 else 1
        upper = min(112, max(8, box_height * 2))
        for size in range(upper, 2, -1):
            font = ImageFont.truetype(str(FONT), size)
            box = draw.textbbox((0, 0), text, font=font,
                                stroke_width=text_stroke)
            text_width = box[2] - box[0]
            text_height = box[3] - box[1]
            if text_width <= width - margin * 2 and text_height <= box_height - 2:
                x = (width - text_width) // 2 - box[0]
                y = top + (box_height - text_height) // 2 - box[1]
                draw.text((x, y), text, font=font, fill=fill,
                          stroke_width=text_stroke, stroke_fill=BLACK)
                return
        raise ValueError("텍스트가 이미지에 들어가지 않습니다: %s (%dx%d)" %
                         (text, width, box_height))

    secondary = item.get("secondary")
    if secondary:
        split = height // 2
        draw_fitted(item["text"], 0, split, stroke)
        draw_fitted(secondary, split, height, item.get("secondary_stroke", 1))
        return image

    draw_fitted(item["text"], 0, height, stroke)
    return image


def encode_image(image, item, source_hsd: bytes) -> bytes:
    if item["fmt"] == 8:
        raw = TX.encode_c4(
            image,
            read_palette(source_hsd, item["palette_off"],
                         item["palette_count"]),
            item["width"], item["height"],
        )
    elif item["fmt"] == 9:
        raw = TX.encode_c8(
            image,
            read_palette(source_hsd, item["palette_off"],
                         item["palette_count"]),
            item["width"], item["height"],
        )
    elif item["fmt"] == 14:
        raw = TX.encode_cmp(image, item["width"], item["height"])
    else:
        raise ValueError("지원하지 않는 HSD 포맷: %s" % item["fmt"])
    if len(raw) != item["size"]:
        raise AssertionError("이미지 raw 크기 변경: %s" % item["text"])
    return raw


def T(index, struct_off, image_off, width, height, fmt, palette_off,
      palette_count, text, **style):
    item = image_spec(struct_off, image_off, width, height, fmt,
                      palette_off, palette_count, text, **style)
    item["index"] = index
    return item


# bank100 HLH/HSD textures. The offsets are relative to each decompressed HLH
# member and were checked against the original HSD image structures.
HLH_TARGETS = {
    "BS_BTN_M": [
        T(1, 0x438, 0x39A0, 44, 12, 8, 0x3DC0, 8, "뒤로"),
        T(3, 0x2EC, 0x3820, 32, 12, 8, 0x3D40, 8, "뒤로"),
        T(5, 0x180, 0x3580, 44, 12, 8, 0x3CC0, 8, "설명"),
    ],
    "BS_FIELD": [
        T(2, 0x2A4, 0x0FC0, 54, 44, 8, 0x1840, 16, "기믹 있음"),
        T(3, 0x350, 0x1500, 100, 16, 8, 0x1880, 16, "BATTLE FIELD"),
    ],
    "BS_INFO": [
        T(3, 0x990, 0x86E0, 112, 18, 8, 0x9180, 16, "건담"),
        T(5, 0x78C, 0x8420, 48, 16, 8, 0x90C0, 16, "공격"),
        T(8, 0x588, 0x7FA0, 48, 16, 8, 0x9040, 16, "방어"),
        T(11, 0x384, 0x7E20, 48, 16, 8, 0x9000, 16, "속도"),
        T(14, 0x22C, 0x7BE0, 48, 18, 8, 0x8FC0, 16, "리더"),
    ],
    "BS_PCSR": [
        T(3, 0x114, 0x2AA0, 64, 54, 8, 0x3A20, 15, "COM"),
    ],
    "BS_START": [
        T(3, 0x648, 0x4120, 80, 30, 8, 0x5920, 16, "준비 OK!"),
        T(7, 0x378, 0x33E0, 128, 18, 8, 0x5860, 16,
          "B 유닛 선택"),
        # The first image is the white/mask companion of PRESS START.
        T(8, 0x154, 0x2720, 126, 22, 8, 0x57A0, 8,
          "PRESS START", stroke=0),
        T(9, 0x200, 0x2D20, 126, 22, 8, 0x57E0, 16,
          "PRESS START"),
    ],
    "BS_VS": [
        T(8, 0xC24, 0x12EC0, 448, 132, 8, 0x24280, 16,
          "간다!", fill=(255, 255, 255, 255)),
        T(9, 0xBB0, 0x10F40, 224, 66, 14, None, None,
          "간다!", fill=(150, 135, 246, 255)),
        T(10, 0xA24, 0xDCA0, 120, 68, 8, 0x241C0, 8,
          "공격!", stroke=3),
        T(11, 0xAF0, 0xFE60, 120, 68, 8, 0x24240, 16,
          "공격!", stroke=3),
    ],
    "IG_AITEM": [
        T(0, 0xC8, 0x4300, 128, 72, 9, 0x11140, 155,
          "+10초", fill=GOLD, stroke=2),
        T(2, 0x208, 0xD7A0, 200, 72, 9, 0x11540, 170,
          "번개", fill=(74, 215, 238, 255), stroke=3),
    ],
    "IG_HP": [
        T(4, 0xD4, 0xEC0, 68, 12, 8, 0x1400, 16,
          "LOCK Z"),
    ],
    "IG_PCSR": [
        T(3, 0x438, 0x2860, 64, 64, 8, 0x30E0, 16,
          "회복", fill=GREEN, stroke=2),
    ],
    "IG_RLOAD": [
        T(0, 0x54, 0x2A0, 88, 24, 8, 0x6C0, 16,
          "파워 다운"),
    ],
    "IG_TIME": [
        T(2, 0x6A4, 0xB580, 64, 24, 8, 0xBD60, 16,
          "TIME"),
    ],
    "IG_TUP": [
        T(0, 0x54, 0x580, 480, 108, 8, 0x6E80, 16,
          "TIME UP!", stroke=3),
        T(1, 0x100, 0x580, 480, 108, 8, 0x6E80, 16,
          "TIME UP!", stroke=3),
    ],
    "IG_WIN": [
        T(0, 0xB3C, 0x79C0, 200, 74, 8, 0xE840, 16, "BLUE"),
        T(1, 0xAC8, 0x6A00, 140, 52, 14, None, None,
          "BLUE", fill=(255, 170, 90, 255)),
        T(2, 0xCC4, 0xAF20, 280, 104, 8, 0xE8C0, 16, "WIN!", stroke=3),
        T(3, 0xC50, 0x9920, 173, 64, 14, None, None,
          "WIN!", fill=(246, 145, 170, 255)),
        T(5, 0x83C, 0x34C0, 200, 74, 8, 0xE800, 16, "RED"),
        T(6, 0x7C8, 0x2500, 140, 52, 14, None, None,
          "RED", fill=(246, 125, 145, 255)),
        T(7, 0x9C4, 0xAF20, 280, 104, 8, 0xE8C0, 16, "WIN!", stroke=3),
        T(8, 0x950, 0x5400, 173, 64, 14, None, None,
          "WIN!", fill=(170, 160, 246, 255)),
    ],
    "ITEM_N00": [
        T(0, 0x74, 0x3C0, 76, 40, 8, 0xA00, 16, "HP 회복 & +100"),
    ],
    "ITEM_N01": [
        T(0, 0x74, 0x480, 60, 40, 8, 0x980, 16, "특별 회복"),
    ],
    "ITEM_N02": [
        T(0, 0x74, 0x480, 86, 52, 8, 0xE20, 16, "스파킹 소울"),
    ],
    "ITEM_N03": [
        T(1, 0x120, 0x880, 54, 24, 8, 0xB60, 16, "속도"),
    ],
    "ITEM_N04": [
        T(1, 0x120, 0x880, 54, 24, 8, 0xB60, 16, "공격"),
    ],
    "ITEM_N05": [
        T(0, 0x74, 0x3C0, 54, 24, 8, 0x660, 16, "무적"),
    ],
    "ITEM_N06": [
        T(0, 0x74, 0x3C0, 64, 24, 8, 0x6C0, 16, "미사일"),
    ],
    "ITEM_N07": [
        T(0, 0x74, 0x3C0, 80, 28, 8, 0x8C0, 16, "판넬"),
    ],
    "ITEM_N08": [
        T(0, 0x74, 0x3C0, 66, 44, 8, 0xA80, 16, "폭렬 격투"),
    ],
    "ITEM_N09": [
        T(0, 0x74, 0x3C0, 64, 44, 8, 0x9C0, 16, "빔 반사"),
    ],
    "ITEM_N10": [
        T(0, 0x74, 0x3C0, 86, 32, 8, 0x940, 16, "하로볼"),
    ],
    "ITEM_N11": [
        T(0, 0x74, 0x3C0, 82, 32, 8, 0x940, 16, "스텔스"),
    ],
    "ITEM_N12": [
        T(0, 0x74, 0x3C0, 100, 24, 8, 0x8A0, 16, "지형 효과 무효"),
    ],
    "ITEM_N13": [
        T(0, 0x74, 0x3C0, 100, 24, 8, 0x8A0, 16, "격투 무효"),
    ],
    "ITEM_N14": [
        T(1, 0x140, 0x8A0, 54, 24, 8, 0xB80, 16, "속도"),
    ],
    "ITEM_N15": [
        T(1, 0x140, 0x8A0, 54, 24, 8, 0xB80, 16, "공격"),
    ],
    "ITEM_N16": [
        T(0, 0x74, 0x3C0, 90, 42, 8, 0xCC0, 16, "지형 효과 무효"),
    ],
    "ITEM_N17": [
        T(0, 0x54, 0x380, 140, 44, 8, 0x1100, 16,
          "HP 회복 +100 / 실드 회복"),
    ],
    "ITEM_N18": [
        T(0, 0x54, 0x380, 64, 24, 8, 0x680, 16, "부활"),
    ],
    "ITEM_N19": [
        T(0, 0x54, 0x380, 72, 24, 8, 0x6E0, 16, "캡슐"),
    ],
    "PB_AU_CR": [
        T(5, 0x418, 0x47A0, 112, 18, 8, 0x4DC0, 13,
          "포비든 건담"),
    ],
    "PB_BF_A": [
        T(5, 0x3A4, 0x5380, 112, 18, 8, 0x5FC0, 16, "건담"),
        T(8, 0x5A8, 0x5C40, 48, 18, 8, 0x6080, 16, "리더"),
        T(9, 0x24C, 0x5380, 112, 18, 8, 0x5FC0, 16, "건담"),
    ],
    "PB_BF_B": [
        T(5, 0x3A4, 0x5380, 112, 18, 8, 0x5FC0, 16, "건담"),
        T(8, 0x5A8, 0x5C40, 48, 18, 8, 0x6080, 16, "리더"),
        T(9, 0x24C, 0x5380, 112, 18, 8, 0x5FC0, 16, "건담"),
    ],
    "PB_BF_AT": [
        T(2, 0x594, 0x6520, 94, 32, 8, 0x6C20, 16, "ATTACK!"),
        T(3, 0x520, 0x5F20, 94, 32, 14, None, None,
          "ATTACK!", fill=(75, 194, 242, 255)),
        T(6, 0x2CC, 0x1CE0, 48, 32, 8, 0x6B60, 16, "OK"),
        T(7, 0x36C, 0x1FE0, 86, 32, 8, 0x6BA0, 16, "CANCEL"),
    ],
    "PB_C_INF": [
        T(2, 0x94, 0x1860, 50, 16, 8, 0x2880, 16, "BASE"),
        T(3, 0x160, 0x1A20, 68, 16, 8, 0x28C0, 16, "BATTLE!"),
    ],
    "PB_I_A": [
        T(8, 0x430, 0x7660, 86, 42, 8, 0xACE0, 16, "DAY"),
        T(10, 0x4FC, 0x7EA0, 120, 64, 8, 0xAD20, 16,
          "BLUE SIDE"),
        T(11, 0x5C8, 0x8DA0, 120, 64, 8, 0xAD60, 16,
          "RED SIDE"),
    ],
    "PB_I_P_A": [
        T(3, 0x458, 0x2400, 48, 24, 8, 0x30A0, 16, "평지"),
        T(6, 0x69C, 0x2D60, 60, 18, 8, 0x3160, 16, "특기 지형"),
    ],
    "PB_I_P_B": [
        T(4, 0x39C, 0x3140, 112, 18, 8, 0x3EE0, 16, "건담"),
    ],
    "PB_I_P_C": [
        T(6, 0x5DC, 0x102E0, 72, 8, 8, 0x12720, 7, "UNIT DATA"),
        T(7, 0x6A8, 0x10400, 65, 7, 8, 0x12760, 8, "COMMENT",
          stroke=0),
        T(9, 0x2944, 0x12380, 44, 11, 8, 0x12CA0, 8, "전환"),
        T(11, 0x228C, 0x11600, 62, 17, 8, 0x12B60, 16, "공격"),
        T(12, 0x2338, 0x11900, 65, 18, 8, 0x12BA0, 16, "방어"),
        T(13, 0x23E4, 0x11C60, 62, 17, 8, 0x12BE0, 16, "속도"),
        T(14, 0x2490, 0x11F60, 62, 17, 8, 0x12C20, 16, "포격"),
        T(23, 0x1D2C, 0x10FA0, 44, 20, 8, 0x12A60, 16, "범용"),
        T(58, 0x990, 0x10FA0, 44, 20, 8, 0x12A60, 16, "범용"),
        T(34, 0xAE8, 0x10820, 91, 7, 8, 0x12820, 8,
          "WEAPON DATA", stroke=0),
    ],
    "PB_P_BNS": [
        T(1, 0x448, 0x66C0, 130, 72, 8, 0x7AA0, 16, "점령!"),
        T(3, 0x55C, 0x66C0, 130, 72, 8, 0x7AA0, 16, "점령!"),
        T(5, 0x288, 0x2860, 118, 42, 8, 0x7A60, 16, "보너스!"),
        T(6, 0xA8, 0x1DC0, 85, 33, 8, 0x79E0, 16, "칸 추가"),
    ],
    "PB_PSTRT": [
        T(1, 0x250, 0x8800, 240, 128, 8, 0x13E20, 16,
          "BLUE SIDE"),
        T(2, 0x2FC, 0x8800, 240, 128, 8, 0x13E20, 16,
          "BLUE SIDE"),
        T(3, 0x41C, 0xC400, 200, 92, 8, 0x13E60, 16, "DAY"),
        T(9, 0x708, 0x101C0, 240, 128, 8, 0x13EE0, 16,
          "RED SIDE"),
        T(10, 0x7B4, 0x101C0, 240, 128, 8, 0x13EE0, 16,
          "RED SIDE"),
        T(11, 0xF8, 0x8000, 256, 16, 8, 0x13DE0, 14,
          "PHASE START", stroke=1),
        T(12, 0x1A4, 0x8000, 256, 16, 8, 0x13DE0, 14,
          "PHASE START", stroke=1),
    ],
    "PB_SY_BT": [
        T(4, 0x4D4, 0xCE40, 52, 12, 8, 0xE0C0, 8, "메뉴"),
        T(6, 0x66C, 0xDC00, 94, 14, 8, 0xE240, 8,
          "전투 맵"),
        T(7, 0x738, 0xDF00, 40, 14, 8, 0xE280, 8, "뒤로"),
    ],
    "PB_TIME": [
        T(4, 0x21C, 0x5480, 80, 22, 8, 0x5B00, 16, "시간"),
    ],
    "PIE_MENU": [
        T(2, 0x74, 0x760, 88, 36, 8, 0x12C0, 16, "이동"),
    ],
    "USEL_INF": [
        T(2, 0x430, 0x4F40, 64, 54, 8, 0x5880, 15, "COM"),
        T(4, 0x2B8, 0x43C0, 68, 32, 8, 0x5800, 8, "메뉴"),
    ],
}


NORMAL_TARGETS = {
    "Info/arc/bank103.arc": {
        "scen/sce_mission.dat": [
            T(62, 0x5D4, 0x15E60, 160, 52, 8, 0x1A020, 16,
              "시나리오 게임"),
        ],
    },
    "Info/arc/bank107.arc": {
        "scen/mission.dat": [
            T(1, 0x140, 0x60E0, 260, 64, 9, 0xB540, 256, "MISSION"),
        ],
        "scen/vs.dat": [
            T(19, 0x1608, 0x34000, 64, 54, 8, 0x3C060, 15,
              "COM"),
            T(20, 0x14B0, 0x32F80, 148, 28, 8, 0x3BFE0, 16,
              "PLAYER"),
            T(23, 0x1358, 0x34000, 64, 54, 8, 0x3C060, 15,
              "COM"),
            T(24, 0x1200, 0x32F80, 148, 28, 8, 0x3BFE0, 16,
              "PLAYER"),
        ],
    },
    # The multiplayer mission header is a byte-identical copy of the
    # single-player header, but lives in a different bank and is shown by a
    # separate scene path.
    "Info/arc/bank115.arc": {
        "scen/sub_title.dat": [
            T(2, 0x318, 0x1860, 160, 52, 8, 0x2AA0, 16,
              "시나리오 게임"),
        ],
    },
    # Multiplayer battle-entry scenes carry their own copies of the shared
    # PRESS START/준비 OK! labels. Keep the original English label intact.
    "Info/arc/bank113.arc": {
        "scen/usel_start.dat": [
            T(0, 0x0B4, 0x20A0, 126, 22, 8, 0x4A60, 8,
              "PRESS START", stroke=0),
            T(1, 0x160, 0x26A0, 126, 22, 8, 0x4AA0, 16,
              "PRESS START"),
            T(4, 0x410, 0x33E0, 80, 30, 8, 0x4B60, 16,
              "준비 OK!"),
        ],
    },
    "Info/arc/bank114.arc": {
        "scen/suv_start.dat": [
            T(0, 0x0B4, 0x20A0, 126, 22, 8, 0x4A60, 8,
              "PRESS START", stroke=0),
            T(1, 0x160, 0x26A0, 126, 22, 8, 0x4AA0, 16,
              "PRESS START"),
            T(4, 0x410, 0x33E0, 80, 30, 8, 0x4B60, 16,
              "준비 OK!"),
        ],
    },
}

# The original scenario header is a two-line texture: Korean title above the
# unchanged English subtitle. Keep both lines in the replacement image.
NORMAL_TARGETS["Info/arc/bank103.arc"]["scen/sce_mission.dat"][0][
    "secondary"
] = "SCENARIO GAME"
NORMAL_TARGETS["Info/arc/bank115.arc"]["scen/sub_title.dat"][0][
    "secondary"
] = "SCENARIO GAME"


def patch_hsd_images(hsd: bytes, items, preview_rows):
    work = bytearray(hsd)
    seen = {}
    for item in items:
        validate_spec(hsd, item)
        key = (item["image_off"], item["size"])
        image = render_text(item)
        if key in seen:
            if seen[key]["text"] != item["text"]:
                raise ValueError("같은 raw 버퍼에 서로 다른 문구가 지정됨")
            continue
        raw = encode_image(image, item, hsd)
        work[item["image_off"]:item["image_off"] + item["size"]] = raw
        seen[key] = item
        preview_rows.append((item["text"], image))
    return bytes(work), len(seen)


def save_preview(rows, filename):
    if not rows:
        return
    columns = 4
    cell_width = 300
    cell_height = 154
    rows_count = (len(rows) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * cell_width, rows_count * cell_height),
                      (31, 31, 40))
    draw = ImageDraw.Draw(sheet)
    caption = ImageFont.truetype(str(FONT), 13)
    for index, (label, image) in enumerate(rows):
        x = (index % columns) * cell_width
        y = (index // columns) * cell_height
        scale = min(272 / image.width, 112 / image.height)
        if scale <= 0:
            continue
        shown = image.resize(
            (max(1, int(image.width * scale)),
             max(1, int(image.height * scale))),
            Image.Resampling.NEAREST,
        )
        bg = Image.new("RGB", shown.size, (75, 75, 86))
        bg.paste(shown, (0, 0), shown)
        sheet.paste(bg, (x + (cell_width - bg.width) // 2, y + 28))
        draw.text((x + 5, y + 5), label, font=caption,
                  fill=(255, 255, 120))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / filename
    sheet.save(path)
    print("preview saved:", path)


def process_hlh(preview_rows):
    rel = "Info/arc/bank100.arc"
    source_container = (BASE / rel).read_bytes()
    work_container = bytearray(source_container)
    changed_assets = 0
    changed_images = 0
    for asset, items in HLH_TARGETS.items():
        entry = "scen/" + asset + ".HLH"
        offset, size = find_entry(source_container, entry)
        source_hlh = source_container[offset:offset + size]
        decoded = HLH.decode_hlh(source_hlh)
        asset_rows = []
        patched, count = patch_hsd_images(decoded, items, asset_rows)
        packed = HLH.encode_hlh(patched, slot_size=size)
        if len(packed) != size:
            raise AssertionError("HLH 슬롯 크기 변경: " + entry)
        if HLH.decode_hlh(packed) != patched:
            raise AssertionError("HLH 재복원 불일치: " + entry)
        work_container[offset:offset + size] = packed
        changed_assets += 1
        changed_images += count
        preview_rows.extend((asset + " " + label, image)
                            for label, image in asset_rows)
    if args.apply:
        dst = PATCHED / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(work_container)
        if dst.stat().st_size != len(source_container):
            raise AssertionError("bank100.arc 크기 변경")
    print("bank100 HLH:", changed_assets, "assets,", changed_images,
          "unique image buffers", "APPLIED" if args.apply else "(dry run)")


def process_normal(preview_rows):
    for rel, groups in NORMAL_TARGETS.items():
        source_container = (BASE / rel).read_bytes()
        work_container = bytearray(source_container)
        file_count = 0
        image_count = 0
        for entry, items in groups.items():
            offset, size = find_entry(source_container, entry)
            source_hsd = source_container[offset:offset + size]
            asset_rows = []
            patched, count = patch_hsd_images(source_hsd, items, asset_rows)
            work_container[offset:offset + size] = patched
            file_count += 1
            image_count += count
            preview_rows.extend((entry + " " + label, image)
                                for label, image in asset_rows)
        if args.apply:
            dst = PATCHED / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(work_container)
            if dst.stat().st_size != len(source_container):
                raise AssertionError("U8 컨테이너 크기 변경: " + rel)
        print(rel, ":", file_count, "HSD files,", image_count,
              "unique image buffers", "APPLIED" if args.apply else "(dry run)")


def main():
    if not args.apply and not args.preview:
        parser.error("--apply 또는 --preview를 지정하세요")
    if not FONT.exists():
        raise FileNotFoundError(FONT)
    hlh_rows = []
    normal_rows = []
    process_hlh(hlh_rows)
    process_normal(normal_rows)
    if args.preview:
        save_preview(hlh_rows, "scenario_battle_hlh_preview.png")
        save_preview(normal_rows, "scenario_ui_hsd_preview.png")
    print("scenario/battle image audit complete:",
          len(hlh_rows), "HLH rows,", len(normal_rows), "normal HSD rows")


if __name__ == "__main__":
    main()
