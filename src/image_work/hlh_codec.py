# -*- coding: utf-8 -*-
"""HAL HLH/Huffman-LZ 리소스 코덱.

Info/arc/bank100.arc/scen/*.HLH 파일은 첫 4바이트에 복원 후 길이를
빅엔디언으로 저장하고, 그 뒤에 9비트 리프를 사용하는 허프만 트리와
4 KiB 링 버퍼 LZ 토큰을 저장한다. 트리는 처음에 한 번, 토큰 0x1000개마다
다시 기록된다. 이 모듈은 원본 바이트를 복원하고, 같은 파일 슬롯 안에
패치된 HSD를 재압축할 수 있도록 한다.

게임 파일의 U8 엔트리 크기는 변경하지 않는다. encode_hlh는 새 스트림이
슬롯보다 큰 경우를 즉시 실패시키며, 작은 경우에는 남은 바이트를 0으로
채운다. 디코더는 목표 길이에 도달하면 패딩을 읽지 않는다.
"""

from __future__ import annotations

import heapq
import struct
from collections import defaultdict


RING_SIZE = 0x1000
RING_START = 0xFEE
BLOCK_TOKENS = 0x1000
MIN_MATCH = 3
MAX_MATCH = 0x12
LITERAL_LIMIT = 0x100
NODE_BASE = 0x110
# Values at or above NODE_BASE are reserved for tree-node references by the
# decoder, so the longest representable copy is symbol 0x10F (18 bytes).
MAX_SYMBOL = 0x10F


class BitReader:
    def __init__(self, data: bytes, offset: int):
        self.data = data
        self.offset = offset
        self.remaining = 0
        self.buffer = 0

    def read1(self) -> int:
        if self.remaining == 0:
            if self.offset >= len(self.data):
                raise ValueError("HLH 비트스트림이 끝났습니다")
            self.buffer = self.data[self.offset]
            self.offset += 1
            self.remaining = 8
        self.remaining -= 1
        return (self.buffer >> self.remaining) & 1

    def read(self, count: int) -> int:
        value = 0
        for _ in range(count):
            value = (value << 1) | self.read1()
        return value


class BitWriter:
    def __init__(self):
        self.data = bytearray()
        self.buffer = 0
        self.count = 0

    def write(self, value: int, count: int) -> None:
        if count < 0 or value < 0 or value >= (1 << count):
            raise ValueError("잘못된 비트 값")
        for shift in range(count - 1, -1, -1):
            self.buffer = (self.buffer << 1) | ((value >> shift) & 1)
            self.count += 1
            if self.count == 8:
                self.data.append(self.buffer)
                self.buffer = 0
                self.count = 0

    def finish(self) -> bytes:
        if self.count:
            self.data.append(self.buffer << (8 - self.count))
            self.buffer = 0
            self.count = 0
        return bytes(self.data)


def _read_tree(reader: BitReader):
    """트리를 읽고 (root, left, right)를 반환한다."""
    left: list[int] = []
    right: list[int] = []

    def visit() -> int:
        if reader.read1() == 0:
            symbol = reader.read(9)
            if symbol > MAX_SYMBOL:
                raise ValueError("HLH 심볼 범위 오류")
            return symbol
        index = len(left)
        if index >= 0x21F:
            raise ValueError("HLH 허프만 노드가 너무 많습니다")
        left.append(0)
        right.append(0)
        left[index] = visit()
        right[index] = visit()
        return NODE_BASE + index

    return visit(), left, right


def _decode_tokens(data: bytes):
    """디버그/재압축용으로 토큰과 복원 바이트를 함께 반환한다."""
    if len(data) < 4:
        raise ValueError("HLH 헤더가 짧습니다")
    target = struct.unpack_from(">I", data, 0)[0]
    if target == 0:
        return b"", []

    reader = BitReader(data, 4)
    ring = bytearray(RING_SIZE)
    ring_pos = RING_START
    output = bytearray()
    tokens = []
    root, left, right = _read_tree(reader)
    block_count = 0

    while len(output) < target:
        if block_count == BLOCK_TOKENS:
            root, left, right = _read_tree(reader)
            block_count = 0
        symbol = root
        while symbol >= NODE_BASE:
            node = symbol - NODE_BASE
            if node >= len(left):
                raise ValueError("HLH 트리 참조 오류")
            symbol = right[node] if reader.read1() else left[node]
        if symbol < LITERAL_LIMIT:
            length = 1
            position = None
        else:
            length = symbol - 0xFD
            if length < MIN_MATCH or length > MAX_MATCH:
                raise ValueError("HLH LZ 길이 오류")
            position = reader.read(12)
        if len(output) + length > target:
            raise ValueError("HLH 토큰이 목표 길이를 초과했습니다")
        tokens.append((symbol, position, length))
        if symbol < LITERAL_LIMIT:
            output.append(symbol)
            ring[ring_pos] = symbol
            ring_pos = (ring_pos + 1) & (RING_SIZE - 1)
        else:
            # Read one byte and write it before reading the next one. This is
            # important for overlapping LZ copies such as distance=1.
            for index in range(length):
                value = ring[(position + index) & (RING_SIZE - 1)]
                output.append(value)
                ring[ring_pos] = value
                ring_pos = (ring_pos + 1) & (RING_SIZE - 1)
        block_count += 1
    return bytes(output), tokens


def decode_hlh(data: bytes) -> bytes:
    """HLH 한 개를 복원한다."""
    return _decode_tokens(data)[0]


def decode_hlh_tokens(data: bytes):
    """HLH를 (복원 바이트, (심볼, 링 위치, 길이) 목록)으로 읽는다."""
    return _decode_tokens(data)


def _longest_match(data: bytes, position: int, candidates: list[int]) -> tuple[int, int]:
    """현재 위치에서 가장 긴 링 버퍼 일치 구간을 찾는다.

    후보는 같은 3바이트 접두어를 가진 최근 위치들이다. 후보가 현재
    토큰과 겹치는 경우에도 링 버퍼의 복사 semantics와 동일하게 미래의
    target 바이트를 비교하므로 반복 패턴을 처리한다.
    """
    remaining = min(MAX_MATCH, len(data) - position)
    best_length = MIN_MATCH - 1
    best_distance = 0
    for previous in reversed(candidates):
        distance = position - previous
        if distance <= 0 or distance > RING_SIZE:
            continue
        length = 0
        while length < remaining and data[previous + length] == data[position + length]:
            length += 1
        if length > best_length:
            best_length = length
            best_distance = distance
            if length == remaining:
                break
    return best_length, best_distance


def _tokenize(data: bytes):
    """탐욕적 LZ 토큰화. 반환 원소는 (symbol, ring_position, length)."""
    if not data:
        return []
    positions: dict[bytes, list[int]] = defaultdict(list)
    tokens = []
    position = 0

    def add(index: int) -> None:
        if index + MIN_MATCH > len(data):
            return
        key = data[index:index + MIN_MATCH]
        bucket = positions[key]
        bucket.append(index)
        cutoff = index - RING_SIZE
        while bucket and bucket[0] <= cutoff:
            bucket.pop(0)
        # Keep the complete 4 KiB ring window. Some UI HSDs contain repeated
        # 3-byte runs where the oldest candidate has the longest continuation;
        # dropping those candidates makes an otherwise unchanged file grow.
        # A bounded tail keeps the parse fast while retaining substantially
        # more choices than the old 96-entry heuristic.
        if len(bucket) > 2048:
            del bucket[:-2048]

    while position < len(data):
        if position + MIN_MATCH <= len(data):
            length, distance = _longest_match(
                data, position, positions[data[position:position + MIN_MATCH]]
            )
        else:
            length, distance = MIN_MATCH - 1, 0
        # A one-byte lazy look-ahead avoids spending a token on a short match
        # when advancing by one literal exposes a materially longer match.
        # This is the small parsing choice used by the original asset packer
        # for many repeated UI/HSD runs.
        if length >= MIN_MATCH and length < MAX_MATCH:
            next_position = position + 1
            if next_position + MIN_MATCH <= len(data):
                current_key = data[position:position + MIN_MATCH]
                positions[current_key].append(position)
                next_length, _ = _longest_match(
                    data, next_position,
                    positions[data[next_position:next_position + MIN_MATCH]],
                )
                positions[current_key].pop()
                if next_length > length + 1:
                    length, distance = MIN_MATCH - 1, 0
        if length >= MIN_MATCH:
            symbol = length + 0xFD
            ring_position = (RING_START + position - distance) & (RING_SIZE - 1)
            tokens.append((symbol, ring_position, length))
            for index in range(position, position + length):
                add(index)
            position += length
        else:
            tokens.append((data[position], None, 1))
            add(position)
            position += 1
    return tokens


def _huffman_tree(tokens):
    """토큰 심볼에서 결정적인 이진 허프만 트리를 만든다."""
    frequencies = defaultdict(int)
    for symbol, _, _ in tokens:
        frequencies[symbol] += 1
    if not frequencies:
        raise ValueError("빈 HLH 블록")
    if len(frequencies) == 1:
        symbol = next(iter(frequencies))
        return ("leaf", symbol), {symbol: ()}

    heap = []
    serial = 0
    for symbol, frequency in sorted(frequencies.items()):
        heap.append((frequency, serial, ("leaf", symbol)))
        serial += 1
    heapq.heapify(heap)
    while len(heap) > 1:
        left_frequency, _, left = heapq.heappop(heap)
        right_frequency, _, right = heapq.heappop(heap)
        heapq.heappush(heap, (
            left_frequency + right_frequency,
            serial,
            ("node", left, right),
        ))
        serial += 1
    root = heap[0][2]
    codes = {}

    def walk(node, path):
        if node[0] == "leaf":
            codes[node[1]] = tuple(path)
            return
        walk(node[1], path + [0])
        walk(node[2], path + [1])

    walk(root, [])
    return root, codes


def _write_tree(writer: BitWriter, node) -> None:
    if node[0] == "leaf":
        writer.write(0, 1)
        writer.write(node[1], 9)
        return
    writer.write(1, 1)
    _write_tree(writer, node[1])
    _write_tree(writer, node[2])


def encode_hlh(data: bytes, slot_size: int | None = None) -> bytes:
    """복원된 HSD를 HLH로 압축한다.

    slot_size가 주어지면 결과가 그 고정 슬롯에 들어가는지 확인하고,
    남은 공간은 0으로 패딩한다. 게임 U8 엔트리의 크기/오프셋을 바꾸지
    않기 위한 기본 사용 방식이다.
    """
    tokens = _tokenize(data)
    writer = BitWriter()
    block_start = 0
    while block_start < len(tokens):
        block = tokens[block_start:block_start + BLOCK_TOKENS]
        root, codes = _huffman_tree(block)
        _write_tree(writer, root)
        for symbol, position, _ in block:
            for bit in codes[symbol]:
                writer.write(bit, 1)
            if symbol >= LITERAL_LIMIT:
                if position is None:
                    raise ValueError("LZ 토큰에 링 위치가 없습니다")
                writer.write(position, 12)
        block_start += BLOCK_TOKENS
    stream = writer.finish()
    encoded = struct.pack(">I", len(data)) + stream
    if slot_size is not None:
        if len(encoded) > slot_size:
            raise ValueError(
                f"HLH 압축 결과가 슬롯보다 큽니다: {len(encoded):#x} > {slot_size:#x}"
            )
        encoded += bytes(slot_size - len(encoded))
    return encoded


def validate_roundtrip(data: bytes, slot_size: int | None = None) -> bytes:
    """압축 결과를 즉시 다시 복원해 코덱 자체를 검증한다."""
    encoded = encode_hlh(data, slot_size)
    if decode_hlh(encoded) != data:
        raise AssertionError("HLH round-trip 불일치")
    return encoded
