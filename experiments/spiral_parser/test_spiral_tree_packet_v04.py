"""v0.4: real 0/1 transport, recovery, atomicity, and regression."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from spiral_dialogue_v03 import CurriculumParser
from spiral_dialogue_v02 import VersionedParser
from spiral_tree_packet_v04 import (make_package, decode_packet, pack_value, unpack_value,
    public_tree, Reader, TreeReceiver, MAGIC, validate_tree)


class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=Path(self.tmp.name)
        self.teacher=CurriculumParser(self.path/'teacher.json','teacher')
        self.student=TreeReceiver(self.path/'student.json')
        self.make_tree()

    def tearDown(self):self.tmp.cleanup()

    def make_tree(self):
        # Setup as if teacher already knew three versions and had verified vocabulary.
        t=copy.deepcopy(self.teacher.state)
        t['active_version']=2
        t['profiles']['1']={'parent':0,'op_n':4,'arg_n':4,'result_n':5,'k':1}
        t['profiles']['2']={'parent':1,'op_n':5,'arg_n':5,'result_n':6,'k':2}
        ops=t['tree']['math']['operators']
        for oid, meaning in [(1,'left'),(5,'add'),(6,'xor'),(9,'and'),(17,'or')]:
            enc={}
            for v,p in t['profiles'].items():
                if int(oid)<(1<<p['op_n']):
                    enc[v]=format(oid,f"0{p['op_n']}b")+'0'*p['k']
            ops[str(oid)]={'status':'confirmed','meaning':meaning,'seen':5,
                'examples':([{'a':1,'b':2,'result':3,'via_version':0}] if oid==5 else []),
                'hypotheses':[], 'encodings':enc}
        self.teacher._commit(t)

    def test_typed_tree_roundtrip(self):
        obj=public_tree(self.teacher.state)
        bits=pack_value(obj)
        reader=Reader(bits)
        self.assertEqual(obj,unpack_value(reader))
        reader.remaining()

    def test_binary_frames_and_exact_import(self):
        m,chunks,_=make_package(self.teacher.state,packet_id=7,chunk_bytes=65)
        self.assertEqual('manifest',decode_packet(m)['type'])
        self.assertTrue(all(set(c)<={'0','1'} for c in [m]+chunks))
        self.assertEqual('started',self.student.receive(m)['status'])
        for c in chunks[:-1]:
            self.assertEqual('partial',self.student.receive(c)['status'])
        done=self.student.receive(chunks[-1])
        self.assertEqual('committed',done['status'])
        self.assertEqual('ack',decode_packet(done['ack'])['type'])
        self.assertEqual(public_tree(self.teacher.state),public_tree(self.student.parser.state))
        self.assertEqual('student',self.student.parser.state['question_bank']['role'])
        self.assertNotIn('levels',self.student.parser.state['question_bank'])
        self.assertIsNone(self.student.session)

    def test_out_of_order_missing_request_and_restart(self):
        m,chunks,_=make_package(self.teacher.state,packet_id=9,chunk_bytes=60)
        self.student.receive(m)
        for c in reversed(chunks):
            if decode_packet(c)['index']!=1:
                self.student.receive(c)
        self.assertEqual(1,decode_packet(self.student.next_request())['index'])
        # Recreate receiver to prove isolated incoming data persists.
        loaded=TreeReceiver(self.path/'student.json')
        self.assertEqual(1,decode_packet(loaded.next_request())['index'])
        self.assertEqual('committed',loaded.receive(chunks[1])['status'])

    def test_corrupt_suffix_error_as_binary_and_retry(self):
        m,chunks,_=make_package(self.teacher.state,packet_id=11,chunk_bytes=96)
        self.student.receive(m)
        bad=chunks[0][:-1]+'1'  # last-byte token suffix corrupted
        err=self.student.receive(bad)
        self.assertEqual('parse_error',err['status'])
        # Error response is a real, parseable old v0.2 error frame.
        old=VersionedParser(self.path/'diagnostics.json')
        msg=old.parse(err['send_bits'])
        self.assertEqual('error',msg['kind'])
        self.assertEqual('BAD_SUFFIX',msg['code'])
        self.assertNotIn('1',self.student.parser.state['profiles'])
        for c in chunks:
            outcome=self.student.receive(c)
        self.assertEqual('committed',outcome['status'])

    def test_chunk_bitflip_digest_rolls_back(self):
        m,chunks,_=make_package(self.teacher.state,packet_id=12,chunk_bytes=90)
        before=copy.deepcopy(self.student.parser.state)
        self.student.receive(m)
        # Change one payload information bit, keeping suffix zero (syntactically valid).
        tampered=chunks[0]
        headlen=2+4+3+3+17+17+17
        i=headlen
        tampered=tampered[:i]+('1' if tampered[i]=='0' else '0')+tampered[i+1:]
        self.assertEqual('chunk',decode_packet(tampered)['type'])
        for idx,c in enumerate(chunks):
            result=self.student.receive(tampered if idx==0 else c)
        self.assertEqual('rejected',result['status'])
        self.assertEqual(before,self.student.parser.state)
        self.assertIsNone(self.student.session)

    def test_duplicate_chunk_conflict_doesnt_write_main_state(self):
        m,chunks,_=make_package(self.teacher.state,packet_id=13,chunk_bytes=120)
        self.student.receive(m)
        self.student.receive(chunks[0])
        self.assertEqual('partial',self.student.receive(chunks[0])['status'])
        c=chunks[0]
        prefix=2+4+3+3+17+17+17
        corrupted=c[:prefix]+('1' if c[prefix]=='0' else '0')+c[prefix+1:]
        self.assertEqual('rejected',self.student.receive(corrupted)['status'])
        self.assertNotIn('2',self.student.parser.state['profiles'])

    def test_version_conflict_rejects_atomic(self):
        me=copy.deepcopy(self.student.parser.state)
        me['profiles']['1']={'parent':0,'op_n':7,'arg_n':7,'result_n':7,'k':1}
        self.student.parser._commit(me)
        before=copy.deepcopy(self.student.parser.state)
        m,chunks,_=make_package(self.teacher.state,packet_id=14)
        self.student.receive(m)
        for c in chunks:result=self.student.receive(c)
        self.assertEqual('rejected',result['status'])
        self.assertIn('profile conflict',result['reason'])
        self.assertEqual(before,self.student.parser.state)

    def test_meaning_conflict_rejects_atomic(self):
        ours=copy.deepcopy(self.student.parser.state)
        ours['tree']['math']['operators']['5']={'status':'confirmed','meaning':'multiply',
            'seen':1,'examples':[],'hypotheses':[],'encodings':{'0':'1010'}}
        self.student.parser._commit(ours)
        before=copy.deepcopy(self.student.parser.state)
        m,chunks,_=make_package(self.teacher.state,packet_id=15)
        self.student.receive(m)
        for c in chunks: result=self.student.receive(c)
        self.assertEqual('rejected',result['status'])
        self.assertEqual(before,self.student.parser.state)

    def test_bad_internal_encoding_rejected_at_source(self):
        ours=copy.deepcopy(self.teacher.state)
        ours['tree']['math']['operators']['5']['encodings']['0']='1110'
        with self.assertRaises(ValueError):make_package(ours)

    def test_teacher_bank_not_exported(self):
        bits=pack_value(public_tree(self.teacher.state))
        r=Reader(bits)
        x=unpack_value(r)
        self.assertNotIn('question_bank',x)
        self.assertNotIn('progress',x)

    def test_real_v03_student_tree_snapshot(self):
        source=Path(__file__).parent/'fixtures'/'v03_student_tree.json'
        tree=json.loads(source.read_text('utf-8'))
        obj=public_tree(tree)
        validate_tree(obj)
        m,chunks,_=make_package(tree,packet_id=18)
        self.student.receive(m)
        for c in chunks: outcome=self.student.receive(c)
        self.assertEqual('committed',outcome['status'])
        self.assertEqual('hypothesis',self.student.parser.state['tree']['math']['operators']['5']['status'])
        self.assertEqual('student',self.student.parser.state['question_bank']['role'])

    def test_local_hypothesis_overwritten_by_confirmed_teacher(self):
        ours=copy.deepcopy(self.student.parser.state)
        ours['tree']['math']['operators']['5']={
            'status':'hypothesis','meaning':'xor','seen':1,
            'examples':[],'hypotheses':['xor'],'encodings':{'0':'1010'}}
        self.student.parser._commit(ours)
        m,chunks,_=make_package(self.teacher.state,packet_id=19)
        self.student.receive(m)
        for c in chunks: out=self.student.receive(c)
        self.assertEqual('committed',out['status'])
        self.assertEqual('confirmed',self.student.parser.state['tree']['math']['operators']['5']['status'])
        self.assertEqual('add',self.student.parser.state['tree']['math']['operators']['5']['meaning'])

    def test_large_tree(self):
        t=copy.deepcopy(self.teacher.state)
        t['profiles']['3']={'parent':2,'op_n':11,'arg_n':12,'result_n':14,'k':2}
        t['active_version']=3
        ops=t['tree']['math']['operators']
        for oid in range(100,1100):
            ops[str(oid)]={'status':'unknown','meaning':None,'seen':1,'examples':[],
                           'hypotheses':[],'encodings':{'3':format(oid,'011b')+'00'}}
        m,chunks,stats=make_package(t,packet_id=16,chunk_bytes=512)
        self.assertGreater(len(chunks),20)
        self.student.receive(m)
        for c in chunks:result=self.student.receive(c)
        self.assertEqual('committed',result['status'])
        self.assertEqual(len(ops),len(self.student.parser.state['tree']['math']['operators']))

if __name__=='__main__':unittest.main()