# -*- coding: utf-8 -*-
"""C4/CMP 인코더의 투명도와 GameCube 블록 배치 회귀 테스트."""
import colorsys
import sys
import unittest

from PIL import Image

sys.path.insert(0, __import__("os").path.dirname(__file__))
import tex_lib as TX


class TextureCodecTests(unittest.TestCase):
    def test_nearest_preserves_exact_alpha_classes(self):
        palette = [
            (255, 255, 255, 0),
            (85, 85, 85, 182),
            (0, 0, 0, 255),
        ]
        self.assertEqual(TX._nearest(palette, (0, 0, 0, 0)), 0)
        self.assertEqual(TX._nearest(palette, (0, 0, 0, 255)), 2)

    def test_c4_transparent_pixels_do_not_become_gray(self):
        palette = [
            (255, 255, 255, 0),
            (255, 255, 255, 36),
            (85, 85, 85, 182),
            (255, 255, 255, 255),
        ]
        img = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
        img.putpixel((7, 7), (255, 255, 255, 255))
        raw = TX.encode_c4(img, palette, 8, 8)
        # Each C4 byte stores two texels. Every empty texel must use index 0;
        # otherwise the palette's semi-transparent gray entries create a box.
        for y in range(8):
            for x in range(8):
                value = raw[y * 4 + x // 2]
                index = value >> 4 if x % 2 == 0 else value & 0xF
                if (x, y) == (7, 7):
                    self.assertEqual(index, 3)
                else:
                    self.assertEqual(index, 0, (x, y, index))

    def test_cmp_subblock_grid_keeps_rows_and_columns(self):
        # 24x16 exercises three 8x8 macroblocks horizontally, two vertically,
        # and all four 4x4 subblock positions inside each macroblock.
        width, height = 24, 16
        blocks_x, blocks_y = width // 4, height // 4
        colors = [
            tuple(round(channel * 255) for channel in colorsys.hsv_to_rgb(
                i / (blocks_x * blocks_y), 0.9, 1.0))
            for i in range(blocks_x * blocks_y)
        ]
        source = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        pixels = source.load()
        for by in range(blocks_y):
            for bx in range(blocks_x):
                color = colors[by * blocks_x + bx]
                for y in range(by * 4, by * 4 + 4):
                    for x in range(bx * 4, bx * 4 + 4):
                        pixels[x, y] = color + (255,)
                # Force distinct CMP endpoints while leaving the center a
                # representative sample of the current 4x4 block.
                pixels[bx * 4, by * 4] = (0, 0, 0, 255)

        decoded = TX.decode_cmp_raw(TX.encode_cmp(source, width, height), width, height)

        def distance(a, b):
            return sum((a[i] - b[i]) ** 2 for i in range(3))

        for by in range(blocks_y):
            for bx in range(blocks_x):
                sample = decoded.getpixel((bx * 4 + 2, by * 4 + 2))[:3]
                actual = min(range(len(colors)), key=lambda i: distance(sample, colors[i]))
                expected = by * blocks_x + bx
                self.assertEqual(actual, expected, (bx, by, sample, actual))


if __name__ == "__main__":
    unittest.main()
