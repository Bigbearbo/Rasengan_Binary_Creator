#!/usr/bin/env python3
"""State, repair, independent peers, and curriculum regression tests for SLE v0.3."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from spiral_dialogue_v02 import encode_config, encode_data, encode_error, encode_ack
from spiral_dialogue_v03 import (CurriculumTeacher, CurriculumStudent,
                                 CurriculumParser, ParseFailure, scenario)


class BankTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.t=CurriculumTeacher(self.root/'teacher.json')
        self.s=CurriculumStudent(self.root/'student.json')

    def student_state_bytes(self):
        return self.s.parser.path.read_bytes()

    def test_bank_and_tree_are_in_same_file(self):
        saved=json.loads(self.t.parser.path.read_text())
        self.assertIn('question_bank',saved)
        self.assertIn('tree',saved)
        self.assertIn('profiles',saved)
        self.assertEqual(saved['question_bank']['active_level'],0)
        self.assertEqual(self.t.bank['levels'][0]['name'],'echo')

    def test_no_teacher_curriculum_leaks_to_student(self):
        bank=self.s.parser.state['question_bank']
        self.assertEqual(bank['observations'],[])
        self.assertNotIn('levels',bank)
        self.assertNotIn('meaning',bank)
        self.assertEqual(self.s.parser.state['tree']['math']['operators'],{})

    def test_query_generated_from_state_and_restart_retries_same(self):
        bits,meta=self.t.choose()
        self.assertEqual(meta['level'],'echo')
        self.assertEqual(self.t.bank['pending']['wire'],bits)
        again=CurriculumTeacher(self.t.parser.path)
        bits2,meta2=again.choose()
        self.assertEqual(bits,bits2)
        self.assertTrue(meta2['action']=='retry')

    def test_bad_suffix_leaves_entire_student_file_unchanged(self):
        bits,_=self.t.choose()
        old=self.student_state_bytes()
        bad=bits[:14]+'1'+bits[15:]
        response=self.s.receive(bad)
        self.assertEqual(response['diagnostic']['error'],'BAD_SUFFIX')
        self.assertEqual(response['diagnostic']['field'],'operator')
        self.assertEqual(response['diagnostic']['offset'],11)
        self.assertEqual(old,self.student_state_bytes())
        teacher=self.t.receive(response['send_bits'])
        self.assertEqual(teacher['send_bits'],bits)
        self.assertEqual(self.s.receive(bits)['status'],'need_example')

    def test_first_example_does_not_pretend_to_be_mastered(self):
        query,_=self.t.choose()
        response=self.s.receive(query)
        self.assertEqual(response['status'],'need_example')
        lesson=self.t.receive(response['send_bits'])
        self.assertEqual(lesson['status'],'teaching')
        self.assertEqual(self.s.receive(lesson['send_bits'])['status'],'example_saved')
        state=self.s.parser.state
        self.assertIn('1',state['question_bank']['by_operator'])
        self.assertEqual(len(state['tree']['math']['operators']['1']['examples']),1)
        self.assertEqual(self.t.bank['progress']['echo']['passes'],0)
        self.assertEqual(self.s.parser.state['tree']['math']['operators']['1']['meaning'],None)
        self.assertGreater(len(self.s.candidates(1)),1)

    def test_no_promotion_before_mastery(self):
        for i in range(2):
            bits,_=self.t.choose()
            reply=self.s.receive(bits)
            self.assertEqual(reply['status'],'need_example')
            lesson=self.t.receive(reply['send_bits'])
            self.s.receive(lesson['send_bits'])
        bits,_=self.t.choose()
        reply=self.s.receive(bits)
        self.assertEqual(reply['status'],'replied')
        graded=self.t.receive(reply['send_bits'])
        self.assertEqual(graded['status'],'correct')
        self.assertEqual(self.t.bank['active_level'],0)
        self.assertEqual(self.t.bank['progress']['echo']['passes'],1)
        self.s.receive(graded['send_bits'])
        bits,_=self.t.choose()
        reply=self.s.receive(bits)
        graded=self.t.receive(reply['send_bits'])
        self.assertEqual(graded['status'],'correct')
        self.assertEqual(self.t.bank['active_level'],1)
        self.assertEqual(self.t.level()['name'],'add')

    def test_unknown_version_triggers_config_recovery(self):
        self.t.parser.parse(encode_config(1,0,4,4,5,1))
        self.t.parser.update_bank(lambda bank: (bank.__setitem__('active_level',3),
            bank.__setitem__('pending',None)))
        bits,info=self.t.choose()
        self.assertEqual(info['level'],'and')
        result=self.s.receive(bits)
        self.assertEqual(result['diagnostic']['error'],'UNKNOWN_VERSION')
        repaired=self.t.receive(result['send_bits'])
        self.assertEqual(repaired['status'],'repair_config')
        self.assertEqual(self.s.receive(repaired['send_bits'])['status'],'updated')
        self.assertEqual(self.s.parser.state['active_version'],1)

    def test_unmatched_valid_reply_does_not_change_syntax_evidence(self):
        bits,_=self.t.choose()
        before=copy.deepcopy(self.t.parser.state['tree'])
        p=self.t._profile(0)
        bad=encode_data('reply',0,p,1,3,2,3)  # different from pending query
        outcome=self.t.receive(bad)
        self.assertEqual(outcome['status'],'bad_reply')
        self.assertEqual(outcome['error']['error'],'INVALID_FRAME')
        self.assertEqual(before,self.t.parser.state['tree'])
        self.assertEqual(self.t.bank['pending']['wire'],bits)

    def test_student_observations_persist_after_restart(self):
        bits,_=self.t.choose()
        self.s.receive(bits)
        resumed=CurriculumStudent(self.s.parser.path)
        self.assertEqual(len(resumed.parser.state['question_bank']['observations']),1)
        self.assertEqual(resumed.parser.state['question_bank']['by_operator']['1']['queries'],1)
        self.assertEqual(resumed.parser.state['tree']['math']['operators']['1']['seen'],1)

    def test_error_ack_do_not_become_lessons(self):
        before=self.student_state_bytes()
        self.s.receive(encode_ack(0,0))
        self.assertEqual(len(self.s.parser.state['question_bank']['observations']),0)
        self.assertEqual(self.s.parser.state['tree']['math']['operators'],{})
        self.assertEqual(len(self.s.parser.state['question_bank']['feedback']),1)
        self.s.receive(encode_error(0,'BAD_SUFFIX',4,11))
        self.assertEqual(len(self.s.parser.state['question_bank']['observations']),0)

    def test_full_run_including_faults_and_reviews(self):
        out=self.root/'demo'
        summary=scenario(out)
        self.assertTrue(summary['completed'])
        self.assertEqual(summary['current_level'],5)
        self.assertEqual(summary['syntax_operators'],[1,5,6,9,17])
        self.assertEqual(summary['versions'],['0','1','2'])
        self.assertEqual({k:v['passes'] for k,v in summary['scores'].items()},
                         {k:2 for k in ('echo','add','xor','and','or')})
        self.assertEqual(sum(len(v['reviews_passed']) for v in summary['scores'].values()),5)
        self.assertEqual(summary['scores']['add']['fails'],1)
        self.assertTrue(all(summary['faults'].values()))
        trace=json.loads((out/'trace.json').read_text())
        self.assertTrue(any(e['step']=='recover_config' for e in trace['events']))
        # The student has learned finite operation labels, but never received
        # the teacher's unexposed course plan.
        student=json.loads((out/'student_tree.json').read_text())
        self.assertNotIn('levels', student['question_bank'])
        self.assertEqual(student['tree']['math']['operators']['1']['meaning'],'left')
        self.assertEqual(student['tree']['math']['operators']['17']['meaning'],'or')

    def test_no_fault_control_run(self):
        summary=scenario(self.root/'control',inject_faults=False)
        self.assertTrue(summary['completed'])
        self.assertEqual(summary['scores']['add']['fails'],0)
        self.assertEqual(sum(len(v['reviews_passed']) for v in summary['scores'].values()),5)
        self.assertEqual(summary['faults'],{'bad_suffix':False,'wrong_reply':False,
                                           'config_dropped':False})

    def test_restart_after_full_run_retains_mastery(self):
        out=self.root/'persist'
        scenario(out)
        teach=CurriculumTeacher(out/'teacher_tree.json')
        stu=CurriculumStudent(out/'student_tree.json')
        self.assertTrue(teach.bank['completed'])
        self.assertIsNone(teach.choose())
        self.assertEqual(stu.parser.state['active_version'],2)
        self.assertIn('1',stu.parser.state['tree']['math']['operators'])


if __name__=='__main__':
    unittest.main()