#!/usr/bin/env python3
"""SLE v0.5: high-water operator IDs, reversible spiral code, incremental tree packets.

Scripted transfer protocol; sender and receiver share the v0.4 bootstrap grammar.
Only public syntax can cross the wire, not the teacher question bank. Chunks are
framed, checksummed, and imported atomically. Changes in meanings are not inferred.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any

from spiral_dialogue_v02 import word, ParseFailure, encode_error
from spiral_dialogue_v03 import CurriculumParser
from spiral_tree_packet_v04 import (
    Reader, pack_value, unpack_value, head, uint, decode_packet, request_chunk,
    ack_packet, validate_tree, merge_tree, MAX_CHUNK_BYTES, MAX_PAYLOAD_BITS,
    MAX_NODES, MAGIC as OLD_MAGIC, PKG_KIND, DATA_KIND
)

MAGIC='sle_tree_transfer_v05'

def _canonical(value:Any)->str:
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'))


def registry_from_state(state:dict)->dict:
    """Old v0.2/v0.3/v0.4 states can be read without rewriting them.

    highwater is the highest EVER allocated ID; never the number of live nodes.
    A value of -1 represents an empty category.
    """
    ops=state['tree']['math']['operators']
    biggest=max((int(x) for x in ops),default=-1)
    saved=state.get('operator_registry',{}).get('math',{}).get('highwater',-1)
    if type(saved)!=int or saved < -1:
        raise ValueError('bad highwater in persistent registry')
    return {'math':max(biggest,saved)}


def needed_width(highwater:int)->int:
    if type(highwater)!=int or highwater < -1:raise ValueError('invalid highwater')
    return max(1,highwater.bit_length())


def highwater_details(state:dict,version:int|None=None)->dict:
    hi=registry_from_state(state)['math']
    v=state['active_version'] if version is None else version
    profile=state['profiles'][str(v)]
    n=profile['op_n']
    return {'max_operator_id':hi,'required_information_bits':needed_width(hi),
            'active_information_bits':n,'suffix_layer':profile['k'],
            'active_version':v,'capacity':(1<<n)}


def encode_operator(state:dict,operator_id:int,version:int|None=None,require_known=True)->str:
    if type(operator_id)!=int or operator_id<0:raise ValueError('invalid operator id')
    high=registry_from_state(state)['math']
    if operator_id>high:raise ValueError('operator is above allocated highwater')
    if require_known and str(operator_id) not in state['tree']['math']['operators']:
        raise ValueError('operator id is allocated/reserved but is not a known node')
    v=state['active_version'] if version is None else version
    p=state['profiles'][str(v)]
    return word(operator_id,p['op_n'],p['k'])


def decode_operator(state:dict,bits:str,version:int|None=None,require_known=True)->int:
    v=state['active_version'] if version is None else version
    p=state['profiles'][str(v)]
    n,k=p['op_n'],p['k']
    if not isinstance(bits,str) or len(bits)!=n+k or set(bits)-{'0','1'}:
        raise ValueError('wrong operator word length/characters')
    if bits[-k:]!='0'*k:raise ValueError('invalid spiral tail')
    oid=int(bits[:n],2)
    if oid>registry_from_state(state)['math']:
        raise ValueError('operator above allocated highwater')
    if require_known and str(oid) not in state['tree']['math']['operators']:
        raise ValueError('unknown operator node')
    return oid


def allocate_operator(state:dict,operator_id:int,meaning:str|None=None,status:str='unknown')->dict:
    """Teacher/admin adds a new node. Returns NEW state; caller commits separately.

    Validated expansions are represented by a new version, never reinterpret an
    older profile. For this demo, v0.2 data headers allow versions 0..3 and
    CONFIG op_n field allows widths 1..7.
    """
    if type(operator_id)!=int or operator_id<0:raise ValueError('bad operator number')
    if status not in ('unknown','hypothesis','confirmed'):
        raise ValueError('bad status')
    if status=='confirmed' and (not isinstance(meaning,str) or not meaning):
        raise ValueError('confirmed node requires meaning')
    if meaning is not None and not isinstance(meaning,str):raise ValueError('bad meaning')
    target=copy.deepcopy(state)
    original_high=registry_from_state(target)['math']
    high=max(original_high,operator_id)
    n=needed_width(high)
    oldv=target['active_version']
    p=target['profiles'][str(oldv)]
    if n>p['op_n']:
        if oldv>=3 or n>7:
            raise ValueError('older v0.2 data envelope needs wider version/CONFIG bootstrap')
        newv=oldv+1
        newp=dict(p)
        newp.update({'parent':oldv,'op_n':n})
        target['profiles'][str(newv)]=newp
        target['active_version']=newv
        for key,node in target['tree']['math']['operators'].items():
            node['encodings'][str(newv)]=word(int(key),n,newp['k'])
    ops=target['tree']['math']['operators']
    if str(operator_id) not in ops:
        ops[str(operator_id)]={'status':status,'meaning':meaning,'seen':0,
            'examples':[],'hypotheses':[],'encodings':{}}
    else:
        old=ops[str(operator_id)]
        if old['status']=='confirmed' and meaning is not None and old['meaning']!=meaning:
            raise ValueError('cannot silently change confirmed meaning')
        if status=='confirmed':old.update(status=status,meaning=meaning)
    node=ops[str(operator_id)]
    for ver,profile in target['profiles'].items():
        if operator_id < (1<<profile['op_n']):
            node['encodings'].setdefault(ver,word(operator_id,profile['op_n'],profile['k']))
    target.setdefault('operator_registry',{})['math']={'highwater':high}
    return target


def prepare_export(state:dict)->dict:
    high=registry_from_state(state)['math']
    if needed_width(high)>state['profiles'][str(state['active_version'])]['op_n']:
        raise ValueError('active profile cannot represent max operator id')
    # Check exact encodings with the already-tested v0.4 validator.
    obj={'schema':OLD_MAGIC,'active_version':state['active_version'],
         'profiles':copy.deepcopy(state['profiles']),
         'tree':copy.deepcopy(state['tree'])}
    validate_tree(obj)
    return obj


def public_fingerprint(state:dict)->str:
    obj=prepare_export(state)
    obj['highwater']=registry_from_state(state)
    return hashlib.sha256(_canonical(obj).encode('utf-8')).hexdigest()


def snapshot_package(state:dict,origin:str,revision:int=1)->dict:
    obj=prepare_export(state)
    if not origin or len(origin)>128 or type(revision)!=int or revision<1:
        raise ValueError('invalid origin/revision')
    return {'schema':MAGIC,'kind':'snapshot','origin':origin,'revision':revision,
            'parent_revision':0,'highwater':registry_from_state(state),
            'active_version':obj['active_version'], 'profiles':obj['profiles'],
            'operators':obj['tree']['math']['operators']}


def delta_package(before:dict,after:dict,origin:str,parent_revision:int)->dict:
    base=prepare_export(before)
    current=prepare_export(after)
    if not origin or len(origin)>128 or type(parent_revision)!=int or parent_revision<1:
        raise ValueError('invalid origin/parent revision')
    if current['active_version']<base['active_version']:
        raise ValueError('version rollback not supported')
    baseops=base['tree']['math']['operators']
    newops=current['tree']['math']['operators']
    removed=set(baseops)-set(newops)
    if removed:raise ValueError('delete requires a separate tombstone protocol')
    before_profiles=base['profiles']
    after_profiles=current['profiles']
    for k,profile in before_profiles.items():
        if k not in after_profiles or after_profiles[k]!=profile:
            raise ValueError('profile replacement is forbidden')
    for field in ('math',):
        if registry_from_state(after)[field] < registry_from_state(before)[field]:
            raise ValueError('highwater rollback')
    profiles={k:copy.deepcopy(v) for k,v in after_profiles.items() if k not in before_profiles}
    # A new profile gives every old node a deterministic new spelling. This is
    # NOT a substantive node change: receiver can regenerate it locally.
    # Sending each old node again would defeat the purpose of a delta packet.
    changes={}
    for k,node in newops.items():
        if k not in baseops:
            changes[k]=copy.deepcopy(node)
            continue
        without_derived=copy.deepcopy(node)
        for newver in profiles:
            without_derived['encodings'].pop(newver,None)
        if without_derived!=baseops[k]:
            changes[k]=copy.deepcopy(node)
    if not changes and not profiles and registry_from_state(after)==registry_from_state(before):
        raise ValueError('no changes to send')
    return {'schema':MAGIC,'kind':'delta','origin':origin,
            'revision':parent_revision+1,'parent_revision':parent_revision,
            'highwater':registry_from_state(after),
            'active_version':after['active_version'],'profiles':profiles,'operators':changes}


def wire_package(envelope:dict,packet_id:int,chunk_bytes:int=96)->tuple[str,list[str],dict]:
    if not 1<=chunk_bytes<=MAX_CHUNK_BYTES:raise ValueError('bad chunk size')
    if type(packet_id)!=int or not 0<=packet_id<65536:raise ValueError('bad packet id')
    payload=pack_value(envelope)
    bitlen=len(payload)
    if bitlen<1 or bitlen>MAX_PAYLOAD_BITS:raise ValueError('bad payload bit length')
    tail=payload+'0'*((-bitlen)%8)
    raw=bytes(int(tail[i:i+8],2) for i in range(0,len(tail),8))
    total=max(1,math.ceil(len(raw)/chunk_bytes))
    if total>65535:raise ValueError('too many chunks')
    digest=int(hashlib.sha256(payload.encode('ascii')).hexdigest(),16)
    manifest=head(PKG_KIND)+uint(packet_id,16)+uint(total,16)+uint(bitlen,32)+uint(digest,256)+uint(0,2)
    chunks=[]
    for i in range(total):
        chunk=raw[i*chunk_bytes:(i+1)*chunk_bytes]
        chunks.append(head(DATA_KIND)+uint(0,2)+uint(packet_id,16)+uint(i,16)+uint(len(chunk),16)+''.join(uint(x,8) for x in chunk))
    return manifest,chunks,{'kind':envelope['kind'],'packet_id':packet_id,'payload_bits':bitlen,
                            'bytes':len(raw),'chunks':total,'changed_nodes':len(envelope['operators'])}


def _validate_envelope(envelope:dict):
    if type(envelope)!=dict or envelope.get('schema')!=MAGIC:
        raise ValueError('wrong package schema')
    if set(envelope)!={'schema','kind','origin','revision','parent_revision','highwater',
                       'active_version','profiles','operators'}:
        raise ValueError('unexpected/missing transfer fields')
    if envelope['kind'] not in ('snapshot','delta'):
        raise ValueError('unknown transfer type')
    if (not isinstance(envelope['origin'],str) or
        not 1<=len(envelope['origin'])<=128 or
        any(not (ch.isalnum() or ch in '_-.') for ch in envelope['origin'])):
        raise ValueError('invalid origin')
    rev,base=envelope['revision'],envelope['parent_revision']
    if type(rev)!=int or type(base)!=int or rev<1 or (base!=0 if envelope['kind']=='snapshot' else rev!=base+1):
        raise ValueError('bad revision sequence')
    high=envelope['highwater']
    if type(high)!=dict or set(high)!={'math'} or type(high['math'])!=int or high['math'] < -1:
        raise ValueError('bad highwater metadata')
    if (type(envelope['active_version'])!=int or not isinstance(envelope['profiles'],dict) or
        not isinstance(envelope['operators'],dict) or len(envelope['operators'])>MAX_NODES):
        raise ValueError('bad tree envelope')


class TreeSyncReceiver:
    def __init__(self,state_file:Path|str,role:str='student'):
        self.parser=CurriculumParser(state_file,role)
        self.incoming_path=Path(str(state_file)+'.v05_incoming.json')
        self.session=(json.loads(self.incoming_path.read_text('utf-8'))
                      if self.incoming_path.exists() else None)

    def _persist(self,value:dict):
        self.session=value
        tmp=Path(str(self.incoming_path)+'.tmp')
        tmp.write_text(_canonical(value),'utf-8')
        os.replace(tmp,self.incoming_path)

    def _clear(self):
        self.session=None
        self.incoming_path.unlink(missing_ok=True)

    def missing(self):
        return ([] if self.session is None else
                [i for i in range(self.session['total']) if str(i) not in self.session['chunks']])

    def next_request(self)->str|None:
        missing=self.missing()
        return None if not missing else request_chunk(self.session['packet_id'],missing[0])

    def _apply(self,envelope:dict)->dict:
        _validate_envelope(envelope)
        origin=envelope['origin'];rev=envelope['revision'];base=envelope['parent_revision']
        current=self.parser.state
        cursor=current.get('sync_cursors',{}).get(origin)
        if cursor is not None and rev==cursor['revision']:
            if cursor['last_digest']==hashlib.sha256(_canonical(envelope).encode()).hexdigest():
                return {'status':'already_applied','revision':rev}
            raise ValueError('revision collision')
        if envelope['kind']=='snapshot':
            if cursor and rev<cursor['revision']:raise ValueError('stale snapshot')
            profiles=envelope['profiles']
        else:
            if cursor is None or cursor['revision']!=base:
                raise ValueError(f'MISSING_BASE: expected revision {base}, have {cursor["revision"] if cursor else "none"}')
            profiles={**current['profiles'],**envelope['profiles']}
            for k,p in envelope['profiles'].items():
                if k in current['profiles'] and current['profiles'][k]!=p:
                    raise ValueError('profile replacement')
        partial={'schema':OLD_MAGIC,'active_version':envelope['active_version'],
                 'profiles':profiles,'tree':{'math':{'operators':envelope['operators']}}}
        validate_tree(partial)
        hi=envelope['highwater']['math']
        existing=registry_from_state(current)['math']
        if hi<max((int(k) for k in envelope['operators']),default=-1):
            raise ValueError('highwater less than received node ID')
        if hi>=1<<profiles[str(envelope['active_version'])]['op_n']:
            raise ValueError('highwater exceeds profile capacity')
        if envelope['kind']=='delta' and hi<existing:
            raise ValueError('highwater regression')
        if envelope['kind']=='snapshot' and cursor and rev==cursor['revision']:
            raise ValueError('revision collision')
        changed=merge_tree(current,partial)
        if envelope['kind']=='delta':
            # Regenerate the purely mechanical encodings for every preexisting
            # node under each newly introduced profile, even if absent in delta.
            for v,profile in envelope['profiles'].items():
                for oid,node in changed['tree']['math']['operators'].items():
                    if int(oid)<(1<<profile['op_n']):
                        expected=word(int(oid),profile['op_n'],profile['k'])
                        if v in node['encodings'] and node['encodings'][v]!=expected:
                            raise ValueError('new profile encoding collision')
                        node['encodings'][v]=expected
        hi=max(existing,hi)
        if hi>=1<<changed['profiles'][str(changed['active_version'])]['op_n']:
            raise ValueError('merged registry too large for profile')
        changed.setdefault('operator_registry',{})['math']={'highwater':hi}
        changed.setdefault('sync_cursors',{})[origin]={
            'revision':rev,'last_digest':hashlib.sha256(_canonical(envelope).encode()).hexdigest()}
        self.parser._commit(changed)
        return {'status':'committed','revision':rev,'max_operator_id':hi,
                'nodes':len(changed['tree']['math']['operators']),
                'changed_nodes':len(envelope['operators'])}

    def receive(self,bits:str)->dict:
        try:packet=decode_packet(bits)
        except ParseFailure as err:
            return {'status':'parse_error','diagnostic':err.as_dict(),
                    'send_bits':encode_error(0,err.code,err.field,err.offset)}
        if packet['type']=='manifest':
            if (packet['mode']!=0 or packet['total']<1 or packet['payload_bits']<1 or
                packet['payload_bits']>MAX_PAYLOAD_BITS or
                packet['total']>math.ceil(packet['payload_bits']/8)):
                return {'status':'rejected','reason':'invalid manifest bounds'}
            if self.session and packet['packet_id']==self.session['packet_id']:
                if all(self.session[k]==packet[k] for k in ('total','payload_bits','digest')):
                    return {'status':'already_started','missing':self.missing()}
                return {'status':'rejected','reason':'packet id collision'}
            self._persist({**packet,'chunks':{}})
            return {'status':'started','missing':self.missing()}
        if packet['type']=='chunk':
            s=self.session
            if not s or packet['packet_id']!=s['packet_id']:
                return {'status':'rejected','reason':'no matching manifest'}
            index=packet['index']
            if index>=s['total'] or not packet['data']:
                return {'status':'rejected','reason':'bad chunk index'}
            seen=s['chunks'].get(str(index))
            if seen and seen!=packet['data']:
                return {'status':'rejected','reason':'conflicting duplicate chunk',
                        'request':request_chunk(s['packet_id'],index)}
            if seen is None:
                s['chunks'][str(index)]=packet['data']
                self._persist(s)
            if self.missing():
                return {'status':'partial','missing_count':len(self.missing())}
            try:
                raw=b''.join(bytes.fromhex(s['chunks'][str(i)]) for i in range(s['total']))
                bits8=''.join(f'{x:08b}' for x in raw)
                if (len(bits8)<s['payload_bits'] or len(bits8)-s['payload_bits']>=8 or
                    '1' in bits8[s['payload_bits']:]):
                    raise ValueError('invalid padding / payload length')
                payload=bits8[:s['payload_bits']]
                if hashlib.sha256(payload.encode('ascii')).hexdigest()!=s['digest']:
                    raise ValueError('SHA256 mismatch')
                r=Reader(payload)
                obj=unpack_value(r);r.remaining()
                result=self._apply(obj)
            except (ValueError,KeyError,TypeError,ParseFailure) as exc:
                result={'status':'rejected','reason':str(exc),'state_unchanged':True,
                        'send_bits':encode_error(0,'INVALID_FRAME',9,0)}
            self._clear()
            if result['status'] in ('committed','already_applied'):
                result['ack']=ack_packet(packet['packet_id'])
            return result
        if packet['type']=='request':return {'status':'request','index':packet['index']}
        if packet['type']=='ack':return {'status':'ack','packet_id':packet['packet_id']}
        return {'status':'rejected','reason':'unsupported packet'}