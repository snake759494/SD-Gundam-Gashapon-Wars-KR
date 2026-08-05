# -*- coding: utf-8 -*-
"""도감(gallery.vsc) 설명 + 챌린지 미션(ab_mission.vsc) 한글 주입.
 - gallery: col0 유닛키 유지, 한글 설명을 ≤8줄×≤18자로 재줄바꿈해 col1~8 배치.
 - ab_mission: 타이틀(col0)/조건(col3)/설명(col4~6, ≤3줄) 배치, 나머지 키 유지.
동일 크기(전체 파일 원본크기에 공백 패딩) 캐리어 인코딩. --apply로 patched_files 기록."""
import sys, io, os, json, argparse
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from vsc_lib import vsc_decode, vsc_encode
BASE = os.path.join(HERE, '..', 'files')
OUT = os.path.join(HERE, 'patched_files')
ap = argparse.ArgumentParser(); ap.add_argument('--apply', action='store_true'); args = ap.parse_args()

carrier = {k: bytes.fromhex(v) for k, v in json.load(open(os.path.join(HERE, 'carrier_map.json'), encoding='utf-8')).items()}
NORM = {'·': '・', '–': '-', '—': '-'}
def is_h(c): return 0xAC00 <= ord(c) <= 0xD7A3
def enc(s):
    out = bytearray()
    for ch in s:
        ch = NORM.get(ch, ch)
        if is_h(ch): out += carrier[ch]
        else:
            try: out += ch.encode('cp932')
            except UnicodeEncodeError: out += b'?'
    return bytes(out)

def wrap(text, width, maxlines):
    """한글 텍스트를 width(글자) 단위 줄로. 공백 우선, 없으면 강제 분할. maxlines로 잘림."""
    words = text.split(' ')
    lines = []; cur = ''
    for w in words:
        while len(w) > width:                 # 긴 단어 강제 분할
            if cur: lines.append(cur); cur = ''
            lines.append(w[:width]); w = w[width:]
        if not cur: cur = w
        elif len(cur) + 1 + len(w) <= width: cur += ' ' + w
        else: lines.append(cur); cur = w
    if cur: lines.append(cur)
    if len(lines) > maxlines:                 # 초과 시 마지막 줄에 몰아넣되 width 유지 위해 재분배
        # 그리디로 다시(폭 무시 방지): 남은 줄 합쳐 잘라냄
        merged = ''.join(lines)
        lines = [merged[i:i+width] for i in range(0, len(merged), width)][:maxlines]
    return lines

_MASTER = os.path.join(HERE, 'translation_master.json')
def load_master_section(name):
    return json.load(open(_MASTER, encoding='utf-8')).get(name, {})

def process_gallery():
    rel = 'Kaw/gallery.vsc'
    raw = open(os.path.join(BASE, rel), 'rb').read()
    plain = vsc_decode(raw); text = plain.decode('cp932')
    rows = [ln.split(',') for ln in text.split('\r\n')]
    ko = load_master_section('gallery')     # {row: {jp, ko}}
    changed = 0
    for ri, r in enumerate(rows):
        e = ko.get(str(ri))
        if not e or not e.get('ko'):
            continue
        lines = wrap(e['ko'].strip(), 18, 8)
        for c in range(1, 9):                 # col1~8
            r[c] = lines[c-1] if c-1 < len(lines) else ''
        changed += 1
    return rel, raw, plain, rows, changed

def process_mission():
    rel = 'Spb/ab_mission/ab_mission.vsc'
    raw = open(os.path.join(BASE, rel), 'rb').read()
    plain = vsc_decode(raw); text = plain.decode('cp932')
    rows = [ln.split(',') for ln in text.split('\r\n')]
    ko = load_master_section('ab_mission')   # {row: {title,cond,desc,...}}
    changed = 0
    for ri, r in enumerate(rows):
        t = ko.get(str(ri))
        if not t:
            continue
        if len(r) > 0 and t.get('title'): r[0] = t['title'].strip()
        if len(r) > 3 and t.get('cond'):  r[3] = t['cond'].strip()
        if t.get('desc'):
            dl = wrap(t['desc'].strip(), 24, 3)
            for k, ci in enumerate((4, 5, 6)):
                if ci < len(r): r[ci] = dl[k] if k < len(dl) else ''
        changed += 1
    return rel, raw, plain, rows, changed

def finish(rel, raw, plain, rows):
    new_plain = b'\r\n'.join(b','.join(enc(c) for c in r) for r in rows)
    if len(new_plain) > len(plain):
        return None, len(new_plain) - len(plain)
    pad = len(plain) - len(new_plain)
    if new_plain.endswith(b'\r\n'): new_plain = new_plain[:-2] + b' ' * pad + b'\r\n'
    else: new_plain = new_plain + b' ' * pad
    assert len(new_plain) == len(plain)
    new_raw = vsc_encode(new_plain)
    assert len(new_raw) == len(raw)
    return new_raw, 0

for proc in (process_gallery, process_mission):
    rel, raw, plain, rows, changed = proc()
    new_raw, over = finish(rel, raw, plain, rows)
    if new_raw is None:
        print('[OVERFLOW] %s +%d bytes' % (rel, over)); continue
    print('%s: %d rows translated, fits (size==orig %s)' % (rel, changed, len(new_raw) == len(raw)))
    if args.apply:
        dst = os.path.join(OUT, rel); os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, 'wb').write(new_raw)
        print('  APPLIED', rel)
