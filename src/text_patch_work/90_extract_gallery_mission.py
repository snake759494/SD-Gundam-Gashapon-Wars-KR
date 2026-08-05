# -*- coding: utf-8 -*-
"""gallery.vsc 도감 설명 + ab_mission.vsc 챌린지 미션 텍스트 추출(번역 소스).
루비 |漢字(かな) -> 표시 base(漢字)만 남겨 번역용 원문 생성. 셀 구조/바이트예산 보존."""
import sys, io, os, re, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from vsc_lib import vsc_decode
BASE = os.path.join(HERE, '..', 'files')

def rows(rel):
    return [r.split(',') for r in vsc_decode(open(os.path.join(BASE, rel), 'rb').read()).decode('cp932').split('\r\n')]

def strip_ruby(s):
    s = re.sub(r'\(([^)]*)\)', '', s)   # 읽기 제거
    return s.replace('|', '')            # 루비 마커 제거

def cellbytes(s):
    return len(s.encode('cp932', 'replace'))

# --- gallery: 유닛별 col1~8 합쳐 base 원문 ---
g = rows('Kaw/gallery.vsc')
gallery = []
for ri, r in enumerate(g):
    if ri < 2 or not r[0]:
        continue
    cells = r[1:9]
    base = strip_ruby(''.join(cells)).strip()
    if not base:
        continue
    budgets = [cellbytes(c) for c in cells]     # 셀별 원본 바이트(참고)
    gallery.append({'row': ri, 'unit_key': r[0], 'jp': base,
                    'total_budget': sum(budgets), 'ncells': 8})

# --- ab_mission: 타이틀(col0)/조건(col3)/설명(col4~6) ---
a = rows('Spb/ab_mission/ab_mission.vsc')
missions = []
for ri, r in enumerate(a):
    if ri < 1 or len(r) < 5 or not r[0].strip():
        continue
    title = strip_ruby(r[0]).strip()
    cond = strip_ruby(r[3]).strip() if len(r) > 3 else ''
    desc = strip_ruby(''.join(r[4:7])).strip() if len(r) > 4 else ''
    missions.append({'row': ri, 'jp_title': title, 'jp_cond': cond, 'jp_desc': desc,
                     'title_budget': cellbytes(r[0]),
                     'cond_budget': cellbytes(r[3]) if len(r) > 3 else 0,
                     'desc_budget': sum(cellbytes(c) for c in r[4:7])})

json.dump(gallery, open(os.path.join(HERE, 'gallery_src.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
json.dump(missions, open(os.path.join(HERE, 'abmission_src.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('gallery units:', len(gallery), '-> gallery_src.json')
print('ab missions:', len(missions), '-> abmission_src.json')
print('gallery 총 원문글자:', sum(len(x['jp']) for x in gallery))
print('mission 총 원문글자:', sum(len(x['jp_title']+x['jp_cond']+x['jp_desc']) for x in missions))
