"""Prospectively specified staged thaw of the MAX comparator during MIN acquisition."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
STATE_KEYS = ("comparator", "adapter", "c_m", "c_v", "ab_m", "ab_v", "c_step", "ab_step")


def load_core(location):
    paths = ([location] if location else []) + [HERE.parent, HERE.parent / "min_transfer_20261119"]
    directory = next((p for p in paths if (p / "study.py").is_file() and (p / "inherited").is_dir()), None)
    if directory is None:
        raise FileNotFoundError("Pass --core pointing to the main study.py and inherited directory")
    spec = importlib.util.spec_from_file_location("maxmin_core", directory / "study.py")
    core = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(core)
    return core


def fit(core, seed, train):
    np = core.np
    a, b, words = train
    batches, _ = core.schedules(seed, a, b)
    c, ab = core.initial(seed)
    oc, oa = core.Adam(15), core.Adam(2)
    trajectory = [core.snapshot(c, ab, oc, oa)]
    eligible = None
    for step, rows in enumerate(batches, 1):
        mode = "frozen" if eligible is None else "joint"
        core.train_step(c, ab, oc, oa, words[rows], a[rows] < b[rows], mode)
        trajectory.append(core.snapshot(c, ab, oc, oa))
        # +1 denotes previously choosing left, -1 choosing right. Ties choose left.
        if eligible is None and ab[0] + ab[1] < 0 and -ab[0] + ab[1] >= 0:
            eligible = step
    arrays = {name: np.array([s[i] for s in trajectory]) for i, name in enumerate(STATE_KEYS)}
    arrays["min_rows"] = batches
    return arrays, eligible


def evaluate(core, panels, state, out):
    np = core.np
    metrics = {}
    for name, triple in panels.items():
        panel = core.prepare_panel(triple)
        a, b = panel[:2]
        reference = core.answers(panel, state["comparator"][0], state["adapter"][0], "joint")
        predictions = []
        for step, (c, ab) in enumerate(zip(state["comparator"], state["adapter"])):
            pred = core.answers(panel, c, ab, "joint")
            predictions.append(pred)
            metrics.setdefault(name, []).append(core.counts(pred, a, b, reference))
            if name == "ideal":
                mask = a+b < 128
                metrics.setdefault("ideal_in_domain", []).append(core.counts(pred[:,mask], a[mask], b[mask], reference[:,mask]))
        # Pack the two decision bits for every step/row; the copy network output is fully
        # determined by these selections and its stored two-entry numeric lookup table.
        block = np.stack(predictions)
        rows = np.arange(len(a))
        assert all(np.array_equal(panel[3][block[:,k,:], rows], block[:,k+2,:]) for k in (0,1))
        np.savez_compressed(out / (name + ".npz"),
                            decisions=np.packbits(block[:,:2,:],axis=2,bitorder="little"),
                            copy_outputs=panel[3], truth_a=a.astype("u1"), truth_b=b.astype("u1"))
    return metrics


def summarize(core, metrics, eligible, state):
    np = core.np
    result = {}
    for name, stages in metrics.items():
        n = stages[0]["n"]
        first_max_min = next((i for i,q in enumerate(stages) if q["min_correct"]/n>=.95 and q["max_correct"]/n>=.95), None)
        minimum = min(q["max_correct"] for q in stages)
        result[name] = dict(n=n, simultaneous_first_95=first_max_min,
                            worst_old_correct=minimum, worst_old_first_step=next(i for i,q in enumerate(stages) if q["max_correct"]==minimum),
                            final=stages[-1])
    return {
        "gate_eligible_after_step":eligible,
        "first_comparator_update":None if eligible is None or eligible>=512 else eligible+1,
        "comparator_optimizer_updates":int(state["c_step"][-1]),
        "adapter_optimizer_updates":int(state["ab_step"][-1]),
        "end_adapter":state["adapter"][-1].tolist(),
        "comparator_max_abs_change_from_baseline":float(np.abs(state["comparator"][-1]-state["comparator"][0]).max()),
        "ranges_across_all_weights_steps":{
            k:[float(state[k].min()),float(state[k].max())] for k in ("comparator","adapter")
        },
        "panels":result
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--core",type=Path)
    parser.add_argument("--output",type=Path,default=HERE / "results")
    args = parser.parse_args()
    core = load_core(args.core)
    out = args.output
    out.mkdir(parents=True,exist_ok=False)
    start = time.perf_counter()
    batch_results, summary = {}, {}
    # Fit all seeds with no validation/intervention before scoring any holdout.
    for seed in core.SEEDS:
        dest = out / f"seed{seed}"
        dest.mkdir()
        panels = core.load_inputs(seed)
        state, eligible = fit(core, seed, panels["train"])
        core.np.savez_compressed(dest / "states.npz", **state)
        batch_results[seed] = (panels,state,eligible)
    for seed, (panels,state,eligible) in batch_results.items():
        dest = out / f"seed{seed}"
        metrics = evaluate(core, panels, state, dest)
        core.dump(dest/"metrics_by_step.json",metrics)
        summary[str(seed)] = summarize(core,metrics,eligible,state)
    core.dump(out / "summary.json", summary)
    core.dump(out / "run_receipt.json", {
        "prereg":"172ada5", "run":"pro_min_transfer_20261119_v1", "arm":"staged",
        "core_sha256":hashlib.sha256((core.BASE/"study.py").read_bytes()).hexdigest(),
        "train_steps":1536, "examples_seen":98304, "recovery_steps":0, "widths":[15,2],
        "adapter_steps":sum(x["adapter_optimizer_updates"] for x in summary.values()),
        "comparator_steps":sum(x["comparator_optimizer_updates"] for x in summary.values()),
        "eval_protocol":"Post-training every step 0..512, train/val/test/challenge/ideal, ideal in-domain subset a+b<128; sign tie selects left",
        "extra_parameters_over_MAX":2, "deployed_values":1370, "per_row_MAX_MAC":1304, "per_row_MIN_MAC":1305,
        "serialization":"states.npz contains all 513 snapshots plus identical sampled minibatches. Packed decision shape (513,2,ceil(N/8)), little bit order; choice 1 selects left. copy_outputs[choice,row] gives the emitted seven-bit integer, no truth substituted.",
        "elapsed_seconds":time.perf_counter()-start
    })

if __name__ == "__main__":
    main()
