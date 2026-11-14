"""Independent R29 NumPy audit. Run with the complete R29 ZIP extracted:
python r29_numpy_audit.py --source base --out r29_outputs

This is evidence verification, not a fresh training run. It relies on original R27
NumPy implementation and six saved checkpoints from R27/R28 in the bundled ZIP.
"""
import importlib.util, json, argparse, collections
from pathlib import Path
import numpy as np

def imp(p):
    s=importlib.util.spec_from_file_location("independent_numpy_r27",str(p))
    m=importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m

def audit(src,out):
    numpy=imp(src/"r27_experiment/audit_numpy_r27.py")
    rows=[json.loads(x) for x in (out/"raw_results.jsonl").read_text().splitlines()]
    assert len(rows)==384
    cache={};maxerr=0.;calls=0
    for r in rows:
        key=(r["arm"],r["seed"])
        if key not in cache:
            parent="r27_outputs" if r["arm"]=="R27_high_only" else "r28_outputs"
            cache[key]=numpy.get_weights(src/parent/("weights_%s_dual.json"%r["seed"]))
        w=cache[key]
        actual,cause,n=numpy.generate(r["Q"],w)
        assert (actual,cause,n)==(r["actual"],r["cause"],r["forward_calls"]-2),key
        bit=numpy.logits(r["Q"],r["expected"][:1],w)
        stop=numpy.logits(r["Q"],r["expected"][:6],w)
        err=float(max(np.max(np.abs(bit-np.asarray(r["bit1_logits"]))),
                      np.max(np.abs(stop-np.asarray(r["STOP_logits"])))))
        maxerr=max(maxerr,err)
        assert err<5e-5,(key,err)
        assert bool(len(actual)>1 and actual[1]==r["expected"][1])==r["bit1_correct"]
        assert bool(np.argmax(stop)==2)==r["STOP_correct_at_true_prefix6"]
        calls+=n+2
    # Critical limitation: firstword route masks b,c,d, so changed contexts
    # do not provide statistically independent firstword neural inputs.
    by=collections.defaultdict(list)
    for r in rows:by[(r["seed"],r["arm"],r["a"])].append(r)
    for key,rr in by.items():
        assert len({z["actual"][:6] for z in rr})==1,key
        assert len({z["bit1_logit_margin_1_minus_0"] for z in rr})==1,key
    print("R29 NUMPY PASS",len(rows),"rows",calls,"forward",
          "max_logit_abs_error",maxerr,
          "effective functional test pairs per model/seed = 2, not 24")
    return {"rows":len(rows),"calls":calls,"max_logit_error":maxerr,
            "functionally_unique_input_pairs_per_seed":2}

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--source",default="base")
    ap.add_argument("--out",default="r29_outputs")
    a=ap.parse_args()
    audit(Path(a.source),Path(a.out))
