"""Bounded Fable W candidate, actual left-aligned raw n5/n7 frames.

Sender request union slots are explicit teaching inputs, not native SLE.
Receiver gets only bytes; unpack/guard expose width/validity, never operands.
parse_for_scoring is an offline evaluator and MUST NOT feed receiver inputs.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np

PROFILE = 'fable_W_candidate_m4_n5_or_n7_two_operands_v1'
OP_IDS = (12, 9, 7, 8)
OP_NAMES = ('加', 'XOR', 'AND', 'OR')
OP_LABELS = ('ADD', 'XOR', 'AND', 'OR')
WIDTHS = (5, 7)

def frame_length(n):
    if n not in WIDTHS: raise ValueError('Only width5/7 in this candidate')
    return 13+3*n

def header(n): return '11110'+'1'*n+'0'

def tail_positions(n):
    p=6+n
    return (p+4,p+5+n,p+6+2*n)

def encode(op: int, a: int, b: int, n: int) -> str:
    if n not in WIDTHS or not (type(op) is int and 0<=op<4 and type(a) is int and type(b) is int and 0<=a<2**n and 0<=b<2**n):
        raise ValueError('Outside candidate profile')
    return header(n)+format(OP_IDS[op],'04b')+'0'+format(a,f'0{n}b')+'0'+format(b,f'0{n}b')+'0'

def guard_bits(bits: str, n: int) -> bool:
    if n not in WIDTHS or type(bits) is not str or len(bits)!=frame_length(n) or set(bits)-set('01'): return False
    p=6+n
    return bits[:p]==header(n) and all(bits[i]=='0' for i in tail_positions(n)) and bits[p:p+4] in tuple(format(v,'04b') for v in OP_IDS)

def parse_for_scoring(bits: str, n: int) -> tuple[int,int,int]:
    if not guard_bits(bits,n): raise ValueError('Invalid frame')
    p=6+n
    return OP_IDS.index(int(bits[p:p+4],2)), int(bits[p+5:p+5+n],2), int(bits[p+6+n:p+6+2*n],2)

def pack(bits: str, n: int) -> bytes:
    length=frame_length(n)
    if type(bits) is not str or len(bits)!=length or set(bits)-set('01'): raise ValueError('Invalid raw bit length/alphabet')
    padding=(-length)%8
    return int(bits+'0'*padding,2).to_bytes((length+7)//8,'big')

def unpack(payload: bytes) -> tuple[int,str] | None:
    if type(payload) is not bytes or len(payload) not in (4,5): return None
    n=5 if len(payload)==4 else 7
    length=frame_length(n); padding=(-length)%8
    if payload[-1] & ((1<<padding)-1): return None
    return n, format(int.from_bytes(payload,'big'),f'0{len(payload)*8}b')[:length]

def bitarray(s): return np.fromiter((int(c) for c in s), dtype=np.float64)

def oracle(op,a,b): return (a+b,a^b,a&b,a|b)[op]

def make_row(op,a,b,n):
    q=format(op,'02b')+format(b&31,'05b')+format(a&31,'05b')+format(b>>5,'02b')+format(a>>5,'02b')+str(int(n==7))
    return {'case_id':f'n{n}_o{op}_a{a:03d}_b{b:03d}','n':n,'op':op,'a':a,'b':b,'question_bits':q,'frame_bits':encode(op,a,b,n),'answer':oracle(op,a,b)}

def arrays(rows,role):
    if role=='speaker':
        x=np.stack([bitarray(r['question_bits']) for r in rows])
        y=np.stack([bitarray(r['frame_bits'].ljust(34,'0')) for r in rows])
        mask=np.stack([np.r_[np.ones(len(r['frame_bits'])),np.zeros(34-len(r['frame_bits']))] for r in rows])
    elif role=='receiver':
        x=np.stack([bitarray(r['frame_bits'].ljust(34,'0')) for r in rows])
        y=np.zeros((len(rows),18),dtype=np.float64)
        for i,r in enumerate(rows):
            y[i,r['op']]=1
            y[i,4:]=bitarray(format(r['a']&31,'05b')+format(r['b']&31,'05b')+format(r['a']>>5,'02b')+format(r['b']>>5,'02b'))
        mask=np.ones_like(y)
    else: raise ValueError(role)
    return x,y,mask

def build_dataset(parent_path):
    old=json.loads(Path(parent_path).read_text())
    oldpairs={k:[tuple(p) for p in v] for k,v in old['pair_splits'].items()}
    oldall=set(sum(oldpairs.values(),[]))
    domain=[(a,b) for a in range(128) for b in range(128) if a+b<128 and (a,b) not in oldall]
    anchors=[p for p in domain if p[0]==0 or p[1]==0]
    others=[p for p in domain if p[0] and p[1]]
    order=np.random.default_rng(2026111702).permutation(len(others))
    shuffled=[others[int(i)] for i in order]
    newpairs={'train':anchors+shuffled[:1856],'val':shuffled[1856:2112],'test':shuffled[2112:2368],'unused':shuffled[2368:]}
    assert len(domain)==7728 and len(anchors)==192
    assert [len(newpairs[k]) for k in ('train','val','test','unused')]==[2048,256,256,5168]
    assert len(set(sum(newpairs.values(),[])))==7728
    assert not oldall.intersection(set(domain))
    panels={}
    for split in ('train','val','test'):
        panels[split+'_old']=[make_row(op,a,b,5) for a,b in oldpairs[split] for op in range(4)]
        panels[split+'_new']=[make_row(op,a,b,7) for a,b in newpairs[split] for op in range(4)]
        if split!='train': panels[split+'_oldwide']=[make_row(op,a,b,7) for a,b in oldpairs[split] for op in range(4)]
    return {'schema':'growth-channel-dataset-v1','profile':PROFILE,'new_split_seed':2026111702,
            'old_pair_splits':{k:[list(p) for p in v] for k,v in oldpairs.items()},
            'new_pair_splits':{k:[list(p) for p in v] for k,v in newpairs.items()},'panels':panels}

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--parent',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise FileExistsError(a.output)
    d=build_dataset(a.parent);a.output.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:len(v) for k,v in d['panels'].items()}))
