## v2.21 — Issue #23 시나리오·멀티플레이 표시 누락 패치

2026-09-14: 새 계정 snake759494의 저장소로 최종본을 재배포합니다.
기존 v2.21과 xdelta 바이트는 동일하며, 소스 ZIP에는 새 저장소 주소와 이전 기록을 포함했습니다.
확인 가능한 Claude Code 로컬 자료에서는 v2.21보다 최신인 변경을 발견하지 못했습니다.
아래 Issue #23은 이전 저장소의 이슈 번호입니다. 검증 내역은 기존 패치 당시의 기록이며,
이번 이전에서는 보존 파일 해시와 회귀 검사를 다시 확인했습니다.


Issue #23의 6개 검수 캡처를 기준으로 미션 진입 → 맵/지형 → 전투 시작 → 전투 중 →
미션 클리어의 실제 경로를 다시 추적했습니다. 시나리오뿐 아니라 멀티플레이와 이전에
처리한 공용 리소스까지 전수 재검사해, 화면에 남아 있던 일본어·잘못 번역된 영문·중복
이미지 경로를 함께 수정했습니다.

### 패치 내역

- SPB 화자명 명령의 `0B` 형식을 새로 확인해 `キラ` 16개를 `키라` 고정 길이 캐리어로
  치환했습니다. 기존 `0E/0F` 형식의 `マリュー` 34개, `シン` 2개, `セイラ・マス` 1개도
  함께 회귀 검사했습니다.
- VSC 382개를 전부 다시 디코드해 `ゲルググ` 214개와 `ジム` 166개를 각각 `겔구그`·`짐`으로
  패치했습니다. 시나리오·멀티플레이·맵 배치·덱·유닛 데이터·상성표에 중복된 모든 사본과
  참조 셀을 동일한 캐리어로 갱신했으며, 패치 후 대상 VSC에 원본 일본어 키가 남지 않는지
  확인했습니다.
- 캐리어가 확인되지 않은 다른 유닛명·맵명 키는 게임 로더의 내부 참조이므로 원문을 유지합니다.
  표시열을 번역하는 기존 정책은 바꾸지 않아 유닛이 사라지거나 미션이 멈추는 회귀를 막았습니다.
- 다음 이미지 중복 경로를 원본 raw·팔레트·U8 슬롯 크기와 위치를 보존해 추가 패치했습니다.
  `bank115/scen/sub_title.dat`의 `시나리오 게임 / SCENARIO GAME`, `bank113/114`의 전투
  준비 화면, `bank111`의 중첩 `미션 클리어`, `bank111/120`의 중첩 `다음` 버튼입니다.
- 같은 `bank111.arc` 안에서 두 DAT를 연속 수정할 때 앞선 수정이 원본 재읽기로 덮어써지던
  누적 패치 문제도 고쳤습니다.
- 원래 영어인 그래픽 표기는 번역하지 않고 원문으로 복원했습니다: `BATTLE FIELD`,
  `PRESS START`, `DAY`, `BLUE/RED SIDE`, `PHASE START`, `ATTACK!`, `OK/CANCEL`,
  `MISSION`, `COM/PLAYER`.

### 검증 결과

- 텍스트·사운드 캐리어 회귀 테스트: 4/4 통과
- Issue #23 SPB/VSC/중첩 DAT 회귀 테스트: 3/3 통과
- C4/CMP/CI8 이미지 및 Issue #20 회귀 테스트: 5/5 통과
- 전체 12개 회귀 테스트 통과
- FST 2,051개 엔트리 중 패치 파일 611개를 ISO와 대조했고, 지정 대상 범위 밖 변경 바이트는 `0`입니다.
- ISO 크기: `962,936,832` bytes (원본과 동일)
- 원본 ISO CRC32 / SHA-256: `D5F67251` / `6DEF14F323742345D9664A37B0241928DA8C56DCD1AB9ED56AA9CD2ADFE17A94`
- v2.21 ISO CRC32 / SHA-256: `80457BEF` / `F2A40A1D7644B270A3888598E26387F839B33C54494B54CC514FF518CAA996FB`
- xdelta 크기 / SHA-256: `891,181` bytes / `A4981DEE6229F59F22F5CA78C661F89D498F90BEA7D0D1780426CC8F94D4DBDB`
- 원본 ISO에 xdelta를 적용한 결과가 v2.21 ISO와 바이트 단위로 일치했습니다.

### 변경된 이미지 PNG

이번 릴리즈에서 재작화·추가 패치한 이미지 자산을 아래 3개 PNG에 모두 모았습니다.
각 미리보기에는 해당 자산의 원본/패치 결과와 중복 경로가 포함되어 있습니다.

![시나리오·전투 HLH 전체](https://github.com/snake759494/SD-Gundam-Gashapon-Wars-KR/releases/download/v2.21/scenario_battle_hlh_preview.png)

![시나리오·전투 HSD 중복 경로](https://github.com/snake759494/SD-Gundam-Gashapon-Wars-KR/releases/download/v2.21/scenario_ui_hsd_preview.png)

![미션 카드·다음 버튼 DAT 중복 경로](https://github.com/snake759494/SD-Gundam-Gashapon-Wars-KR/releases/download/v2.21/custom_dat_sprites_preview.png)

### 다운로드

이전 버전에서 누적 반영된 메뉴·전투 조작설명·사운드 이미지도 함께 제공합니다.

![대형 메뉴 전체 레이어](https://github.com/snake759494/SD-Gundam-Gashapon-Wars-KR/releases/download/v2.21/menu_titles_all_layers_preview.png)

![중첩 메뉴](https://github.com/snake759494/SD-Gundam-Gashapon-Wars-KR/releases/download/v2.21/nested_menu_titles_preview.png)

![중복 제목](https://github.com/snake759494/SD-Gundam-Gashapon-Wars-KR/releases/download/v2.21/nested_duplicate_titles_preview.png)

![헤더·사운드 플레이어](https://github.com/snake759494/SD-Gundam-Gashapon-Wars-KR/releases/download/v2.21/nested_ui_assets_preview.png)

![전투 조작설명 1](https://github.com/snake759494/SD-Gundam-Gashapon-Wars-KR/releases/download/v2.21/battle_help_encoded_native.png)

![전투 조작설명 2](https://github.com/snake759494/SD-Gundam-Gashapon-Wars-KR/releases/download/v2.21/battle_help_effect_arc_native.png)

![타이틀·조작설명](https://github.com/snake759494/SD-Gundam-Gashapon-Wars-KR/releases/download/v2.21/custom_ui_assets_preview.png)

![사운드 곡목](https://github.com/snake759494/SD-Gundam-Gashapon-Wars-KR/releases/download/v2.21/sound_volume_preview.png)


- `SDGundamGashaponWars_KR_v2.21.xdelta` — 원본 CRC32 `D5F67251`용 배포 패치
- `SDGundamGashaponWars_KR_v2.21_source.zip` — v2.21 재빌드 소스
- 위 PNG 3종 — 변경된 이미지 자산 전체 검수용 미리보기

게임 ISO 자체는 저장소와 릴리즈에 포함하지 않습니다. 본인 소유의 원본 ISO에 xdelta를
적용해 사용하세요.
