"""Syntax and label-free student transport for P031. No solver or answer loader."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


@dataclass(frozen=True)
class Profile:
    profile_id: str
    n_op: int
    n_data: int
    operators: tuple[str, ...]
    active_end: bool
    layer: int = 1
    version: str = 'v0'
    highwater: int = 0

    def __post_init__(self):
        if self.n_op not in (1, 2, 3) or not 1 <= self.n_data <= 4:
            raise ValueError('Unsupported width; define a new audited profile first')
        if self.layer not in (1, 2) or self.version not in ('v0', 'v1', 'v2'):
            raise ValueError('Unknown layer/version')
        if not self.operators or len(set(self.operators)) != len(self.operators):
            raise ValueError('Empty or duplicate operator table')
        table = self.codes
        if set(self.operators) - table.keys():
            raise ValueError('Operator absent from versioned vocabulary')
        allocated = [int(table[op][:-1], 2) for op in self.operators]
        if self.highwater < max(allocated) or self.highwater >= 2 ** self.n_op:
            raise ValueError('Invalid branch high-water mark')
        if self.active_end and self.highwater >= 2 ** self.n_op - 1:
            raise ValueError('END collides with an allocated ID')
        if self.n_op == 1 and self.active_end:
            raise ValueError('n=1 END is not activated in this teaching protocol')
        if self.layer == 2 and (not self.active_end or self.n_op < 2):
            raise ValueError('Two-layer teaching requires its declared END profile')

    @property
    def codes(self):
        names = ['echo', 'neg', 'zero', 'one', 'cut', 'and']
        if self.version != 'v0':
            names.append('or' if self.version == 'v1' else 'xor')
        limit = 1 if self.n_op == 1 else 3 if self.n_op == 2 else len(names)
        return {name: format(i, f'0{self.n_op}b') + '0'
                for i, name in enumerate(names[:limit])}

    @property
    def end(self):
        return '1' * self.n_op + '0' if self.active_end else ''

    @property
    def header(self):
        return '01' if self.layer == 1 else '00100001100'


@dataclass(frozen=True)
class Question:
    operator: str
    operands: tuple[int, ...]


def require_bits(text):
    if not isinstance(text, str) or not text or set(text) - set('01'):
        raise ValueError('Expected nonempty raw 0/1')
    return text


def encode_question(question: Question, profile: Profile) -> str:
    if question.operator not in profile.operators:
        raise ValueError('Inactive operator')
    arity = 2 if question.operator in ('and', 'or', 'xor') else 1
    if len(question.operands) != arity:
        raise ValueError('Wrong arity')
    if any(type(v) is not int or not 0 <= v < 2 ** profile.n_data
           for v in question.operands):
        raise ValueError('Operand outside declared width')
    return (profile.header + profile.codes[question.operator]
            + ''.join(format(v, f'0{profile.n_data}b') + '0'
                      for v in question.operands) + profile.end)


def parse_question(raw: str, profile: Profile) -> Question:
    """Syntax only: deliberately does not calculate or attach an answer."""
    require_bits(raw)
    if not raw.startswith(profile.header):
        raise ValueError('Wrong frame header')
    index = len(profile.header)
    code = raw[index:index + profile.n_op + 1]
    index += profile.n_op + 1
    inverse = {profile.codes[name]: name for name in profile.operators}
    if code not in inverse:
        raise ValueError('Unknown/reserved operator code')
    op = inverse[code]
    arity = 2 if op in ('and', 'or', 'xor') else 1
    width = profile.n_data + 1
    if len(raw) != index + arity * width + len(profile.end):
        raise ValueError('Wrong frame length or missing END')
    values = []
    for _ in range(arity):
        word = raw[index:index + width]
        if not word.endswith('0'):
            raise ValueError('Invalid data tail')
        values.append(int(word[:-1], 2))
        index += width
    if raw[index:] != profile.end:
        raise ValueError('Wrong END')
    return Question(op, tuple(values))


class CurriculumPosition:
    """Host-side state only. It is never attached to a student's bit input."""
    def __init__(self):
        self.n_op = self.n_data = self.layer = self.highwater = 0
        self.active_end = False

    def advance(self, profile: Profile):
        if (profile.n_op < self.n_op or profile.n_data < self.n_data
                or profile.layer < self.layer or profile.highwater < self.highwater
                or self.active_end and not profile.active_end):
            raise ValueError('Curriculum cannot downgrade widths/layer/highwater/END')
        self.n_op, self.n_data, self.layer = profile.n_op, profile.n_data, profile.layer
        self.highwater, self.active_end = profile.highwater, profile.active_end


def canonical_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


class StudentBank:
    """Read only label-free rows. Manifest carries coordinator-only routing."""
    def __init__(self, folder: Path):
        self.folder = Path(folder)
        self.manifest = json.loads((self.folder / 'manifest.json').read_text('utf-8'))
        if self.manifest['schema_version'] != 'sle-math-bank/1':
            raise ValueError('Unsupported bank schema')
        raw = (self.folder / 'questions.jsonl').read_bytes()
        if hashlib.sha256(raw).hexdigest() != self.manifest['files']['questions.jsonl']:
            raise ValueError('Question file integrity failure')
        self.rows = [json.loads(row) for row in raw.decode('utf-8').splitlines()]
        identifiers = set()
        for row in self.rows:
            if set(row) != {'case_id', 'raw_question_bits'} or row['case_id'] in identifiers:
                raise ValueError('Unexpected student fields or duplicate case ID')
            identifiers.add(row['case_id'])
            require_bits(row['raw_question_bits'])
        self.index = self.manifest['case_index']
        if identifiers != self.index.keys():
            raise ValueError('Case index differs from questions')

    def select(self, profile_id, split):
        if profile_id not in self.manifest['profiles'] or split not in ('train', 'val', 'test'):
            raise ValueError('Unknown profile or split')
        return [row for row in self.rows if self.index[row['case_id']] == [profile_id, split]]

    def dispatch(self, profile_id: str, split: str, student: Callable[[str], str]):
        """NN/VM callbacks receive the exact same string, without labels or AST."""
        outputs = []
        for row in self.select(profile_id, split):
            prediction = student(row['raw_question_bits'])
            outputs.append({'case_id': row['case_id'], 'generated': prediction})
        return outputs


def normalize_nn(tokens: str) -> str:
    """Accept only one final external STOP, never reinterpret native END as STOP."""
    if not isinstance(tokens, str) or not tokens.endswith('S') or 'S' in tokens[:-1]:
        raise ValueError('Exactly one final STOP is required')
    return require_bits(tokens[:-1])


def normalize_vm(bits: str, completed: bool) -> str:
    if completed is not True:
        raise ValueError('VM transport did not complete its response')
    return require_bits(bits)
