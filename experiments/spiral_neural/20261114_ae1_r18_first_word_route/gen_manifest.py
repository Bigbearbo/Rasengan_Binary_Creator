"""Rebuild preregistered 168-case native SLE01 R18 evaluation manifest.
Public deterministic derivation helper; full frozen runner and checkpoints are
in the R18 companion ZIP. Never feed expected to the neural student.
"""
from pathlib import Path
import hashlib,json,argparse
ap=argparse.ArgumentParser()
ap.add_argument('out',type=Path)
args=ap.parse_args()
rows=[]
def case(split,r,a,b,c,d):
    q='01'+'010'+f'{r:03b}0'+''.join(f'{z:05b}0' for z in (a,b,c,d))+'111100'
    assert len(q)==39 and all(0<=z<=29 for z in (a,b,c,d))
    expected=f'{a:05b}0'+(f'{b:05b}0' if r==2 else '')+'S'
    rows.append(dict(split=split,r=r,a=a,b=b,c=c,d=d,Q=q,expected=expected))
for r in (1,2):
    for a in range(6):
        for b in (18,19,22,23):
            case('seen_baseline',r,a,b,0,0)
for a in (*range(8,12),*range(16,20)):
    for b in range(4):
        case('taught_high',2,a,b,0,1)
for b in (4,5,16,17):
    case('val_a24',2,24,b,0,1)
for a in range(25,30):
    for b in (18,19,22,23):
        case('test_new_a_d2',2,a,b,0,2)
for a in range(25,30):
    for b in (16,20,17,21):
        case('test_new_a_new_b',2,a,b,0,1)
for a in range(25,30):
    for b in (0,5,9,29):
        case('test_new_a_extreme',2,a,b,1,2)
for a in range(24,30):
    for b in (16,20,17,21):
        case('paired_invariance',2,a,b,0,2)
assert len(rows)==168 and len({x['Q'] for x in rows})==168
output=''.join(json.dumps(x,separators=(',',':'))+'\n' for x in rows)
sha=hashlib.sha256(output.encode()).hexdigest()
assert sha=='1b16c0cf72d9a9517959aac21b8cf9e7a81110b7ab6c2b52dd634d181c5ca3cc'
args.out.write_text(output)
print('R18 manifest 168/168 SHA256',sha)
