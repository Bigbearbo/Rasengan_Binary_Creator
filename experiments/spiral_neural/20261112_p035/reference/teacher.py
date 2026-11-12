"""Offline-only semantic oracle, deterministic bank builder and answer grading."""
from __future__ import annotations

import hashlib
import itertools
import json
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

from student_io import Profile, Question, canonical_json, encode_question, parse_question


SCHEMA = 'sle-math-bank/1'
SEED = 20261112
SOURCE_COMMIT = '524487f61ed2e1f6abb2eace57ed76fadc9c4fea'
PENDING = {
    'B2_add_sub': 'pending-vocabulary: result widths, carry/negative policy and operator IDs',
    'B3_B6': 'pending-vocabulary: MUL/DIV/MOD/composition grammar and semantics',
    'B7_B8': 'pending-vocabulary: fractions/equations/scope/geometry/answer equivalence',
    'B9': 'metadata-only planned; no external exam questions copied',
    'B10': 'neural translation not implemented; structured synthetic questions only',
    'upgrade_ritual': 'syntax-pending: independently distinguishable ritual frame not defined',
}


@dataclass(frozen=True)
class TaskCase:
    case_id: str
    semantic_group: str
    family: str
    operator: str
    operands: tuple[int, ...]
    result_bits: str
    digit_width: int
    profile_id: str
    seed: int
    split: str
    flags: tuple[str, ...]
    provenance: str = 'synthetic-exhaustive; teacher offline; U/F/A separated in README'
    school_level: str = 'prerequisite-bit-operations'
    output_kind: str = 'native-SLE-word; CUT returns bare information bits'
    bridge_mode: str = 'structured-AST; no natural-language reading claim'
    semantic_version: str = 'reference-codec-v0-v1-v2/1'


def profiles():
    stages = [
        Profile('s0_echo_d1', 1, 1, ('echo',), False),
        Profile('s1_echo_d2', 1, 2, ('echo',), False),
        Profile('s2_echo_d3', 1, 3, ('echo',), False),
        Profile('s3_op2', 2, 3, ('echo',), False),
        Profile('s4_neg', 2, 3, ('echo', 'neg'), False, highwater=1),
        Profile('s5_zero', 2, 3, ('echo', 'neg', 'zero'), False, highwater=2),
        Profile('s6_end', 2, 3, ('echo', 'neg', 'zero'), True, highwater=2),
        Profile('s7_one_cut', 3, 3, ('echo', 'neg', 'zero', 'one', 'cut'), True, highwater=4),
        Profile('s8_and', 3, 3, ('echo', 'neg', 'zero', 'one', 'cut', 'and'), True, highwater=5),
    ]
    base = stages[-1].operators
    # Branches are independent version/layer catalogues, not a single training order.
    stages += [Profile('v1_or', 3, 3, base + ('or',), True, version='v1', highwater=6),
               Profile('v2_xor', 3, 3, base + ('xor',), True, version='v2', highwater=6),
               Profile('d4_and', 3, 4, base, True, highwater=5)]
    for version in ('v0', 'v1', 'v2'):
        ops = base + (() if version == 'v0' else ('or' if version == 'v1' else 'xor',))
        stages.append(Profile('layer2_' + version, 3, 3, ops, True, layer=2,
                              version=version, highwater=5 if version == 'v0' else 6))
    return stages


def oracle(q: Question, p: Profile):
    """Not imported by student_io; no use during dispatch or prediction."""
    a = q.operands[0]
    mask = 2 ** p.n_data - 1
    if q.operator == 'echo' or q.operator == 'cut':
        value = a
    elif q.operator == 'neg':
        value = mask ^ a
    elif q.operator == 'zero':
        value = 0
    elif q.operator == 'one':
        value = mask
    elif q.operator == 'and':
        value = a & q.operands[1]
    elif q.operator == 'or':
        value = a | q.operands[1]
    elif q.operator == 'xor':
        value = a ^ q.operands[1]
    else:
        raise ValueError('pending-vocabulary: no semantic oracle for this operator')
    return format(value, f'0{p.n_data}b') + ('' if q.operator == 'cut' else '0')


def semantic_key(q):
    operands = tuple(sorted(q.operands)) if q.operator in ('and', 'or', 'xor') else q.operands
    # Conservatively keep a whole operand/operation family together across widths,
    # even for width-sensitive NOT/ONE. This can merge distinct tasks, never split one.
    return canonical_json([q.operator, operands])


def group_split(q, seed=SEED):
    key = semantic_key(q)
    digest = hashlib.sha256((str(seed) + ':' + key).encode()).hexdigest()
    bucket = int(digest[:8], 16) % 8
    return key, 'train' if bucket < 6 else 'val' if bucket == 6 else 'test'


def generate(seed=SEED):
    for p in profiles():
        for op in p.operators:
            arity = 2 if op in ('and', 'or', 'xor') else 1
            for operands in itertools.product(range(2 ** p.n_data), repeat=arity):
                q = Question(op, operands)
                raw = encode_question(q, p)
                if parse_question(raw, p) != q:
                    raise AssertionError('AST round-trip failed')
                group, split = group_split(q, seed)
                identifier = hashlib.sha256(canonical_json([p.profile_id, op, operands]).encode()).hexdigest()[:24]
                flags = []
                if 0 in operands:
                    flags.append('zero-operand')
                if 2 ** p.n_data - 1 in operands:
                    flags.append('all-ones-operand')
                if arity == 2 and operands[0] == operands[1]:
                    flags.append('equal-operands')
                task = TaskCase(identifier, group, 'B1' if arity == 2 else 'B0', op,
                                operands, oracle(q, p), p.n_data, p.profile_id, seed, split, tuple(flags))
                yield task, raw


def json_lines(rows):
    return ''.join(canonical_json(row) + '\n' for row in rows).encode('utf-8')


def build_bank(destination: Path, seed=SEED):
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError('Bank is immutable: choose a new output directory')
    records = list(generate(seed))
    questions = [{'case_id': t.case_id, 'raw_question_bits': raw} for t, raw in records]
    labels = [asdict(t) | {'raw_expected_answer_bits': t.result_bits} for t, _ in records]
    files = {'questions.jsonl': json_lines(questions), 'teacher-labels.jsonl': json_lines(labels)}
    counts = {}
    for t, _ in records:
        key = t.profile_id + '/' + t.split
        counts[key] = counts.get(key, 0) + 1
    manifest = {
        'schema_version': SCHEMA, 'seed': seed, 'source_commit': SOURCE_COMMIT,
        'profiles': {p.profile_id: asdict(p) for p in profiles()},
        'tree': {'math': {'operator_branch': {
            'highwater_by_profile': {p.profile_id: p.highwater for p in profiles()},
            'authority': 'branch node; not inferred from currently active nodes'}}},
        'case_index': {t.case_id: [t.profile_id, t.split] for t, _ in records},
        'files': {name: hashlib.sha256(raw).hexdigest() for name, raw in files.items()},
        'cases': len(records), 'counts': counts,
        'semantic_groups': len({t.semantic_group for t, _ in records}),
        'pending': PENDING,
        'split_rule': 'SHA256(seed:operation,canonical-operands) mod8; 6/1/1 buckets; width/version/commutative swaps grouped',
        'training_status': 'data-and-transport-only; no new NN/VM math-learning result',
        'curriculum_core': [p.profile_id for p in profiles()[:9]],
        'branches': ['v1_or', 'v2_xor', 'd4_and', 'layer2_v0', 'layer2_v1', 'layer2_v2'],
    }
    # Validate label consistency before publishing a bank directory atomically.
    prefix_targets = {}
    for t, raw in records:
        for i, token in enumerate(t.result_bits + 'S'):
            key = (t.profile_id, raw + t.result_bits[:i])
            old = prefix_targets.setdefault(key, token)
            if old != token:
                raise AssertionError('Conflicting teacher-forcing labels within one profile')
    manifest['teacher_prefixes_checked'] = len(prefix_targets)
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=destination.name + '-building-', dir=destination.parent))
    for name, raw in files.items():
        (staging / name).write_bytes(raw)
    (staging / 'manifest.json').write_text(canonical_json(manifest) + '\n', encoding='utf-8')
    os.rename(staging, destination)
    return manifest


class OfflineGrader:
    def __init__(self, folder):
        folder = Path(folder)
        manifest = json.loads((folder / 'manifest.json').read_text('utf-8'))
        raw = (folder / 'teacher-labels.jsonl').read_bytes()
        if hashlib.sha256(raw).hexdigest() != manifest['files']['teacher-labels.jsonl']:
            raise ValueError('Teacher labels integrity failure')
        self.expected = {t['case_id']: t['raw_expected_answer_bits']
                         for t in map(json.loads, raw.decode().splitlines())}

    def grade(self, case_id, normalized_bits):
        if case_id not in self.expected:
            raise ValueError('Unknown case')
        return normalized_bits == self.expected[case_id]
