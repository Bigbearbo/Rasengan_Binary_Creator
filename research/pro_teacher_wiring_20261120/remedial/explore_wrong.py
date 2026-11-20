"""Exploratory paired fourth arm, choosing any actual wrong step on an endpoint-error paper."""
import argparse
import json
from pathlib import Path

import numpy as np
import remedial

def run(args):
    original = json.loads(args.primary.read_text())
    previous = remedial.load_previous(args.previous)
    full_a, full_b, gold, _ = previous.snapshots(args.adder)
    seeds = original["stuck_seeds"]
    indices = [original["starting_seeds"].index(seed) for seed in seeds]
    ids = np.array(original["training_ids"])[indices]
    a, b, gold_batch = full_a[:,ids],full_b[:,ids],gold[:,ids].astype(float)
    w = np.array([original["initial"][str(s)]["weights"] for s in seeds])
    randoms = [np.random.default_rng(s+1000000) for s in seeds]
    counts = np.zeros((len(w),8),dtype=int)
    first_counts = np.zeros(len(w),dtype=int)
    changed = np.zeros(len(w),dtype=int)
    def score(ww):
        cache={}
        out=[]
        for params, cases in zip(ww,ids,strict=True):
            c=previous.signature(params)
            if c not in cache:
                trajectory=previous.traces(c,full_a,full_b)
                cache[c]=trajectory[-1],previous.scores(trajectory,gold)
            end,stats=cache[c]
            out.append({"weights":params.tolist(),"truth_table_code":c,"training_endpoints_correct":int((end[cases]==gold[-1,cases]).sum()),**stats})
        return out
    for _ in range(32):
        tr, xs = remedial.forward(w,a,b,gold_batch)
        error = tr-gold_batch
        wrong = error != 0
        end_wrong = wrong[-1]
        uniform = np.stack([r.random(64) for r in randoms])
        wrong_count = wrong.sum(axis=0)
        wanted = (uniform*wrong_count).astype(int) + 1
        chosen = np.argmax(np.cumsum(wrong,axis=0) >= wanted,axis=0)
        choice = np.where(end_wrong,chosen,7)
        counts += np.stack([((choice==k)&end_wrong).sum(axis=1) for k in range(8)],axis=1)
        assert np.all(np.take_along_axis(wrong,choice[None],axis=0)[0][end_wrong])
        first_counts += (end_wrong & (choice == wrong.argmax(axis=0))).sum(axis=1)
        delta=np.zeros_like(tr[-1]); grad=np.zeros_like(w)
        for k in reversed(range(8)):
            delta += (choice==k)*error[k]
            grad += np.mean(delta[:,:,None]*xs[k],axis=1)
            delta *= w[:,2,None]
        new_w = w-0.25*grad
        changed += np.any(new_w != w,axis=1)
        w=new_w
    middle=score(w)
    w,fc=remedial.update_endpoint(previous,w,a,b,gold_batch,64)
    end=score(w)
    rows={str(s):{"step288":x,"step352":y,"hints_by_step":cc.tolist(),
                  "hints_total":int(cc.sum()),"hints_that_are_first":int(f),
                  "changed_32":int(ch),"changed_64":int(chf)} for s,x,y,cc,f,ch,chf in zip(seeds,middle,end,counts,first_counts,changed,fc,strict=True)}
    return {"status":"exploratory_after_viewing_other_arms","explore_protocol":remedial.digest(remedial.HERE/"explore_protocol.md"),
            "source_sha256":remedial.digest(args.adder),"primary_result_sha256":remedial.digest(args.primary),"script_sha256":remedial.digest(Path(__file__)),
            "stuck_students":len(seeds),"trace_perfect_288":sum(x["sequence_correct"]==65536 for x in middle),
            "trace_perfect_352":sum(x["sequence_correct"]==65536 for x in end),"total_prompts":int(counts.sum()),
            "intermediate_prompts":int(counts[:,:7].sum()),"first_error_prompts":int(first_counts.sum()),"trials":rows}

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("primary",type=Path);p.add_argument("previous",type=Path);p.add_argument("adder",type=Path);p.add_argument("--output",type=Path,default=remedial.HERE/"explore_results.json")
    args=p.parse_args(); r=run(args);args.output.write_text(json.dumps(r,indent=2)+"\n");print({k:v for k,v in r.items() if k!='trials'})
