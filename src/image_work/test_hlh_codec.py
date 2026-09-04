# -*- coding: utf-8 -*-
"""HLH 압축/복원과 링 버퍼 겹침 복사 회귀 테스트."""
import sys
import unittest

sys.path.insert(0, __import__("os").path.dirname(__file__))
import hlh_codec as HLH


class HLHCodecTests(unittest.TestCase):
    def test_round_trip_exercises_literals_and_overlapping_copies(self):
        payload = (b"ABCD" * 97) + bytes(range(256)) + (b"XYZ" * 211)
        packed = HLH.encode_hlh(payload)
        self.assertEqual(HLH.decode_hlh(packed), payload)
        self.assertLess(len(packed), len(payload))

    def test_fixed_slot_round_trip_and_padding(self):
        payload = (b"0123456789" * 173) + b"tail"
        packed = HLH.encode_hlh(payload)
        slot = len(packed) + 37
        fixed = HLH.encode_hlh(payload, slot_size=slot)
        self.assertEqual(len(fixed), slot)
        self.assertEqual(fixed[len(packed):], b"\0" * 37)
        self.assertEqual(HLH.decode_hlh(fixed), payload)


if __name__ == "__main__":
    unittest.main()
