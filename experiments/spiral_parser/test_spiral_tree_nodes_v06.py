import copy, json, tempfile, unittest
from pathlib import Path
from spiral_tree_packet_v05 import wire_package
from spiral_dialogue_v02 import encode_data
from spiral_tree_nodes_v06 import (migrate,highwater,allocate_operator,encode_operator,
    decode_operator,snapshot_package,delta_package,TreeNodeReceiver,TreeNodeCurriculumParser,public_fingerprint)
BASE=Path(__file__).parent/'fixtures'/'v03_teacher_tree.json'

def deliver(recv,envelope,pid):
    manifest,chunks,_=wire_package(envelope,pid,chunk_bytes=125)
    assert recv.receive(manifest)['status']=='started'
    last=None
    for part in chunks:last=recv.receive(part)
    return last

class TestBranch(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.recv=TreeNodeReceiver(Path(self.tmp.name)/'student.json')
        self.old=json.loads(BASE.read_text('utf-8'))
    def tearDown(self):self.tmp.cleanup()

    def test_migrate_sidecar_moves_to_actual_tree_node(self):
        old=copy.deepcopy(self.old)
        old['operator_registry']={'math':{'highwater':31}}
        s=migrate(old)
        self.assertEqual({'highwater':31},s['tree']['math']['operator_branch'])
        self.assertNotIn('operator_registry',s)

    def test_highwater_retirement_and_no_silent_shrink(self):
        s=allocate_operator(self.old,31)
        s['tree']['math']['operators'].pop('31')
        self.assertEqual(31,highwater(s))
        self.assertEqual('1111100',encode_operator(s,31,require_known=False))
        self.assertEqual(31,decode_operator(s,'1111100',require_known=False))
        with self.assertRaises(ValueError):encode_operator(s,31)

    def test_branch_node_is_in_package_not_sidecar(self):
        s=allocate_operator(self.old,31)
        env=snapshot_package(s,'teacher',1)
        self.assertEqual({'highwater':31},env['branch'])
        self.assertNotIn('operator_registry',env)
        self.assertNotIn('highwater',env) # no orphaned root metadata
        self.assertNotIn('question_bank',env)

    def test_snapshot_delta_and_encoding_old_versions(self):
        s=migrate(self.old)
        a=deliver(self.recv,snapshot_package(s,'teacher',1),11)
        self.assertEqual('committed',a['status'])
        self.assertEqual(17,highwater(self.recv.parser.state))
        s31=allocate_operator(s,31,'xor','confirmed')
        a=deliver(self.recv,delta_package(s,s31,'teacher',1),12)
        self.assertEqual('committed',a['status'])
        s32=allocate_operator(s31,32,'and','confirmed')
        a=deliver(self.recv,delta_package(s31,s32,'teacher',2),13)
        self.assertEqual('committed',a['status'])
        got=self.recv.parser.state
        self.assertEqual({'highwater':32},got['tree']['math']['operator_branch'])
        self.assertNotIn('operator_registry',got)
        self.assertEqual('00010100',encode_operator(got,5))
        self.assertEqual(5,decode_operator(got,'0010100',version=2))
        self.assertEqual(public_fingerprint(s32),public_fingerprint(got))

    def test_corrupt_branch_decline_and_state_unchanged(self):
        s=migrate(self.old)
        self.assertEqual('committed',deliver(self.recv,snapshot_package(s,'teacher',1),21)['status'])
        before=copy.deepcopy(self.recv.parser.state)
        changed=allocate_operator(s,32)
        envelope=delta_package(s,changed,'teacher',1)
        envelope['branch']={'highwater':4} # less than existing leaf and wrong for new leaf
        result=deliver(self.recv,envelope,22)
        self.assertEqual('rejected',result['status'])
        self.assertEqual(before,self.recv.parser.state)

    def test_new_word_direct_parse_updates_parent_node_and_bank(self):
        p=Path(self.tmp.name)/'direct.json'
        p.write_text(json.dumps(self.old),'utf-8')
        parser=TreeNodeCurriculumParser(p,'teacher')
        profile=parser.state['profiles']['2']
        wire=encode_data('query',2,profile,20,1,2)
        result=parser.parse(wire)
        self.assertEqual(20,result['operator'])
        self.assertEqual(20,highwater(parser.state))
        self.assertEqual(20,highwater(TreeNodeCurriculumParser(p,'teacher').state))
        self.assertNotIn('operator_registry',parser.state)
        self.assertEqual(20,parser.state['tree']['math']['operator_branch']['highwater'])

    def test_old_state_without_mark_uses_highest_existing_only_during_migration(self):
        old=copy.deepcopy(self.old)
        old.pop('operator_registry',None)
        self.assertEqual(17,highwater(migrate(old)))
        self.assertEqual(17,migrate(old)['tree']['math']['operator_branch']['highwater'])
        # Once branch persisted, same value survives removing live leaf.
        new=migrate(old)
        new['tree']['math']['operators'].pop('17')
        self.assertEqual(17,highwater(new))

if __name__=='__main__':unittest.main()