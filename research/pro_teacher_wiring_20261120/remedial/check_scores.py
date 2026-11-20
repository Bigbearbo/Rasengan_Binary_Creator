"""Independent integer-state audit: evaluate each observed Boolean rule without the study scorer."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

def gate(code,a,b,q):
    return (code >> ((a<<2)+(b<<1)+q)) & 1

def rule(w):
    return sum(int(w[0]*a+w[1]*b+w[2]*q+w[3]>=0) << (4*a+2*b+q)
               for a in range(2) for b in range(2) for q in range(2))

def audit(code):
    counts={(0,0,True):1}
    for _ in range(8):
        following=Counter()
        for (q,prev,correct),n in counts.items():
            for a in range(2):
                for b in range(2):
                    val=gate(code,a,b,q)
                    true=int(a < b+prev)
                    following[val,true,correct and val==true] += n
        counts=following
    return (sum(n for (q,t,_),n in counts.items() if q==t),
            sum(n for (_,_,ok),n in counts.items() if ok))

def grade(code,ids):
    assert len(ids)==64 and len(set(ids))==64
    N=0
    for x in ids:
        a,b=divmod(x,256);q=0
        for k in range(8): q=gate(code,(a>>k)&1,(b>>k)&1,q)
        N+= q==(a<b)
    return N

def main(pri,exp):
    p=json.loads(pri.read_text());e=json.loads(exp.read_text())
    assert hashlib.sha256(pri.read_bytes()).hexdigest()==e["primary_result_sha256"]
    cases=dict(zip(p["starting_seeds"],p["training_ids"],strict=True))
    seen=set();n=0
    def check(seed,r):
        nonlocal n
        code=rule(r["weights"]);seen.add(code)
        assert code==r["truth_table_code"]
        assert audit(code)==(r["endpoint_correct"],r["sequence_correct"])
        assert grade(code,cases[int(seed)])==r["training_endpoints_correct"]
        n+=1
    for s,r in p['initial'].items():check(s,r)
    assert set(p["stuck_seeds"])=={int(s) for s,r in p["initial"].items() if r["training_endpoints_correct"]!=64}
    for population in [*p["results"].values(),e["trials"]]:
        for s,r in population.items():
            for stage in ("step288","step352"):check(s,r[stage])
    print(json.dumps({"scores_verified":n,"unique_rules":len(seen),"score_and_training_ids":"PASS"}))

if __name__=="__main__":main(*(Path(p) for p in sys.argv[1:]))
