## v2.22 — 시나리오 검수 #1: 실제 표시 이미지와 누적 패치 경로 수정

[검수 이슈 #1](https://github.com/snake759494/SD-Gundam-Gashapon-Wars-KR/issues/1)의 6개 캡처와 5개 항목을 기준으로 수정했습니다. 원본 일본판 ISO(CRC32 `D5F67251`)에 적용하는 **전체 xdelta 패치**입니다. v2.21 패치본에 덧씌우지 마세요.

### 항목별 원인과 조치

1. **조작설명 제목 및 흰색 테두리**
   - 실행파일에 같은 제목의 별도 문자열(`main.dol`의 `0x2D33DC`)이 남아 있어, 기존 한글 폰트와 조합될 때 잘못된 글자로 보였습니다. 기존 제목 위치와 새로 확인한 위치 모두 `조작설명`으로 치환합니다.
   - 버튼 문구를 지우는 사각형이 말풍선 테두리까지 덮던 처리도 수정했습니다. 원본 알파 실루엣과 문구 영역 밖 픽셀을 보존하고, 테두리에 닿은 일본어 획은 흰색 테두리로 복구합니다. 일본어 후리가나 제거 범위도 보완했습니다.
   - `Info/tpl/con_img.tpl`과 `Effect/Arc/bank0.arc`, `bank1.arc`, `bank2.arc`의 C8 사본 총 4개를 함께 처리했습니다.
2. **배틀 메뉴와 지형 표시**
   - 실제 표시 경로는 실행파일 안의 C4 텍스처였습니다. 이동·탑재·포격·발진·닫기·대기·거점 병기·변형 등의 명령, 상태, 지형, 역할 표시 **59개**를 교체했습니다.
   - 청색/적색 팀용 지형 사본까지 포함하며, 기존 팔레트·크기·오프셋을 유지합니다. 전투 관련 이미지 전체가 번역되었다는 뜻은 아니며, 이번 확인 범위는 아래 PNG에 모두 공개합니다.
3. **미션 3 제목 뒤 불필요한 획**
   - `건탱크 갑니다~!`의 ASCII 물결표를 제거해 `건탱크 갑니다！`로 수정했습니다. 2바이트 전각 느낌표로 고정 슬롯 인코딩을 유지합니다.
4. **미션 설명 및 전투 대화의 캐릭터 이름**
   - `Info/tex/chr00.arc`~`chr15.arc`의 첫 HLH 압축 블록에 이름 이미지가 있었습니다. 기존 SPB/VSC 문자열 수정만으로 이 이미지가 바뀌지 않았습니다.
   - 마류·신·발트펠트를 포함한 **16명 전체**를 번역했습니다. 초기 허프만 트리를 처리하는 정상 디코더로 추출하고, 동일 압축 슬롯에 재삽입했습니다. 뒤쪽 초상화 데이터, 멤버 오프셋, 파일 길이는 그대로입니다.
5. **전투 진입 유닛명**
   - 유닛명 역시 실행파일의 별도 이미지였습니다. 짐·겔구그뿐 아니라 변형·색상·GOLD·함선 사본을 포함한 **174개**를 모두 교체했습니다.
   - v2.21에서 표시명으로 오인해 바꿨던 VSC의 `ジム`/`ゲルググ` 내부 참조 키는 원문으로 되돌렸습니다. 화면 이미지를 번역하고 게임 내부 식별자는 보존하는 방식으로 수정했습니다.

### 이전 시나리오·멀티플레이 회귀 방지

- 후속 ARC 처리 단계가 원본 컨테이너를 다시 읽어 이전 메뉴 패치를 지우던 문제를 `75_custom_dat_sprites.py`와 `78_scenario_battle_assets.py`에서 수정했습니다. 원본은 검증용으로 읽고, 출력은 이미 수정된 컨테이너에 누적합니다.
- `bank111`의 기존 메뉴/결과 문구 및 `bank113`의 메뉴와 전투 준비 이미지가 함께 남는지 검사합니다.
- 빌드 시작 시 VSC를 원본에서 재생성한 뒤 표시열 번역을 순서대로 적용해, 이전 버전의 불필요한 키 치환이 남지 않게 했습니다.
- 빌드 명령의 상대 ISO 경로를 절대 경로로 확정해 하위 스크립트의 작업 폴더 변경에도 올바른 파일을 사용합니다.
- 기존 사운드 설정의 스테레오/모노 캐리어 정렬, CMP 블록 배열, 메뉴 색상 및 이전 이슈의 SPB/중첩 DAT 검사도 함께 실행했습니다.

### 검증 범위

- 회귀 테스트 **19/19 통과**: 새 실제 표시 경로 5개, 이전 이슈 #23의 3개, 텍스트/사운드 4개, 텍스처 코덱 3개, 이전 이슈 #20의 2개, HLH 코덱 2개.
- ISO 크기: `962,936,832` bytes (원본과 동일).
- v2.22 ISO CRC32: `BF4B495B`.
- v2.22 ISO SHA-256: `6CEBE6F96383E5A9D89D060C35772AAA2F4C769A85D19FDF7BA011969489055E`.
- xdelta 크기: `1,059,146` bytes.
- xdelta SHA-256: `997A2F3B77F32CA2964B666E1D1383545539C737DA807AD71587C066E551D2AB`.
- 원본 ISO에 배포 xdelta를 적용한 왕복 ISO의 크기·CRC32·SHA-256이 빌드 결과와 모두 일치했습니다.

에뮬레이터에서 실제 시나리오를 플레이하는 검수는 이번 작업에서 수행하지 않았습니다. 신규 유닛명·전투 표시·화자명·조작설명 PNG는 재인코딩한 리소스를 다시 디코드한 결과이며, 기존 메뉴 비교 PNG는 빌드 미리보기입니다. 게임 실행 캡처는 아닙니다. 실기/에뮬레이터에서 다른 경로의 문제가 확인되면 재현 순서와 화면을 첨부해 주세요.

### 변경 이미지 전체 PNG

이미지를 열면 원본 크기로 확대해서 확인할 수 있습니다. 유닛명·명령/지형·화자명은 이번에 교체한 249개 이미지 전체를 담았습니다.

![유닛명 174개](https://github.com/snake759494/SD-Gundam-Gashapon-Wars-KR/releases/download/v2.22/runtime_unit_names.png)

![전투 명령·상태·지형·역할 59개](https://github.com/snake759494/SD-Gundam-Gashapon-Wars-KR/releases/download/v2.22/runtime_battle_commands.png)

![캐릭터 이름 16개](https://github.com/snake759494/SD-Gundam-Gashapon-Wars-KR/releases/download/v2.22/runtime_character_names.png)

![조작설명 TPL 재디코드](https://github.com/snake759494/SD-Gundam-Gashapon-Wars-KR/releases/download/v2.22/battle_help_verified.png)

![조작설명 Effect ARC 사본 재디코드](https://github.com/snake759494/SD-Gundam-Gashapon-Wars-KR/releases/download/v2.22/battle_help_effect_verified.png)

누적 패치가 보존되는 메뉴 레이어와 시나리오/멀티플레이 준비 화면도 함께 제공합니다.

![메뉴 C4·CMP 레이어](https://github.com/snake759494/SD-Gundam-Gashapon-Wars-KR/releases/download/v2.22/menu_titles_all_layers_preview.png)

![시나리오·멀티플레이 준비 화면](https://github.com/snake759494/SD-Gundam-Gashapon-Wars-KR/releases/download/v2.22/scenario_ui_hsd_preview.png)

![기존 결과·메뉴 문구](https://github.com/snake759494/SD-Gundam-Gashapon-Wars-KR/releases/download/v2.22/misc_labels_preview.png)

![중첩 메뉴 레이어](https://github.com/snake759494/SD-Gundam-Gashapon-Wars-KR/releases/download/v2.22/nested_menu_titles_preview.png)

![중복 메뉴 제목](https://github.com/snake759494/SD-Gundam-Gashapon-Wars-KR/releases/download/v2.22/nested_duplicate_titles_preview.png)

### 재검사 명령

원본 추출 및 한글 폰트 빌드 후 저장소 루트에서 실행합니다.

```powershell
python src/text_patch_work/BUILD_FROM_MASTER.py --iso --src-iso "원본.iso" --out-iso "SDGundamGashaponWars_KR_v2.22.iso"
python -m unittest -v src/image_work/test_issue1_runtime.py src/text_patch_work/test_issue23_regressions.py src/text_patch_work/test_encoding_regressions.py src/image_work/test_texture_codecs.py src/image_work/test_issue20_regressions.py src/image_work/test_hlh_codec.py
```

배포물은 xdelta·소스 ZIP·PNG입니다. 게임 ISO 및 원본 추출 데이터는 배포하지 않습니다.
