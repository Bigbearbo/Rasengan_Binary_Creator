#!/usr/bin/env python3
"""Spiral Language transcript wire-packing experiment.

Packets consist of raw 01 fields separated by exactly 16 '1' bits.
It is a temporary teaching envelope, NOT the language's intrinsic tokenizer.
All fields must end in 0; otherwise boundaries may be ambiguous.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import re

SEP = '1' * 16
OPS = {'echo':'0000', 'neg':'0100', 'zero':'1000', 'one':'0110'}


def check_field(field: str, index: int = 1) -> None:
    if not field or not re.fullmatch(r'[01]+', field):
        raise ValueError(f'field {index}: only 0 or 1 allowed, nonempty')
    if not field.endswith('0'):
        raise ValueError(f'field {index}: must end with 0 to anchor boundary')
    if SEP in field:
        raise ValueError(f'field {index}: contains 16 consecutive ones; delimiter collision')


def read_lines(text: str) -> list[str]:
    fields = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not fields:
        raise ValueError('no fields')
    for i, field in enumerate(fields, start=1):
        check_field(field, i)
    return fields


def pack(fields: list[str], terminal: bool = True) -> str:
    if not fields:
        raise ValueError('no fields')
    for i, field in enumerate(fields, start=1):
        check_field(field, i)
    return SEP.join(fields) + (SEP if terminal else '')


def unpack(wire: str) -> tuple[list[str], bool]:
    wire = re.sub(r'\s+', '', wire)
    if not wire or not re.fullmatch('[01]+', wire):
        raise ValueError('wire must contain only 0 and 1')
    terminal = wire.endswith(SEP)
    parts = wire.split(SEP)
    if terminal:
        parts.pop()
    if not parts:
        raise ValueError('no fields found')
    for i, part in enumerate(parts, start=1):
        check_field(part, i)
    if pack(parts, terminal) != wire:
        raise ValueError('wire is not canonical')
    return parts, terminal


def make_problem(operation: str, data: str) -> tuple[str, str]:
    if operation not in OPS:
        raise ValueError(f'unknown operation: {operation}')
    check_field(data)
    if len(data) < 3:
        raise ValueError('data word must be at least 3 bits')
    end = '1' * (len(OPS[operation]) - 1) + '0'  # punctuation matches operator width
    if SEP in end:
        raise ValueError('terminator conflicts with 16-ones delimiter; choose shorter data')
    q = '01' + OPS[operation] + data + end
    value = data[:-1]
    ans = {'echo':data,
           'neg':''.join('1' if x == '0' else '0' for x in value) + '0',
           'zero':'0' * len(data),
           'one':'1' * len(value) + '0'}[operation]
    check_field(q)
    check_field(ans)
    return q, ans


def test():
    for w in range(3, 16):
        for v in range(1 << (w-1)):
            data = f'{v:0{w-1}b}0'
            for op in OPS:
                q, ans = make_problem(op, data)
                assert len(q) == 2 + 4 + w + 4
                assert len(ans) == w and ans.endswith('0')
                assert q.endswith('1110')
                assert unpack(pack([q,ans], True)) == ([q,ans], True)
                assert unpack(pack([q,ans], False)) == ([q,ans], False)
    fields=['01001110','1110','010000100010111110','100010','010010101000111110']
    assert unpack(pack(fields)) == (fields, True)
    # A delimiter can be followed by an answer beginning in 1, creating a
    # visible run of 17 ones. Its 16 delimiter bits remain unambiguous.
    sample=pack(['01001110','1110'])
    assert '1'*17 in sample and unpack(sample)[0] == ['01001110','1110']
    for invalid in (['0101'], ['0100','11111111111111110'], ['0100','0102']):
        try:
            pack(invalid)
        except ValueError:
            pass
        else:
            raise AssertionError(f'invalid data accepted: {invalid}')
    for invalid in ('0101', '1111111111111111', '0100a'):
        try:
            unpack(invalid)
        except ValueError:
            pass
        else:
            raise AssertionError(f'invalid wire accepted: {invalid}')
    print('PASS: 262,112 Q/A framing round-trips plus invalid-input and 17-one-boundary checks')


def main():
    a=argparse.ArgumentParser(description='01 transcript ↔ continuous 01 wire; separator = exactly 16 ones')
    s=a.add_subparsers(dest='cmd', required=True)
    en=s.add_parser('pack'); en.add_argument('file', type=Path); en.add_argument('--no-terminal', action='store_true')
    de=s.add_parser('unpack'); de.add_argument('file', type=Path)
    pr=s.add_parser('problem'); pr.add_argument('operation', choices=OPS); pr.add_argument('data')
    s.add_parser('test')
    args=a.parse_args()
    try:
        if args.cmd=='pack':
            print(pack(read_lines(args.file.read_text('utf-8')), not args.no_terminal))
        elif args.cmd=='unpack':
            parts, terminal=unpack(args.file.read_text('utf-8'))
            print('\n'.join(parts))
            print(f'# fields={len(parts)}, terminal={terminal}', file=__import__('sys').stderr)
        elif args.cmd=='problem':
            print('\n'.join(make_problem(args.operation,args.data)))
        elif args.cmd=='test':test()
    except ValueError as e:a.error(str(e))

if __name__=='__main__':main()