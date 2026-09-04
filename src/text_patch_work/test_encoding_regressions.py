# -*- coding: utf-8 -*-
"""Issue #18 텍스트/VSC 캐리어 경계 회귀 테스트."""
import json
import struct
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
        self.assertNotIn("※", ko)
        self.assertNotIn("@c7", ko)
        self.assertNotIn("@c8", ko)
        carrier = load_carrier(HERE / "carrier_map.json")
        encoded = bytearray()
        for ch in ko:
            encoded += carrier[ch] if 0xAC00 <= ord(ch) <= 0xD7A3 else ch.encode("cp932")
        self.assertEqual(len(encoded) % 2, 0)
        self.assertIn(carrier["레"], encoded)
        dol = (HERE / "patched_main.dol").read_bytes()
        off = entry["occ"][0]["off"]
        self.assertEqual(dol[off:off + len(encoded)], bytes(encoded))

        # 보충 주입 목록에도 이전 "모노럴" 표기가 남지 않아야 한다.
        extra = master["dol_extra"]
        stereo_extra = next(e for e in extra if "ステレオ/モノラル" in e["jp"])
        self.assertEqual(stereo_extra["ko"],
                         "스테레오／모노\n전환과 음량 조절\n설정을 합니다")
        self.assertNotIn("모노럴", stereo_extra["ko"])

    def test_issue21_dialogue_lines_fit_their_original_slots(self):
        master = json.loads((HERE / "translation_master.json").read_text(encoding="utf-8"))
        occurrences = json.loads((HERE / "dialogue_all.json").read_text(encoding="utf-8"))
        carrier = load_carrier(HERE / "carrier_map.json")

        def encode(text):
            return b"".join(
                carrier[ch] if 0xAC00 <= ord(ch) <= 0xD7A3 else ch.encode("cp932")
                for ch in text
            )

        expected = {
            "587": "붙은 게, 적이 되는",
            "601": "자기 차례를",
        }
        for dialogue_id, marker in expected.items():
            ko = master["dialogue"][dialogue_id]["ko"]
            slots = [o["length"] for o in occurrences
                     if o["jp"] == master["dialogue"][dialogue_id]["jp"]]
            self.assertTrue(slots)
            self.assertTrue(any(len(encode(ko)) + 1 <= slot for slot in slots))
            self.assertIn(marker, ko)
            self.assertEqual(ko.count("\\\\n"), 1)

    def test_all_fixed_speaker_name_command_forms_are_patched(self):
        cmap = load_carrier(HERE / "carrier_map.json")
        display_map = json.loads((HERE / "disp_map.json").read_text(encoding="utf-8"))["char"]
        markers = (bytes.fromhex("0b0008001300"),
                   bytes.fromhex("0e0008001300"),
                   bytes.fromhex("0f0008001300"))
        expected = {"キラ": 16, "マリュー": 34, "シン": 2, "セイラ・マス": 1}
        seen = {key: 0 for key in expected}

        def encode(text):
            return b"".join(
                cmap[ch] if ch in cmap else ch.encode("cp932")
                for ch in text
            )

        base = ROOT / "src" / "files"
        patched = ROOT / "src" / "text_patch_work" / "patched_files"
        for source in base.rglob("*.SPB"):
            target = patched / source.relative_to(base)
            if not target.exists():
                continue
            original_data = source.read_bytes()
            patched_data = target.read_bytes()
            for marker in markers:
                cursor = 0
                while True:
                    command = original_data.find(marker, cursor)
                    if command < 0:
                        break
                    slot = struct.unpack_from("<H", original_data, command + 6)[0]
                    start = command + 8
                    end = start + slot
                    raw = original_data[start:end]
                    if (2 <= slot <= 128 and len(raw) == slot and raw[-1] == 0):
                        original = raw[:-1].decode("cp932")
                        if original in expected:
                            payload = encode(display_map[original])
                            self.assertLessEqual(len(payload) + 1, slot)
                            self.assertEqual(patched_data[start:start + len(payload)], payload)
                            self.assertEqual(
                                patched_data[start + len(payload):end],
                                b"\0" * (slot - len(payload)),
                            )
                            seen[original] += 1
                    cursor = command + 2
        self.assertEqual(seen, expected)

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
