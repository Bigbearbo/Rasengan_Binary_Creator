#!/usr/bin/env python3
"""Execute: python -m unittest -v test_spiral_parser test_spiral_dialogue"""
import tempfile
import unittest
from pathlib import Path
from spiral_dialogue import (DialogueParser, ParseFailure, ScriptedStudent, ScriptedTeacher,
                             encode, encode_error, run_scenario)


class DialogueTests(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.path = Path(self.t.name) / 'student.json'
        self.parser = DialogueParser(self.path)

    def test_new_word_autocreates_and_persists(self):
        data = self.parser.parse(encode('example', 5, 1, 2, 3))
        self.assertTrue(data['new_node'])
        self.assertEqual(data['operator_word'], '1010')
        r = DialogueParser(self.path).parse(encode('query', 5, 3, 2))
        self.assertFalse(r['new_node'])
        self.assertEqual(r['examples_known'], 1)

    def test_repeated_example_is_idempotent_for_evidence(self):
        msg = encode('example', 5, 1, 2, 3)
        self.parser.parse(msg)
        self.parser.parse(msg)
        self.assertEqual(len(self.parser.state['tree']['math']['operators']['1010']['examples']), 1)

    def test_bad_suffix_does_not_write_state(self):
        bit = encode('example', 5, 1, 2, 3)
        bit = bit[:8] + '1' + bit[9:]
        with self.assertRaises(ParseFailure) as cm:
            self.parser.parse(bit)
        self.assertEqual(cm.exception.code, 'BAD_SUFFIX')
        self.assertEqual(cm.exception.field, 2)
        self.assertEqual(cm.exception.offset, 5)
        self.assertFalse(self.path.exists())

    def test_other_errors_dont_mutate(self):
        for data, code in [(encode('query', 5, 1, 2)[:-1], 'TRUNCATED'),
                           (encode('query', 5, 1, 2) + '0', 'EXTRA_BITS'),
                           (encode('query', 5, 1, 2).replace('0', 'x', 1), 'NON_BINARY')]:
            with self.subTest(code=code), self.assertRaises(ParseFailure) as cm:
                self.parser.parse(data)
            self.assertEqual(cm.exception.code, code)
            self.assertFalse(self.path.exists())

    def test_conflicting_example_does_not_change_seen_or_evidence(self):
        self.parser.parse(encode('example', 5, 1, 2, 3))
        before = self.path.read_bytes()
        with self.assertRaises(ParseFailure) as cm:
            self.parser.parse(encode('example', 5, 1, 2, 7))
        self.assertEqual(cm.exception.code, 'CONFLICTING_EXAMPLE')
        self.assertEqual(self.path.read_bytes(), before)

    def test_error_response_can_cross_wire(self):
        wire = encode_error('BAD_SUFFIX', 2, 5)
        self.assertEqual(DialogueParser(self.path).parse(wire), {
            'kind': 'error', 'code': 'BAD_SUFFIX', 'field_index': 2,
            'field': 'operator', 'offset': 5})
        self.assertFalse(self.path.exists())

    def test_bad_category_is_rejected(self):
        data = encode('query', 5, 1, 2)
        with self.assertRaises(ParseFailure) as cm:
            self.parser.parse(data[:3] + '10' + data[5:])
        self.assertEqual(cm.exception.code, 'UNKNOWN_CATEGORY')

    def test_query_no_observed_semantics(self):
        student = ScriptedStudent(self.path)
        r = student.receive(encode('query', 5, 1, 2))
        self.assertEqual(r['status'], 'insufficient_evidence')
        self.assertEqual(len(r['hypotheses']), 8)
        self.assertEqual(DialogueParser(Path(self.t.name) / "teacher.json").parse(r["send_bits"])["code"], "NEED_EXAMPLE")

    def test_two_examples_disambiguate_add_without_weight_training(self):
        student = ScriptedStudent(self.path)
        r1 = student.receive(encode('example', 5, 1, 2, 3))
        self.assertGreater(len(r1['hypotheses']), 1)
        r2 = student.receive(encode('example', 5, 2, 3, 5))
        self.assertEqual(r2['hypotheses'], ['add'])
        answer = student.receive(encode('query', 5, 4, 2))
        self.assertEqual(answer['status'], 'replied')
        self.assertEqual(DialogueParser(Path(self.t.name) / 'teacher.json').parse(answer['send_bits'])['result'], 6)

    def test_operator_isolation_and_replay(self):
        out = Path(self.t.name) / 'run'
        summary = run_scenario(out)
        self.assertEqual(summary['query_correct'], [True, True, True])
        self.assertTrue(summary['syntax_error_repaired'])
        self.assertTrue(summary['student_requested_more_examples'])
        self.assertTrue(summary['semantic_error_rejected'])
        self.assertEqual(summary['operator_count'], 2)
        data = DialogueParser(out / 'student_tree.json').state['tree']['math']['operators']
        self.assertEqual(data['1010']['meaning'], 'add')
        self.assertEqual(data['1100']['meaning'], 'xor')
        self.assertEqual(len(data['1010']['examples']), 2)

    def test_wire_roundtrip_example_and_reply(self):
        for kind, result in [('query', None), ('example', 3), ('reply', 3)]:
            bits = encode(kind, 5, 1, 2, result)
            self.assertEqual(self.parser.parse(bits)['kind'], kind)
        with self.assertRaises(ValueError):
            encode('example', 5, 1, 2)   # missing answer


if __name__ == '__main__':
    unittest.main()