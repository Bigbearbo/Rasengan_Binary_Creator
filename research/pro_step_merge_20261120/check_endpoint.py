"""Independent scalar verifier for the bounded endpoint study. No fitter imports."""
import itertools
import json
from pathlib import Path
import sys


def local(w, a, b, carry):
    values = (a % 2, a // 2, b % 2, b // 2, carry, 1)
    return max(0, min(7, sum(x*y for x,y in zip(w,values))))


def replay(table, a, b):
    total, carry, good = 0, 0, True
    for base in (1,4,16,64):
        da,db=a//base%4,b//base%4
        unrolled = table[8*da+2*db+carry]
        carry, digit = divmod(unrolled,4)
        total += digit*base
        good &= total+4*base*carry == a%(4*base)+b%(4*base)
    return total+256*carry, good


def verify(file):
    data=json.loads(file.read_text())
    candidates=sorted(itertools.product(range(-2,3),repeat=6),
                      key=lambda w:(sum(x*x for x in w),w))
    tables=[tuple(local(w,a,b,c) for a in range(4) for b in range(4) for c in range(2))
            for w in candidates]
    cached={}
    for t in data['trials']:
        for arm, records in t['arms'].items():
            active=list(range(len(candidates)))
            by_n={r['papers']:r for r in records}
            for n,pair in enumerate(t['training_pairs'],1):
                a,b=divmod(pair,256)
                def admissible(index):
                    summed, correct=replay(tables[index], a, b)
                    return summed==a+b and (arm=='endpoint' or correct)
                active=[i for i in active if admissible(i)]
                if n not in by_n:
                    continue
                r=by_n[n]
                assert len(active)==r['remaining']
                assert tuple(r['selected_weights'])==candidates[active[0]]
                table=tables[active[0]]
                assert table==tuple(r['table'])
                if table not in cached:
                    trace=final=0
                    for x,y in itertools.product(range(256),repeat=2):
                        val, legal=replay(table,x,y)
                        trace += legal
                        final += val == x+y
                    cached[table]=(trace,final)
                assert cached[table]==(r['every_prefix_and_final_correct'],r['final_correct'])
    checks=sum(len(x) for t in data['trials'] for x in t['arms'].values())
    print(f'PASS {checks} checkpoints; {len(cached)} distinct policies exhaustively scored; all sets of candidate counts independently matched.')


if __name__=='__main__':
    verify(Path(sys.argv[1]))
