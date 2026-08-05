# -*- coding: utf-8 -*-
"""zip에 담긴 텍스처(사용자 지정)를 일본어 원본으로 되돌림.
파일명 iNNN_0xOFFSET_WxH.png -> 오프셋. all_inventory.json으로 오프셋→뱅크파일 매핑.
patched_files의 해당 텍스처 이미지 영역을 원본 files/ 바이트로 복원(다른 텍스처·팔레트 보존)."""
import sys, io, os, re, json, zipfile
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tex_lib as TX
BASE = os.path.join(HERE, '..', 'files')
PF = os.path.join(HERE, '..', 'text_patch_work', 'patched_files')
ZIP = os.path.join(HERE, '한글패치대상이미지', '3', '3.zip')

inv = json.load(open(os.path.join(HERE, 'all_inventory.json'), encoding='utf-8'))
off2file = {}
for e in inv:
    off2file.setdefault(e['off'], e['file'])

names = zipfile.ZipFile(ZIP).namelist()
offs = []
for n in names:
    m = re.search(r'0x([0-9A-Fa-f]+)', n)
    if m:
        offs.append(int(m.group(1), 16))

# group by file
by_file = {}
for off in offs:
    rel = off2file.get(off)
    if rel is None:
        print('WARN offset 0x%X not in inventory' % off); continue
    by_file.setdefault(rel, []).append(off)

reverted = 0; noop = 0
for rel, olist in sorted(by_file.items()):
    o = open(os.path.join(BASE, rel.replace('/', os.sep)), 'rb').read()
    pf = os.path.join(PF, rel.replace('/', os.sep))
    if not os.path.exists(pf):
        print('%s: not in patched_files (already original) -> %d texture(s) no-op' % (rel, len(olist)))
        noop += len(olist); continue
    p = bytearray(open(pf, 'rb').read())
    fch = 0
    for off in sorted(olist):
        hd = TX.parse_header(o, off)
        s = hd['img_off']; e = s + hd['imgsize']
        if bytes(p[s:e]) != o[s:e]:
            p[s:e] = o[s:e]        # restore original JP image data
            fch += 1; reverted += 1
        else:
            noop += 1
    if fch:
        assert len(p) == len(o)
        open(pf, 'wb').write(bytes(p))
        print('%s: reverted %d texture(s) to JP' % (rel, fch))
    else:
        print('%s: all %d already original (no-op)' % (rel, len(olist)))
print('TOTAL reverted:', reverted, '| already-original:', noop)
