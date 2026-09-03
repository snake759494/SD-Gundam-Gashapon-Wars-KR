# -*- coding: utf-8 -*-
"""translation_master.json 하나로부터 전체 한글패치를 재생성.
   마스터 -> 각 도메인 데이터파일 -> 검증된 주입 스크립트 실행 -> (옵션)ISO 빌드.
사용: python BUILD_FROM_MASTER.py            # patched_files/ + patched_main.dol 재생성
      python BUILD_FROM_MASTER.py --iso      # 위 + patched ISO 빌드
전제: patched_main.dol(폰트 적용본)이 이미 존재해야 함(폰트빌드는 텍스트번역과 별개, 06_build_font).
"""
import sys, io, os, json, subprocess, argparse
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(HERE, '..', 'image_work')
PY = sys.executable
ap = argparse.ArgumentParser()
ap.add_argument('--iso', action='store_true', help='ISO까지 빌드')
ap.add_argument('--src-iso', default=None, help='원본 ISO 경로(본인 사본). 생략 시 12_build_iso 기본값')
ap.add_argument('--out-iso', default=None, help='출력 ISO 경로')
args = ap.parse_args()

M = json.load(open(os.path.join(HERE, 'translation_master.json'), encoding='utf-8'))

def dump(rel, obj, base=HERE):
    p = os.path.join(base, rel)
    json.dump(obj, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

# 1) 마스터 -> 도메인 데이터파일 분배
dump('ko_final.json', {i: d['ko'] for i, d in M['dialogue'].items()})
dump('unit_name_map.json', M['unit_names'])
dump('help_final.json', M['help'])
dump('disp_map.json', {'char': M['disp_char'], 'terrain': M['disp_terrain']})
dump('field_map.json', M['field'])
dump('dol_inject_all.json', M['dol'])
dump('dol_extra.json', M['dol_extra'])
dump('dol_exclude_keys.json', M['dol_exclude'])
dump('image_labels.json', M['images'], IMG)
dump('sound_volume.json', M['sound_volume'])
print('[1] 도메인 데이터파일 재생성 완료')

# 2) 주입 스크립트 실행(검증된 순서)
def run(script, cwd, apply=True, extra=()):
    cmd = [PY, script] + (['--apply'] if apply else []) + list(extra)
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding='utf-8')
    tag = os.path.basename(script)
    if r.returncode != 0:
        print('  ✗ %s FAILED' % tag)
        print(r.stdout[-800:]); print(r.stderr[-800:])
        raise SystemExit(1)
    last = [l for l in r.stdout.strip().splitlines() if l.strip()]
    print('  ✓ %s : %s' % (tag, last[-1] if last else 'ok'))

print('[2] 주입 실행')
# SPB 대사
run('07_encode_inject.py', HERE)
run('54_spb_speaker_names.py', HERE)
run('53_fix_spb_refs.py', HERE, apply=False)   # 참조 되돌림(플래그 없음)
# vsc (46 표시명/지형 -> 52 화자plate col0/2 가 pbmode_character 최종본)
run('46_disp_inject.py', HERE)
run('52_char_col0_safe.py', HERE)
run('51_field_inject.py', HERE)
run('33_vsc_inject.py', HERE)                  # help 적용, 유닛명 오버플로는 자동 skip
run('91_inject_gallery_mission.py', HERE)      # 도감 설명 + 챌린지 미션
run('92_inject_sound_volume.py', HERE)         # 사운드 플레이어 BGM 제목/설명
# dol (patched_main.dol 제자리 재적용, 멱등)
run('43_dol_inject.py', HERE)
# 이미지 라벨
run('60_label_inject.py', IMG)
run('61_rule_labels.py', IMG)
run('62_misc_labels.py', IMG)
run('63_menu_titles.py', IMG)                  # 외부 C4/CMP 메뉴 타이틀(25쌍)
run('64_nested_menu_titles.py', IMG)           # 중첩 U8/HSD 메뉴 타이틀(4쌍+1개)
run('75_custom_dat_sprites.py', IMG)           # HAL DAT 미션 제목/결과 화면
run('76_custom_ui_assets.py', IMG)              # 타이틀 로고/전투 조작설명 이미지
run('77_nested_ui_assets.py', IMG)              # 중복 HSD 헤더/로고/gtitle 이미지
print('[2] 완료: patched_files/ + patched_main.dol 재생성')

# 3) ISO
if args.iso:
    print('[3] ISO 빌드')
    _ex = []
    if args.src_iso: _ex += ['--iso', args.src_iso]
    if args.out_iso: _ex += ['--out', args.out_iso]
    run('12_build_iso.py', HERE, extra=_ex)
    print('[3] 완료')
else:
    print('[3] ISO 건너뜀 (--iso로 빌드)')
