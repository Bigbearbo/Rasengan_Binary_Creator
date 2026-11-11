#!/usr/bin/env python3
"""Regression tests for the scripted, versioned spiral-language protocol v0.2."""
import tempfile
import unittest
from pathlib import Path

from spiral_dialogue_v02 import (
    VersionedParser, ParseFailure, Student, Teacher, scenario,
    encode_config, encode_data, encode_error, encode_ack, word,
)


class V02Tests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.parser = VersionedParser(self.root / 'tree.json')

    def state_bytes(self):
        return self.parser.path.read_bytes() if self.parser.path.exists() else None

    def expect_error_no_mutation(self, bits, code, field=None, offset=None):
        before = self.state_bytes()
        with self.assertRaises(ParseFailure) as exc:
            self.parser.parse(bits)
        self.assertEqual(exc.exception.code, code)
        if field is not None:
            self.assertEqual(exc.exception.field, field)
        if offset is not None:
            self.assertEqual(exc.exception.offset, offset)
        self.assertEqual(before, self.state_bytes())
        return exc.exception

    def data(self, kind, op=5, a=1, b=2, result=None, version=0):
        return encode_data(kind, version, self.parser.state['profiles'][str(version)], op, a, b, result)

    def test_first_new_operator_persists(self):
        out = self.parser.parse(self.data('example', result=3))
        self.assertTrue(out['new_node'])
        self.assertEqual(out['operator_word'], '1010')
        r = VersionedParser(self.parser.path).parse(self.data('query'))
        self.assertFalse(r['new_node'])
        self.assertEqual(r['known_examples'], 1)

    def test_config_growth_retains_same_operator_numeric_id(self):
        self.parser.parse(self.data('example', result=3))
        v1 = encode_config(1, 0, 4, 4, 5, 1)
        result = self.parser.parse(v1)
        self.assertTrue(result['changed'])
        node = self.parser.state['tree']['math']['operators']['5']
        self.assertEqual(node['encodings'], {'0': '1010', '1': '01010'})
        self.assertEqual(len(node['examples']), 1)
        msg = self.data('query', op=5, a=3, b=2, version=1)
        ret = self.parser.parse(msg)
        self.assertEqual(ret['operator'], 5)
        self.assertEqual(ret['known_examples'], 1)

    def test_successive_k_growth_and_legacy_read(self):
        self.parser.parse(self.data('example', result=3))
        self.parser.parse(encode_config(1, 0, 4, 4, 5, 1))
        self.parser.parse(encode_config(2, 1, 5, 5, 6, 2))
        p = self.parser.state['profiles']['2']
        bits = encode_data('query', 2, p, 17, 7, 3)
        got = self.parser.parse(bits)
        self.assertEqual(got['operator_word'], word(17, 5, 2))
        self.assertEqual(self.parser.state['active_version'], 2)
        self.parser.parse(self.data('query', a=2, b=3, version=0))
        self.assertEqual(self.parser.state['active_version'], 2)
        self.assertEqual(len(self.parser.state['tree']['math']['operators']['5']['examples']), 1)

    def test_unknown_version_does_not_update(self):
        p = {'op_n': 4, 'arg_n': 4, 'result_n': 5, 'k': 1}
        self.expect_error_no_mutation(encode_data('query', 1, p, 5, 1, 2), 'UNKNOWN_VERSION', 1, 6)

    def test_malformed_config_does_not_update(self):
        cfg = encode_config(1, 0, 4, 4, 5, 1)
        self.expect_error_no_mutation(cfg[:15] + '1' + cfg[16:], 'BAD_SUFFIX', 8, 12)

    def test_unknown_parent_does_not_update(self):
        self.expect_error_no_mutation(encode_config(2, 1, 5, 4, 5, 2), 'UNKNOWN_PARENT')

    def test_no_change_or_shrink_rejected(self):
        self.expect_error_no_mutation(encode_config(1, 0, 3, 3, 4, 1), 'UNSAFE_UPGRADE')
        self.expect_error_no_mutation(encode_config(1, 0, 2, 4, 5, 1), 'UNSAFE_UPGRADE')

    def test_conflicting_config_and_duplicate_idempotent(self):
        cfg = encode_config(1, 0, 4, 4, 5, 1)
        self.parser.parse(cfg)
        old = self.state_bytes()
        repeated = self.parser.parse(cfg)
        self.assertFalse(repeated['changed'])
        self.assertEqual(old, self.state_bytes())
        self.expect_error_no_mutation(encode_config(1, 0, 5, 4, 5, 1), 'CONFIG_CONFLICT')

    def test_wrong_suffix_in_payload_has_precise_diagnostic(self):
        msg = self.data('example', result=3)
        self.expect_error_no_mutation(msg[:14] + '1' + msg[15:], 'BAD_SUFFIX', 4, 11)

    def test_wrong_suffix_new_layer_rejected(self):
        self.parser.parse(encode_config(1, 0, 4, 4, 5, 1))
        self.parser.parse(encode_config(2, 1, 5, 5, 6, 2))
        msg = self.data('query', 17, 4, 3, version=2)
        op_start = 9 + 2
        op_end = op_start + 5 + 2
        bad = msg[:op_end - 1] + '1' + msg[op_end:]
        self.expect_error_no_mutation(bad, 'BAD_SUFFIX', 4, op_start)

    def test_conflicting_examples_across_versions_blocked(self):
        self.parser.parse(self.data('example', result=3))
        self.parser.parse(encode_config(1, 0, 4, 4, 5, 1))
        bad = self.data('example', result=7, version=1)
        self.expect_error_no_mutation(bad, 'CONFLICTING_EXAMPLE', 7)
        node = self.parser.state['tree']['math']['operators']['5']
        self.assertEqual([e['result'] for e in node['examples']], [3])

    def test_error_and_ack_frames_do_not_update(self):
        for frame, kind in [(encode_ack(1), 'ack'),
                            (encode_error(2, 'BAD_SUFFIX', 4, 11), 'error')]:
            before = self.state_bytes()
            parsed = self.parser.parse(frame)
            self.assertEqual(parsed['kind'], kind)
            self.assertEqual(before, self.state_bytes())

    def test_invalid_input_and_extra_bits(self):
        bits = self.data('query')
        self.expect_error_no_mutation(bits[:-1], 'TRUNCATED')
        self.expect_error_no_mutation(bits + '0', 'EXTRA_BITS')
        self.expect_error_no_mutation('x' + bits[1:], 'NON_BINARY')
        self.expect_error_no_mutation('00' + bits[2:], 'INVALID_FRAME')

    def test_binary_repair_roundtrip(self):
        teach = Teacher(self.root / 'teacher.json')
        stu = Student(self.root / 'student.json')
        cfg = encode_config(1, 0, 4, 4, 5, 1)
        teach.parser.parse(cfg)
        msg = teach.make('example', 5, 3, 2, 1)
        answer = stu.receive(msg)
        self.assertEqual(answer['diagnostic']['error'], 'UNKNOWN_VERSION')
        self.assertEqual(teach.receive(answer['send_bits'])['report']['code'], 'UNKNOWN_VERSION')
        answer = stu.receive(cfg)
        self.assertEqual(answer['status'], 'updated')
        self.assertEqual(teach.receive(answer['send_bits'])['report']['kind'], 'ack')
        self.assertEqual(stu.receive(msg)['status'], 'example_saved')

    def test_scripted_end_to_end(self):
        out = self.root / 'run'
        s = scenario(out)
        self.assertEqual((s['correct'], s['checks']), (6, 6))
        self.assertEqual(s['version_switches'], 2)
        self.assertEqual(s['known_operators'], [5, 9, 17])
        self.assertEqual(s['known_profiles'], ['0', '1', '2'])
        self.assertEqual(s['student_active_version'], 2)


if __name__ == '__main__':
    unittest.main()