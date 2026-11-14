"""R23 independent dependency-free offline verification of frozen raw01 study design.
Run at the archive root: python r23_experiment/public_preflight.py
Does not run neural nets, train students, or alter any file.
"""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
P=ROOT/'r23_experiment'
EXPECTED_MANIFEST='81a6be7650ac89380434535e9df361ce461e9cafe7dd2d5dca835cd3dfa67f5e'
EXPECTED_CURRICULUM='b542f32b592cc68eecc7b7029eb93c7f061d07f5e89ed8ea2a6ea5785cf921d5'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def word(n):
 assert type(n) is int and 0<=n<=29
 return format(n,'05b')+'0'
def Q(r,a,b,c,d):return '01'+'010'+format(r,'03b')+'0'+''.join(word(v) for v in (a,b,c,d))+'111100'
def answer(r,a,b):return word(a)+(word(b) if r==2 else '')+'S'
parent=json.loads((ROOT/'r14_source/parent_course.json').read_text())
assert len(parent)==120
hi8=[[2,a,(a-8+j)%4,0,1] for a in (8,9,10,11) for j in (0,1)]
hi16=[[2,a,(a-16+j+2)%4,0,1] for a in (16,17,18,19) for j in (0,1)]
old=parent+hi8+hi16
idx=[i for i,(r,a,b,c,d) in enumerate(old) if i<48 and r==1 and c==0]
assert len(idx)==24 and len(old)==136
new=[[r,a,b,2 if i in idx else c,d] for i,(r,a,b,c,d) in enumerate(old)]
assert sum(len(answer(r,a,b)) for r,a,b,c,d in new)==1408
assert sha(P/'curriculum.json')==EXPECTED_CURRICULUM
assert (P/'curriculum.json').read_text()==json.dumps(new,separators=(',',':'))+'\n'
rows=[]
for split,bs in (('validation',(12,13)),('test',(10,11,25,26))):
 for a in range(6):
  for b in bs:
   for c in (0,2):
    rows.append(dict(split=split,pair=f'a{a}_b{b}',r=1,a=a,b=b,c=c,d=1,Q=Q(1,a,b,c,1),expected=answer(1,a,b)))
assert len(rows)==72 and len({x['Q'] for x in rows})==72
assert sha(P/'manifest.jsonl')==EXPECTED_MANIFEST
assert (P/'manifest.jsonl').read_text()==''.join(json.dumps(x,separators=(',',':'))+'\n' for x in rows)
assert {x['Q'] for x in rows}.isdisjoint({Q(*x) for x in new})
print('R23 PUBLIC PREFLIGHT PASS: 24 c0->c2 replacements; 136 events, 1408 targets/epoch; 24 validation + 48 test legal 39-bit raw Q; exact SHA256')
