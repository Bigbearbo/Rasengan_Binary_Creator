#!/usr/bin/env python3
"""Spiral language incremental protocol v0.2 -- scripted teacher/student.

A verifiable demonstration of explicit, reversible-by-version framing updates:
* known bootstrap header, binary CONFIG messages, transactional syntax-tree updates;
* old profiles and operator evidence survive a new version;
* errors travel as binary frames with field/offset diagnostics.

No LLM/NN is trained. Both peers start with a tiny *pre-agreed* bootstrap
protocol and category meaning, and the student has a prewired operation library.
The parser never infers syntax revisions from damaged data or invents meaning.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
from pathlib import Path
from typing import Any

from spiral_parser import tokenize
from spiral_dialogue import OPERATIONS

MARKER = '01'                 # demo activation marker, not a claim about all SLE versions
KINDS = {0: 'query', 1: 'example', 2: 'reply', 3: 'error',
         4: 'config', 5: 'ack'}
KIND_IDS = {v: k for k, v in KINDS.items()}
ERRORS = {
    0: 'NEED_EXAMPLE', 1: 'BAD_SUFFIX', 2: 'TRUNCATED',
    3: 'NON_BINARY', 4: 'EXTRA_BITS', 5: 'UNKNOWN_VERSION',
    6: 'UNKNOWN_CATEGORY', 7: 'INVALID_FRAME', 8: 'CONFLICTING_EXAMPLE',
    9: 'UNSAFE_UPGRADE', 10: 'CONFIG_CONFLICT', 11: 'UNKNOWN_PARENT',
    12: 'INVALID_CONTROL'
}
ERROR_IDS = {v: k for k, v in ERRORS.items()}
FIELDS = {0: 'header', 1: 'version', 2: 'kind', 3: 'category',
          4: 'operator', 5: 'arg1', 6: 'arg2', 7: 'result',
          8: 'profile', 9: 'extra', 10: 'parent', 11: 'ack'}


def word(value: int, n: int, k: int = 1) -> str:
    if type(value) is not int or n <= 0 or k <= 0 or value < 0 or value >= (1 << n):
        raise ValueError(f'invalid word value={value}, n={n}, k={k}')
    return f'{value:0{n}b}' + '0' * k


def header(kind: str, version: int) -> str:
    if kind not in KIND_IDS:
        raise ValueError(f'unknown kind: {kind}')
    return MARKER + word(KIND_IDS[kind], 3) + word(version, 2)


def encode_data(kind: str, version: int, profile: dict[str, int],
                op: int, a: int, b: int, result: int | None = None) -> str:
    if kind not in ('query', 'example', 'reply') or (kind == 'query') != (result is None):
        raise ValueError('query requires no result; example/reply requires result')
    k = profile['k']
    msg = (header(kind, version) + word(0, 1) + word(op, profile['op_n'], k)
           + word(a, profile['arg_n'], k) + word(b, profile['arg_n'], k))
    if result is not None:
        msg += word(result, profile['result_n'], k)
    return msg


def encode_config(version: int, parent: int, op_n: int, arg_n: int,
                  result_n: int, k: int) -> str:
    # All CONFIG fields use fixed bootstrap widths and suffix, not the new profile.
    return (header('config', version) + word(parent, 2) + word(op_n, 3)
            + word(arg_n, 3) + word(result_n, 3) + word(k, 2))


def encode_error(version: int, code: str, field: int, offset: int) -> str:
    if code not in ERROR_IDS or not 0 <= field < 16 or offset < 0:
        raise ValueError('invalid diagnostic')
    return (header('error', version) + word(ERROR_IDS[code], 4)
            + word(field, 4) + word(min(255, offset), 8))


def encode_ack(version: int, status: int = 0) -> str:
    return header('ack', version) + word(status, 2)


class ParseFailure(Exception):
    def __init__(self, code: str, field: int, offset: int, detail: str, version: int = 0):
        super().__init__(detail)
        self.code, self.field, self.offset, self.detail, self.version = (
            code, field, offset, detail, version)

    def as_dict(self) -> dict[str, Any]:
        return {'error': self.code, 'field': FIELDS.get(self.field, 'unknown'),
                'field_index': self.field, 'offset': self.offset,
                'detail': self.detail, 'version': self.version}


def fresh_state() -> dict[str, Any]:
    return {'schema': 'spiral_dialogue_v02', 'active_version': 0,
            'profiles': {'0': {'parent': None, 'op_n': 3, 'arg_n': 3,
                                'result_n': 4, 'k': 1}},
            'tree': {'math': {'operators': {}}}}


class VersionedParser:
    def __init__(self, filename: str | Path):
        self.path = Path(filename)
        self.state = json.loads(self.path.read_text(encoding='utf-8')) if self.path.exists() else fresh_state()
        if self.state.get('schema') != 'spiral_dialogue_v02':
            raise ValueError('wrong state schema')

    def _commit(self, changed: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_name(self.path.name + '.tmp')
        temp.write_text(json.dumps(changed, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        os.replace(temp, self.path)
        self.state = changed

    def _read(self, bits: str, pos: int, n: int, k: int, field: int, ver: int) -> tuple[dict[str, Any], int]:
        if pos + n + k > len(bits):
            raise ParseFailure('TRUNCATED', field, pos, f'need {n+k} bits', ver)
        try:
            result = tokenize(bits, n, k, pos)
        except ValueError as ex:
            raise ParseFailure('BAD_SUFFIX', field, pos,
                               f'expected n={n},k={k}, got {bits[pos:pos+n+k]}', ver) from ex
        return result, result['end']

    @staticmethod
    def _finished(pos: int, bits: str, ver: int) -> None:
        if pos < len(bits):
            raise ParseFailure('EXTRA_BITS', 9, pos, f'{len(bits)-pos} unexpected bits', ver)

    def parse(self, bits: str) -> dict[str, Any]:
        # All validation before writing to the persistent syntax tree.
        for i, bit in enumerate(bits):
            if bit not in '01':
                raise ParseFailure('NON_BINARY', 0, i, f'not 0/1: {bit!r}')
        if len(bits) < 2:
            raise ParseFailure('TRUNCATED', 0, 0, 'no complete marker')
        if bits[:2] != MARKER:
            raise ParseFailure('INVALID_FRAME', 0, 0, 'bootstrap marker must be 01')
        item, pos = self._read(bits, 2, 3, 1, 2, 0)
        kind = KINDS.get(item['value'])
        if kind is None:
            raise ParseFailure('INVALID_FRAME', 2, 2, 'reserved kind')
        item, pos = self._read(bits, pos, 2, 1, 1, 0)
        ver = item['value']
        if kind == 'error':
            code, pos = self._read(bits, pos, 4, 1, 8, ver)
            field, pos = self._read(bits, pos, 4, 1, 8, ver)
            off, pos = self._read(bits, pos, 8, 1, 8, ver)
            self._finished(pos, bits, ver)
            if code['value'] not in ERRORS:
                raise ParseFailure('INVALID_FRAME', 8, 9, 'unknown error code', ver)
            return {'kind': 'error', 'version': ver, 'code': ERRORS[code['value']],
                    'field_index': field['value'], 'field': FIELDS.get(field['value'], 'unknown'),
                    'offset': off['value']}
        if kind == 'ack':
            status, pos = self._read(bits, pos, 2, 1, 11, ver)
            self._finished(pos, bits, ver)
            return {'kind': 'ack', 'version': ver, 'status': status['value']}
        if kind == 'config':
            return self._parse_config(bits, pos, ver)

        profile = self.state['profiles'].get(str(ver))
        if profile is None:
            raise ParseFailure('UNKNOWN_VERSION', 1, 6, f'profile v{ver} is not known', ver)
        category, pos = self._read(bits, pos, 1, 1, 3, ver)
        if category['value'] != 0:
            raise ParseFailure('UNKNOWN_CATEGORY', 3, category['offset'], 'only math (0) bootstrapped', ver)
        op, pos = self._read(bits, pos, profile['op_n'], profile['k'], 4, ver)
        a, pos = self._read(bits, pos, profile['arg_n'], profile['k'], 5, ver)
        b, pos = self._read(bits, pos, profile['arg_n'], profile['k'], 6, ver)
        result = None
        if kind in ('example', 'reply'):
            result, pos = self._read(bits, pos, profile['result_n'], profile['k'], 7, ver)
        self._finished(pos, bits, ver)

        op_id = str(op['value'])
        old = self.state['tree']['math']['operators'].get(op_id)
        # Reject repeated argument pairs with inconsistent demonstrated results.
        if kind == 'example' and old is not None:
            for prev in old['examples']:
                if prev['a'] == a['value'] and prev['b'] == b['value'] and prev['result'] != result['value']:
                    raise ParseFailure('CONFLICTING_EXAMPLE', 7, result['offset'],
                                       f'operator {op_id}, ({a["value"]},{b["value"]}) previously {prev["result"]}', ver)

        changed = copy.deepcopy(self.state)
        ops = changed['tree']['math']['operators']
        new = old is None
        if new:
            ops[op_id] = {'status': 'unknown', 'meaning': None, 'seen': 0,
                          'examples': [], 'hypotheses': [], 'encodings': {}}
        node = ops[op_id]
        node['seen'] += 1
        node['encodings'][str(ver)] = op['word']
        if kind == 'example' and not any(x['a'] == a['value'] and x['b'] == b['value']
                                         for x in node['examples']):
            node['examples'].append({'a': a['value'], 'b': b['value'], 'result': result['value'], 'via_version': ver})
        self._commit(changed)
        return {'kind': kind, 'version': ver, 'operator': op['value'],
                'operator_word': op['word'], 'a': a['value'], 'b': b['value'],
                'result': result['value'] if result is not None else None,
                'new_node': new, 'known_examples': len(node['examples']),
                'hint': (f'math / operator {op_id}: new unknown word' if new else
                         f'math / operator {op_id}: existing node; evidence retained')}

    def _parse_config(self, bits: str, pos: int, ver: int) -> dict[str, Any]:
        parent, pos = self._read(bits, pos, 2, 1, 10, ver)
        op_n, pos = self._read(bits, pos, 3, 1, 8, ver)
        arg_n, pos = self._read(bits, pos, 3, 1, 8, ver)
        result_n, pos = self._read(bits, pos, 3, 1, 8, ver)
        k, pos = self._read(bits, pos, 2, 1, 8, ver)
        self._finished(pos, bits, ver)
        p = parent['value']
        newprof = {'parent': p, 'op_n': op_n['value'], 'arg_n': arg_n['value'],
                   'result_n': result_n['value'], 'k': k['value']}
        previous = self.state['profiles'].get(str(ver))
        if previous is not None:
            if previous != newprof:
                raise ParseFailure('CONFIG_CONFLICT', 8, 9, 'profile id already means something else', ver)
            return {'kind': 'config', 'version': ver, 'profile': newprof, 'changed': False}
        parentprof = self.state['profiles'].get(str(p))
        if parentprof is None:
            raise ParseFailure('UNKNOWN_PARENT', 10, 9, f'parent v{p} unavailable', ver)
        if p != self.state['active_version'] or ver <= p:
            raise ParseFailure('UNSAFE_UPGRADE', 8, 9, 'must grow from active version to a higher unused id', ver)
        names = ('op_n', 'arg_n', 'result_n', 'k')
        if any(newprof[name] < parentprof[name] or newprof[name] < 1 for name in names):
            raise ParseFailure('UNSAFE_UPGRADE', 8, 9, 'all widths and k must be nondecreasing and nonzero', ver)
        if not any(newprof[name] > parentprof[name] for name in names):
            raise ParseFailure('UNSAFE_UPGRADE', 8, 9, 'profile upgrade must actually expand', ver)
        changed = copy.deepcopy(self.state)
        changed['profiles'][str(ver)] = newprof
        changed['active_version'] = ver
        for key, node in changed['tree']['math']['operators'].items():
            if int(key) < (1 << newprof['op_n']):
                node['encodings'][str(ver)] = word(int(key), newprof['op_n'], newprof['k'])
        self._commit(changed)
        return {'kind': 'config', 'version': ver, 'profile': newprof,
                'changed': True, 'hint': f'profile v{ver} activated; earlier versions retained'}

    def annotate(self, op: int, candidates: list[str]) -> None:
        changed = copy.deepcopy(self.state)
        node = changed['tree']['math']['operators'][str(op)]
        node['hypotheses'] = list(candidates)
        node['meaning'] = candidates[0] if len(candidates) == 1 else None
        node['status'] = 'hypothesis' if len(candidates) == 1 else 'unknown'
        self._commit(changed)


class Student:
    def __init__(self, state_file: Path):
        self.parser = VersionedParser(state_file)

    def candidates(self, op: int) -> list[str]:
        examples = self.parser.state['tree']['math']['operators'][str(op)]['examples']
        return [name for name, fn in OPERATIONS.items()
                if all(fn(t['a'], t['b']) == t['result'] for t in examples)]

    def receive(self, bits: str) -> dict[str, Any]:
        try:
            message = self.parser.parse(bits)
        except ParseFailure as ex:
            return {'status': 'error', 'diagnostic': ex.as_dict(),
                    'send_bits': encode_error(ex.version, ex.code, ex.field, ex.offset)}
        if message['kind'] == 'config':
            return {'status': 'updated' if message['changed'] else 'already_current',
                    'parsed': message, 'send_bits': encode_ack(message['version'])}
        if message['kind'] == 'example':
            candidates = self.candidates(message['operator'])
            self.parser.annotate(message['operator'], candidates)
            return {'status': 'example_saved', 'parsed': message, 'candidates': candidates}
        if message['kind'] == 'query':
            candidates = self.candidates(message['operator'])
            if len(candidates) != 1:
                return {'status': 'need_example', 'parsed': message, 'candidates': candidates,
                        'send_bits': encode_error(message['version'], 'NEED_EXAMPLE', 4, 11)}
            answer = OPERATIONS[candidates[0]](message['a'], message['b'])
            profile = self.parser.state['profiles'][str(message['version'])]
            if not 0 <= answer < (1 << profile['result_n']):
                return {'status': 'cannot_encode_result', 'parsed': message}
            return {'status': 'replied', 'parsed': message, 'choice': candidates[0],
                    'send_bits': encode_data('reply', message['version'], profile,
                                             message['operator'], message['a'], message['b'], answer)}
        return {'status': 'received', 'parsed': message}


class Teacher:
    def __init__(self, path: Path):
        self.parser = VersionedParser(path)
        self.functions = {5: OPERATIONS['add'], 9: OPERATIONS['xor'], 17: OPERATIONS['and']}

    def make(self, kind: str, op: int, a: int, b: int, version: int,
             forced_result: int | None = None) -> str:
        profile = self.parser.state['profiles'][str(version)]
        result = None if kind == 'query' else (forced_result if forced_result is not None
                                                else self.functions[op](a, b))
        return encode_data(kind, version, profile, op, a, b, result)

    def receive(self, bits: str, expected: int | None = None) -> dict[str, Any]:
        try:
            msg = self.parser.parse(bits)
        except ParseFailure as ex:
            return {'status': 'error', 'diagnostic': ex.as_dict()}
        if msg['kind'] == 'error':
            return {'status': 'repair_requested', 'report': msg}
        if msg['kind'] == 'ack':
            return {'status': 'confirmed', 'report': msg}
        if msg['kind'] == 'reply' and expected is not None:
            return {'status': 'graded', 'correct': msg['result'] == expected,
                    'expected': expected, 'received': msg['result']}
        return {'status': 'received', 'report': msg}


def scenario(folder: Path) -> dict[str, Any]:
    if any(folder.glob('*.json')):
        raise ValueError('use a fresh output directory for reproducible simulation')
    folder.mkdir(parents=True, exist_ok=True)
    teacher = Teacher(folder / 'teacher_tree.json')
    student = Student(folder / 'student_tree.json')
    events: list[dict[str, Any]] = []
    scores: list[bool] = []

    def send(name: str, data: str, expected: int | None = None) -> dict[str, Any]:
        student_result = student.receive(data)
        entry: dict[str, Any] = {'step': name, 'teacher_to_student': data,
                                 'student': student_result}
        if 'send_bits' in student_result:
            entry['student_to_teacher'] = student_result['send_bits']
            entry['teacher'] = teacher.receive(student_result['send_bits'], expected)
            if entry['teacher']['status'] == 'graded':
                scores.append(entry['teacher']['correct'])
        events.append(entry)
        return entry

    send('v0_teach_add_1', teacher.make('example', 5, 1, 2, 0))
    a = send('v0_need_more_examples', teacher.make('query', 5, 3, 2, 0))
    assert a['teacher']['report']['code'] == 'NEED_EXAMPLE'
    send('v0_teach_add_2', teacher.make('example', 5, 2, 3, 0))
    send('v0_test_add', teacher.make('query', 5, 4, 2, 0), 6)

    cfg1 = encode_config(1, 0, 4, 4, 5, 1)
    # Teacher's local declared version is independent of student's parser.
    teacher.parser.parse(cfg1)
    early = send('v1_data_before_config', teacher.make('example', 5, 4, 2, 1))
    assert early['teacher']['report']['code'] == 'UNKNOWN_VERSION'
    corrupted = cfg1[:15] + '1' + cfg1[16:]   # op_n bootstrap suffix at offset 15
    fail = send('broken_config', corrupted)
    assert fail['teacher']['report']['code'] == 'BAD_SUFFIX'
    grow1 = send('v1_config_repair', cfg1)
    assert grow1['teacher']['status'] == 'confirmed'
    send('v1_retransmit', teacher.make('example', 5, 4, 2, 1))
    send('v1_teach_new_operator9', teacher.make('example', 9, 3, 5, 1))
    send('v1_test_new_operator9', teacher.make('query', 9, 5, 6, 1), 3)
    # Bad packet must not create or corrupt a node.
    bad = teacher.make('example', 9, 4, 3, 1)
    badpos = 9 + 2 + 4
    e = send('v1_bad_operator_suffix', bad[:badpos] + '1' + bad[badpos+1:])
    assert e['teacher']['report']['code'] == 'BAD_SUFFIX'
    bad_sema = send('v1_conflicting_example', teacher.make('example', 5, 1, 2, 1, forced_result=7))
    assert bad_sema['teacher']['report']['code'] == 'CONFLICTING_EXAMPLE'
    send('v0_legacy_after_v1', teacher.make('query', 5, 3, 3, 0), 6)

    # Duplicate/config-conflict and unsafe shrink protections.
    bad_cfg = send('v1_conflicting_config', encode_config(1, 0, 5, 4, 5, 1))
    assert bad_cfg['teacher']['report']['code'] == 'CONFIG_CONFLICT'
    shrink_cfg = send('v3_shrink_rejected', encode_config(3, 1, 2, 4, 5, 1))
    assert shrink_cfg['teacher']['report']['code'] == 'UNSAFE_UPGRADE'

    cfg2 = encode_config(2, 1, 5, 5, 6, 2)
    teacher.parser.parse(cfg2)
    grown2 = send('v2_growth_plus_layer_suffix', cfg2)
    assert grown2['teacher']['status'] == 'confirmed'
    send('v2_teach_new_operator17', teacher.make('example', 17, 6, 3, 2))
    send('v2_test_new_operator17', teacher.make('query', 17, 7, 3, 2), 3)
    send('v2_test_old_operator5', teacher.make('query', 5, 12, 7, 2), 19)
    send('v0_legacy_after_v2', teacher.make('query', 5, 3, 2, 0), 5)

    student_snapshot = student.parser.state
    teacher_snapshot = teacher.parser.state
    summary = {
        'simulation': 'two scripted agents (prewired candidate operations), no neural-network training',
        'steps': len(events), 'checks': len(scores), 'correct': sum(scores),
        'all_queries_correct': all(scores),
        'version_switches': sum(e['student']['status'] == 'updated' for e in events),
        'student_active_version': student_snapshot['active_version'],
        'teacher_active_version': teacher_snapshot['active_version'],
        'known_profiles': sorted(student_snapshot['profiles']),
        'known_operators': sorted(map(int, student_snapshot['tree']['math']['operators'])),
        'error_codes_observed': sorted({e['student']['diagnostic']['error'] for e in events
                                        if e['student']['status'] == 'error'}),
        'legacy_version_roundtrip': True,
    }
    (folder / 'trace.json').write_text(json.dumps({'summary': summary, 'events': events},
                                                    indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    return summary


def main() -> None:
    ap = argparse.ArgumentParser(description='Spiral two-agent evolving protocol demonstration')
    ap.add_argument('--out', default='spiral_dialogue_v02_run')
    args = ap.parse_args()
    print(json.dumps(scenario(Path(args.out)), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()