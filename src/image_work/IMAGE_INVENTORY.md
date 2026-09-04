# 번역 대상 이미지(일본어 텍스트 그래픽) 정리

게임의 UI 로고·라벨은 폰트가 아니라 **텍스처 이미지**로 그려집니다. 전수 추출 결과, 번역이 필요한 일본어 텍스트 이미지는 대부분 **`Info/arc/*.arc`** 아카이브 안의 **@Texture(GameCube C4/C8)** 블록입니다.

- 추출 도구: `image_work/tex_lib.py`(@Texture 디코더) + `extract_all.py`
- 컨택트시트: `image_work/sheets/*.png` (파일별로 텍스처 미리보기)
- 총 텍스처(라벨/로고 크기, ≥24×12): **143개** / 전체 @Texture 블록 971개
- 별도 HSD 메뉴 그래픽: 기존 `bank113/scen/usel_mode.dat` 4쌍 + `bank101/scen/ce_menu_title.dat` 1개와
  Issue #18에서 확인한 `bank102/msel_base.dat`, `bank102·108·113/*_gtitle.dat`,
  `bank108/cap_base.dat`, `bank119/osp_base.dat` 중복 리소스

---

## A. 메인 메뉴 라벨  — `Info/arc/bank102.arc`, `bank108.arc`
일영 병기 소형(160×52) + 대형(368×74) 두 버전이 각 뱅크에 중복 존재. 대형은 흰색 실루엣.

| 일본어 | 영어 | 한국어(안) |
|---|---|---|
| モードセレクト | MODE SELECT | 모드 선택 |
| シングルプレイ | SINGLE PLAY | 싱글 플레이 |
| マルチプレイ | MULTI PLAY | 멀티 플레이 |
| オプション | OPTION | 옵션 |
| 振動 | VIBRATION | 진동 |
| サウンド設定 | SOUND SETUP | 사운드 설정 |
| メモリーカード | MEMORY CARD | 메모리 카드 |
| シナリオゲーム | SCENARIO GAME | 시나리오 게임 |
| カプセルウォーズ | — | 캡슐 워즈 |
| １００問バトル | — | 100문 배틀 |
| マップたいせん | — | 맵 대전 |
| アクションたいせん | — | 액션 대전 |
| サバイバル | — | 서바이벌 |
| カプセル編集 | — | 캡슐 편집 |
| ギャラリー | — | 갤러리 |
| サウンドプレイヤー | — | 사운드 플레이어 |
| ヘルプ | — | 도움말 |
| NEW! (배지) | | (그대로/신규) |

v2.18에서 `bank102.arc`의 대형 메뉴 타이틀 17종을 원본 오프셋·합성 이미지와 다시
대조했다. v2.16에서 뒤섞였던 `맵 대전`·`액션 대전`·`서바이벌`·`캡슐 편집`·`갤러리`
매칭을 바로잡고, C4 하이라이트와 CMP 색상 레이어에 **동일한 글꼴 크기와 공통 원점**을
적용했다. 중복 메뉴 리소스인 `bank108.arc`의 6종도 같은 방식으로 처리했다.
`bank113.arc`의 대전 방식 타이틀 2종(`블루사이드 VS 레드사이드`, `배틀 로얄`)도
C4/CMPR 쌍을 함께 재작화했다. bank108의 잠금 `???`는 문구가 아니므로 원본 유지다.

Issue #14 캡처에서 계속 일본어로 남던 실제 선택 화면은 `bank113.arc` 내부
`scen/usel_mode.dat`의 HSD 이미지였다. `대전 형식을 선택하세요`·`필드를 선택하세요`
안내와 `배틀 로얄`·`블루사이드 VS 레드사이드`를 각각 C4/CMPR 또는 C4/CI8 쌍으로
재작화했고, 동일한 TextLayout을 두 레이어에 공유했다. 같은 방식으로
`bank101.arc/scen/ce_menu_title.dat`의 `カプセルボックス編集`도 `캡슐 박스 편집`으로
처리했다.

Issue #18에서는 같은 화면을 구성하는 HSD 복제본도 다시 추적했다. `msel_base.dat`의
188×80 공유 로고와 모드 선택 헤더, `cap_base.dat`의 캡슐 워즈 헤더,
`bank119.arc/scen/osp_base.dat`의 사운드 플레이어 헤더를 통째로 재작화했다.
또한 `msel_gtitle.dat`·`cap_gtitle.dat`·`usel_gtitle.dat`의 C4/CMP 대형 제목
15쌍(멀티 플레이 3개와 옵션 12개)을 같은 TextLayout으로 처리해 어느 진입 경로에서도
일본어 제목이 남지 않게 했다.

## B. 룰 설정 라벨 — `Info/arc/bank113.arc`
- **지형**: 地上/GROUND, 水中/WATER, 宇宙/SPACE, 空中/SKY (64×28)
- タイム設定(시간 설정), アイテム出現(아이템 출현), ギミック(기믹), 味方ヒット(아군 히트), じゃんけん(가위바위보), COMレベル(COM 레벨)
- ON / OFF / なし(없음)
- **난이도**: Lv.1 よわい(약함), Lv.2 ふつう(보통), Lv.3 つよい(강함), Lv.4 ゲキつよ(엄청강함), Lv.5 ニュータイプ(뉴타입)
- **시간**: 15秒/30秒/45秒/60秒/75秒/90秒
- デフォルトにもどす(기본값으로), BLUE SIDE 対 RED SIDE 対戦形式(대전 형식)

## C. PB모드(캡슐워즈) 룰 라벨 — `Info/arc/bank118.arc`
- ランダムマップ(랜덤 맵, 128×128), デフォルトにもどす
- 日数(일수), 時間制限(시간 제한), ハイド(하이드), カード(카드), ★
- ON / OFF / なし
- **일수**: 5日/10日/15日/20日/25日/30日
- **시간**: 30秒/60秒/90秒/120秒/150秒

## D. 난이도·결과 통계 — `Info/arc/bank114.arc`
- **난이도**: かんたん(쉬움), むずかしい(어려움), ゲキむず(매우 어려움)
- クリアタイム(클리어 타임), 敵を倒した数(쓰러뜨린 적 수)
- 지형(地上/水中/宇宙/空中)

## E. 모드 아이콘 — `bank102 #0~20`, `bank108 #0~6` (64×64)
대부분 그림 아이콘. 일부 텍스트 포함(VS., 100 등). 번역 우선순위 낮음.

---

## F. 타이틀·로고·연출 — HAL DAT 처리 현황
미션 연출 `.dat` 중 `sub_t*`, `m_seikou`, `m_sippai`는 HAL HSD/DAT 컨테이너의
고정 CI4 텍스처 버퍼를 사용한다. v2.11에서 `75_custom_dat_sprites.py`로 원시
텍스처 길이와 팔레트를 보존한 채 제목·결과·다음 버튼을 재작화했다.
- `Info/dat/sub_t01.dat` ~ `sub_t14.dat` — 미션 제목 14종 + `다음` (v2.11 처리)
- `Info/dat/m_seikou.dat`, `m_sippai.dat` — `미션 클리어`/`미션 실패` (v2.12 처리)
- `Info/dat/battle_start.dat` — `BATTLE`/`START` 원본 영문
- `demo_title.dat` — 타이틀 로고 `SD 건담 가샤폰 워즈` (RGB5A3, v2.12 처리)
- `ban_rogo.dat`, `sim_title.dat` — 반다이/시뮬레이션 영문 로고, 원본 유지

## G. v2.12~v2.19 검수 이슈 반영

- Issue #18의 사운드 플레이어 화면은 `bank119.arc/scen/osp_base.dat`의 162×52 CI4
  헤더와 `bank102.arc/scen/msel_base.dat`의 188×80 CI8 공유 로고를 사용한다. 두 이미지의
  원본 raw SHA-256·구조체·팔레트 범위를 검증한 뒤 한글/영문 2행 헤더와 로고를 재작화했다.
  모드 선택·캡슐 워즈의 중복 160×52 헤더도 함께 교체했다.
- `bank102.arc/scen/msel_gtitle.dat`, `bank108.arc/scen/cap_gtitle.dat`,
  `bank113.arc/scen/usel_gtitle.dat`의 중복 C4/CMP 제목 5쌍씩(총 15쌍)을 추가했다.
  CMP 색상 레이어의 8×8 매크로블록·C4 팔레트·파일 크기는 유지하고 두 레이어에 동일한
  글꼴 크기와 원점을 공유시켰다.
- `Sound/volume.vsc`는 내부 번호·SE 키·볼륨 열을 건드리지 않고 BGM 제목/설명 표시열
  39행과 CSV 헤더만 바꿨다. `스테레오／모노` DOL 문자열은 ASCII 공백과 `@c7/@c8`가
  한글 2바이트 캐리어를 홀수 경계로 밀지 않는지 별도 회귀 테스트로 고정했다.

- `Info/arc/bank102.arc`·`bank108.arc` — 대형 메뉴 타이틀을 C4 하이라이트와 CMP
  색상 레이어 한 쌍으로 재작화했다. v2.17의 `63_menu_titles.py`는 쌍마다 공통
  `TextLayout`을 한 번만 계산해 두 레이어의 위치·크기를 정확히 일치시킨다. bank102
  소형 헤더 7종은 `60_label_inject.py`의 결과를 이어받아 재빌드 때 일본어로 덮이지 않는다.
- `Info/arc/bank113.arc` — 멀티플레이 대전 방식의 `블루사이드 VS 레드사이드`와
  `배틀 로얄`을 외부 C4/CMPR 쌍으로 패치했다. 블루·VS·레드 색상 구분도 유지한다.
- `Info/arc/bank113.arc/scen/usel_mode.dat` — Issue #14의 실제 대전 방식 선택 화면에
  포함된 안내 2쌍과 대전 방식 2쌍을 HSD 이미지 버퍼 제자리 치환으로 한글화했다.
  두 레이어의 공통 글꼴·원점·바운딩을 공유하고, 일본어 제목과 잔상은 제거했다.
- `Info/arc/bank113.arc/scen/usel_base.dat` — Issue #16에서 확인된 공통 멀티플레이 진입
  경로의 중복 `대전 형식을 선택하세요` raw C4/CMP 버퍼도 원본 SHA-256·크기를 검증한 뒤
  같은 레이아웃으로 함께 치환했다. 이 복제본을 빼먹어 일본어 안내가 남던 경로를 제거했다.
- `Info/arc/bank101.arc/scen/ce_menu_title.dat` — 캡슐 박스 편집 메뉴 제목을 중첩 C4
  이미지로 확인해 한글화했다. U8/HSD 파일 크기와 포인터는 변경하지 않는다.
- `Info/tpl/con_img.tpl` 및 `Effect/Arc/bank0.arc`~`bank2.arc` — 334×182 C8
  전투 조작설명 도식의 `ガード`/`とくべつ`/`格闘攻撃` 등 7개 라벨을 한글화.
  세 Effect 복제본도 함께 갱신해 모드별 리소스 선택 차이를 반영했다(v2.12).
  v2.13에서는 일본어 글리프 픽셀만 교체하고 도식·캐릭터·연결선의 원본 raw를 보존한다.
  v2.14에서는 한글 안티앨리어싱의 부분 알파가 투명 팔레트로 들어가던 경로를 차단하고,
  완전 투명 영역에는 글자를 쓰지 않도록 마스크한 뒤 실제 C8 바이트를 재검증했다.
  v2.15에서는 C8 표준 8×4 타일 순서로 디코드·인코드해 가로 분할과 짝수 줄 수평 밀림을
  수정하고, 후리가나를 포함한 원문 라벨까지 제거한 뒤 한글 7종을 다시 주입했다.
- `main.dol`의 사운드 설정 표시 문자열에서 `모노랄`/`모노럴` 표기를 사용자 검수 의견에
  맞춰 `모노`로 정리해 `스테레오／모노`로 표시한다. v2.18에서는 이 표시 전용 문자열에
  남아 있던 `@c7`/`@c8` 토큰도 제거해 `※테레오`/`※노`가 다시 나타나지 않도록 했다.
- `tex_lib.py` — 완전 투명 픽셀은 투명 팔레트, 완전 불투명 픽셀은 불투명 팔레트로
  먼저 제한하는 최근접 매핑을 적용했다. 기존 RGB·알파 거리만으로 C4 빈 영역이
  반투명 회색으로 양자화되던 문제를 수정했고, CMP 8×8/4×4 블록 왕복 회귀 테스트를
  추가해 행·열 밀림을 검증한다.
- `Spb/mission/M00_01.SPB` — 별도 화자명 명령 슬롯의 `シン`을 동일 길이
  캐리어 코드 `신`으로 치환. 내부 유닛/리소스 키는 변경하지 않음.

## H. 번역 불필요
- `Info/tpl/chr01~15_*.pic.tpl` — 캐릭터 초상화(300×360, 텍스트 없음)

## I. v2.20 시나리오·전투 공용 이미지 전수 검수

Issue #21의 미션 1 캡처를 시작점으로 시나리오 선택→대화→맵→전투 시작→전투 필드의
**실제 진입 경로**를 원본 리소스와 대조했다. 공용 전투 화면은 일반 @Texture만이 아니라
`Info/arc/bank100.arc`의 HLH 압축 HSD와 `bank103`·`bank107`의 중첩 HSD에도 같은 문구가
복제되어 있었다. `78_scenario_battle_assets.py`는 다음을 한 번의 빌드에서 모두 처리한다.

- bank100 HLH **48개 자산, 93개 고유 raw 이미지 버퍼**: 지형·유닛 표시, 전투 필드,
  전투/공격/확인/취소, 메뉴·전투 맵·뒤로, BLUE/RED SIDE, DAY/PHASE START,
  아이템·능력·승패·전투 준비 문구와 중복 버퍼
- bank103 `scen/sce_mission.dat`: `シナリオゲーム / SCENARIO GAME` 2행 헤더
- bank107 `scen/mission.dat`·`scen/vs.dat`: `MISSION`, COM/플레이어 양쪽 중복 표시
- HLH는 먼저 복원한 뒤 HSD 구조체·팔레트·타일 순서를 유지한 채 raw만 교체하고, 원래
  U8 엔트리 슬롯 크기로 재압축한다. C4/CI8/CMP raw 크기, HSD 포인터, arc 크기를
  모두 검증한다.
- Issue #20의 `bank102/msel_base.dat` 선택 상태 `싱글 플레이`는 원본 캡처의 민트 본문과
  녹색 외곽선을 복원해 회색으로 보이던 CMP 레이어를 교정했다. `bank119/osp_base.dat`
  사운드 플레이어 헤더는 일본어 원본과 같은 두 행의 glyph bbox를 유지해 고정 divider가
  영문 행을 가로지르지 않도록 했다.

시나리오 SPB도 전체 204개 파일을 다시 확인했다. 고정 화자명 명령의 두 형식(0E/0F)을
모두 검사해 `マリュー` 34개, `シン` 2개, `セイラ・マス` 1개를 번역하고 슬롯 크기를
보존했다. 유닛명·맵명처럼 게임 로더가 참조하는 키(`ゲルググ`, `ジム` 등)는 안전을 위해
일본어로 유지하고 표시 열만 번역한다.

검수용 PNG는 `out/scenario_battle_hlh_preview.png`와 `out/scenario_ui_hsd_preview.png`이며,
중복 메뉴의 C4/CMP 레이어는 기존 `out/menu_titles_all_layers_preview.png`와
`out/nested_ui_assets_preview.png`에서 함께 확인할 수 있다.

## J. v2.21 Issue #23 누락 이미지·중복 경로 재검수

Issue #23의 시나리오 화면 캡처를 원본 raw와 다시 대조해, 기존 공용 자산 외에 다음
중복 경로를 통합 빌드에 추가했다.

- `Info/arc/bank115.arc/scen/sub_title.dat` — `시나리오 게임 / SCENARIO GAME` 헤더
- `Info/arc/bank113.arc/scen/usel_start.dat`·`bank114.arc/scen/suv_start.dat` —
  `PRESS START`와 `준비 OK!` 전투 준비 화면
- `Info/arc/bank111.arc/scen/pb_m_cl.dat` — 중첩 `미션 클리어` 결과 카드
- `Info/arc/bank111.arc/scen/rw_push_a.dat`·`bank120.arc/scen/rw_push_a.dat` —
  중첩 `다음` 버튼

각 DAT는 U8 엔트리 슬롯, HSD 구조체, raw 크기, C4 팔레트를 보존한다. bank111의
두 중첩 파일처럼 같은 ARC 안에서 여러 DAT를 연속 수정하는 경우에도 원본 ARC를
덮어쓰지 않고 누적 패치한 뒤 저장하도록 해 앞선 변경이 사라지지 않게 했다.
전체 결과는 `out/scenario_battle_hlh_preview.png`, `out/scenario_ui_hsd_preview.png`,
`out/custom_dat_sprites_preview.png`에서 확인한다.

---

## 작업 방식
1. @Texture 라벨(A~D): 디코드→PNG→한글 로고 다시 그리기→같은 C4 포맷으로 재인코딩→arc 제자리 주입(동일 크기 or arc 재빌드).
   - 폰트 셀 재활용과 달리 이미지를 직접 편집해야 하므로, 팔레트·타일 배치를 보존한 재인코더가 필요.
2. HAL DAT 연출: 고정 CI4 image buffer를 검증하고 동일 길이로 재인코딩해 주입
   (`75_custom_dat_sprites.py`, `76_custom_ui_assets.py`). 압축 `chr*.arc`의 초상화와
   `ban_rogo.dat`는 원본 구조·용도상 별도 보류.
