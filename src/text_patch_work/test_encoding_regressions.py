# -*- coding: utf-8 -*-
"""Issue #18 텍스트/VSC 캐리어 경계 회귀 테스트."""
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from sound_volume_lib import load_carrier, serialize_rows, translate_rows
from vsc_lib import vsc_decode


class EncodingRegressionTests(unittest.TestCase):
    def test_sound_setup_row_is_even_and_has_no_ascii_color_token(self):
        master = json.loads((HERE / "translation_master.json").read_text(encoding="utf-8"))
        entry = next(e for e in master["dol"]
                     if e["jp"] == "サウンド　　　　　 @c7ステレオ@c7／@c8モノラル")
        ko = entry["ko"]
        self.assertEqual(ko, "사운드　　　　　스테레오／모노")
        self.assertNotIn(" ", ko)
        self.assertNotIn("@c7", ko)
        self.assertNotIn("@c8", ko)
        carrier = load_carrier(HERE / "carrier_map.json")
        encoded = bytearray()
        for ch in ko:
            encoded += carrier[ch] if 0xAC00 <= ord(ch) <= 0xD7A3 else ch.encode("cp932")
        self.assertEqual(len(encoded) % 2, 0)
        dol = (HERE / "patched_main.dol").read_bytes()
        off = entry["occ"][0]["off"]
        self.assertEqual(dol[off:off + len(encoded)], bytes(encoded))

    def test_sound_volume_round_trip_keeps_file_size_and_translates_japanese_rows(self):
        master = json.loads((HERE / "translation_master.json").read_text(encoding="utf-8"))
        raw = (ROOT / "src" / "files" / "Sound" / "volume.vsc").read_bytes()
        carrier = load_carrier(HERE / "carrier_map.json")
        rows, changed = translate_rows(vsc_decode(raw), master["sound_volume"])
        patched, overflow = serialize_rows(rows, len(vsc_decode(raw)), carrier)
        self.assertEqual(overflow, 0)
        self.assertEqual(len(patched), len(raw))
        self.assertEqual(changed, 40)
        self.assertEqual(rows[0][0], "번호")
        row13 = next(row for row in rows if row[0] == "13")
        self.assertEqual(row13[5], "철저 항전")
        self.assertEqual(row13[7], "기동전사 건담 SEED에서")

        def is_japanese(ch):
            code = ord(ch)
            return (0x3040 <= code <= 0x30FF or
                    0x3400 <= code <= 0x9FFF or
                    0xF900 <= code <= 0xFAFF)

        for row in rows:
            if len(row) >= 8:
                self.assertFalse(any(is_japanese(ch) for ch in row[5] + row[7]))


if __name__ == "__main__":
    unittest.main()
