"""Paired first-error remediation on terminal-supervised recurrent hard threshold gates."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np


STUDY_SEEDS = np.arange(20261201, 20261265)
PREVIOUS_SHA = "94bdd0334a2232232aaed41ee025eb8fe31d4b0ecb3607dcdcbddbf4afb1a9bd"
HERE = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_previous(path):
    if digest(path) != PREVIOUS_SHA:
        raise ValueError("Unexpected preceding study implementation")
    spec = importlib.util.spec_from_file_location("previous_ste_study", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def forward(w, a, b, gold):
    q = np.zeros(gold.shape[1:], dtype=np.float64)
    trace, features = [], []
    for ai, bi in zip(a, b):
        features.append(np.stack([ai, bi, q, np.ones_like(q)], axis=-1))
        z = w[:, 0, None]*ai + w[:, 1, None]*bi + w[:, 2, None]*q + w[:, 3, None]
        q = (z >= 0).astype(np.float64)
        trace.append(q)
    return np.array(trace), features


def coupled_update(w, a, b, gold, rule, generators):
    trace, features = forward(w, a, b, gold)
    n_students, n_cases = trace.shape[1:]
    wrong = trace[-1] != gold[-1]
    pick = np.full((n_students, n_cases), 7, dtype=int)
    if rule == "first":
        pick[wrong] = np.argmax(trace != gold, axis=0)[wrong]
    if rule == "random":
        draws = np.stack([rng.integers(0, 8, n_cases) for rng in generators])
        pick[wrong] = draws[wrong]
    error_at = trace-gold
    adjoint = np.zeros_like(trace[-1])
    grad = np.zeros_like(w)
    for k in reversed(range(8)):
        adjoint += (pick == k)*error_at[k]
        grad += np.mean(adjoint[:, :, None]*features[k], axis=1)
        adjoint *= w[:, 2, None]
    selected = wrong if rule != "endpoint" else np.zeros_like(wrong)
    hints = np.stack([np.sum((pick == k) & selected, axis=1) for k in range(8)], axis=1)
    informative = selected & (np.take_along_axis(error_at, pick[None], axis=0)[0] != 0)
    return grad, hints, np.sum(informative, axis=1)


def update_endpoint(previous, weights, a, b, gold, total):
    n_changes = np.zeros(len(weights), dtype=int)
    for _ in range(total):
        grad, _ = previous.gradient(weights, a, b, gold[-1], "straight")
        next_w = weights-0.25*grad
        n_changes += np.any(next_w != weights, axis=1)
        weights = next_w
    return weights, n_changes


def run(previous_path, adder_path):
    previous = load_previous(previous_path)
    full_a, full_b, full_truth, original = previous.snapshots(adder_path)
    ids = np.stack([np.random.default_rng(int(s)).choice(65536,64,replace=False) for s in STUDY_SEEDS])
    a, b = full_a[:,ids], full_b[:,ids]
    gold = full_truth[:,ids].astype(np.float64)
    cache = {}
    def checkpoints(weights, case_ids):
        rows = []
        for w, training in zip(weights, case_ids, strict=True):
            code = previous.signature(w)
            if code not in cache:
                trace = previous.traces(code, full_a, full_b)
                cache[code] = (trace[-1], previous.scores(trace, full_truth))
            predicted, stats = cache[code]
            train_fit = int((predicted[training] == full_truth[-1,training]).sum())
            rows.append({"weights": w.tolist(), "truth_table_code": code,
                         "training_endpoints_correct": train_fit, **stats})
        return rows

    weights, base_changes = update_endpoint(previous, np.zeros((64,4)), a, b, gold, 256)
    starting = checkpoints(weights, ids)
    stuck = np.array([row["training_endpoints_correct"] != 64 for row in starting])
    result = {"numpy":np.__version__, "source_sha256":digest(adder_path), "prior_study_sha256":digest(previous_path),
              "preregistered":digest(HERE/"protocol.md"), "script_sha256":digest(Path(__file__)), "original_regression":original,
              "starting_seeds":STUDY_SEEDS.tolist(), "training_ids":ids.tolist(),
              "student_cell":{"trainable_weights":4,"extra_units":1,"extra_work_bits":1,"extra_dense_forward_MACs_per_paper":24,"bias_additions_per_paper":8},
              "supervision":"terminal only except during 32-step comparator arms; own feedback at all times",
              "initial":{str(seed):dict(changed_updates=int(n),**row) for seed,n,row in zip(STUDY_SEEDS,base_changes,starting)},
              "stuck_seeds":STUDY_SEEDS[stuck].tolist(),"results":{}}
    for name, subset, rule in (("already_fit", ~stuck, "endpoint"),("endpoint",stuck,"endpoint"),
                                ("first",stuck,"first"), ("random",stuck,"random")):
        seq = STUDY_SEEDS[subset]
        case_ids = ids[subset]
        aa,bb,gg = a[:,subset], b[:,subset], gold[:,subset]
        w = weights[subset].copy()
        if len(seq) == 0:
            result["results"][name]={}
            continue
        grad_previous = previous.gradient(w,aa,bb,gg[-1],"straight")[0]
        grad_local = coupled_update(w,aa,bb,gg,"endpoint",[])[0]
        np.testing.assert_allclose(grad_local,grad_previous,rtol=1e-12,atol=1e-12)
        hint_counts = np.zeros((len(seq),8),dtype=int)
        informative = np.zeros(len(seq),dtype=int)
        changed = np.zeros(len(seq),dtype=int)
        rngs = [np.random.default_rng(int(s)+1000000) for s in seq]
        for _ in range(32):
            gradient, new_hints, useful = coupled_update(w,aa,bb,gg,rule,rngs)
            next_w = w - .25*gradient
            changed += np.any(next_w != w,axis=1)
            w = next_w
            hint_counts += new_hints
            informative += useful
        middle = checkpoints(w, case_ids)
        w, final_changes = update_endpoint(previous,w,aa,bb,gg,64)
        final = checkpoints(w,case_ids)
        result["results"][name] = {
            str(s):{"step288":m,"step352":f,"changed_updates_256_to_288":int(ch),
                    "changed_updates_288_to_352":int(fc),"chosen_hints_by_step":hc.tolist(),
                    "chosen_hints_total":int(hc.sum()),"chosen_intermediate":int(hc[:7].sum()),
                    "chosen_hints_wrong_at_target":int(hit),"presented_targets_32steps":32*64,
                    "presented_targets_final64":64*64}
            for s,m,f,ch,fc,hc,hit in zip(seq,middle,final,changed,final_changes,hint_counts,informative,strict=True)}
    def summary(rows):
        return {"students":len(rows),"terminal_perfect":sum(x["endpoint_correct"]==65536 for x in rows),
                "trace_perfect":sum(x["sequence_correct"]==65536 for x in rows),
                "trace_95":sum(x["sequence_correct"]*100>=65536*95 for x in rows),
                "terminal_95":sum(x["endpoint_correct"]*100>=65536*95 for x in rows),
                "training_fit":sum(x["training_endpoints_correct"]==64 for x in rows)}
    result["summary"]={"initial":summary(starting)}
    for name,rows in result["results"].items():
        result["summary"][name]={point:summary([r[point] for r in rows.values()]) for point in ("step288","step352")}
        result["summary"][name].update({k:sum(r[k] for r in rows.values()) for k in ("chosen_hints_total","chosen_intermediate","chosen_hints_wrong_at_target")})
    return result

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("previous",type=Path)
    p.add_argument("adder",type=Path)
    p.add_argument("--output",type=Path,default=HERE/"results.json")
    args=p.parse_args()
    report=run(args.previous,args.adder)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n", encoding="utf-8")
    print(json.dumps(report["summary"],indent=2))
