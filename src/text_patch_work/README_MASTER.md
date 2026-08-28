# 통합 번역 마스터 (translation_master.json)

지금까지 일본어→한글로 번역·반영한 **모든 텍스트를 하나의 JSON**으로 모았습니다.
이 파일만 수정하고 빌드하면 한글패치가 그대로 바뀝니다.

## 파일
- **`translation_master.json`** — 편집할 단 하나의 파일 (약 463 KB).
- `make_master.py` — 개별 데이터에서 마스터를 (재)생성. *보통 쓸 일 없음.*
- `BUILD_FROM_MASTER.py` — 마스터 → 패치 재생성.

## 수정 → 반영 방법
1. `translation_master.json`을 열어 원하는 `ko`(한글) 값을 고칩니다.
2. 빌드:
   ```
   python text_patch_work/BUILD_FROM_MASTER.py --iso
   ```
   → `patched_files/`·`patched_main.dol` 재생성 후 `SD Gundam Gashapon Wars (KR text).iso` 빌드.
   (`--iso` 빼면 ISO 없이 패치 파일만 재생성)
3. 나온 ISO로 플레이하거나 xdelta를 떠서 배포.

> 검증됨: 마스터를 안 고치고 빌드하면 현재 배포본(v2.10)과 **바이트 단위로 동일**.

## 섹션 (무엇을 고치면 무엇이 바뀌나)
| 섹션 | 개수 | 내용 | 편집 |
|---|---|---|---|
| `dialogue` | 1101 | SPB 스토리·전투 대사 (`id → {jp, ko}`) | `ko`만 수정. `@c7`·`\\n` 등 제어토큰 유지 |
| `unit_names` | 175 | 유닛명 vsc (`jp → ko`) | ⚠원본보다 길면 오버플로로 미적용(짧으면 적용됨) |
| `help` | 74 | 도움말 vsc 셀 | 각 항목 `ko` |
| `disp_char` | 21 | 캐릭터 표시명 vsc | `jp → ko` |
| `disp_terrain` | 30 | 지형명 vsc | `jp → ko` |
| `field` | 43행 | 맵 선택 화면 vsc | `row → {열: ko}` |
| `dol` | 813 | 실행파일 UI 문자열 | `ko` (예산 초과 시 자동 잘림) |
| `dol_extra` | 12 | 실행파일 추가 문자열(번역 제외 목록에 있던 공통 UI 포함) | `ko` |
| `dol_exclude` | 260 | **번역 금지** jp 목록(AI 명령어·내부키 등) | 건드리지 말 것 |
| `images` | 56 | 라벨 이미지(뱅크 offset → 한글) | 문자열 수정 → 이미지 재작화 |
| `gallery` | 163 | 도감 유닛 설명 (`row → {jp, ko}`) | `ko`만 수정, 8줄×18자 자동 줄바꿈 |
| `ab_mission` | 100 | 챌린지 미션 (`row → {title, cond, desc}`) | 표시열만. 시작유닛 키는 자동 유지 |

## 주의
- **동일 크기 제자리 치환** 방식이라, 한글이 원본 슬롯보다 길면 잘리거나 미적용됩니다.
  대사는 폭·줄수 규칙(한 줄 폭, 화면당 줄수)을 지키세요.
- `dol_exclude`의 문자열은 게임 내부 키/enum이라 번역하면 오작동(미션 진행 정지 등)합니다.
- `unit_names`는 대부분 슬롯이 짧아 현재 미적용 상태입니다(번역은 보존).
- `patched_main.dol`은 **폰트 적용본**이 전제입니다(폰트 빌드는 텍스트 번역과 별개).
  폰트부터 새로 만들려면 `06_build_font.py` → `BUILD_FROM_MASTER.py` 순서.

## 커버리지
번역 문자열 약 **2,635개**(대사 1101 + 유닛명 175 + 도움말 74 + 표시명 51 + 필드 + dol 813
+ 이미지 56 + 도감 163 + 챌린지 미션 100).

> 폰트: 도감/미션 번역에 새 한글 음절 73자가 필요해 폰트를 810음절로 확장했습니다
> (`syllables.json` + `06_build_font.py`). 음절을 더 늘리려면 syllables.json에 추가 후
> `06_build_font.py` → `BUILD_FROM_MASTER.py --iso` 순서로 재빌드하세요.

> v2.10부터 `BUILD_FROM_MASTER.py`가 `63_menu_titles.py`도 자동 실행합니다.
> 따라서 bank102 대형 메뉴 타이틀을 별도 수동 단계 없이 재현할 수 있습니다.
