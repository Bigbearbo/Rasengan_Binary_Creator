"""Executable acceptance: syntax, teacher parity, splits and label-free transport."""
import hashlib
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import reference_codec as reference
import teacher
from student_io import (CurriculumPosition, Profile, Question, StudentBank,
                        encode_question, normalize_nn, normalize_vm, parse_question)


class BankTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = list(teacher.generate())

    def test_full_round_trip_and_binary_alphabet(self):
        ps = {p.profile_id: p for p in teacher.profiles()}
        for t, raw in self.records:
            p = ps[t.profile_id]
            self.assertEqual(set(raw) - set('01'), set())
            self.assertEqual(parse_question(raw, p), Question(t.operator, t.operands))

    def test_exhaustive_existing_codec_parity(self):
        ps = {p.profile_id: p for p in teacher.profiles()}
        checked = 0
        for t, raw in self.records:
            p = ps[t.profile_id]
            if p.n_op == 1:
                continue
            data = [format(v, f'0{p.n_data}b') + '0' for v in t.operands]
            self.assertEqual(reference.calc(t.operator, data), t.result_bits)
            encoded = reference.encode_math(t.operator, data, p.n_op + 1, p.version)
            expected = encoded if p.layer == 2 else '01' + encoded[11:]
            if not p.active_end:
                expected = expected[:-(p.n_op + 1)]
            self.assertEqual(raw, expected)
            if p.layer == 2:
                decoded = reference.decode_math(raw, p.n_op + 1, p.n_data + 1,
                                                p.n_data + 1, p.version)
                self.assertEqual(decoded['answer'], t.result_bits)
            checked += 1
        self.assertGreater(checked, 1000)

    def test_paper4_startup_and_delayed_end(self):
        p = teacher.profiles()[0]
        self.assertEqual(encode_question(Question('echo', (1,)), p), '010010')
        self.assertEqual(teacher.oracle(Question('echo', (1,)), p), '10')
        before = Profile('q5', 2, 2, ('echo', 'neg', 'zero'), False, highwater=2)
        after = replace(before, profile_id='q6', active_end=True)
        self.assertEqual(encode_question(Question('zero', (1,)), before), '01100010')
        self.assertEqual(encode_question(Question('zero', (1,)), after), '01100010110')
        self.assertEqual(teacher.oracle(Question('zero', (1,)), after), '000')

    def test_native_end_equal_data_and_answer_not_stop(self):
        p = Profile('collision', 2, 2, ('echo', 'neg', 'zero'), True, highwater=2)
        q = Question('echo', (3,))
        self.assertIn('110110', encode_question(q, p))
        self.assertEqual(parse_question(encode_question(q, p), p), q)
        self.assertEqual(normalize_nn('110S'), '110')
        self.assertEqual(normalize_vm('110', True), '110')

    def test_cut_is_bare_information_bits(self):
        p = teacher.profiles()[7]
        self.assertEqual(teacher.oracle(Question('cut', (1,)), p), '001')
        self.assertEqual(normalize_nn('001S'), '001')

    def test_malformed_questions_rejected(self):
        p = teacher.profiles()[8]
        raw = encode_question(Question('and', (1, 7)), p)
        for bad in (raw[:-1], raw + '0', '11' + raw[2:], raw[:-4] + '0000',
                    raw[:9] + '1' + raw[10:], raw.replace('0', '|', 1)):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                parse_question(bad, p)

    def test_reserved_and_undefined_operator_rejected(self):
        p = teacher.profiles()[8]
        for code in ('1100', '1110'):
            with self.assertRaises(ValueError):
                parse_question('01' + code + '0010' + p.end, p)
        with self.assertRaises(ValueError):
            encode_question(Question('add', (1, 2)), p)

    def test_version_alias_is_explicit(self):
        ps = {p.profile_id: p for p in teacher.profiles()}
        a = encode_question(Question('or', (1, 3)), ps['v1_or'])
        b = encode_question(Question('xor', (1, 3)), ps['v2_xor'])
        self.assertEqual(a, b)
        self.assertEqual(parse_question(a, ps['v1_or']).operator, 'or')
        self.assertEqual(parse_question(a, ps['v2_xor']).operator, 'xor')
        self.assertNotEqual(teacher.oracle(Question('or', (1, 3)), ps['v1_or']),
                            teacher.oracle(Question('xor', (1, 3)), ps['v2_xor']))

    def test_no_split_leakage_across_width_version_layer_or_swaps(self):
        groups = {}
        for t, _ in self.records:
            groups.setdefault(t.semantic_group, set()).add(t.split)
        self.assertTrue(all(len(v) == 1 for v in groups.values()))
        for op in ('and', 'or', 'xor'):
            self.assertEqual(teacher.group_split(Question(op, (1, 3))),
                             teacher.group_split(Question(op, (3, 1))))
        self.assertNotEqual(teacher.group_split(Question('or', (1, 3)))[0],
                            teacher.group_split(Question('xor', (1, 3)))[0])

    def test_width_growth_preserves_low_bits_and_ids(self):
        p = teacher.profiles()[0]
        words = []
        for nd in (1, 2, 3, 4):
            current = replace(p, n_data=nd)
            words.append(encode_question(Question('echo', (1,)), current)[4:])
        self.assertEqual(words, ['10', '010', '0010', '00010'])

    def test_highwater_survives_removed_operator_and_curriculum_never_downgrades(self):
        p = replace(teacher.profiles()[8], operators=('echo',))
        self.assertEqual(p.highwater, 5)
        position = CurriculumPosition()
        for p in teacher.profiles()[:9]:
            position.advance(p)
        for p in (teacher.profiles()[0], replace(teacher.profiles()[8], active_end=False),
                  replace(teacher.profiles()[8], highwater=4, operators=('echo',))):
            with self.assertRaises(ValueError):
                position.advance(p)

    def test_invalid_profile_and_operand_rejected(self):
        p = teacher.profiles()[0]
        for values in ((True,), (2,), (-1,), (0, 1)):
            with self.assertRaises(ValueError):
                encode_question(Question('echo', values), p)
        for kwargs in ({'active_end': True}, {'n_op': 0}, {'layer': 3},
                       {'version': 'v9'}, {'operators': ('add',)}, {'highwater': 2}):
            with self.assertRaises(ValueError):
                replace(p, **kwargs)

    def test_rebuild_exact_bytes_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / 'a', Path(tmp) / 'b'
            teacher.build_bank(a)
            teacher.build_bank(b)
            for name in ('questions.jsonl', 'teacher-labels.jsonl', 'manifest.json'):
                self.assertEqual((a / name).read_bytes(), (b / name).read_bytes())
            with self.assertRaises(FileExistsError):
                teacher.build_bank(a)

    def test_label_free_same_raw_nn_vm_transport(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / 'bank'
            teacher.build_bank(folder)
            # Deliberately make labels inaccessible: transport still works.
            (folder / 'teacher-labels.jsonl').rename(folder / 'offline-only.jsonl')
            with patch.object(teacher, 'oracle', side_effect=AssertionError('oracle in inference')):
                bank = StudentBank(folder)
                nn_seen, vm_seen = [], []
                def nn(raw):
                    self.assertIs(type(raw), str)
                    nn_seen.append(raw)
                    return '0S'
                def vm(raw):
                    self.assertIs(type(raw), str)
                    vm_seen.append(raw)
                    return '0'
                for p in teacher.profiles():
                    for split in ('train', 'val', 'test'):
                        bank.dispatch(p.profile_id, split, nn)
                        bank.dispatch(p.profile_id, split, vm)
                self.assertEqual(nn_seen, vm_seen)
                self.assertEqual(len(nn_seen), len(self.records))

    def test_answer_computation_cannot_change_question_encoding(self):
        p = teacher.profiles()[8]
        q = Question('and', (3, 5))
        before = encode_question(q, p)
        with patch.object(teacher, 'oracle', side_effect=AssertionError('solver not translator')):
            self.assertEqual(encode_question(q, p), before)
            self.assertEqual(parse_question(before, p), q)

    def test_tamper_questions_and_labels_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / 'bank'
            teacher.build_bank(folder)
            path = folder / 'questions.jsonl'
            path.write_bytes(path.read_bytes() + b'\n')
            with self.assertRaises(ValueError):
                StudentBank(folder)
            labels = folder / 'teacher-labels.jsonl'
            labels.write_bytes(labels.read_bytes() + b'\n')
            with self.assertRaises(ValueError):
                teacher.OfflineGrader(folder)

    def test_strict_output_stop_and_exact_offline_grading(self):
        for bad in ('110', 'S110', '110SS', 'S', '110S0', '1|0S'):
            with self.assertRaises(ValueError):
                normalize_nn(bad)
        with self.assertRaises(ValueError):
            normalize_vm('110', False)
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / 'bank'
            teacher.build_bank(folder)
            grader = teacher.OfflineGrader(folder)
            task = self.records[0][0]
            self.assertTrue(grader.grade(task.case_id, task.result_bits))
            self.assertFalse(grader.grade(task.case_id, '0' + task.result_bits))
            with self.assertRaises(ValueError):
                grader.grade('unknown', task.result_bits)


if __name__ == '__main__':
    unittest.main()
