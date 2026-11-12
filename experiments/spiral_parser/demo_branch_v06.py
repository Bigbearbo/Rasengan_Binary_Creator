#!/usr/bin/env python3
"""Reproducible v0.6 tree-node highwater example."""
import copy,json,tempfile
from pathlib import Path
from spiral_tree_nodes_v06 import (migrate,highwater,allocate_operator,encode_operator,
    decode_operator,snapshot_package,delta_package,TreeNodeReceiver)
from spiral_tree_packet_v05 import wire_package
ROOT=Path(__file__).parent
base=json.loads((ROOT/'fixtures'/'v03_teacher_tree.json').read_text('utf-8'))
with tempfile.TemporaryDirectory() as td:
    recv=TreeNodeReceiver(Path(td)/'student.json')
    current=migrate(base)
    stages=[]
    def send(env,pid):
        m,chunks,stats=wire_package(env,pid,chunk_bytes=160)
        answer=recv.receive(m)
        assert answer['status']=='started'
        for ch in chunks:answer=recv.receive(ch)
        assert answer['status']=='committed',answer
        stages.append({'kind':env['kind'],'packet':pid,'chunks':len(chunks),
          'changed_nodes':len(env['operators']),'branch_on_wire':env['branch'],
          'receiver_branch':copy.deepcopy(recv.parser.state['tree']['math']['operator_branch'])})
    send(snapshot_package(current,'teacher',1),25)
    s31=allocate_operator(current,31,'xor','confirmed')
    send(delta_package(current,s31,'teacher',1),26)
    s32=allocate_operator(s31,32,'and','confirmed')
    send(delta_package(s31,s32,'teacher',2),27)
    latest=recv.parser.state
    assert latest['tree']['math']['operator_branch']['highwater']==32
    assert 'operator_registry' not in latest
    assert decode_operator(latest,encode_operator(latest,5,version=2),version=2)==5
    result={'summary':'branch metadata stored on syntax tree; no external operator_registry',
      'stages':stages,'active_version':latest['active_version'],
      'highwater':highwater(latest),'latest_operator5':encode_operator(latest,5),
      'old_v2_operator5':encode_operator(latest,5,version=2),
      'question_bank_preserved':latest['question_bank']['role']=='student'}
    run=ROOT/'run_v06';run.mkdir(exist_ok=True)
    (run/'trace.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf-8')
    (run/'student.json').write_text(json.dumps(latest,ensure_ascii=False,indent=2)+'\n','utf-8')
    (run/'teacher.json').write_text(json.dumps(s32,ensure_ascii=False,indent=2)+'\n','utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))