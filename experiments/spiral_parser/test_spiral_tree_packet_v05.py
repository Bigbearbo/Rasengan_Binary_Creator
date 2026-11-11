#!/usr/bin/env python3
"""Regression and failure injection for incremental SLE tree packets."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from spiral_dialogue_v02 import word, encode_data, VersionedParser
from spiral_tree_packet_v04 import decode_packet
from spiral_tree_packet_v05 import (
    registry_from_state,needed_width,encode_operator,decode_operator,
    highwater_details,allocate_operator,delta_package,snapshot_package,
    wire_package,TreeSyncReceiver, public_fingerprint)

BASE = Path(__file__).parent/'spiral_dialogue_v03_run'/'teacher_tree.json'

def transmit(receiver,envelope,pid,chunk_bytes=180,skip=None):
    manifest,chunks,stat=wire_package(envelope,pid,chunk_bytes)
    initial=receiver.receive(manifest)
    assert initial['status']=='started',initial
    last=None
    for ix,part in enumerate(chunks):
        if ix!=skip:last=receiver.receive(part)
    return stat,last,chunks

class SyncTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=Path(self.tmp.name)
        self.receiver=TreeSyncReceiver(self.path/'student.json')
        self.teacher=json.loads(BASE.read_text('utf-8'))
        self.base=copy.deepcopy(self.teacher)
    def tearDown(self):self.tmp.cleanup()
    def snapshot(self):
        env=snapshot_package(self.base,'teacher',1)
        st,result,parts=transmit(self.receiver,env,11)
        self.assertEqual('committed',result['status'],result)
        return env,st

    def test_old_state_highwater_is_max_id_not_count(self):
        x=registry_from_state(self.base)['math']
        self.assertEqual(17,x)
        self.assertLess(len(self.base['tree']['math']['operators']),18)
        self.assertEqual(5,needed_width(x))
        self.assertEqual('1000100',encode_operator(self.base,17)) # v2 n=5,k=2
        self.assertEqual(17,decode_operator(self.base,'1000100'))
        with self.assertRaises(ValueError):decode_operator(self.base,'1000101')
        with self.assertRaises(ValueError):encode_operator(self.base,18)

    def test_snapshot_plus_delta_new_id_31_and_32_auto_version(self):
        self.snapshot()
        with31=allocate_operator(self.base,31,'xor','confirmed')
        self.assertEqual(2,with31['active_version'])
        self.assertEqual(31,registry_from_state(with31)['math'])
        self.assertEqual(5,needed_width(31))
        env=delta_package(self.base,with31,'teacher',1)
        self.assertEqual({'31'},set(env['operators']))
        self.assertFalse(env['profiles'])
        st,result,_=transmit(self.receiver,env,12)
        self.assertEqual('committed',result['status'],result)
        self.assertEqual('1111100',encode_operator(self.receiver.parser.state,31))
        with32=allocate_operator(with31,32,'and','confirmed')
        self.assertEqual(3,with32['active_version'])
        self.assertEqual(6,needed_width(32))
        self.assertEqual({'3'},set(delta_package(with31,with32,'teacher',2)['profiles']))
        env=delta_package(with31,with32,'teacher',2)
        self.assertEqual({'32'},set(env['operators']), 'profile-only reencodings should be regenerated')
        st,result,_=transmit(self.receiver,env,13)
        self.assertEqual('committed',result['status'],result)
        got=self.receiver.parser.state
        self.assertEqual(32,registry_from_state(got)['math'])
        self.assertEqual('10000000',encode_operator(got,32))  # v3 n=6 k=2
        self.assertEqual('00010100',encode_operator(got,5))
        self.assertEqual(5,decode_operator(got,'00010100'))
        self.assertEqual('1000100',encode_operator(got,17,version=2))
        self.assertEqual('0010100',encode_operator(got,5,version=2))
        self.assertEqual('student',got['question_bank']['role'])
        self.assertNotIn('levels',got['question_bank'])
        self.assertEqual({'revision':3}, {'revision':got['sync_cursors']['teacher']['revision']})
        self.assertEqual(public_fingerprint(with32),public_fingerprint(got))

    def test_no_base_delta_rejected_no_memory_change(self):
        after=allocate_operator(self.base,31)
        env=delta_package(self.base,after,'teacher',1)
        before=copy.deepcopy(self.receiver.parser.state)
        _,result,_=transmit(self.receiver,env,14)
        self.assertEqual('rejected',result['status'])
        self.assertIn('MISSING_BASE',result['reason'])
        self.assertEqual(before,self.receiver.parser.state)

    def test_replay_and_wrong_revision(self):
        self.snapshot()
        after=allocate_operator(self.base,31)
        env=delta_package(self.base,after,'teacher',1)
        _,r,_=transmit(self.receiver,env,15)
        self.assertEqual('committed',r['status'])
        unchanged=copy.deepcopy(self.receiver.parser.state)
        _,repeat,_=transmit(self.receiver,env,16)
        self.assertEqual('already_applied',repeat['status'])
        self.assertEqual(unchanged,self.receiver.parser.state)
        wrong=delta_package(after,allocate_operator(after,32),'teacher',3)
        _,rejected,_=transmit(self.receiver,wrong,17)
        self.assertEqual('rejected',rejected['status'])
        self.assertEqual(unchanged,self.receiver.parser.state)

    def test_missing_chunk_restart_then_request(self):
        env=snapshot_package(self.base,'teacher',1)
        m,chunks,_=wire_package(env,18,chunk_bytes=40)
        self.receiver.receive(m)
        for i,ch in enumerate(chunks):
            if i!=1:self.receiver.receive(ch)
        assert len(chunks)>2
        restarted=TreeSyncReceiver(self.path/'student.json')
        self.assertEqual(1,decode_packet(restarted.next_request())['index'])
        self.assertEqual('committed',restarted.receive(chunks[1])['status'])

    def test_suffix_error_and_data_flip_roll_back(self):
        env=snapshot_package(self.base,'teacher',1)
        m,chunks,_=wire_package(env,19,chunk_bytes=60)
        old=copy.deepcopy(self.receiver.parser.state)
        self.receiver.receive(m)
        bad=chunks[0][:-1]+'1'
        self.assertEqual('parse_error',self.receiver.receive(bad)['status'])
        self.assertEqual(old,self.receiver.parser.state)
        # A legal frame with a modified payload should fail digest at commit.
        flipped=list(chunks[0]); start=2+4+3+3+17+17+17
        flipped[start]='1' if flipped[start]=='0' else '0'
        for i,ch in enumerate(chunks):
            result=self.receiver.receive(''.join(flipped) if i==0 else ch)
        self.assertEqual('rejected',result['status'])
        self.assertIn('SHA256',result['reason'])
        self.assertEqual(old,self.receiver.parser.state)

    def test_conflicting_meaning_does_not_overwrite(self):
        self.snapshot()
        ours=copy.deepcopy(self.receiver.parser.state)
        ours['tree']['math']['operators']['5']['status']='confirmed'
        ours['tree']['math']['operators']['5']['meaning']='multiply'
        self.receiver.parser._commit(ours)
        old=copy.deepcopy(ours)
        changed=copy.deepcopy(self.base)
        changed['tree']['math']['operators']['5']['status']='confirmed'
        changed['tree']['math']['operators']['5']['meaning']='add'
        env=delta_package(self.base,changed,'teacher',1)
        _,result,_=transmit(self.receiver,env,20)
        self.assertEqual('rejected',result['status'])
        self.assertEqual(old,self.receiver.parser.state)

    def test_highwater_does_not_shrink_after_missing_node(self):
        after=allocate_operator(self.base,31)
        # Simulate local operator retirement while keeping the persistent allocation counter.
        after['tree']['math']['operators'].pop('31')
        self.assertEqual(31,registry_from_state(after)['math'])
        self.assertEqual(5,needed_width(registry_from_state(after)['math']))
        self.assertEqual('1111100',encode_operator(after,31,require_known=False))
        with self.assertRaises(ValueError):encode_operator(after,31)

    def test_32_bit_word_requires_new_version_and_v03_data_roundtrip(self):
        got=allocate_operator(self.base,32)
        profile=got['profiles']['3']
        bits=encode_data('query',3,profile,32,1,2)
        from spiral_dialogue_v02 import VersionedParser
        p=VersionedParser(self.path/'other.json')
        p._commit(got)
        parsed=p.parse(bits)
        self.assertEqual(32,parsed['operator'])
        self.assertEqual('10000000',parsed['operator_word'])

    def test_unsupported_fourth_upgrade_fail_explicitly(self):
        got=allocate_operator(self.base,32)
        with self.assertRaisesRegex(ValueError,'wider version'):
            allocate_operator(got,128)

    def test_snapshot_only_public_tree_not_private_bank(self):
        env=snapshot_package(self.base,'teacher',1)
        self.assertNotIn('question_bank',env)
        self.assertNotIn('progress',json.dumps(env))

if __name__=='__main__': unittest.main()