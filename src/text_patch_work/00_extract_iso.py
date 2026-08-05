# -*- coding: utf-8 -*-
"""[부트스트랩] 사용자 본인의 원본 GameCube ISO에서 files/ 와 sys/ 를 추출.
저작물이라 저장소에 포함할 수 없는 게임 데이터를 각자 준비하는 단계.

사용:
  python text_patch_work/00_extract_iso.py --iso "SD Gundam Gashapon Wars.iso"

결과: <repo>/files/**  (게임 리소스)  +  <repo>/sys/main.dol 등
"""
import sys, io, os, struct, argparse
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')

ap = argparse.ArgumentParser()
ap.add_argument('--iso', required=True, help='원본 ISO 경로 (본인 소유 사본)')
ap.add_argument('--out', default=ROOT, help='추출 대상 루트(기본: 저장소 루트)')
args = ap.parse_args()

iso_path = args.iso
if not os.path.exists(iso_path):
    raise SystemExit('ISO를 찾을 수 없습니다: %s' % iso_path)

f = open(iso_path, 'rb')
hdr = f.read(0x440)
game_id = hdr[:6].decode('ascii', 'replace')
if game_id != 'GGPJB2':
    print('경고: 게임 ID가 GGPJB2가 아닙니다 (%s). 일본판 원본인지 확인하세요.' % game_id)

dol_off = struct.unpack('>I', hdr[0x420:0x424])[0]
fst_off = struct.unpack('>I', hdr[0x424:0x428])[0]
fst_sz = struct.unpack('>I', hdr[0x428:0x42C])[0]

# --- sys/ ---
sysdir = os.path.join(args.out, 'sys')
os.makedirs(sysdir, exist_ok=True)
def dump(name, off, size):
    f.seek(off); open(os.path.join(sysdir, name), 'wb').write(f.read(size))
dump('boot.bin', 0, 0x440)
dump('bi2.bin', 0x440, 0x2000)
f.seek(0x2440)
appldr_hdr = f.read(0x20)
appl_size = struct.unpack('>I', appldr_hdr[0x14:0x18])[0] + struct.unpack('>I', appldr_hdr[0x18:0x1C])[0]
dump('apploader.img', 0x2440, 0x20 + appl_size)
dump('fst.bin', fst_off, fst_sz)

# main.dol 크기 = DOL 헤더의 최대 (offset+size)
f.seek(dol_off); dh = f.read(0x100)
dol_size = 0
for i in range(18):                      # 7 text + 11 data
    o = struct.unpack('>I', dh[i*4:i*4+4])[0]
    s = struct.unpack('>I', dh[0x90 + i*4: 0x90 + i*4+4])[0]
    if o and s:
        dol_size = max(dol_size, o + s)
dump('main.dol', dol_off, dol_size)
print('sys/ 추출 완료 (main.dol %d bytes)' % dol_size)

# --- FST 순회 -> files/ ---
f.seek(fst_off); fst = f.read(fst_sz)
N = struct.unpack('>I', fst[8:12])[0]
str_base = N * 12
def name_at(o):
    e = fst.index(b'\x00', str_base + o)
    return fst[str_base + o:e].decode('cp932', 'replace')

filesdir = os.path.join(args.out, 'files')
os.makedirs(filesdir, exist_ok=True)
stack = []          # (name, end_index)
count = 0; total_bytes = 0
for i in range(1, N):
    while stack and i >= stack[-1][1]:
        stack.pop()
    node = fst[i*12:(i+1)*12]
    typ = node[0]
    noff = struct.unpack('>I', b'\x00' + node[1:4])[0]
    a, b = struct.unpack('>II', node[4:12])
    name = name_at(noff)
    if typ == 1:                                  # 디렉터리
        stack.append((name, b))
        os.makedirs(os.path.join(filesdir, *[d[0] for d in stack]), exist_ok=True)
    else:                                          # 파일
        rel = os.path.join(*[d[0] for d in stack], name) if stack else name
        dst = os.path.join(filesdir, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        f.seek(a)
        with open(dst, 'wb') as g:
            left = b
            while left > 0:
                chunk = f.read(min(1 << 22, left))
                if not chunk: break
                g.write(chunk); left -= len(chunk)
        count += 1; total_bytes += b
f.close()
print('files/ 추출 완료: %d 파일, %.1f MB' % (count, total_bytes / 1048576))
print()
print('다음 단계:')
print('  python text_patch_work/06_build_font.py')
print('  python text_patch_work/BUILD_FROM_MASTER.py --iso --src-iso "%s"' % iso_path)
