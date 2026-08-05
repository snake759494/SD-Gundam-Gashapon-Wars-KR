# -*- coding: utf-8 -*-
"""curated jp_text_images/ 폴더에서 translated/untranslated 통합 컨택트시트 2장 생성."""
import sys, io, os, glob
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, 'jp_text_images')

def sheet(group):
    files = sorted(glob.glob(os.path.join(ROOT, group, '**', '*.png'), recursive=True))
    if not files:
        return
    cols, cw, ch = 3, 300, 130
    rows = (len(files) + cols - 1) // cols
    im = Image.new('RGB', (cols * cw, rows * ch), (30, 30, 30))
    d = ImageDraw.Draw(im)
    for i, f in enumerate(files):
        cx, cy = (i % cols) * cw, (i // cols) * ch
        t = Image.open(f).convert('RGB')
        sc = min((cw - 10) / t.width, (ch - 26) / t.height, 3.0)
        t = t.resize((max(1, int(t.width * sc)), max(1, int(t.height * sc))))
        im.paste(t, (cx + 5, cy + 22))
        bank = os.path.basename(os.path.dirname(f)).replace('Info_arc_', '').replace('.arc', '')
        d.text((cx + 4, cy + 3), '%s %s' % (bank, os.path.basename(f).split('_')[0]), fill=(0, 255, 0))
        d.text((cx + 4, cy + 12), os.path.basename(f).split('_', 1)[1][:34], fill=(180, 180, 180))
    out = os.path.join(HERE, 'jp_text_%s_sheet.png' % group)
    im.save(out)
    print('%s: %d imgs -> %s' % (group, len(files), os.path.basename(out)))

sheet('translated')
sheet('untranslated')
