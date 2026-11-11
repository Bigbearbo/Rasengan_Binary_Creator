#!/usr/bin/env python3
"""v0.6: authoritative operator high-water mark lives on the syntax-tree branch node.

V0.5's operator_registry was a *sidecar*. This migration instead writes:
  state['tree']['math']['operator_branch'] = {'highwater': integer}

Existing v0.3/v0.5 states can be imported; the sidecar is then removed.
Only syntax (never private question_bank) crosses the wire.
"""
from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path
from spiral_dialogue_v02 import word
from spiral_dialogue_v03 import CurriculumParser
from spiral_tree_packet_v04 import validate_tree,merge_tree,MAX_NODES,MAGIC as OLD_MAGIC
from spiral_tree_packet_v05 import (TreeSyncReceiver, needed_width,wire_package,
  _canonical, MAGIC as OLD_PACKET_MAGIC)

MAGIC='sle_tree_transfer_v06'
NODE_KEY='operator_branch'


def _max_existing(state:dict)->int:
    return max((int(k) for k in state['tree']['math']['operators']),default=-1)


def highwater(state:dict)->int:
    math=state['tree']['math']
    meta=math.get(NODE_KEY)
    if meta is None:
        # Legacy migration ONLY. Never use live count to replace a persisted mark.
        old=state.get('operator_registry',{}).get('math',{}).get('highwater',-1)
        if type(old)!=int or old < -1:raise ValueError('invalid legacy highwater')
        return max(old,_max_existing(state))
    if type(meta)!=dict or set(meta)!={'highwater'}:
        raise ValueError('invalid operator branch node')
    hi=meta['highwater']
    if type(hi)!=int or hi < _max_existing(state):
        raise ValueError('branch highwater is missing or below a child ID')
    return hi


def migrate(state:dict)->dict:
    s=copy.deepcopy(state)
    hi=highwater(s)
    s['tree']['math'][NODE_KEY]={'highwater':hi}
    s.pop('operator_registry',None)
    return s


def _legacy_export(state:dict)->dict:
    """Validate existing operator leaves without changing legacy grammar."""
    s=migrate(state)
    hi=highwater(s)
    profile=s['profiles'][str(s['active_version'])]
    if hi >= (1<<profile['op_n']):raise ValueError('highwater beyond version capacity')
    public={'schema':OLD_MAGIC,'active_version':s['active_version'],
        'profiles':copy.deepcopy(s['profiles']),
        'tree':{'math':{'operators':copy.deepcopy(s['tree']['math']['operators'])}}}
    validate_tree(public)
    return public


def encode_operator(state:dict,oid:int,version:int|None=None,require_known:bool=True)->str:
    s=migrate(state)
    if type(oid)!=int or oid<0 or oid>highwater(s):raise ValueError('unallocated operator')
    if require_known and str(oid) not in s['tree']['math']['operators']:
        raise ValueError('not a known operator leaf')
    p=s['profiles'][str(s['active_version'] if version is None else version)]
    return word(oid,p['op_n'],p['k'])


def decode_operator(state:dict,bits:str,version:int|None=None,require_known:bool=True)->int:
    s=migrate(state)
    p=s['profiles'][str(s['active_version'] if version is None else version)]
    n,k=p['op_n'],p['k']
    if (not isinstance(bits,str) or len(bits)!=n+k or
        set(bits)-{'0','1'} or bits[-k:]!='0'*k):
        raise ValueError('not a valid spiral operator word')
    oid=int(bits[:n],2)
    if oid>highwater(s) or (require_known and str(oid) not in s['tree']['math']['operators']):
        raise ValueError('unallocated or unknown operator')
    return oid


def allocate_operator(state:dict,oid:int,meaning:str|None=None,status:str='unknown')->dict:
    s=migrate(state)
    if type(oid)!=int or oid<0:raise ValueError('invalid operator number')
    if status not in ('unknown','hypothesis','confirmed'):raise ValueError('invalid status')
    if status=='confirmed' and (not isinstance(meaning,str) or not meaning):
        raise ValueError('confirmed operator needs meaning')
    if meaning is not None and not isinstance(meaning,str):raise ValueError('invalid meaning')
    before=highwater(s)
    hi=max(before,oid)
    n=needed_width(hi)
    oldv=s['active_version']
    p=s['profiles'][str(oldv)]
    if n>p['op_n']:
        if oldv>=3 or n>7:raise ValueError('v0.2 header version capacity reached')
        newv=oldv+1
        s['profiles'][str(newv)]={**p,'parent':oldv,'op_n':n}
        s['active_version']=newv
        for key,leaf in s['tree']['math']['operators'].items():
            leaf['encodings'][str(newv)]=word(int(key),n,s['profiles'][str(newv)]['k'])
    ops=s['tree']['math']['operators']
    if str(oid) not in ops:
        ops[str(oid)]={'status':status,'meaning':meaning,'seen':0,
                     'examples':[],'hypotheses':[],'encodings':{}}
    else:
        leaf=ops[str(oid)]
        if leaf['status']=='confirmed' and meaning is not None and leaf['meaning']!=meaning:
            raise ValueError('confirmed meaning conflict')
        if status=='confirmed':leaf.update(status=status,meaning=meaning)
    for v,profile in s['profiles'].items():
        if oid<(1<<profile['op_n']):
            ops[str(oid)]['encodings'].setdefault(v,word(oid,profile['op_n'],profile['k']))
    s['tree']['math'][NODE_KEY]['highwater']=hi
    _legacy_export(s)
    return s


def _package(before:dict|None,after:dict,origin:str,revision:int)->dict:
    if not origin or len(origin)>128 or not all(c.isalnum() or c in '_-.' for c in origin):
        raise ValueError('invalid origin')
    if type(revision)!=int or revision<1:raise ValueError('invalid revision')
    current=_legacy_export(after)
    hi=highwater(after)
    if before is None:
        return {'schema':MAGIC,'kind':'snapshot','origin':origin,
                'revision':revision,'parent_revision':0,
                'branch':{'highwater':hi},'active_version':current['active_version'],
                'profiles':current['profiles'],'operators':current['tree']['math']['operators']}
    original=_legacy_export(before)
    if current['active_version']<original['active_version'] or hi<highwater(before):
        raise ValueError('rollback of version/branch mark')
    oldops=original['tree']['math']['operators'];ops=current['tree']['math']['operators']
    if set(oldops)-set(ops):raise ValueError('deletion requires tombstone protocol')
    for v,p in original['profiles'].items():
        if current['profiles'].get(v)!=p:raise ValueError('profile mutation forbidden')
    profiles={v:copy.deepcopy(p) for v,p in current['profiles'].items() if v not in original['profiles']}
    changed={}
    for key,leaf in ops.items():
        if key not in oldops:
            changed[key]=copy.deepcopy(leaf);continue
        without=copy.deepcopy(leaf)
        for v in profiles:without['encodings'].pop(v,None)
        if without!=oldops[key]:changed[key]=copy.deepcopy(leaf)
    if not changed and not profiles and hi==highwater(before):
        raise ValueError('nothing to transmit')
    return {'schema':MAGIC,'kind':'delta','origin':origin,
            'revision':revision+1,'parent_revision':revision,
            'branch':{'highwater':hi},'active_version':current['active_version'],
            'profiles':profiles,'operators':changed}


def snapshot_package(state:dict,origin:str,revision:int=1)->dict:
    return _package(None,state,origin,revision)


def delta_package(before:dict,after:dict,origin:str,parent_revision:int)->dict:
    return _package(before,after,origin,parent_revision)


def public_fingerprint(state:dict)->str:
    obj=_legacy_export(state)
    obj['tree']['math'][NODE_KEY]={'highwater':highwater(state)}
    return hashlib.sha256(_canonical(obj).encode('utf-8')).hexdigest()


class TreeNodeCurriculumParser(CurriculumParser):
    """Ensure ordinary successful parsing also advances branch metadata atomically.

    CurriculumParser stages VersionedParser's writes through _commit;
    normalizing at that dispatch point happens before its final disk commit.
    """
    def __init__(self, filename:Path|str, role:str):
        super().__init__(filename,role)
        normalized=migrate(self.state)
        if normalized!=self.state:
            # One-time migration from a legacy state; preserves bank.
            super()._commit(normalized)

    def _commit(self, changed:dict)->None:
        # Reached only after ordinary parser has validated the whole message.
        # Advance the parent node BEFORE the single staged/disk commit.
        staged=copy.deepcopy(changed)
        branch=staged['tree']['math'].get(NODE_KEY)
        if branch is not None and type(branch)==dict and type(branch.get('highwater'))==int:
            branch['highwater']=max(branch['highwater'],_max_existing(staged))
        return super()._commit(migrate(staged))


class TreeNodeReceiver(TreeSyncReceiver):
    def __init__(self,state_file:Path|str,role:str='student'):
        self.parser=TreeNodeCurriculumParser(state_file,role)
        self.incoming_path=Path(str(state_file)+'.v05_incoming.json')
        self.session=(json.loads(self.incoming_path.read_text('utf-8'))
                      if self.incoming_path.exists() else None)
    """v0.5 packet framing, but v0.6 branch node and one atomic final commit."""
    def _apply(self,envelope:dict)->dict:
        required={'schema','kind','origin','revision','parent_revision','branch',
                  'active_version','profiles','operators'}
        if type(envelope)!=dict or set(envelope)!=required or envelope['schema']!=MAGIC:
            raise ValueError('wrong v0.6 syntax tree packet')
        kind=envelope['kind']; origin=envelope['origin']
        rev=envelope['revision'];parent=envelope['parent_revision']
        if kind not in ('snapshot','delta') or type(rev)!=int or rev<1 or type(parent)!=int:
            raise ValueError('bad kind/revision')
        if (not isinstance(origin,str) or not 1<=len(origin)<=128 or
            not all(c.isalnum() or c in '_-.' for c in origin)):
            raise ValueError('invalid origin')
        if (kind=='snapshot' and parent!=0) or (kind=='delta' and rev!=parent+1):
            raise ValueError('invalid revision order')
        branch=envelope['branch']
        if type(branch)!=dict or set(branch)!={'highwater'} or type(branch['highwater'])!=int or branch['highwater']<-1:
            raise ValueError('invalid operator branch metadata')
        hi=branch['highwater']
        current=migrate(self.parser.state)
        cursor=current.get('sync_cursors',{}).get(origin)
        digest=hashlib.sha256(_canonical(envelope).encode()).hexdigest()
        if cursor and rev==cursor['revision']:
            if digest==cursor['last_digest']:return {'status':'already_applied','revision':rev}
            raise ValueError('revision collision')
        if kind=='snapshot':
            if cursor and rev<cursor['revision']:raise ValueError('stale snapshot')
            profiles=envelope['profiles']
        else:
            if cursor is None or cursor['revision']!=parent:
                raise ValueError('MISSING_BASE')
            profiles={**current['profiles'],**envelope['profiles']}
            for v,p in envelope['profiles'].items():
                if v in current['profiles'] and current['profiles'][v]!=p:
                    raise ValueError('profile replacement')
        partial={'schema':OLD_MAGIC,'active_version':envelope['active_version'],
                 'profiles':profiles,'tree':{'math':{'operators':envelope['operators']}}}
        validate_tree(partial)
        if hi < max((int(x) for x in envelope['operators']),default=-1):
            raise ValueError('branch highwater smaller than received leaf')
        if hi >= 1 << profiles[str(envelope['active_version'])]['op_n']:
            raise ValueError('branch highwater cannot fit active profile')
        if kind=='delta' and hi<highwater(current):
            raise ValueError('branch highwater rollback')
        # old merge routine only sees legacy leaves; branch metadata is attached after merge.
        changed=merge_tree(current,partial)
        if kind=='delta':
            for version,profile in envelope['profiles'].items():
                for oid,leaf in changed['tree']['math']['operators'].items():
                    if int(oid)<(1<<profile['op_n']):
                        expected=word(int(oid),profile['op_n'],profile['k'])
                        if version in leaf['encodings'] and leaf['encodings'][version]!=expected:
                            raise ValueError('re-encoding conflict')
                        leaf['encodings'][version]=expected
        final_hi=max(highwater(current),hi)
        changed['tree']['math'][NODE_KEY]={'highwater':final_hi}
        changed.pop('operator_registry',None)
        if final_hi >= 1<<changed['profiles'][str(changed['active_version'])]['op_n']:
            raise ValueError('merged highwater overflow')
        changed.setdefault('sync_cursors',{})[origin]={'revision':rev,'last_digest':digest}
        self.parser._commit(changed)
        return {'status':'committed','revision':rev,'max_operator_id':final_hi,
                'changed_nodes':len(envelope['operators'])}