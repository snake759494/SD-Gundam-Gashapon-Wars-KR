# -*- coding: utf-8 -*-
"""Issue #23 시나리오 표시명·중복 HSD 회귀 테스트."""
import json
import struct
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from vsc_lib import vsc_decode


BASE = ROOT / "src" / "files"
PATCHED = HERE / "patched_files"


def u32(data, offset):
    return struct.unpack_from(">I", data, offset)[0]


def u8_entries(data):
    if u32(data, 0) != 0x55AA382D:
        raise AssertionError("U8 magic mismatch")
    root = u32(data, 4)
    count = u32(data, root + 8)
    string_base = root + count * 12
    stack = []
    result = []
    for index in range(1, count):
        node = root + index * 12
        raw_name = u32(data, node)
        kind = raw_name >> 24
        name_offset = raw_name & 0xFFFFFF
        end = data.index(b"\0", string_base + name_offset)
        name = data[string_base + name_offset:end].decode("cp932", "replace")
        first = u32(data, node + 4)
        last = u32(data, node + 8)
        while stack and index >= stack[-1][1]:
            stack.pop()
        if kind:
            stack.append((name, last))
        else:
            result.append(("/".join(x[0] for x in stack + [(name, last)]),
                           first, last))
    return result


def u8_file(data, wanted):
    for name, offset, size in u8_entries(data):
        if name == wanted:
            return data[offset:offset + size]
    raise AssertionError("U8 entry missing: " + wanted)


class Issue23RegressionTests(unittest.TestCase):
    def test_reported_unit_keys_are_closed_in_every_vsc_copy(self):
        carriers = json.loads(
            (HERE / "carrier_map.json").read_text(encoding="utf-8")
        )

        def encode(text):
            return b"".join(
                bytes.fromhex(carriers[ch])
                if 0xAC00 <= ord(ch) <= 0xD7A3 else ch.encode("cp932")
                for ch in text
            )

        for jp, ko in (("ゲルググ", "겔구그"), ("ジム", "짐")):
            jp_raw = jp.encode("cp932")
            ko_raw = encode(ko)
            source_total = 0
            for source in BASE.rglob("*.vsc"):
                source_plain = vsc_decode(source.read_bytes())
                source_count = source_plain.count(jp_raw)
                if not source_count:
                    continue
                source_total += source_count
                target = PATCHED / source.relative_to(BASE)
                self.assertTrue(target.exists(), source)
                target_raw = target.read_bytes()
                self.assertEqual(len(target_raw), source.stat().st_size)
                target_plain = vsc_decode(target_raw)
                self.assertNotIn(jp_raw, target_plain,
                                 str(source.relative_to(BASE)))
                self.assertGreaterEqual(target_plain.count(ko_raw), source_count)
            self.assertGreater(source_total, 0)

    def test_mission_clear_and_next_button_copies_match_patched_sources(self):
        original_success = (BASE / "Info/dat/m_seikou.dat").read_bytes()
        patched_success = (PATCHED / "Info/dat/m_seikou.dat").read_bytes()
        success_size = ((240 + 7) // 8 * 8) * ((182 + 7) // 8 * 8) // 2
        original_success_raw = original_success[0x36C0:0x36C0 + success_size]
        patched_success_raw = patched_success[0x36C0:0x36C0 + success_size]
        self.assertNotEqual(original_success_raw, patched_success_raw)

        nested_success = u8_file(
            (PATCHED / "Info/arc/bank111.arc").read_bytes(),
            "scen/pb_m_cl.dat",
        )
        self.assertEqual(nested_success[0x36C0:0x36C0 + success_size],
                         patched_success_raw)

        original_sub = (BASE / "Info/dat/sub_t01.dat").read_bytes()
        patched_sub = (PATCHED / "Info/dat/sub_t01.dat").read_bytes()
        next_size = ((42 + 7) // 8 * 8) * ((18 + 7) // 8 * 8) // 2
        original_next = original_sub[0xCE20:0xCE20 + next_size]
        patched_next = patched_sub[0xCE20:0xCE20 + next_size]
        self.assertNotEqual(original_next, patched_next)
        for rel in ("Info/arc/bank111.arc", "Info/arc/bank120.arc"):
            nested = u8_file((PATCHED / rel).read_bytes(),
                             "scen/rw_push_a.dat")
            self.assertEqual(nested[0x12E0:0x12E0 + next_size], patched_next)

    def test_scenario_and_multiplayer_header_copies_are_patched(self):
        checks = (
            ("Info/arc/bank103.arc", "scen/sce_mission.dat", 0x15E60, 4480),
            ("Info/arc/bank115.arc", "scen/sub_title.dat", 0x1860, 4480),
        )
        for rel, entry, offset, size in checks:
            original = u8_file((BASE / rel).read_bytes(), entry)
            patched = u8_file((PATCHED / rel).read_bytes(), entry)
            self.assertEqual(len(original), len(patched))
            self.assertNotEqual(original[offset:offset + size],
                                patched[offset:offset + size])

        for rel, entry in (("Info/arc/bank113.arc", "scen/usel_start.dat"),
                           ("Info/arc/bank114.arc", "scen/suv_start.dat")):
            original = u8_file((BASE / rel).read_bytes(), entry)
            patched = u8_file((PATCHED / rel).read_bytes(), entry)
            self.assertEqual(len(original), len(patched))
            start_size = ((126 + 7) // 8 * 8) * ((22 + 7) // 8 * 8) // 2
            self.assertNotEqual(original[0x26A0:0x26A0 + start_size],
                                patched[0x26A0:0x26A0 + start_size])


if __name__ == "__main__":
    unittest.main()
