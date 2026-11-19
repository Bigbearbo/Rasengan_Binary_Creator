"""Independent training recursion, direct-output replay, and comparison to main arms."""
import argparse
import json
import os
from pathlib import Path

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable]="1"
import numpy as np

HERE = Path(__file__).resolve().parent


def adam(w, m, v, t, grad):
    m = .9*m + .1*grad
    v = .999*v + .001*grad*grad
    w = w - .02*(m/(1-.9**t))/(np.sqrt(v/(1-.999**t))+1e-8)
    return w,m,v


def check_state(path, inputs, summary, seed, core):
    with np.load(path) as states:
        c,ab=states["comparator"].copy(),states["adapter"].copy()
        cm,cv,am,av=(states[k] for k in ("c_m","c_v","ab_m","ab_v"))
        rows = states["min_rows"]
        with np.load(core / "results" / f"batches_{seed}.npz") as paired:
            assert np.array_equal(rows, paired["min_rows"])
        with np.load(core / "results" / f"frozen_{seed}" / "states.npz") as frozen:
            for i,s in enumerate(frozen["stages"]):
                if s.startswith("min_") and int(s[4:])<=summary["gate_eligible_after_step"]:
                    step=int(s[4:])
                    assert np.array_equal(c[step],frozen["comparator"][i])
                    assert np.array_equal(ab[step],frozen["adapter"][i])
        a,b,words = inputs
        hand = np.r_[2**np.arange(6,-1,-1),-2**np.arange(6,-1,-1),.5]/64
        assert np.array_equal(hand,c[0])
        assert np.array_equal(ab[0],[1.,0.])
        eligible=None
        # Verify every independent one-step recurrence from the actual stored predecessor.
        # This prevents harmless differences across alternate algebraic orderings from
        # compounding across 512 sensitive surrogate-gradient steps.
        max_error = 0
        for step,idx in enumerate(rows,1):
            independent_c, independent_ab = c[step-1], ab[step-1]
            mc, vc, ma, va = (q[step-1] for q in (cm, cv, am, av))
            x = words[idx].astype(np.float64)
            assert np.all(a[idx]!=b[idx])
            cscore = x @ independent_c[:-1] + independent_c[-1]
            direction = np.where(cscore>=0,1.,-1.)
            logit = independent_ab[0]*direction + independent_ab[1]
            residual = (1/(1+np.exp(-logit)) - (a[idx]<b[idx]))/len(idx)
            ac = np.r_[residual @ direction, residual.sum()]
            gc = residual * independent_ab[0] * 4/(1+np.abs(4*cscore))**2
            independent_ab,ma,va = adam(independent_ab,ma,va,step,ac)
            if eligible is not None:
                independent_c,mc,vc = adam(independent_c,mc,vc,step-eligible,np.r_[x.T@gc, gc.sum()])
            if eligible is None and independent_ab[0]+independent_ab[1]<0<=-independent_ab[0]+independent_ab[1]:
                eligible=step
            for actual, expected in zip((c[step],ab[step],cm[step],cv[step],am[step],av[step]),(independent_c,independent_ab,mc,vc,ma,va)):
                diff=float(np.max(np.abs(actual-expected)))
                max_error=max(max_error,diff)
                assert diff<1.e-12, (seed,step,diff)
            assert states["ab_step"][step]==step and states["c_step"][step]==(0 if eligible is None else step-eligible)
        assert eligible==summary["gate_eligible_after_step"]
    return c,ab,max_error


def pairs(inherited, seed):
    rows=json.loads((inherited/"data.json").read_text())["panels"]
    result={}
    weights=2**np.arange(6,-1,-1)
    with np.load(inherited/"sources"/f"receiver_seed{seed}.npz") as src:
        for name,data in rows.items():
            a,b = [np.array([x[k] for x in data]) for k in ("a","b")]
            x = np.array([list(map(int,r["frame_bits"])) for r in data],dtype=float)
            out=(np.tanh(x@src["param_W1"]+src["param_b1"])@src["param_W2"]+src["param_b2"])>=0
            bits=out[:,[14,15,4,5,6,7,8,16,17,9,10,11,12,13]].astype(np.uint8)
            result[name]=(a,b,bits)
    a = np.repeat(np.arange(128),128)
    b = np.tile(np.arange(128),128)
    bits=np.column_stack([((v[:,None]&weights)>0) for v in (a,b)]).astype(np.uint8)
    result["ideal"]=(a,b,bits)
    return result


def all_outputs(root, inputs, c, ab, summary):
    stored=json.loads((root/"metrics_by_step.json").read_text())
    checked = 0
    for name,(a,b,words) in inputs.items():
        n=len(a)
        weights=2**np.arange(6,-1,-1)
        actual_a, actual_b=words[:,:7]@weights,words[:,7:]@weights
        baseline=actual_a>=actual_b
        with np.load(root/(name+".npz")) as z:
            assert np.array_equal(z["truth_a"],a) and np.array_equal(z["truth_b"],b)
            table=z["copy_outputs"]
            assert np.array_equal(table,np.stack([actual_b,actual_a]))
            choices=np.unpackbits(z["decisions"],axis=2,count=n,bitorder="little")
            for step in range(len(c)):
                # Direct mathematical equation from saved weights, with decoded numeric words.
                old = words @ c[step,:14]+c[step,-1]>=0
                new = ab[step,0]*np.where(old,1.,-1.)+ab[step,1]>=0
                assert np.array_equal(old,choices[step,0])
                assert np.array_equal(new,choices[step,1])
                got_max=np.where(old,actual_a,actual_b)
                got_min=np.where(new,actual_a,actual_b)
                seen=(("ideal",np.ones(n,dtype=bool)),("ideal_in_domain",a+b<128)) if name=="ideal" else ((name,np.ones(n,dtype=bool)),)
                for panel,mask in seen:
                    scores=dict(n=int(mask.sum()),
                                max_correct=int(np.sum(mask & (got_max==np.maximum(a,b)))),
                                min_correct=int(np.sum(mask & (got_min==np.minimum(a,b)))),
                                changed_old_answers=int(np.sum(mask & (got_max!=np.maximum(actual_a,actual_b)))),
                                changed_old_tie_choices=int(np.sum(mask & (a==b) & (baseline!=old))))
                    assert stored[panel][step]==scores,(panel,step)
                    if step==512: assert summary["panels"][panel]["final"]==scores
                checked += n
    return checked


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--core",type=Path)
    parser.add_argument("--results",default=HERE/"results",type=Path)
    args=parser.parse_args()
    cores=([args.core] if args.core else [])+[HERE.parent,HERE.parent/"min_transfer_20261119"]
    core=next(p for p in cores if (p/"study.py").is_file() and (p/"inherited").is_dir())
    summary=json.loads((args.results/"summary.json").read_text())
    mains=json.loads((core/"results"/"metrics.json").read_text())
    checked=0
    max_error=0
    endpoints={}
    for seed in (101,202,303):
        root=args.results/f"seed{seed}"
        s=summary[str(seed)]
        inputs=pairs(core/"inherited",seed)
        c,ab,err=check_state(root/"states.npz",inputs["train"],s,seed,core)
        max_error=max(max_error,err)
        checked+=all_outputs(root,inputs,c,ab,s)
        endpoints[str(seed)]={panel: {arm:mains[f"{arm}_{seed}"]["min_512"][panel] for arm in ("frozen","joint")} for panel in s["panels"]}
        for name in s["panels"]: endpoints[str(seed)][name]["staged"]=s["panels"][name]["final"]
    receipt=dict(status="PASS",verified_optimizer_steps=1536,max_weight_and_moment_abs_error=max_error,
                 decoded_predictions_rows_per_task=checked,both_task_numeric_predictions=2*checked,
                 verification="Independently decode receiver outputs, check every optimization transition from its saved predecessor with an independent formula, unpack both selectors for every panel and step, score selected numeric operands directly, cross-check all saved metrics, paired batches and matching initially frozen checkpoints.",
                 matched_endpoints=endpoints)
    print(json.dumps(receipt,indent=2))

if __name__=="__main__":
    main()
