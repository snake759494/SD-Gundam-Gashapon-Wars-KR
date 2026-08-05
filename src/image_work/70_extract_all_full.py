# -*- coding: utf-8 -*-
"""전 파일 @Texture 전수 추출 -> PNG + 파일별 컨택트시트 + 인벤토리.
Effect/Info/tpl/cardicon 등 모든 @Texture 포함(작은 아이콘까지)."""
import sys, io, os, glob, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tex_lib as TX
from PIL import Image, ImageDraw
BASE = os.path.join(HERE, '..', 'files')
OUT = os.path.join(HERE, 'all_images')
SHEETS = os.path.join(HERE, 'all_sheets')
os.makedirs(OUT, exist_ok=True); os.makedirs(SHEETS, exist_ok=True)
BG = (90, 90, 95)

def process(path):
    b = open(path, 'rb').read()
    if b'@Texture' not in b:
        return []
    items = []
    for o in TX.find_blocks(b):
        try:
            hd = TX.parse_header(b, o)
        except Exception:
            continue
        if hd['palcnt'] not in (16, 256) or not (4 <= hd['w'] <= 1024 and 4 <= hd['h'] <= 1024):
            continue
        img = TX.decode(b, o)
        if img is not None:
            items.append((o, img))
    return items

targets = sorted(glob.glob(os.path.join(BASE, '**', '*'), recursive=True))
inventory = []
for tp in targets:
    if not os.path.isfile(tp):
        continue
    rel = os.path.relpath(tp, BASE).replace(os.sep, '/')
    try:
        items = process(tp)
    except Exception:
        continue
    if not items:
        continue
    tag = rel.replace('/', '_')
    subdir = os.path.join(OUT, tag)
    os.makedirs(subdir, exist_ok=True)
    # save each PNG (on gray bg for visibility) + transparent original
    for idx, (o, img) in enumerate(items):
        bg = Image.new('RGB', img.size, BG); bg.paste(img, (0, 0), img)
        bg.save(os.path.join(subdir, 'i%03d_0x%X_%dx%d.png' % (idx, o, img.width, img.height)))
        inventory.append({'file': rel, 'idx': idx, 'off': o, 'w': img.width, 'h': img.height})
    # contact sheet
    cols = 4; cw, ch = 200, 90
    rows = (len(items) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * cw, max(1, rows) * ch), (40, 40, 40))
    d = ImageDraw.Draw(sheet)
    for idx, (o, img) in enumerate(items):
        cx = (idx % cols) * cw; cy = (idx // cols) * ch
        bg = Image.new('RGB', img.size, BG); bg.paste(img, (0, 0), img)
        sc = min((cw - 8) / img.width, (ch - 16) / img.height, 2.0)
        disp = bg.resize((max(1, int(img.width * sc)), max(1, int(img.height * sc))))
        sheet.paste(disp, (cx + 4, cy + 14))
        d.text((cx + 3, cy + 2), 'i%d 0x%X %dx%d' % (idx, o, img.width, img.height), fill=(0, 255, 0))
    sheet.save(os.path.join(SHEETS, tag + '.png'))
    print('%s: %d textures' % (rel, len(items)))

json.dump(inventory, open(os.path.join(HERE, 'all_inventory.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
print('TOTAL textures:', len(inventory), '-> PNGs in all_images/, sheets in all_sheets/')
