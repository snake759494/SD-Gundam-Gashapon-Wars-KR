# -*- coding: utf-8 -*-
"""사운드 플레이어 BGM 제목/설명(Sound/volume.vsc) 한글 주입.

번호·SE 키·볼륨 값은 그대로 두고 화면 표시 열인 BGM 제목(6열)과
설명(8열)만 교체한다. VSC는 파일 전체를 역순+XOR로 저장하므로,
캐리어 인코딩 후 원본 파일 길이에 맞춰 후행 공백을 채운다.
"""
import argparse
import io
import json
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, "..", "files")
OUT = os.path.join(HERE, "patched_files")
FONT = os.path.join(HERE, "..", "fonts", "NanumSquareNeocBd.ttf")
PREVIEW = os.path.join(HERE, "..", "image_work", "out", "sound_volume_preview.png")

sys.path.insert(0, HERE)
from sound_volume_lib import load_carrier, serialize_rows, translate_rows
from vsc_lib import vsc_decode

ap = argparse.ArgumentParser()
ap.add_argument("--apply", action="store_true", help="patched_files에 바이너리 패치 저장")
ap.add_argument("--preview", action="store_true", help="곡 목록 검수용 PNG 저장")
args = ap.parse_args()


def save_preview(rows):
    from PIL import Image, ImageDraw, ImageFont

    rows = [row for row in rows if len(row) >= 8]
    font = ImageFont.truetype(FONT, 18)
    small = ImageFont.truetype(FONT, 15)
    line_h = 34
    width = 1100
    sheet = Image.new("RGB", (width, line_h * len(rows) + 54), (30, 30, 38))
    draw = ImageDraw.Draw(sheet)
    draw.text((18, 10), "사운드 플레이어 BGM 목록", font=font, fill=(255, 255, 100))
    draw.text((18, 37), "번호", font=small, fill=(170, 210, 230))
    draw.text((95, 37), "곡목", font=small, fill=(170, 210, 230))
    draw.text((590, 37), "설명", font=small, fill=(170, 210, 230))
    for i, row in enumerate(rows):
        y = 54 + i * line_h
        fill = (238, 238, 242) if i % 2 == 0 else (190, 196, 204)
        draw.text((18, y), row[0], font=small, fill=fill)
        draw.text((95, y), row[5], font=small, fill=fill)
        draw.text((590, y), row[7], font=small, fill=fill)
    os.makedirs(os.path.dirname(PREVIEW), exist_ok=True)
    sheet.save(PREVIEW)
    print("preview saved:", PREVIEW)


def main():
    rel = "Sound/volume.vsc"
    source = os.path.join(BASE, rel)
    raw = open(source, "rb").read()
    mapping_path = os.path.join(HERE, "sound_volume.json")
    if not os.path.exists(mapping_path):
        mapping_path = os.path.join(HERE, "translation_master.json")
        mapping = json.load(open(mapping_path, encoding="utf-8"))["sound_volume"]
    else:
        mapping = json.load(open(mapping_path, encoding="utf-8"))
    carrier = load_carrier(os.path.join(HERE, "carrier_map.json"))
    rows, changed = translate_rows(vsc_decode(raw), mapping)
    new_raw, overflow = serialize_rows(rows, len(vsc_decode(raw)), carrier)
    if new_raw is None:
        raise ValueError("Sound/volume.vsc 오버플로: +%d bytes" % overflow)
    print("%s: %d rows translated, size=%d (original=%d)" %
          (rel, changed, len(new_raw), len(raw)))
    if args.preview:
        save_preview(rows)
    if args.apply:
        dst = os.path.join(OUT, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, "wb") as f:
            f.write(new_raw)
        if os.path.getsize(dst) != len(raw):
            raise AssertionError("Sound/volume.vsc 파일 크기 변경")
        print("APPLIED", rel)


if __name__ == "__main__":
    main()
