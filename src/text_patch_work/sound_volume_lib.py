# -*- coding: utf-8 -*-
"""Sound/volume.vsc의 고정 길이 캐리어 인코딩 공통 함수."""
import json

from vsc_lib import vsc_encode


NORMALIZE = {
    "·": "・",
    "–": "-",
    "—": "-",
}


def is_hangul(ch):
    return 0xAC00 <= ord(ch) <= 0xD7A3


def encode_text(text, carrier):
    out = bytearray()
    for ch in text:
        ch = NORMALIZE.get(ch, ch)
        if is_hangul(ch):
            if ch not in carrier:
                raise KeyError("font carrier가 없는 한글: %s" % ch)
            out += carrier[ch]
        else:
            try:
                out += ch.encode("cp932")
            except UnicodeEncodeError:
                out += b"?"
    return bytes(out)


def load_carrier(path):
    with open(path, encoding="utf-8") as f:
        return {k: bytes.fromhex(v) for k, v in json.load(f).items()}


def translate_rows(plain, mapping):
    """BGM 번호로 제목/설명 열을 교체하고 원본 열 구조를 보존한다."""
    text = plain.decode("cp932")
    rows = [line.split(",") for line in text.split("\r\n")]
    changed = 0
    header = mapping.get("_header")
    if header and rows and len(rows[0]) >= 8:
        if rows[0][0] != header["jp_number"]:
            raise ValueError("Sound/volume.vsc 헤더 기준 불일치")
        if rows[0][5] != header["jp_title"] or rows[0][7] != header["jp_desc"]:
            raise ValueError("Sound/volume.vsc 헤더 열 기준 불일치")
        rows[0][0] = header["number"]
        rows[0][5] = header["title"]
        rows[0][7] = header["desc"]
        changed += 1
    for row_index, row in enumerate(rows):
        if len(row) < 8:
            continue
        item = mapping.get(row[0])
        if not item:
            continue
        # 파일 버전이 바뀌어 번호가 재배치되면 조용히 다른 곡을 덮지 않는다.
        if item.get("jp_title") is not None and row[5] != item["jp_title"]:
            raise ValueError("Sound/volume.vsc 제목 기준 불일치: row %s" % row[0])
        if item.get("jp_desc") is not None and row[7] != item["jp_desc"]:
            raise ValueError("Sound/volume.vsc 설명 기준 불일치: row %s" % row[0])
        if item.get("title") is not None:
            row[5] = item["title"]
        if item.get("desc") is not None:
            row[7] = item["desc"]
        changed += 1
    return rows, changed


def serialize_rows(rows, original_length, carrier):
    """캐리어 인코딩 후 전체 원본 길이에 후행 공백으로 맞춘다."""
    new_plain = b"\r\n".join(
        b",".join(encode_text(cell, carrier) for cell in row)
        for row in rows
    )
    if len(new_plain) > original_length:
        return None, len(new_plain) - original_length
    padding = original_length - len(new_plain)
    if new_plain.endswith(b"\r\n"):
        new_plain = new_plain[:-2] + b" " * padding + b"\r\n"
    else:
        new_plain += b" " * padding
    if len(new_plain) != original_length:
        raise AssertionError("Sound/volume.vsc 평문 길이 불일치")
    new_raw = vsc_encode(new_plain)
    if len(new_raw) != original_length:
        raise AssertionError("Sound/volume.vsc raw 길이 불일치")
    return new_raw, 0
