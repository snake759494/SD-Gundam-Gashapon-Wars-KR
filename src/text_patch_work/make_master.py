# -*- coding: utf-8 -*-
"""모든 도메인의 일본어→한글 번역을 하나의 translation_master.json으로 통합.
소스: ko_final(+unique_jp) / unit_name_map / help_final / disp_map / field_map
      / dol_inject_all(+dol_extra,dol_exclude) / image_work/image_labels.json
이후 이 마스터만 수정하고 BUILD_FROM_MASTER.py 실행하면 패치가 재생성됨."""
import sys, io, os, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(HERE, '..', 'image_work')
def L(p, base=HERE):
    return json.load(open(os.path.join(base, p), encoding='utf-8'))

# --- dialogue (SPB): id -> {jp, ko} ---
uniq = L('unique_jp.json')                       # [{id, jp}]
ko = L('ko_final.json')                           # {id: ko}
jp_by_id = {str(u['id']): u['jp'] for u in uniq}
dialogue = {}
for i in sorted(jp_by_id, key=lambda x: int(x)):
    dialogue[i] = {'jp': jp_by_id[i], 'ko': ko.get(i, jp_by_id[i])}

disp = L('disp_map.json')                          # {char:{}, terrain:{}}

# --- gallery 도감 설명 (row -> {jp, ko}) ---
gsrc = {str(x['row']): x['jp'] for x in L('gallery_src.json')}
gko = {}
for _i in range(8):
    _p = os.path.join(HERE, 'trans_batch', 'gallery_%d.out.json' % _i)
    if os.path.exists(_p):
        gko.update(json.load(open(_p, encoding='utf-8')))
gallery = {r: {'jp': gsrc.get(r, ''), 'ko': gko.get(r, '')} for r in sorted(gsrc, key=int)}

# --- ab_mission 챌린지 미션 (row -> {jp_*, title/cond/desc}) ---
msrc = {str(x['row']): x for x in L('abmission_src.json')}
mko = {}
for _i in range(4):
    _p = os.path.join(HERE, 'trans_batch', 'mission_%d.out.json' % _i)
    if os.path.exists(_p):
        mko.update(json.load(open(_p, encoding='utf-8')))
abmission = {}
for r in sorted(msrc, key=int):
    s = msrc[r]; k = mko.get(r, {})
    abmission[r] = {'jp_title': s['jp_title'], 'title': k.get('title', ''),
                    'jp_cond': s['jp_cond'], 'cond': k.get('cond', ''),
                    'jp_desc': s['jp_desc'], 'desc': k.get('desc', '')}

master = {
    '_meta': {
        'desc': 'SD건담 가샤폰 워즈 한글패치 통합 번역 마스터. 이 파일만 수정 후 BUILD_FROM_MASTER.py 실행.',
        'sections': {
            'dialogue': 'SPB 대사 (id->{jp,ko}). ko만 수정.',
            'unit_names': '유닛명 vsc (jp->ko). 원본보다 길면 오버플로로 미적용(짧게 하면 적용).',
            'help': '도움말 vsc 셀 목록. ko 수정.',
            'disp_char': '캐릭터 표시명 vsc (jp->ko).',
            'disp_terrain': '지형명 vsc (jp->ko).',
            'field': '맵 선택 vsc (row->{col:ko}).',
            'dol': 'main.dol UI 문자열 [{jp,ko,occ,...}]. ko 수정(예산 초과 시 잘림).',
            'dol_extra': 'main.dol 추가 문자열.',
            'dol_exclude': '번역 제외할 jp 문자열 목록(AI enum·키 등).',
            'images': '라벨 이미지 텍스트(뱅크 offset->한글). 렌더 재작화.',
            'gallery': '도감 유닛 설명 (row->{jp,ko}). ko만 수정, 8줄×18자로 자동 줄바꿈.',
            'ab_mission': '챌린지 미션 (row->{title,cond,desc}). 표시열만, 시작유닛 키는 유지.',
        },
        'build': 'python text_patch_work/BUILD_FROM_MASTER.py --apply',
    },
    'dialogue': dialogue,
    'unit_names': L('unit_name_map.json'),
    'help': L('help_final.json'),
    'disp_char': disp['char'],
    'disp_terrain': disp['terrain'],
    'field': L('field_map.json'),
    'dol': L('dol_inject_all.json'),
    'dol_extra': L('dol_extra.json'),
    'dol_exclude': L('dol_exclude_keys.json'),
    'images': L('image_labels.json', IMG),
    'gallery': gallery,
    'ab_mission': abmission,
}

out = os.path.join(HERE, 'translation_master.json')
json.dump(master, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('translation_master.json written')
print('  dialogue:', len(dialogue))
print('  unit_names:', len(master['unit_names']))
print('  help:', len(master['help']))
print('  disp_char:', len(master['disp_char']), 'disp_terrain:', len(master['disp_terrain']))
print('  field rows:', len(master['field']))
print('  dol:', len(master['dol']), '+extra', len(master['dol_extra']), 'exclude', len(master['dol_exclude']))
print('  image groups:', list(master['images'].keys()))
print('  gallery:', len(master['gallery']), ' ab_mission:', len(master['ab_mission']))
print('  size: %.1f KB' % (os.path.getsize(out) / 1024))
