#!/usr/bin/env python3
"""SLE v0.3: curriculum/question bank as part of each parser's durable state.

Scripted teacher and finite-hypothesis student exchange ONLY binary frames.
Adds stateful adaptive curriculum to v0.2. This is NOT neural learning or
unguided syntax discovery. All wire kinds/profiles are those of v0.2.
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any, Callable

from spiral_dialogue import OPERATIONS
from spiral_dialogue_v02 import (VersionedParser, Student, ParseFailure, encode_ack,
                                 encode_config, encode_data, encode_error)

# Lesson seeds are part of *teacher* question-bank state, not a hardcoded
# run-by-run transcript. The student initially has NONE of this table.
LESSONS = [
    {'name':'echo', 'op':1, 'meaning':'left', 'min_version':0, 'min_arg':1,
     'max_arg':3, 'examples': [[1,2], [3,1]], 'mastery':2},
    {'name':'add',  'op':5, 'meaning':'add', 'min_version':0, 'min_arg':2,
     'max_arg':5, 'examples': [[1,2], [2,3]], 'mastery':2},
    {'name':'xor',  'op':6, 'meaning':'xor', 'min_version':0, 'min_arg':3,
     'max_arg':7, 'examples': [[5,3]], 'mastery':2},
    {'name':'and',  'op':9, 'meaning':'and', 'min_version':1, 'min_arg':3,
     'max_arg':7, 'examples': [[6,3]], 'mastery':2},
    {'name':'or',   'op':17,'meaning':'or',  'min_version':2, 'min_arg':7,
     'max_arg':15,'examples': [[5,3]], 'mastery':2},
]
CONFIGS = {1: (1, 0, 4, 4, 5, 1), 2: (2, 1, 5, 5, 6, 2)}


def new_bank(role: str) -> dict[str, Any]:
    if role == 'teacher':
        return {
            'schema':'sle_bank_v03', 'role':role, 'active_level':0,
            'levels':copy.deepcopy(LESSONS),
            'progress':{l['name']:{'passes':0,'fails':0,'need_examples':0,
                                  'lessons_sent':[], 'questions_passed':[],
                                  'questions_failed':[], 'query_cursor':0, 'review_cursor':0,
                                  'reviews_passed':[],
                                  'reviews_failed':[]} for l in LESSONS},
            'pending':None, 'completed':False, 'reviews_due':[],
            'journal':[], 'wire_received':0,
        }
    if role == 'student':
        return {'schema':'sle_bank_v03', 'role':role, 'observations':[],
                'by_operator':{}, 'feedback':[], 'wire_received':0}
    raise ValueError('role must be teacher or student')


class CurriculumParser(VersionedParser):
    """Atomic parsing+bank observation in SAME JSON file as syntax tree.

    Base v0.2 mutates syntax tree on success. We stage its commit, then add
    the bank observation, and commit both together. Validation and diagnostics
    happen before any write. This also allows teacher-side reply validation.
    """
    def __init__(self, filename: str | Path, role: str):
        super().__init__(filename)
        self._staging = False
        self._staged: dict[str, Any] | None = None
        if 'question_bank' not in self.state:
            changed=copy.deepcopy(self.state)
            changed['question_bank']=new_bank(role)
            super()._commit(changed)
        if self.state['question_bank']['role'] != role:
            raise ValueError(f'file belongs to a {self.state["question_bank"]["role"]}')

    def _commit(self, changed: dict[str, Any]) -> None:
        if self._staging:
            self._staged=changed
        else:
            super()._commit(changed)

    def update_bank(self, fn: Callable[[dict[str, Any]], None]) -> None:
        changed=copy.deepcopy(self.state)
        fn(changed['question_bank'])
        super()._commit(changed)

    def parse(self, bits: str, guard: Callable[[dict[str, Any]], None] | None = None) -> dict[str, Any]:
        if self._staging:
            raise RuntimeError('nested parser transaction')
        self._staging=True
        self._staged=None
        try:
            result=super().parse(bits)
            if guard is not None:
                guard(result)   # Can reject semantically invalid replies before ANY commit
            if result['kind'] in ('query','example','reply'):
                changed=self._staged if self._staged is not None else copy.deepcopy(self.state)
                bank=changed['question_bank']
                bank['wire_received']+=1
                if bank['role']=='student':
                    op=str(result['operator'])
                    item=bank['by_operator'].setdefault(op, {'examples':0,'queries':0,'replies':0})
                    item[{'query':'queries','example':'examples','reply':'replies'}[result['kind']]]+=1
                    bank['observations'].append({k:result[k] for k in
                      ('kind','version','operator','a','b','result')})
                    # Keep summaries of all interactions, but only a bounded
                    # recent window inside the parser JSON. Full wire trace
                    # belongs to the experiment's separate trace.json.
                    if len(bank['observations'])>128:
                        del bank['observations'][:-128]
                self._staged=changed
            if self._staged is not None:
                super()._commit(self._staged)
            return result
        finally:
            self._staging=False
            self._staged=None


class CurriculumStudent(Student):
    def __init__(self, state_file: Path):
        self.parser=CurriculumParser(state_file, 'student')

    def receive(self, bits: str) -> dict[str, Any]:
        # Reuse v0.2 student's fixed candidate inference, and ensure its
        # actual tokenizer and persistent tree are the same.
        result=super().receive(bits)
        if result['status']=='received' and result.get('parsed',{}).get('kind')=='ack':
            self.parser.update_bank(lambda bank: bank['feedback'].append(
                {'status':result['parsed']['status'], 'version':result['parsed']['version']}))
        return result


class CurriculumTeacher:
    def __init__(self, state_file: Path):
        self.parser=CurriculumParser(state_file, 'teacher')

    @property
    def bank(self):
        return self.parser.state['question_bank']

    def level(self) -> dict[str, Any] | None:
        if self.bank['completed'] or self.bank['active_level']>=len(self.bank['levels']):
            return None
        return self.bank['levels'][self.bank['active_level']]

    def _history(self, status: str, **kwargs) -> None:
        self.parser.update_bank(lambda b: b['journal'].append({'status':status, **kwargs}))

    def _profile(self, ver: int) -> dict[str, int]:
        return self.parser.state['profiles'][str(ver)]

    def ensure_version(self) -> str | None:
        lesson=self.level()
        if lesson is None or lesson['min_version'] <= self.parser.state['active_version']:
            return None
        nextv=self.parser.state['active_version']+1
        cfg=encode_config(*CONFIGS[nextv])
        self.parser.parse(cfg)  # teacher has its own profile, student will validate independently
        self._history('config_sent', version=nextv)
        return cfg

    def choose(self) -> tuple[str, dict[str, Any]] | None:
        """Select next query from persistent teacher bank, including old-skill reviews."""
        if self.bank['completed']:
            return None
        pending=self.bank['pending']
        if pending is not None:
            return pending['wire'], {'action':'retry', 'level':pending['level'],
                                     'review':pending.get('review',False),
                                     'a':pending['a'], 'b':pending['b']}
        review=bool(self.bank['reviews_due'])
        lesson=(next(l for l in self.bank['levels'] if l['name']==self.bank['reviews_due'][0])
                if review else self.level())
        assert lesson is not None
        if lesson['min_version'] > self.parser.state['active_version']:
            cfg=self.ensure_version()
            return cfg, {'action':'config', 'level':lesson['name']}
        progress=self.bank['progress'][lesson['name']]
        # No full enumerated bank: generate candidate questions from the stored
        # difficulty bounds, excluding examples and already-answered pairs.
        excluded={tuple(pair) for pair in lesson['examples']}
        excluded.update(tuple(pair) for pair in progress['questions_passed'])
        excluded.update(tuple(pair) for pair in progress['reviews_passed'])
        ver=self.parser.state['active_version']
        profile=self._profile(ver)
        fn=OPERATIONS[lesson['meaning']]
        span=lesson['max_arg']-lesson['min_arg']+1
        cursor_key='review_cursor' if review else 'query_cursor'
        start=progress[cursor_key]
        for step in range(span*span):
            index=(start+step) % (span*span)
            a,b=lesson['min_arg']+index//span, lesson['min_arg']+index%span
            if ((a,b) in excluded or a >= (1 << profile['arg_n']) or
                b >= (1 << profile['arg_n']) or fn(a,b) >= (1 << profile['result_n'])):
                continue
            bits=encode_data('query',ver,profile,lesson['op'],a,b)
            def remember(bank):
                bank['progress'][lesson['name']][cursor_key]=(index+1) % (span*span)
                bank['pending']={'level':lesson['name'], 'a':a, 'b':b,
                                 'version':ver, 'op':lesson['op'],
                                 'review':review,'wire':bits}
                bank['journal'].append({'status':'review_sent' if review else 'query_sent',
                                        'level':lesson['name'], 'a':a,'b':b})
            self.parser.update_bank(remember)
            return bits, {'action':'review' if review else 'query',
                          'level':lesson['name'], 'a':a,'b':b}
        raise RuntimeError(f'question pool exhausted at {lesson["name"]}')

    def _lesson(self, name: str) -> str:
        level=next(l for l in self.bank['levels'] if l['name']==name)
        progress=self.bank['progress'][level['name']]
        sent={tuple(x) for x in progress['lessons_sent']}
        example=next((pair for pair in level['examples'] if tuple(pair) not in sent), None)
        if example is None:
            # Additional evidence for a failed review is allowed, but only
            # from the registered rule and bounded space in the teacher bank.
            fn=OPERATIONS[level['meaning']]
            ver=self.parser.state['active_version']
            prof=self._profile(ver)
            example=next(([a,b] for a in range(1, level['max_arg']+1)
                        for b in range(1,level['max_arg']+1)
                        if ((a,b) not in sent and a < 1 << prof['arg_n'] and
                            b < 1 << prof['arg_n'] and
                            fn(a,b) < 1 << prof['result_n'])),None)
            if example is None:
                raise RuntimeError('lesson evidence exhausted')
        a,b=example
        ver=self.parser.state['active_version']
        answer=OPERATIONS[level['meaning']](a,b)
        bits=encode_data('example',ver,self._profile(ver),level['op'],a,b,answer)
        self.parser.update_bank(lambda bank: (
            bank['progress'][level['name']]['lessons_sent'].append([a,b]),
            bank['journal'].append({'status':'teach','level':level['name'],'a':a,'b':b,'answer':answer})))
        return bits

    def receive(self, bits: str) -> dict[str, Any]:
        pending=self.bank['pending']
        def verify(result):
            if result['kind']=='reply':
                if pending is None or any(result[k] != pending[k] for k in ('version','operator','a','b') if k != 'operator'):
                    raise ParseFailure('INVALID_FRAME', 0, 0, 'reply does not match pending query', result['version'])
                if result['operator'] != pending['op']:
                    raise ParseFailure('INVALID_FRAME', 4, 11, 'reply operator does not match pending query', result['version'])
        try:
            msg=self.parser.parse(bits,guard=verify)
        except ParseFailure as exc:
            self._history('untrusted_reply_rejected',code=exc.code)
            return {'status':'bad_reply', 'error':exc.as_dict()}
        if msg['kind']=='error':
            if msg['code']=='UNKNOWN_VERSION' and pending is not None and pending['version'] in CONFIGS:
                self._history('resend_config', version=pending['version'])
                return {'status':'repair_config', 'send_bits':encode_config(*CONFIGS[pending['version']]),
                        'code':msg['code']}
            if msg['code']=='NEED_EXAMPLE':
                if pending is None:
                    return {'status':'unexpected_error', 'code':msg['code']}
                lesson=pending['level']
                self.parser.update_bank(lambda b: setattr_progress(b,lesson,'need_examples'))
                return {'status':'teaching', 'send_bits':self._lesson(lesson), 'code':msg['code']}
            # For a malformed frame, retry the same pending wire instead
            # of advancing difficulty or damaging the tree.
            self._history('repair_requested', code=msg['code'], offset=msg['offset'])
            return {'status':'retry_requested', 'send_bits':pending['wire'] if pending else None,
                    'code':msg['code'], 'field':msg['field'], 'offset':msg['offset']}
        if msg['kind']=='ack':
            return {'status':'config_ack' if msg['version'] == self.parser.state['active_version'] else 'ack_received'}
        if msg['kind']!='reply':
            return {'status':'other', 'kind':msg['kind']}
        assert pending is not None
        lesson=next(l for l in self.bank['levels'] if l['name']==pending['level'])
        wanted=OPERATIONS[lesson['meaning']](pending['a'],pending['b'])
        correct=msg['result']==wanted
        def score(bank):
            p=bank['progress'][lesson['name']]
            pair=[pending['a'],pending['b']]
            if correct:
                bank['pending']=None
                if pending.get('review',False):
                    p['reviews_passed'].append(pair)
                    assert bank['reviews_due'].pop(0)==lesson['name']
                else:
                    p['passes']+=1
                    p['questions_passed'].append(pair)
                    if p['passes']>=lesson['mastery']:
                        bank['active_level']+=1
                        # Review one earlier skill after each later stage;
                        # add a final older-v0 review after finishing v2.
                        i=bank['active_level']-1
                        if i>=1:
                            bank['reviews_due'].append(bank['levels'][i-1]['name'])
                        if i==len(bank['levels'])-1:
                            bank['reviews_due'].append(bank['levels'][0]['name'])
                bank['completed']=(bank['active_level']>=len(bank['levels'])
                                   and not bank['reviews_due'])
            else:
                if pending.get('review',False):
                    p['reviews_failed'].append(pair)
                else:
                    p['fails']+=1
                    p['questions_failed'].append(pair)
            bank['journal'].append({'status':'correct' if correct else 'wrong',
                                    'level':lesson['name'],'a':pending['a'], 'b':pending['b'],
                                    'expected':wanted,'received':msg['result']})
        self.parser.update_bank(score)
        if correct:
            return {'status':'correct', 'expected':wanted,
                    'send_bits':encode_ack(msg['version'],0),
                    'review':pending.get('review',False),
                    'advanced':self.bank['completed'] or (self.level() is not None and self.level()['name']!=lesson['name'])}
        return {'status':'wrong','expected':wanted,
                'send_bits':encode_data('example',pending['version'],self._profile(pending['version']),
                              pending['op'],pending['a'],pending['b'],wanted)}


def setattr_progress(bank: dict,level: str, field: str) -> None:
    bank['progress'][level][field]+=1


def scenario(folder: Path, *, inject_faults: bool=True, max_messages: int=150) -> dict[str, Any]:
    if folder.exists() and any(folder.iterdir()):
        raise ValueError('use a fresh folder (or resume teacher/student state explicitly)')
    folder.mkdir(parents=True,exist_ok=True)
    teacher=CurriculumTeacher(folder/'teacher_tree.json')
    student=CurriculumStudent(folder/'student_tree.json')
    trace=[]
    faults={'bad_suffix':False,'wrong_reply':False,'config_dropped':False}
    def exchange(data: str, name: str, meta: dict|None=None, override: str|None=None, auto_reply: bool=True):
        actual=data if override is None else override
        receiver=student.receive(actual)
        row={'step':name,'teacher_to_student':actual,'meta':meta or {},'student':receiver}
        if 'send_bits' in receiver and (auto_reply or receiver['status']!='replied'):
            row['student_to_teacher']=receiver['send_bits']
            teacher_result=teacher.receive(receiver['send_bits'])
            row['teacher']=teacher_result
        trace.append(row)
        return row

    for _ in range(max_messages):
        if teacher.bank['completed']:
            break
        packet=teacher.choose()
        assert packet is not None
        bits,meta=packet
        if meta['action']=='config':
            if inject_faults and meta['level']=='and' and not faults['config_dropped']:
                faults['config_dropped']=True
                trace.append({'step':'simulate_lost_config','teacher_to_student':bits,
                              'delivered':False,'meta':meta})
                continue
            row=exchange(bits,'config',meta)
            assert row['teacher']['status']=='config_ack',row
            continue
        # One intentional recoverable syntax corruption at echo level.
        if inject_faults and meta['level']=='echo' and not faults['bad_suffix']:
            faults['bad_suffix']=True
            corrupted=bits[:14]+'1'+bits[15:]  # operator suffix in v0, field starts at offset 11
            row=exchange(bits,'inject_bad_suffix',meta,corrupted)
            assert row['teacher']['status']=='retry_requested',row
            assert row['teacher']['send_bits']==bits
        deliberate_wrong = (inject_faults and meta['level']=='add' and not faults['wrong_reply'])
        row=exchange(bits,'question',meta,auto_reply=not deliberate_wrong)
        if row['student']['status']=='error' and row['teacher']['status']=='repair_config':
            recovery=exchange(row['teacher']['send_bits'],'recover_config',meta)
            assert recovery['teacher']['status']=='config_ack'
            continue
        if row['student']['status']=='need_example':
            lesson_bits=row['teacher']['send_bits']
            exchange(lesson_bits,'teaching_example',{'level':meta['level']})
            continue
        if row['student']['status']!='replied':
            raise RuntimeError('unexpected student response '+repr(row))
        # Once, imitate an accidental but syntactically VALID wrong answer.
        # The teacher supplies an example correction, then repeats the same query.
        if deliberate_wrong and row['student']['status']=='replied':
            faults['wrong_reply']=True
            msg=row['student']['parsed']
            false_result=(msg['a']+msg['b']+1) % (1 << teacher._profile(msg['version'])['result_n'])
            incorrect=encode_data('reply',msg['version'],teacher._profile(msg['version']),
                                  msg['operator'],msg['a'],msg['b'],false_result)
            result=teacher.receive(incorrect)
            assert result['status']=='wrong',result
            trace.append({'step':'inject_wrong_answer','student_to_teacher':incorrect,'teacher':result})
            exchange(result['send_bits'],'teacher_correction',{'level':meta['level']})
            continue
        # Use reply already generated by student. Prevent duplicate grading.
        # exchange already sent the student's reply to teacher and advanced state.
        assert row['teacher']['status']=='correct',row
        if row['teacher'].get('send_bits'):
            exchange(row['teacher']['send_bits'],'ack_to_student',meta)
    else:
        raise RuntimeError('maximum messages exceeded')

    if not teacher.bank['completed']:
        raise AssertionError('did not finish curriculum')
    levels=teacher.bank['levels']
    progress=teacher.bank['progress']
    summary={'simulation':'scripted teacher/student, fixed candidate operations, not neural learning',
             'completed':teacher.bank['completed'], 'current_level':teacher.bank['active_level'],
             'scores':{l['name']:{k:progress[l['name']][k] for k in ('passes','fails','need_examples','reviews_passed','reviews_failed')}
                       for l in levels},
             'versions':sorted(student.parser.state['profiles']),
             'syntax_operators':sorted(map(int,student.parser.state['tree']['math']['operators'])),
             'student_bank_operators':sorted(map(int,student.parser.state['question_bank']['by_operator'])),
             'events':len(trace),'faults':faults,
             'teacher_bank_in_same_file':'question_bank' in teacher.parser.state,
             'student_bank_in_same_file':'question_bank' in student.parser.state}
    (folder/'trace.json').write_text(json.dumps({'summary':summary,'events':trace},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    return summary


def main():
    ap=argparse.ArgumentParser(description='SLE v0.3 adaptive question-bank simulation')
    ap.add_argument('--out',default='spiral_dialogue_v03_run')
    ap.add_argument('--no-faults',action='store_true',help='disable deliberately injected errors')
    args=ap.parse_args()
    print(json.dumps(scenario(Path(args.out),inject_faults=not args.no_faults),ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()