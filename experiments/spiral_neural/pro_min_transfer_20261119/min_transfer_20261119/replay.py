"""Read-only replay of all registered decisions, numeric answers, metrics and fitted weights."""
import argparse
import os
for variable in ("OPENBLAS_NUM_THREADS","OMP_NUM_THREADS","MKL_NUM_THREADS"):
    os.environ[variable]="1"
import hashlib
import json
from pathlib import Path
import sys
import numpy as np

import study

def replay(results):
    metrics = json.loads((results/"metrics.json").read_text())
    receipt = json.loads((results/"run_receipt.json").read_text())
    prereg = hashlib.sha256((study.BASE/"PREREG.md").read_bytes()).hexdigest()
    assert prereg=="51ca6bcaab3b8182b9360e6cb661efbd5a998b3fdbf863aa638338e135d52d49"
    lock = json.loads((study.BASE/"inherited/source_lock.json").read_text())["source_sha256"]
    for name in ["data.json","hybrid_model.py","handfilled_mux.npz"]+[f"sources/receiver_seed{q}.npz" for q in study.SEEDS]:
        assert hashlib.sha256((study.BASE/"inherited"/name).read_bytes()).hexdigest() == lock[name]
    # Gate truth table: independent algebra vs actual threshold network on the full interface.
    ai=np.repeat(np.arange(128),128)
    bi=np.tile(np.arange(128),128)
    words=study.bitwords(ai,bi)
    mux=study.prior.load_mux()
    for choice,target in [(0,bi),(1,ai)]:
        gate=study.prior.mux_forward(mux,words,np.full(len(ai),choice,dtype=np.uint8))
        assert np.array_equal(gate["output_bits"] @ study.BITS,target)
    replay_rows=stored_states=0
    worst_param_delta=0.
    replay_updates=0
    for seed in study.SEEDS:
        panels=study.load_inputs(seed)
        with np.load(results/f"batches_{seed}.npz",allow_pickle=False) as bz:
            batches=(bz["min_rows"],bz["max_rows"])
        a,b,_=panels["train"]
        assert all(np.array_equal(x,y) for x,y in zip(batches,study.schedules(seed,a,b)))
        assert all(np.all(a[rows]!=b[rows]) for rows in batches)
        for arm in study.ARMS:
            run=f"{arm}_{seed}"
            checks=study.fit(arm,seed,panels["train"],batches)
            replay_updates+=512+(128 if arm!="frozen" else 0)
            with np.load(results/run/"states.npz",allow_pickle=False) as weights:
                stages=weights["stages"].tolist()
                assert list(checks)==stages
                for j,key in enumerate(("comparator","adapter","c_m","c_v","ab_m","ab_v","c_step","ab_step")):
                    vals=np.array([checks[st][j] for st in stages])
                    delta=np.abs(weights[key]-vals).max()
                    assert delta<1e-12
                    worst_param_delta=max(worst_param_delta,float(delta))
                stored_states+=len(stages)
                for panel,(a,b,x) in panels.items():
                    da,db=x[:,:7]@study.BITS,x[:,7:]@study.BITS
                    with np.load(results/run/(panel+".npz"),allow_pickle=False) as scored:
                        assert np.array_equal(weights["stages"],scored["stages"])
                        preds=scored["predictions"]
                    assert preds.shape==(len(stages),4,len(a))
                    for i,stage in enumerate(stages):
                        c,ab=weights["comparator"][i], weights["adapter"][i]
                        left_old=(x@c[:-1]+c[-1]>=0)
                        left_new=left_old if arm=="overwrite" else (ab[1]+np.where(left_old,ab[0],-ab[0])>=0)
                        answers=np.stack([left_old,left_new,np.where(left_old,da,db),np.where(left_new,da,db)])
                        assert np.array_equal(preds[i],answers)
                        masks=[(panel,np.ones(len(a),bool))]
                        if panel=="ideal": masks.append(("ideal_in_domain",a+b<128))
                        for label,m in masks:
                            calc=dict(n=int(m.sum()),max_correct=int((m&(answers[2]==np.maximum(a,b))).sum()),
                                      min_correct=int((m&(answers[3]==np.minimum(a,b))).sum()),
                                      changed_old_answers=int((m&(answers[2]!=preds[0,2])).sum()),
                                      changed_old_tie_choices=int((m&(a==b)&(answers[0]!=preds[0,0])).sum()))
                            assert metrics[run][stage][label]==calc
                        if stage in ("min_000","restore_000") or arm=="frozen":
                            assert np.array_equal(answers[2],np.maximum(a,b))
                        replay_rows+=len(a)
    assert replay_updates==receipt["min_update_steps"]+receipt["recovery_update_steps"]
    return {"status":"PASS","verified_checkpoint_states":stored_states,
            "verified_panel_rows_with_both_predictions":replay_rows,"verified_answer_values":2*replay_rows,
            "exhaustive_copy_network_checks":32768,
            "replay_optimizer_updates_in_memory":replay_updates,"max_abs_weight_or_adam_delta":worst_param_delta,
            "prereg_sha256":prereg,"new_training_to_change_results":0}

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--results",type=Path,default=study.BASE/"results")
    print(json.dumps(replay(ap.parse_args().results),indent=2))
