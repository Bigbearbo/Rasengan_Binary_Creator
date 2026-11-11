#!/usr/bin/env python3
"""SLE v0.4: transactional transfer of syntax trees as binary spiral words.

Both sides already share a small bootstrap grammar. No natural-language payload,
JSON tunneling, neural learning or unrestricted code execution on the wire.
Only PUBLIC parser profiles and syntax tree are transferable: private question
bank / mastery / answer key never leave their owner's state.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any

from spiral_dialogue_v02 import ParseFailure, word, encode_error
from spiral_dialogue_v03 import CurriculumParser

MARKER='01'
PKG_KIND=6
DATA_KIND=7
MAGIC='sle_tree_packet_v04'
# Cap per individual fragment, not the size of the whole syntax tree.
MAX_CHUNK_BYTES=1024
MAX_PAYLOAD_BITS=64*1024*1024*8
MAX_NODES=100000


def head(kind:int)->str:
    return MARKER+word(kind,3)+word(0,2)


def uint(value:int,n:int)->str:
    return word(value,n,1)


def vint(value:int)->str:
    if type(value) is not int or value<0:
        raise ValueError('unsigned integer required')
    out=''
    while True:
        octet=value&127
        value >>= 7
        out += uint(octet | (128 if value else 0),8)
        if not value: return out


class Reader:
    def __init__(self,bits:str):
        if not isinstance(bits,str) or any(c not in '01' for c in bits):
            raise ParseFailure('NON_BINARY',0,0,'binary only')
        self.bits=bits
        self.pos=0
    def read(self,n:int,field:int=8)->int:
        start=self.pos
        if n<=0 or self.pos+n+1>len(self.bits):
            raise ParseFailure('TRUNCATED',field,start,'not enough bits')
        piece=self.bits[start:start+n+1]
        if piece[-1]!='0':
            raise ParseFailure('BAD_SUFFIX',field,start, f'expected terminal 0 in {piece}')
        self.pos+=n+1
        return int(piece[:-1],2)
    def remaining(self):
        if self.pos != len(self.bits):
            raise ParseFailure('EXTRA_BITS',9,self.pos,'unexpected bits')
    def varint(self):
        v=0; shift=0
        while True:
            byte=self.read(8)
            v |= (byte & 127) << shift
            if not byte & 128: return v
            shift+=7
            if shift>70: raise ParseFailure('INVALID_FRAME',9,self.pos,'length overflow')


def pack_value(value:Any,depth:int=0)->str:
    if depth>64: raise ValueError('tree is too deeply nested')
    if value is None: return uint(0,3)
    if value is False: return uint(1,3)
    if value is True: return uint(2,3)
    if type(value) is int:
        z=(value*2 if value>=0 else -value*2-1)
        return uint(3,3)+vint(z)
    if type(value) is str:
        chars=value.encode('utf-8')
        return uint(4,3)+vint(len(chars))+''.join(uint(c,8) for c in chars)
    if type(value) is list:
        return uint(5,3)+vint(len(value))+''.join(pack_value(x,depth+1) for x in value)
    if type(value) is dict:
        if not all(isinstance(x,str) for x in value):
            raise ValueError('dict keys must be strings')
        return (uint(6,3)+vint(len(value))+
                ''.join(pack_value(key,depth+1)+pack_value(value[key],depth+1)
                        for key in sorted(value)))
    raise ValueError(f'not transferable: {type(value).__name__}')


def unpack_value(r:Reader,depth:int=0):
    if depth>64: raise ParseFailure('INVALID_FRAME',9,r.pos,'nesting limit')
    t=r.read(3)
    if t==0:return None
    if t==1:return False
    if t==2:return True
    if t==3:
        z=r.varint()
        return (z>>1) if z%2==0 else -(z//2)-1
    if t==4:
        n=r.varint()
        if n>10_000_000:raise ParseFailure('INVALID_FRAME',9,r.pos,'string too long')
        try:
            return bytes(r.read(8) for _ in range(n)).decode('utf-8')
        except UnicodeDecodeError as e:
            raise ParseFailure('INVALID_FRAME',9,r.pos,'invalid UTF-8') from e
    if t==5:
        n=r.varint()
        if n>MAX_NODES:raise ParseFailure('INVALID_FRAME',9,r.pos,'list too long')
        return [unpack_value(r,depth+1) for _ in range(n)]
    if t==6:
        n=r.varint()
        if n>MAX_NODES:raise ParseFailure('INVALID_FRAME',9,r.pos,'dict too large')
        result={}
        for _ in range(n):
            key=unpack_value(r,depth+1)
            if not isinstance(key,str) or key in result:
                raise ParseFailure('INVALID_FRAME',9,r.pos,'invalid/duplicate key')
            result[key]=unpack_value(r,depth+1)
        return result
    raise ParseFailure('INVALID_FRAME',9,r.pos,'unknown value type')


def public_tree(state:dict)->dict:
    """Explicit allowlist keeps teacher's private bank and progress private."""
    return {'schema':MAGIC,
            'active_version': state['active_version'],
            'profiles':copy.deepcopy(state['profiles']),
            'tree':copy.deepcopy(state['tree'])}


def make_package(state:dict,packet_id:int=1,chunk_bytes:int=96)->tuple[str,list[str],dict]:
    if not 1<=chunk_bytes<=MAX_CHUNK_BYTES:raise ValueError('chunk_bytes outside limit')
    obj=public_tree(state)
    validate_tree(obj)
    bits=pack_value(obj)
    bitlen=len(bits)
    if bitlen>MAX_PAYLOAD_BITS:raise ValueError('payload exceeds receiver cap')
    pad=bits+'0'*((-bitlen)%8)
    blob=bytes(int(pad[i:i+8],2) for i in range(0,len(pad),8))
    count=max(1,math.ceil(len(blob)/chunk_bytes))
    if count>65535: raise ValueError('too many chunks')
    digest=int(hashlib.sha256(bits.encode('ascii')).hexdigest(),16)
    manifest=(head(PKG_KIND)+uint(packet_id,16)+uint(count,16)+uint(bitlen,32)
              +uint(digest,256)+uint(0,2)) # 0=merge-only, not replace private state
    chunks=[]
    for index in range(count):
        data=blob[index*chunk_bytes:(index+1)*chunk_bytes]
        chunks.append(head(DATA_KIND)+uint(0,2)+uint(packet_id,16)
                      +uint(index,16)+uint(len(data),16)
                      +''.join(uint(x,8) for x in data))
    return manifest,chunks,{'packet_id':packet_id,'chunks':count,'bytes':len(blob),'payload_bits':bitlen,
                            'digest':f'{digest:064x}','node_count':len(obj['tree']['math']['operators'])}


def request_chunk(packet_id:int,index:int)->str:
    return head(DATA_KIND)+uint(1,2)+uint(packet_id,16)+uint(index,16)


def ack_packet(packet_id:int,status:int=0)->str:
    return head(DATA_KIND)+uint(2,2)+uint(packet_id,16)+uint(status,2)


def decode_packet(bits:str)->dict:
    r=Reader(bits)
    if not bits.startswith(MARKER):
        raise ParseFailure('INVALID_FRAME',0,0,'bad bootstrap')
    r.pos=2
    kind=r.read(3,2)
    ver=r.read(2,1)
    if ver!=0:raise ParseFailure('UNKNOWN_VERSION',1,6,'unknown packet bootstrap')
    if kind==PKG_KIND:
        result={'type':'manifest','packet_id':r.read(16),
                'total':r.read(16),'payload_bits':r.read(32),
                'digest':f'{r.read(256):064x}','mode':r.read(2)}
    elif kind==DATA_KIND:
        mode=r.read(2)
        if mode==0:
            pk=r.read(16); ix=r.read(16); n=r.read(16)
            if n>MAX_CHUNK_BYTES:raise ParseFailure('INVALID_FRAME',9,r.pos,'oversized chunk')
            data=bytes(r.read(8) for _ in range(n))
            result={'type':'chunk','packet_id':pk,'index':ix,'data':data.hex()}
        elif mode==1:
            result={'type':'request','packet_id':r.read(16),'index':r.read(16)}
        elif mode==2:
            result={'type':'ack','packet_id':r.read(16),'status':r.read(2)}
        else:raise ParseFailure('INVALID_FRAME',9,r.pos,'reserved mode')
    else:raise ParseFailure('INVALID_FRAME',2,2,'not a tree packet')
    r.remaining()
    return result


def validate_tree(obj:dict):
    if not isinstance(obj,dict) or obj.get('schema')!=MAGIC:
        raise ValueError('wrong tree package schema')
    profiles=obj.get('profiles')
    tree=obj.get('tree')
    active=obj.get('active_version')
    if not isinstance(profiles,dict) or not isinstance(tree,dict) or type(active)!=int:
        raise ValueError('missing profiles/tree/version')
    if not profiles or len(profiles)>4096 or str(active) not in profiles:
        raise ValueError('invalid active version')
    for version,p in profiles.items():
        if not version.isdecimal() or not isinstance(p,dict):raise ValueError('bad profile')
        for field in ('op_n','arg_n','result_n','k'):
            if type(p.get(field))!=int or not 1<=p[field]<=256:
                raise ValueError('invalid profile width')
        parent=p.get('parent')
        if parent is not None and (type(parent)!=int or str(parent) not in profiles or parent>=int(version)):
            raise ValueError('invalid profile parent')
    if set(tree)!={'math'} or not isinstance(tree['math'],dict) or set(tree['math'])!={'operators'}:
        raise ValueError('unsupported tree category layout')
    ops=tree['math']['operators']
    if not isinstance(ops,dict) or len(ops)>MAX_NODES:raise ValueError('invalid operators')
    for oid,node in ops.items():
        if not oid.isdecimal() or not isinstance(node,dict):raise ValueError('invalid operator node')
        if type(node.get('seen'))!=int or node['seen']<0:raise ValueError('invalid seen counter')
        if node.get('status') not in ('unknown','hypothesis','confirmed'):
            raise ValueError('invalid knowledge status')
        meaning=node.get('meaning')
        if node['status']=='confirmed' and (not isinstance(meaning,str) or not meaning):
            raise ValueError('confirmed node missing meaning')
        if meaning is not None and not isinstance(meaning,str):raise ValueError('bad meaning')
        examples=node.get('examples')
        enc=node.get('encodings')
        if not isinstance(examples,list) or not isinstance(enc,dict):raise ValueError('bad examples/encodings')
        seen_example={}
        for example in examples:
            if not isinstance(example,dict) or any(type(example.get(k))!=int or example[k]<0
                                for k in ('a','b','result','via_version')):
                raise ValueError('bad example')
            key=example['a'],example['b']
            if key in seen_example and seen_example[key]!=example['result']:
                raise ValueError('contradictory examples in package')
            seen_example[key]=example['result']
        for v,bits in enc.items():
            if v not in profiles or not isinstance(bits,str):raise ValueError('bad encoding version')
            p=profiles[v]
            if int(oid)>=(1<<p['op_n']) or bits!=word(int(oid),p['op_n'],p['k']):
                raise ValueError('encoding does not match profile')


def merge_tree(target:dict,incoming:dict)->dict:
    """All-or-nothing merge. An unknown remote label cannot erase local knowledge."""
    validate_tree(incoming)
    fresh=copy.deepcopy(target)
    for ver,profile in incoming['profiles'].items():
        if ver in fresh['profiles'] and fresh['profiles'][ver]!=profile:
            raise ValueError(f'profile conflict v{ver}')
        fresh['profiles'][ver]=copy.deepcopy(profile)
    fresh['active_version']=max(fresh['active_version'],incoming['active_version'])
    ops=fresh['tree']['math']['operators']
    for oid,incoming_node in incoming['tree']['math']['operators'].items():
        if oid not in ops:
            ops[oid]=copy.deepcopy(incoming_node)
            continue
        old=ops[oid]
        old_status=old.get('status')
        new_status=incoming_node.get('status')
        if (old_status=='confirmed' and new_status=='confirmed' and
            old['meaning']!=incoming_node['meaning']):
            raise ValueError(f'meaning conflict for {oid}')
        if new_status=='confirmed' and old_status!='confirmed':
            old['status']='confirmed'
            old['meaning']=incoming_node['meaning']
        elif new_status=='hypothesis' and old_status=='unknown':
            old['status']='hypothesis'
            old['meaning']=incoming_node['meaning']
        # When both peers only have tentative hypotheses, keep local judgement.
        # Incoming examples still have to pass deterministic consistency checks.
        old['seen']=max(old['seen'],incoming_node['seen'])
        for version,code in incoming_node['encodings'].items():
            if version in old['encodings'] and old['encodings'][version]!=code:
                raise ValueError(f'encoding conflict for {oid} at v{version}')
            old['encodings'][version]=code
        examples={(x['a'],x['b']):x for x in old['examples']}
        for e in incoming_node['examples']:
            key=e['a'],e['b']
            if key in examples and examples[key]['result']!=e['result']:
                raise ValueError(f'example conflict for {oid} at {key}')
            if key not in examples:
                old['examples'].append(copy.deepcopy(e));examples[key]=e
    # Keep the receiving student's question_bank intact.
    return fresh


class TreeReceiver:
    def __init__(self,state_path:str|Path,role:str='student'):
        self.parser=CurriculumParser(state_path,role)
        self.session_path=Path(str(state_path)+'.incoming.json')
        self.session=json.loads(self.session_path.read_text('utf-8')) if self.session_path.exists() else None
        self.last_error=None

    def _save_session(self,s):
        self.session=s
        tmp=Path(str(self.session_path)+'.tmp')
        tmp.write_text(json.dumps(s,sort_keys=True),'utf-8')
        os.replace(tmp,self.session_path)

    def _clear_session(self):
        self.session=None
        if self.session_path.exists():self.session_path.unlink()

    def receive(self,bits:str)->dict:
        try:
            packet=decode_packet(bits)
        except ParseFailure as ex:
            return {'status':'parse_error','error':ex.as_dict(),
                    'send_bits':encode_error(0,ex.code,ex.field,ex.offset)}
        if packet['type']=='manifest':
            if (packet['total']<1 or packet['payload_bits']<1 or
                packet['payload_bits']>MAX_PAYLOAD_BITS or packet['mode']!=0 or
                packet['total']>math.ceil(packet['payload_bits']/8)):
                return {'status':'rejected','reason':'invalid manifest bounds/mode'}
            if self.session is not None and self.session['packet_id']==packet['packet_id']:
                if all(self.session.get(k)==packet[k] for k in ('digest','total','payload_bits')):
                    return {'status':'already_started','missing':self.missing()}
                return {'status':'rejected','reason':'package ID collision'}
            self._save_session({**packet,'chunks':{}})
            return {'status':'started','missing':self.missing()}
        if packet['type']=='chunk':
            s=self.session
            if s is None or s['packet_id']!=packet['packet_id']:
                return {'status':'rejected','reason':'no matching manifest'}
            ix=packet['index']
            if ix>=s['total'] or not packet['data']:
                return {'status':'rejected','reason':'bad chunk index or empty chunk'}
            old=s['chunks'].get(str(ix))
            if old is not None and old!=packet['data']:
                return {'status':'rejected','reason':'conflicting duplicate chunk', 'request':request_chunk(s['packet_id'],ix)}
            if old is None:
                s['chunks'][str(ix)]=packet['data']
                self._save_session(s)
            missing=self.missing()
            if missing:
                return {'status':'partial','received':len(s['chunks']),'missing_count':len(missing)}
            try:
                content=b''.join(bytes.fromhex(s['chunks'][str(i)]) for i in range(s['total']))
                allbits=''.join(f'{b:08b}' for b in content)
                if len(allbits)<s['payload_bits'] or len(allbits)-s['payload_bits']>=8:
                    raise ValueError('inconsistent payload length')
                payload=allbits[:s['payload_bits']]
                if any(c!='0' for c in allbits[s['payload_bits']:]):
                    raise ValueError('nonzero padding')
                if hashlib.sha256(payload.encode('ascii')).hexdigest()!=s['digest']:
                    raise ValueError('SHA256 mismatch')
                reader=Reader(payload)
                obj=unpack_value(reader)
                reader.remaining()
                changed=merge_tree(self.parser.state,obj)
            except (ValueError,KeyError,TypeError,ParseFailure) as exc:
                self._clear_session()
                return {'status':'rejected','reason':str(exc),'state_unchanged':True,
                        'send_bits':encode_error(0,'INVALID_FRAME',9,0)}
            self.parser._commit(changed)
            self._clear_session()
            return {'status':'committed','packet_id':packet['packet_id'],
                    'operators':len(changed['tree']['math']['operators']),
                    'ack':ack_packet(packet['packet_id'])}
        if packet['type']=='request':
            return {'status':'request_received','index':packet['index']}
        if packet['type']=='ack':
            return {'status':'ack_received','packet_id':packet['packet_id'],'code':packet['status']}
        return {'status':'rejected','reason':'unknown packet type'}

    def missing(self)->list[int]:
        if self.session is None:return []
        return [i for i in range(self.session['total']) if str(i) not in self.session['chunks']]

    def next_request(self)->str|None:
        missing=self.missing()
        return request_chunk(self.session['packet_id'],missing[0]) if missing else None