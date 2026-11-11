#!/usr/bin/env python3
"""Minimal SpiralToken codec compatible with the constructor in Hamu_VM_v0.1.cpp.

Source: https://github.com/Bigbearbo/Rasengan_Binary_Creator/blob/main/Hamu_VM_v0.1.cpp
A regular token is exactly n bits of value followed by k zero bits.
The level/field activation header is NOT a regular token and is NOT auto-inserted.
"""

import argparse
import json
import re
from pathlib import Path


def encode(value: int, order: int, level: int) -> str:
    """Equivalent to SpiralToken(value, order, level) for valid positive parameters."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError('value must be an integer')
    if order < 1 or level < 1:
        raise ValueError('order and level must be >= 1')
    if not (0 <= value < (1 << order)):
        raise ValueError('value is outside the n-bit range')
    return f'{value:0{order}b}' + '0' * level


def encode_bits(bits: str, level: int) -> str:
    """Take an n-bit payload literally and append k zeros; n=len(bits)."""
    if not bits or re.fullmatch(r'[01]+', bits) is None:
        raise ValueError('bits must be a nonempty sequence of 0 and 1')
    if level < 1:
        raise ValueError('level must be >= 1')
    return bits + '0' * level


def decode(code: str, order: int, level: int) -> int:
    """Decode with KNOWN n and k. Inferring k from trailing zeros is ambiguous."""
    if not code or re.fullmatch(r'[01]+', code) is None:
        raise ValueError('code must consist solely of 0 and 1')
    if order < 1 or level < 1:
        raise ValueError('order and level must be >= 1')
    if len(code) != order + level:
        raise ValueError(f'expected {order+level} bits, got {len(code)}')
    if code[-level:] != '0' * level:
        raise ValueError('missing or incorrect zero suffix')
    return int(code[:order], 2)


def encode_multiline(source: str, level: int, order: int | None = None) -> str:
    """Input one payload per line; preserve blank lines as example separators."""
    out = []
    for number, line in enumerate(source.splitlines(), start=1):
        bits = line.strip()
        if not bits:
            out.append('')
            continue
        if order is not None and len(bits) != order:
            raise ValueError(f'line {number}: expected {order} value bits, got {len(bits)}')
        try:
            out.append(encode_bits(bits, level))
        except ValueError as exc:
            raise ValueError(f'line {number}: {exc}') from exc
    return '\n'.join(out)


def test() -> None:
    count = 0
    for n in range(1, 9):
        for k in range(1, 5):
            for val in range(1 << n):
                code = encode(val, n, k)
                assert code == format(val, f'0{n}b') + '0' * k
                assert decode(code, n, k) == val
                count += 1
    assert encode(1, 2, 1) == '010'
    assert encode(3, 2, 1) == '110'
    assert encode(0, 1, 1) == '00'
    assert encode_bits('001', 1) == '0010'
    assert encode_multiline('001\n1\n\n101\n00', 1) == '0010\n10\n\n1010\n000'
    for bad in ('1', '011', '01a'):
        try:
            decode(bad, 2, 1)
        except ValueError:
            continue
        raise AssertionError(f'did not reject {bad}')
    print(f'PASS: {count} round-trips across n=1..8, k=1..4; edge cases PASS')


def main() -> None:
    ap = argparse.ArgumentParser(description='SpiralToken encoder / decoder (n-bit value + k zeros)')
    sub = ap.add_subparsers(dest='cmd', required=True)
    e = sub.add_parser('encode', help='encode a decimal value')
    e.add_argument('value', type=int)
    e.add_argument('order', type=int, help='n: width of value')
    e.add_argument('level', type=int, help='k: number of trailing zeros')
    b = sub.add_parser('bits', help='encode a raw binary payload')
    b.add_argument('payload')
    b.add_argument('level', type=int)
    d = sub.add_parser('decode', help='decode a token with KNOWN n and k')
    d.add_argument('code')
    d.add_argument('order', type=int)
    d.add_argument('level', type=int)
    m = sub.add_parser('multiline', help='encode each binary payload line in a text file')
    m.add_argument('file', type=Path)
    m.add_argument('level', type=int)
    m.add_argument('--order', type=int, default=None)
    sub.add_parser('test', help='run self-tests')
    a = ap.parse_args()
    try:
        if a.cmd == 'encode': print(encode(a.value, a.order, a.level))
        elif a.cmd == 'bits': print(encode_bits(a.payload, a.level))
        elif a.cmd == 'decode': print(decode(a.code, a.order, a.level))
        elif a.cmd == 'multiline': print(encode_multiline(a.file.read_text('utf-8'), a.level, a.order))
        elif a.cmd == 'test': test()
    except ValueError as exc:
        ap.error(str(exc))


if __name__ == '__main__':
    main()