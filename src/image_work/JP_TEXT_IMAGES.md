# 일본어 텍스트 포함 이미지 목록 (GGPJB2)

전체 파일에서 `@Texture` 611개를 추출(`all_images/`, `all_sheets/`)한 뒤, **일본어 텍스트가
들어있는 이미지만** 별도로 추렸습니다.

- 큐레이션 폴더: `image_work/jp_text_images/{translated, untranslated}/`
- 통합 시트: `jp_text_translated_sheet.png` (88개), `jp_text_untranslated_sheet.png` (1개)
- 원자료: `jp_text_inventory.json`
- 판별 기준(그라운드 트루스): 원본 `files/` ↔ 패치본 `text_patch_work/patched_files/` 의
  `@Texture` 블록 바이트를 비교해 **실제로 바뀐 것 = 번역완료**, 텍스트인데 안 바뀐 것 = 미번역.
- 아래 @Texture 통계와 별도로, v2.17에서 중첩 U8/HSD 메뉴 이미지 4쌍과 캡슐
  편집 제목 1개를 `64_nested_menu_titles.py`로 재작화했습니다.

아이콘 뱅크(103/104/105/107/109/112/115~117: 숫자·기호·이펙트·초상), Effect/Arc(아이템·이펙트
픽토그램), Info/tpl(캐릭터 초상), files/cardicon 등은 **텍스트가 없어 제외**했습니다.

---

## 요약

| 구분 | @Texture | 상태 |
|---|---|---|
| 번역 완료 (라벨/버튼) | **88** | 패치 반영됨 (한글) |
| 미번역 @Texture | **1** | 잠금 상태 `???` placeholder만 유지 |
| 보류 커스텀 스프라이트(.dat) | **2** | `ban_rogo.dat`/`sim_title.dat` (아래 C) |

---

## A. 번역 완료 — @Texture 88개  ✅

`jp_text_translated_sheet.png` 참조. 뱅크별 내용:

| 뱅크 | 개수 | 내용 |
|---|---|---|
| bank101 | 1 | ほうげき(포격) |
| bank102 | 24 | 소형 메뉴 알약 7종 + 대형 메뉴 타이틀 17종(C4/CMP 쌍) |
| bank106 | 1 | ランダムマップ(랜덤 맵) 명패 |
| bank110 | 1 | ほうげき(포격) |
| bank111 | 3 | 100%占領 / 100%拠点占領 / 100%ユニット生還 (승리 조건) |
| bank108 | 6 | 메인 메뉴 중복 대형 타이틀 6종(C4/CMP 쌍) |
| bank113 | 25 | 룰 라벨 23종 + 외부 대전 방식 타이틀 2종(C4/CMP/CMPR 쌍) |
| bank114 | 9 | ゲキむず/かんたん/クリアタイム·敵を倒した数·地上/水中/宇宙/空中·むずかしい |
| bank118 | 18 | 룰 라벨(랜덤맵·時間制限·ハイド·カード·日/数·なし·5~30日·30~150秒·デフォルトにもどす) |

---

## B. 미번역 — @Texture 1개  ⛔

`jp_text_untranslated_sheet.png` 참조.

| 뱅크 | 개수 | 내용 | 미처리 사유 |
|---|---|---|---|
| bank108 | 1 | `0x40100` 잠금 상태 `???` placeholder | 번역할 문구가 아니므로 원본 유지 |

---

## C. 커스텀 스프라이트(.dat)·중첩 HSD — v2.12~v2.17 처리/보류 현황

`.dat` 전체가 같은 포맷은 아니다. 미션 연출 파일은 HAL HSD/DAT 컨테이너 안의
고정 레이아웃 CI4 텍스처로 확인했으며, OAM/포인터를 건드리지 않고 원시 이미지 버퍼만
동일 길이로 재인코딩할 수 있다. `75_custom_dat_sprites.py`가 이 작업을 자동화한다.

| 파일 | 내용 |
|---|---|
| `Info/dat/sub_t01.dat` ~ `sub_t14.dat` (14) | 미션 제목 카드 → **v2.11 한글화** |
| `Info/dat/m_seikou.dat` | ミッション クリア → **미션 클리어** |
| `Info/dat/m_sippai.dat` | ミッション失敗 → **미션 실패** |
| `Info/dat/sub_t01.dat` ~ `sub_t14.dat`의 버튼 텍스처 | つぎへ → **다음** |
| `Info/dat/battle_start.dat` | `BATTLE`/`START` 원본 영문, 추가 번역 불필요 |
| `files/demo_title.dat` | 데모 타이틀 로고 → **SD 건담 가샤폰 워즈** (v2.12) |
| `Info/tpl/con_img.tpl`, `Effect/Arc/bank0~2.arc` | 전투 조작설명 C8 7개 라벨 → 한글 (v2.12) |
| `Info/arc/bank113.arc/scen/usel_mode.dat` | 대전 형식/필드 안내 2쌍 + 배틀 로얄/블루사이드 대전 2쌍 → 한글 (v2.17) |
| `Info/arc/bank101.arc/scen/ce_menu_title.dat` | 캡슐 박스 편집 제목 1개 → 한글 (v2.17) |
| `files/ban_rogo.dat` | 반다이 로고, 원본 유지 |
| `files/sim_title.dat` | 시뮬레이션 타이틀 로고 |

> `シン` 화자명은 `chr*.arc` 이미지가 아니라 미션 SPB의 별도 고정 길이 화자명
> 명령 슬롯이므로 v2.12에서 안전하게 캐리어 코드로 치환했다. `chr*.arc`는 캐릭터
> 초상화 데이터라 내부 키·압축 포맷을 변경하지 않았다.

> v2.13에서는 위 C8 텍스처를 전체 재인코딩하지 않고, 원본과 달라진 한글 글자 픽셀만
> 기존 팔레트에 매핑해 도식·캐릭터·말풍선 외곽선·연결선의 raw 데이터를 보존한다.

> v2.14에서는 Pillow RGBA 안티앨리어싱의 부분 알파가 C8 투명 팔레트로 양자화되어
> 글자 가장자리가 톱니처럼 깨질 수 있던 문제를 수정했다. 한글 레이어를 표시 영역의
> 불투명 픽셀에만 합성하고, 변경 픽셀에는 투명 팔레트 인덱스가 사용되지 않도록 검증한다.

> v2.15에서는 GameCube C8의 실제 8×4 타일 순서를 디코더와 오버레이 인코더에 함께 적용했다.
> 기존 8×8 가정 때문에 생기던 가로 분할·짝수 줄 수평 이동을 제거하고, 원문 후리가나까지
> 포함한 7개 라벨 영역을 한글로 다시 그렸다. 네 복제본의 라벨 밖 픽셀 변경은 0개다.

> v2.17에서는 Issue #14의 실제 화면과 원본 리소스를 다시 대조했다. bank102 후반부의
> 잘못된 제목 매칭을 바로잡고, bank102/bank108의 C4 하이라이트와 CMP 색상 레이어를
> 한 공통 글꼴 크기·원점으로 재작화했다. bank113의 `블루사이드 VS 레드사이드`와
> `배틀 로얄`도 같은 C4/CMPR 쌍으로 처리했으며, 중첩 HSD의 `대전 형식을 선택하세요`·
> `필드를 선택하세요` 안내와 캡슐 박스 편집 제목도 추가로 처리했다. sound setup 표기는
> `스테레오／모노`로 정리했고, 대전 방식의 영문 보조 표기는 의미를 유지해 깨끗하게
> 재작화했다. bank108의 잠금 `???` 1개는 원문 상태를 유지한다.

---

## 재현 방법

```
python image_work/70_extract_all_full.py   # 전체 611 @Texture 추출
python image_work/71_curate_jp_text.py     # 일본어 텍스트만 큐레이션
python image_work/72_jp_text_sheets.py     # 통합 컨택트시트 2장
python image_work/63_menu_titles.py --apply --preview # C4/CMP 메뉴 타이틀 쌍
python image_work/64_nested_menu_titles.py --apply --preview # 중첩 U8/HSD 메뉴 타이틀 쌍
python image_work/75_custom_dat_sprites.py --apply  # HAL DAT 미션 연출 패치
python image_work/76_custom_ui_assets.py --apply     # 타이틀/전투 조작설명 패치
```
