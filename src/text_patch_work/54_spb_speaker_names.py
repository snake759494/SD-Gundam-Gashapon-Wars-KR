# -*- coding: utf-8 -*-
"""미션 SPB 화자명 명령을 한글로 치환한다.

대사 본문(04 00)과 달리 화자명은 0F 00 08 00 13 00 명령의 별도 고정
길이 슬롯에 들어 있다. 이 슬롯은 리소스 참조 키가 아니므로 명령 형태와
널 종료를 모두 확인한 뒤 표시명 매핑에 있는 항목만 같은 길이로 바꾼다.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import struct
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / "files"
PATCHED = HERE / "patched_files"

parser = argparse.ArgumentParser()
parser.add_argument("--apply", action="store_true")
args = parser.parse_args()

carrier = {
    key: bytes.fromhex(value)
    for key, value in json.loads((HERE / "carrier_map.json").read_text(encoding="utf-8")).items()
}
display_map = json.loads((HERE / "disp_map.json").read_text(encoding="utf-8"))["char"]


def encode_display(text: str) -> bytes:
    encoded = bytearray()
    for character in text:
        if "\uac00" <= character <= "\ud7a3":
            encoded += carrier[character]
        else:
            encoded += character.encode("cp932")
    return bytes(encoded)


def patch_file(path: Path) -> tuple[bytes, int, list[str]]:
    data = bytearray(path.read_bytes())
    changed = 0
    names: list[str] = []
    cursor = 0
    while True:
        command = data.find(b"\x0f\x00\x08\x00\x13\x00", cursor)
        if command < 0:
            break
        if command + 8 > len(data):
            break
        slot = struct.unpack_from("<H", data, command + 6)[0]
        string_offset = command + 8
        string_end = string_offset + slot
        if not 2 <= slot <= 128 or string_end > len(data):
            cursor = command + 2
            continue
        raw = bytes(data[string_offset:string_end])
        if raw[-1] != 0:
            cursor = command + 2
            continue
        try:
            original = raw[:-1].decode("cp932")
        except UnicodeDecodeError:
            cursor = command + 2
            continue
        translated = display_map.get(original)
        if translated is None or translated == original:
            cursor = string_end
            continue
        payload = encode_display(translated)
        if len(payload) + 1 > slot:
            raise RuntimeError(
                f"화자명 슬롯 오버플로: {path.relative_to(PATCHED)} {original!r} -> {translated!r}"
            )
        if args.apply:
            data[string_offset:string_end] = payload + b"\0" * (slot - len(payload))
        changed += 1
        names.append(f"{original}->{translated}")
        cursor = string_end
    return bytes(data), changed, names


total = 0
for path in sorted(PATCHED.rglob("*.SPB")):
    rebuilt, changed, names = patch_file(path)
    if not changed:
        continue
    total += changed
    print(f"{path.relative_to(PATCHED).as_posix()}: {changed} speaker name(s) {', '.join(names)}")
    if args.apply:
        path.write_bytes(rebuilt)

print(f"speaker names changed: {total}")
print("APPLIED" if args.apply else "(dry run)")
