"""Patch actual runtime DOL textures and the first HLH member of chr*.arc.

Names are images, independent of VSC resource lookup keys. Keep every pointer,
palette, compressed member slot and file length unchanged.
"""
from pathlib import Path
import argparse
import struct
import sys
from PIL import Image, ImageDraw, ImageFont
import tex_lib as TX
import hlh_codec as HLH

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / "files"
TEXT = HERE.parent / "text_patch_work"
FONT = HERE.parent / "fonts/NanumSquareNeocBd.ttf"
CHAR_NAMES = "플레이어|아무로|샤아|브라이트|키시리아|기렌|카미유|제리드|하만|시로코|포우|키라|크루제|발트펠트|마류|신".split("|")
# Physical texture order, checked against the decoded Japanese contact sheets.
UNIT_NAMES = """건담|건캐논|건탱크|짐|볼|건담 Ez8|알렉스|코어 부스터|자쿠|샤아 자쿠|자쿠|구프|돔|
겔구그|샤아 겔구그|걍|즈고크|샤아 즈고크|조크|구프 커스텀|앗가이|켐퍼|자크렐로|빅잠|엘메스|지옹|건담 Mk-II|백식|
Z 건담|네모|릭 디아스|메타스|ZZ 건담|슈퍼 건담|건담 Mk-II[흑]|슈퍼 건담[흑]|하이자쿠|가브스레이|마라사이|함브라비|파라스 아테네|디 오|갸프란|
앗시마|바운드 독|멧사라|사이코 건담|가자 C|가자 C[백]|큐베레이|큐베레이 Mk-II[흑]|큐베레이 Mk-II[적]|양산형 큐베레이|드라이센|카풀|퀸 만사|뉴 건담|리 가지|
제간|사자비|야크트 도가|알파 아질|105 대거|웨이브 라이더|메타스/MA|G 포트리스|가브스레이/MA|함브라비/MA|갸프란/MA|앗시마/MA|바운드 독/MA|멧사라/MA|사이코 건담/MA|
가자 C/MA|리 가지/BWS|이지스/MA|포비든/MA|레이더/MA|세이버/MA|가이아/MA|어비스/MA|카오스/MA|무라사메/MA|무라사메/MA[황]|딘/공중|가자 C/MA[백]|에일 스트라이크|소드 스트라이크|
런처 스트라이크|스트라이크 루주|프리덤|M1 아스트레이|버스터 대거|레드 프레임|레드 프레임/공중|저스티스|메비우스 제로|스카이 그래스퍼|이지스|듀얼|듀얼 어설트S|버스터|블리츠|
진|바쿠|라고우|조노|딘|게이츠|프로비던스|캘러미티|포비든|레이더|스트라이크 대거|메비우스|VTOL 전투기|퍼펙트 건담|사이코로 건담|
무샤 건담|나이트 건담|릭돔|매드록|하로|포스 임펄스|소드 임펄스|블래스트 임펄스|세이버|가이아|어비스|카오스|자쿠 워리어[녹]|자쿠 워리어[적]|블레이즈 자쿠 팬텀|
슬래시 자쿠 팬텀|구프 이그나이티드|무라사메|무라사메[황]|데스티니|S 프리덤|인피니트 저스티스|돔 트루퍼|아카츠키|미아 라이브 자쿠|짐[GOLD]|자쿠[GOLD]|네모[GOLD]|가자 C[GOLD]|가자 C/MA[GOLD]|
M1 아스트레이[GOLD]|진[GOLD]|스트라이크 대거[GOLD]|볼|61식 전차|마젤라 어택|마젤라 톱|가토루|쁘띠 모빌슈트|미사일 에레카|미스트랄|불독|릭 디아스[적]|화이트 베이스|무사이|
잔지바르|그와진|아가마|알렉산드리아|도고스 기어|사다란|아크엔젤|이터널|나스카급|미네르바|도미니온""".replace("\n", "").split("|")

COMMANDS = {
    0x243900:"이동", 0x244040:"탑재", 0x244780:"포격",
    0x244EC0:"발진", 0x245600:"닫기", 0x245D40:"대기",
    0x246480:"거점 병기", 0x246BC0:"변형", 0x25B980:"포격",
    0x25D5C0:"파워 다운", 0x25DA40:"재장전 중", 0x25DEC0:"탄약 없음",
}
TERRAINS = dict(zip(range(0x25E5A0,0x2624A0,0x2A0),
    [s for s in ("G폴리스","G베이스","마을","공장") for _ in range(3)] * 2))
TERRAINS.update(dict(zip(range(0x2624A0,0x265140,0x2A0),
    "평지|산|산맥|삼림|모래땅|설원|바다|심해|우주|대기권|운석|지표|크레이터|우주 요새|기뢰밭|거점 병기|거점".split("|"))))
TERRAINS.update({0x2671A0:"범용",0x2676E0:"육전",0x267980:"수륙",
                 0x267C20:"비행",0x267EC0:"우주",0x268160:"모함"})

def render(text,w,h,fill=(255,255,255,255),stroke=1):
    im=Image.new("RGBA",(w,h));d=ImageDraw.Draw(im)
    for size in range(min(h,28),4,-1):
        font=ImageFont.truetype(str(FONT),size)
        bb=d.textbbox((0,0),text,font=font,stroke_width=stroke)
        if bb[2]-bb[0]<=w-4 and bb[3]-bb[1]<=h-2:
            d.text(((w-bb[2]+bb[0])//2-bb[0],(h-bb[3]+bb[1])//2-bb[1]),
                   text,font=font,fill=fill,stroke_width=stroke,stroke_fill=(20,20,20,255))
            return im
    raise ValueError((text,w,h))

def replace_texture(buf,source,off,text,fill=(255,255,255,255)):
    hd=TX.parse_header(source,off)
    assert hd["palcnt"]==16, (off,hd)
    im=render(text,hd["w"],hd["h"],fill)
    raw=TX.encode_c4(im,TX.read_palette(source,hd["pal_off"],16),hd["w"],hd["h"])
    assert len(raw)==hd["imgsize"]
    buf[hd["img_off"]:hd["img_off"]+len(raw)]=raw
    return TX.decode(buf,off)

def preview(rows,name):
    cols=4;cw=300;ch=80
    sheet=Image.new("RGB",(cols*cw,((len(rows)+cols-1)//cols)*ch),(55,60,65))
    d=ImageDraw.Draw(sheet);font=ImageFont.truetype(str(FONT),12)
    for i,(label,im) in enumerate(rows):
        x=i%cols*cw;y=i//cols*ch
        d.text((x+4,y+2),label,font=font,fill="yellow")
        im=im.resize((im.width*2,im.height*2))
        sheet.paste(im,(x+4,y+22),im)
    out=HERE/"out";out.mkdir(exist_ok=True)
    sheet.save(out/name)

def main(apply=False):
    source=(HERE.parent/"sys/main.dol").read_bytes()
    dest=TEXT/"patched_main.dol";work=bytearray(dest.read_bytes())
    offsets=[o for o in TX.find_blocks(source) if 0x2065e0<=o<=0x243360]
    assert len(offsets)==len(UNIT_NAMES)==174,(len(offsets),len(UNIT_NAMES))
    rows=[]
    for off,name in zip(offsets,UNIT_NAMES):
        rows.append((f"{off:06X} {name}",replace_texture(work,source,off,name)))
    preview(rows,"runtime_unit_names.png")
    rows=[]
    for off,name in {**COMMANDS,**TERRAINS}.items():
        # Preserve blue/red team colors on terrain copies.
        pal=TX.read_palette(source,TX.parse_header(source,off)["pal_off"],16)
        vivid=[p for p in pal if p[3]==255 and max(p[:3])-min(p[:3])>80]
        fill=max(vivid,key=lambda p:sum(p[:3])) if vivid else (255,255,255,255)
        rows.append((f"{off:06X} {name}",replace_texture(work,source,off,name,fill)))
    preview(rows,"runtime_battle_commands.png")
    if apply:dest.write_bytes(work)
    rows=[]
    for i,name in enumerate(CHAR_NAMES):
        rel=Path(f"Info/tex/chr{i:02d}.arc")
        source=(BASE/rel).read_bytes();work=bytearray(source)
        start,end=struct.unpack_from("<II",source)
        decoded=HLH.decode_hlh(source[start:end])
        hd=TX.parse_header(decoded,0)
        assert (hd["w"],hd["h"],hd["palcnt"])==(148,28,16)
        modified=bytearray(decoded)
        im=replace_texture(modified,decoded,0,name)
        packed=HLH.encode_hlh(bytes(modified),slot_size=end-start)
        assert HLH.decode_hlh(packed)==modified
        work[start:end]=packed
        assert len(work)==len(source) and work[end:]==source[end:]
        if apply:
            dst=TEXT/"patched_files"/rel;dst.parent.mkdir(parents=True,exist_ok=True)
            dst.write_bytes(work)
        rows.append((rel.name+" "+name,im))
    preview(rows,"runtime_character_names.png")
    print(f"runtime labels: {len(offsets)} units, {len(COMMANDS)+len(TERRAINS)} commands/terrain, 16 character plates")

if __name__=="__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    p=argparse.ArgumentParser();p.add_argument("--apply",action="store_true")
    main(p.parse_args().apply)
