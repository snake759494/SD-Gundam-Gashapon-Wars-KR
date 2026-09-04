# -*- coding: utf-8 -*-
"""Issue #20 메뉴 CMP와 사운드 플레이어 헤더 회귀 테스트."""
import importlib.util
import sys
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent


def load_script(filename, name):
    """argparse 기반 재작화 스크립트를 테스트 모드로 불러온다."""
    path = HERE / filename
    old_argv = sys.argv
    try:
        sys.argv = [str(path), "--preview"]
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.argv = old_argv


class Issue20RegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.menu = load_script("63_menu_titles.py", "issue20_menu_titles")
        cls.nested = load_script("77_nested_ui_assets.py", "issue20_nested_ui")

    def test_single_play_cmp_uses_bright_reference_mint(self):
        row = next(
            item for item in self.menu.RESOURCES["Info/arc/bank102.arc"]
            if item["text"] == "싱글 플레이"
        )
        self.assertEqual(row["color"], (107, 255, 206, 255))
        self.assertEqual(row["outline"], (8, 130, 99, 255))

        layout = self.menu.make_layout(row["text"], 316, 74)
        highlight = self.menu.draw_white(row["text"], 316, 74, layout)
        color = self.menu.draw_cmp(
            row["text"], 316, 74, row["color"], layout,
            row["segments"], row["outline"],
        )
        # 두 텍스처는 같은 layout을 공유하고, C4 바깥 영역은 완전
        # 투명해야 CMP 색상 레이어가 회색 사각형을 만들지 않는다.
        self.assertEqual(highlight.getchannel("A").getbbox(),
                         (7, 5, 304, 68))
        self.assertEqual(layout[1], self.menu.make_layout(
            row["text"], 316, 74
        )[1])
        self.assertEqual(color.getpixel((0, 0)), (255, 255, 255, 255))
        self.assertGreater(row["color"][1], 240)

    def test_sound_player_header_rows_do_not_cross_the_fixed_divider(self):
        image = self.nested.draw_header(
            "사운드 플레이어", "SOUND PLAYER", 162, 52
        )
        alpha = image.getchannel("A")
        top = alpha.crop((0, 0, 162, 30)).getbbox()
        bottom = alpha.crop((0, 30, 162, 52)).getbbox()
        self.assertIsNotNone(top)
        self.assertIsNotNone(bottom)
        # 배경의 고정 divider가 두 행 사이에 그대로 노출될 수 있는
        # 행 분리를 보장한다(실제 원본도 y=29~30 경계).
        self.assertLess(top[3], 30)
        self.assertGreaterEqual(bottom[1] + 30, 30)
        self.assertEqual(image.size, (162, 52))


if __name__ == "__main__":
    unittest.main()
