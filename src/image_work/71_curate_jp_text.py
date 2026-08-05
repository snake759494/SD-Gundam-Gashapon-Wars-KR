# -*- coding: utf-8 -*-
"""일본어 텍스트가 든 이미지를 별도 폴더(jp_text_images/)로 추리고 목록 생성.
그라운드-트루스 = 원본(files/) vs 패치본(text_patch_work/patched_files/) @Texture 블록 바이트 비교.
 - 라벨 뱅크의 텍스처 중 실제로 바뀐 것 = 번역완료(translated/)
 - 안 바뀐 텍스트 텍스처(대형 라벨/배너 등 수동목록) = 미번역(untranslated/)
커스텀 스프라이트(.dat, 타이틀로고)는 마크다운에 별도 표기(디코더 필요)."""
import sys, io, os, shutil, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tex_lib as TX
from PIL import Image
BASE = os.path.join(HERE, '..', 'files')
PF = os.path.join(HERE, '..', 'text_patch_work', 'patched_files')
OUT = os.path.join(HERE, 'jp_text_images')
if os.path.exists(OUT):
    shutil.rmtree(OUT)
os.makedirs(OUT)

# 라벨 뱅크(텍스트 라벨이 있는 후보). 아이콘 뱅크(103/104/105/107/109/112/115~117 등)는 제외.
LABEL_BANKS = ['bank101', 'bank102', 'bank106', 'bank108', 'bank110',
               'bank111', 'bank113', 'bank114', 'bank118']
# 미번역이지만 일본어 텍스트가 확실한 텍스처(수동 확인) — 번역본에 없으면 여기로.
UNTRANS_TEXT = {
    'Info/arc/bank102.arc': [0x309A0, 0x36E40, 0x3D2E0, 0x43780, 0x4A3A0, 0x840A0, 0x8B440, 0x927E0,
                             0x99B80, 0xA0F20, 0x51740, 0x58AE0, 0x5FE80, 0x67220, 0x6E5C0, 0x75960, 0x7CD00],
    'Info/arc/bank108.arc': [0x14B40, 0x1BEE0, 0x23280, 0x2A620, 0x319C0, 0x38D60, 0x40100],
    'Info/arc/bank113.arc': [0x4BEC0, 0x52F00, 0x593A0],
}

def blocks(b):
    out = {}
    for o in TX.find_blocks(b):
        try:
            hd = TX.parse_header(b, o)
        except Exception:
            continue
        if hd['palcnt'] not in (16, 256) or not (4 <= hd['w'] <= 1024 and 4 <= hd['h'] <= 1024):
            continue
        out[o] = hd
    return out

def save_png(b, off, hd, dstdir):
    img = TX.decode(b, off)
    if img is None:
        return None
    bg = Image.new('RGB', img.size, (90, 90, 95)); bg.paste(img, (0, 0), img)
    os.makedirs(dstdir, exist_ok=True)
    fn = '0x%X_%dx%d.png' % (off, img.width, img.height)
    bg.save(os.path.join(dstdir, fn))
    return (img.width, img.height)

rows = []
for bank in LABEL_BANKS:
    rel = 'Info/arc/%s.arc' % bank
    op = os.path.join(BASE, rel.replace('/', os.sep))
    pp = os.path.join(PF, rel.replace('/', os.sep))
    if not os.path.exists(op):
        continue
    o = open(op, 'rb').read()
    p = open(pp, 'rb').read() if os.path.exists(pp) else o
    obl = blocks(o)
    manual_un = set(UNTRANS_TEXT.get(rel, []))
    for off, hd in sorted(obl.items()):
        end = TX.block_end(o, off) if hasattr(TX, 'block_end') else None
        # compare block region: header..next-block-start (approx via image size)
        seg = 0x40 + hd['palcnt'] * 2 + hd['imgsize']
        changed = p[off:off + seg] != o[off:off + seg]
        if changed:
            tag = rel.replace('/', '_')
            sz = save_png(p, off, hd, os.path.join(OUT, 'translated', tag))  # 패치본(한글) 표시
            if sz:
                rows.append(('translated', rel, off, sz[0], sz[1]))
        elif off in manual_un:
            tag = rel.replace('/', '_')
            sz = save_png(o, off, hd, os.path.join(OUT, 'untranslated', tag))
            if sz:
                rows.append(('untranslated', rel, off, sz[0], sz[1]))

nt = sum(1 for r in rows if r[0] == 'translated')
nu = sum(1 for r in rows if r[0] == 'untranslated')
print('translated JP-text textures:', nt)
print('untranslated JP-text textures:', nu)
json.dump([{'status': r[0], 'file': r[1], 'off': '0x%X' % r[2], 'w': r[3], 'h': r[4]} for r in rows],
          open(os.path.join(HERE, 'jp_text_inventory.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('-> jp_text_images/{translated,untranslated}/, jp_text_inventory.json')
