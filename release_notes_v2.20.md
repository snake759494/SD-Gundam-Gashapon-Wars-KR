## v2.20 — Issue #20·#21 전체 시나리오·전투 UI 재검수

열린 이슈 #20·#21과 누적 이슈 #1의 첨부 캡처를 기준으로, 메뉴 선택→시나리오 선택→대화→맵→전투 시작→전투 필드→결과까지 실제 진입 경로를 전수 대조했습니다. 공용 리소스와 중복본, 아직 검수하지 않았던 이전 시나리오 경로도 같은 manifest와 회귀 검사에 포함했습니다.

### 패치 내역

- Issue #20의 `Info/arc/bank102.arc/scen/msel_base.dat` 모드 선택 타이틀에서 C4 하이라이트와 CMP 색상 레이어의 위치·크기는 그대로 유지하면서, 선택 상태 `싱글 플레이`의 원본 민트 본문과 녹색 외곽선을 복원했습니다. 회색처럼 보이던 색상 레이어를 고쳤고 25개 C4/CMP 쌍을 모두 다시 검사했습니다.
- `Info/arc/bank102.arc/scen/msel_base.dat`와 `Info/arc/bank119.arc/scen/osp_base.dat`의 사운드 플레이어 헤더를 원본 배경 divider와 대조해 두 행의 glyph bbox를 다시 배치했습니다. `사운드 플레이어 / SOUND PLAYER`가 고정 흰 선과 겹치지 않으며 일본어 잔상이 없습니다.
- `main.dol`의 사운드 설정 표시를 정확히 `사운드　　　　　스테레오／모노`로 고정했습니다. `※`, ASCII 공백, `@c7/@c8` 토큰이 payload에 들어가지 않는지 확인하고 `레` 캐리어(`9378`)가 실제 폰트 셀에 존재하는지 검사했습니다. 보충 설명의 이전 `모노럴` 표기도 `스테레오／모노`로 교정했습니다.
- `Info/arc/bank100.arc`의 HLH 전투 공용 자산 48개(중복 제거 후 93개 고유 raw 이미지 버퍼)를 전수 복원·재작화했습니다. 지형·유닛명 표시, 전투 필드, `전투/공격/확인/취소`, 전투 맵·복귀, `BLUE/RED SIDE`, `DAY/PHASE START`, 아이템·능력·승패·전투 준비 등 Issue #21 캡처에 나온 경로와 중복 버퍼를 모두 포함합니다.
- `bank100` HLH는 초기 허프먼 트리까지 복원한 뒤 HSD raw만 교체하고 원래 U8 엔트리 슬롯 크기로 재압축합니다. 재복원 왕복과 C4/CI8/CMP raw 크기·타일 순서·HSD 포인터·arc 크기를 자동 검증해 전투 조작설명 때의 가로 분할/짝수 행 밀림이 재발하지 않게 했습니다.
- `Info/arc/bank103.arc/scen/sce_mission.dat`의 `シナリオゲーム / SCENARIO GAME` 두 행과 `bank107.arc`의 `scen/mission.dat`, `scen/vs.dat` 미션/VS 중복 표시를 한글로 재작화했습니다. 양쪽 플레이어 표시와 미검수 이전 시나리오의 공용 자산까지 동일 manifest로 처리했습니다.
- 시나리오 SPB 204개를 다시 스캔하고 화자명 명령의 두 형식 `0E/0F 00 08 00 13 00`을 모두 처리했습니다. 고정 길이 슬롯의 `マリュー` 34개, `シン` 2개, `セイラ・マス` 1개를 한글화하고 파일 크기·슬롯 크기·참조 키는 보존했습니다.
- 미션 1 대사 슬롯의 줄 경계에 맞춰 `붙어 있는 게`→`붙은 게`, `자신의 차례`→`자기 차례`로 의미를 유지한 재래핑을 적용해 끝 글자 잘림을 제거했습니다.

### 검증 결과

- 텍스트/사운드 캐리어 회귀 테스트: 4/4 통과
- C4/CMP/CI8 이미지 코덱 회귀 테스트: 3/3 통과
- HLH 압축·복원 회귀 테스트: 2/2 통과
- Issue #20 메뉴·헤더 회귀 테스트: 2/2 통과
- ISO 크기: `962,936,832` bytes (원본과 동일)
- 원본 ISO CRC32: `D5F67251`
- v2.20 ISO CRC32: `3D7FBCA2`
- v2.20 ISO SHA-256: `D542F8BFA90ACEB35EC1F27186EE09D852E2C529872AFC78256D3FA0EFC65943`
- xdelta 크기: `940,795` bytes
- xdelta SHA-256: `8DE6BD3821216FFF2CC1B3C5FCD165A848AE2DA38C5D87F572178D359D857CBF`
- FST 2,051개 엔트리와 패치 대상 235개 파일을 대조했으며 대상 범위 밖 변경 바이트는 `0`입니다. 대상 범위 안 변경 바이트는 `2,079,267`입니다.
- 원본 ISO→xdelta→v2.20 ISO 왕복 적용 결과가 v2.20 ISO와 CRC32·SHA-256 모두 일치합니다.

### 변경·검수 이미지 PNG

아래 이미지는 이번 릴리즈에서 재작화한 메뉴·중첩 HSD·시나리오/전투·사운드 화면을 모두 확인할 수 있는 PNG 미리보기입니다.

![대형 메뉴 C4/CMP 레이어 전체](https://github.com/snake7594/SD-Gundam-Gashapon-Wars-KR/releases/download/v2.20/menu_titles_all_layers_preview.png)

![대형 메뉴 재작화 결과](https://github.com/snake7594/SD-Gundam-Gashapon-Wars-KR/releases/download/v2.20/menu_titles_preview.png)

![중첩 메뉴 C4/CMP 레이어](https://github.com/snake7594/SD-Gundam-Gashapon-Wars-KR/releases/download/v2.20/nested_menu_titles_preview.png)

![중첩 HSD 중복 제목 전체](https://github.com/snake7594/SD-Gundam-Gashapon-Wars-KR/releases/download/v2.20/nested_duplicate_titles_preview.png)

![중첩 HSD 헤더·공유 로고](https://github.com/snake7594/SD-Gundam-Gashapon-Wars-KR/releases/download/v2.20/nested_ui_assets_preview.png)

![시나리오·전투 HLH 자산 전체](https://github.com/snake7594/SD-Gundam-Gashapon-Wars-KR/releases/download/v2.20/scenario_battle_hlh_preview.png)

![시나리오·VS 중복 HSD 자산](https://github.com/snake7594/SD-Gundam-Gashapon-Wars-KR/releases/download/v2.20/scenario_ui_hsd_preview.png)

![사운드 플레이어 제목·설명 목록](https://github.com/snake7594/SD-Gundam-Gashapon-Wars-KR/releases/download/v2.20/sound_volume_preview.png)

### 다운로드

- `SDGundamGashaponWars_KR_v2.20.xdelta` — 원본 CRC32 `D5F67251`용 배포 패치
- `SDGundamGashaponWars_KR_v2.20_source.zip` — v2.20 재빌드 소스
- 위 PNG 미리보기 8종 — 릴리즈 화면에서 한글 재작화 결과를 직접 확인하기 위한 검수 자료
