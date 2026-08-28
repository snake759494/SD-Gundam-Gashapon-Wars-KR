# 일본어 텍스트 포함 이미지 목록 (GGPJB2)

전체 파일에서 `@Texture` 611개를 추출(`all_images/`, `all_sheets/`)한 뒤, **일본어 텍스트가
들어있는 이미지만** 별도로 추렸습니다.

- 큐레이션 폴더: `image_work/jp_text_images/{translated, untranslated}/`
- 통합 시트: `jp_text_translated_sheet.png` (73개), `jp_text_untranslated_sheet.png` (17개)
- 원자료: `jp_text_inventory.json`
- 판별 기준(그라운드 트루스): 원본 `files/` ↔ 패치본 `text_patch_work/patched_files/` 의
  `@Texture` 블록 바이트를 비교해 **실제로 바뀐 것 = 번역완료**, 텍스트인데 안 바뀐 것 = 미번역.

아이콘 뱅크(103/104/105/107/109/112/115~117: 숫자·기호·이펙트·초상), Effect/Arc(아이템·이펙트
픽토그램), Info/tpl(캐릭터 초상), files/cardicon 등은 **텍스트가 없어 제외**했습니다.

---

## 요약

| 구분 | @Texture | 상태 |
|---|---|---|
| 번역 완료 (라벨/버튼) | **73** | 패치 반영됨 (한글) |
| 미번역 @Texture | **17** | 아래 B 참조 |
| 보류 커스텀 스프라이트(.dat) | **4** | 로고 3종 + 원본 영문 연출 1종 (아래 C) |

---

## A. 번역 완료 — @Texture 라벨 63개  ✅

`jp_text_translated_sheet.png` 참조. 뱅크별 내용:

| 뱅크 | 개수 | 내용 |
|---|---|---|
| bank101 | 1 | ほうげき(포격) |
| bank102 | 7 | 메뉴 알약: モードセレクト·シングルプレイ·マルチプレイ·オプション·振動·サウンド設定·メモリーカード |
| bank106 | 1 | ランダムマップ(랜덤 맵) 명패 |
| bank110 | 1 | ほうげき(포격) |
| bank111 | 3 | 100%占領 / 100%拠点占領 / 100%ユニット生還 (승리 조건) |
| bank113 | 23 | 룰 라벨: 地上/水中/宇宙/空中·タイム設定·アイテム出現·ギミック·味方ヒット·じゃんけん·COMレベル·よわい/ふつう/つよい/ゲキつよ/ニュータイプ·15~90秒·デフォルトにもどす |
| bank114 | 9 | ゲキむず/かんたん/クリアタイム·敵を倒した数·地上/水中/宇宙/空中·むずかしい |
| bank118 | 18 | 룰 라벨(랜덤맵·時間制限·ハイド·カード·日/数·なし·5~30日·30~150秒·デフォルトにもどす) |

---

## B. 미번역 — @Texture 27개  ⛔

`jp_text_untranslated_sheet.png` 참조.

| 뱅크 | 개수 | 내용 | 미처리 사유 |
|---|---|---|---|
| bank102 | 7 | 용도 미확정 대형 흰색 헤더 | 메뉴 타이틀 10종은 v2.10에서 `63_menu_titles.py`로 번역 |
| bank108 | 7 | 대형 흰색 헤더 라벨(1개는 `???` 잠금 placeholder) | 화면 표시 위치·용도 미확정 |
| bank113 | 3 | 룰 화면 배너(VS/글로우 마스크 계열) | 텍스트+장식 합성이라 단순 교체 부적합 |

---

## C. 커스텀 스프라이트(.dat) — v2.11 처리/보류 현황

`.dat` 전체가 같은 포맷은 아니다. 미션 연출 파일은 HAL HSD/DAT 컨테이너 안의
고정 레이아웃 CI4 텍스처로 확인했으며, OAM/포인터를 건드리지 않고 원시 이미지 버퍼만
동일 길이로 재인코딩할 수 있다. `75_custom_dat_sprites.py`가 이 작업을 자동화한다.

| 파일 | 내용 |
|---|---|
| `Info/dat/sub_t01.dat` ~ `sub_t14.dat` (14) | 미션 제목 카드 → **v2.11 한글화** |
| `Info/dat/m_seikou.dat` | ミッション成功 → **미션 성공** |
| `Info/dat/m_sippai.dat` | ミッション失敗 → **미션 실패** |
| `Info/dat/sub_t01.dat` ~ `sub_t14.dat`의 버튼 텍스처 | つぎへ → **다음** |
| `Info/dat/battle_start.dat` | `BATTLE`/`START` 원본 영문, 추가 번역 불필요 |
| `files/ban_rogo.dat` | 반다이/타이틀 로고 |
| `files/demo_title.dat` | 데모 타이틀 로고 |
| `files/sim_title.dat` | 시뮬레이션 타이틀 로고 |

> 이 외 화자명 플레이트(예: バルトフェルド)는 압축 `chr*.arc`(커스텀 LZ) 안의
> 스프라이트로, arc 디코더가 있어야 접근 가능.

---

## 재현 방법

```
python image_work/70_extract_all_full.py   # 전체 611 @Texture 추출
python image_work/71_curate_jp_text.py     # 일본어 텍스트만 큐레이션
python image_work/72_jp_text_sheets.py     # 통합 컨택트시트 2장
python image_work/75_custom_dat_sprites.py --apply  # HAL DAT 미션 연출 패치
```
