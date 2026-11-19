"""Preregistered MAX -> MIN transfer. Fit on original PR133 training pairs and score from frozen receivers."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import time

# Make small matrix operations consistent across machines.
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"
import numpy as np

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE / "inherited"))
import hybrid_model as prior

SEEDS = (101, 202, 303)
ARMS = ("frozen", "joint", "overwrite")
PANELS = ("train", "val", "test", "challenge", "ideal")
MIN_STEPS = (0, 1, 4, 16, 32, 64, 128, 256, 512)
MAX_STEPS = (1, 4, 16, 32, 64, 128)
BITS = prior.BIT_WEIGHTS
LR = .02


def dump(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def bitwords(a, b):
    return np.column_stack([((v[:, None] >> np.arange(6, -1, -1)) & 1) for v in (a,b)]).astype(np.uint8)


def load_inputs(seed):
    parent = BASE / "inherited"
    source = prior.load_source(seed)
    data = json.loads((parent / "data.json").read_text())
    cache = json.loads((parent / "pr133_cache_hashes.json").read_text())[str(seed)]
    panels = {}
    for name in PANELS[:-1]:
        rows = data["panels"][name]
        raw = np.array([list(map(int, r["frame_bits"])) for r in rows], dtype=np.uint8)
        decoded = prior.decode(source, raw)
        ids = np.asarray([r["case_id"] for r in rows])
        for key, arr in (("words",decoded["words"]),("pred_op",decoded["pred_op"]),("case_ids",ids)):
            assert hashlib.sha256(arr.tobytes()).hexdigest() == cache[name][key]
        a, b, opcode = [np.array([r[k] for r in rows], dtype=int) for k in ("a","b","op")]
        panels[name] = (a, b, decoded["words"])
        assert np.array_equal(decoded["pred_op"], opcode)
        assert max(a+b) < 128
    pairs = {k: set(zip(np.minimum(v[0],v[1]),np.maximum(v[0],v[1]))) for k,v in panels.items()}
    assert all(pairs[k].isdisjoint(pairs[q]) for i,k in enumerate(pairs) for q in list(pairs)[i+1:])
    a, b = np.repeat(np.arange(128),128), np.tile(np.arange(128),128)
    panels["ideal"] = (a, b, bitwords(a,b))
    return panels


def initial(seed):
    p = BASE / "inherited/results/handfilled_frozen" / f"seed{seed}/checkpoints/step_0000.npz"
    with np.load(p, allow_pickle=False) as z:
        comparator = np.r_[z["param_w"], z["param_b"]]/64
    return comparator, np.array([1.,0.], dtype=float)


def schedules(seed, a, b):
    unequal = np.flatnonzero(a != b)
    rng = np.random.default_rng(3100000+seed)
    return (rng.choice(unequal, size=(512,64)), rng.choice(unequal,size=(128,64)))


class Adam:
    def __init__(self, count):
        self.m = np.zeros(count)
        self.v = np.zeros(count)
        self.t = 0

    def update(self, weights, gradient):
        self.t += 1
        self.m += .1*(gradient-self.m)
        self.v += .001*(gradient**2-self.v)
        weights -= LR*(self.m/(1-.9**self.t))/(np.sqrt(self.v/(1-.999**self.t))+1e-8)


def train_step(c, ab, opt_c, opt_ab, words, labels, mode):
    """mode=frozen or joint for adapter MIN. mode=direct for comparator BCE (MIN overwrite or MAX recovery)."""
    logits = words @ c[:-1] + c[-1]
    sign = np.where(logits >= 0, 1., -1.)
    if mode == "direct":
        error = (np.exp(-np.logaddexp(0, -logits)) - labels) / len(labels)
    else:
        z = ab[0]*sign + ab[1]
        error = (np.exp(-np.logaddexp(0,-z)) - labels) / len(labels)
        dz_dc = ab[0]*4/(1+np.abs(4*logits))**2
        opt_ab.update(ab, np.array([error @ sign, error.sum()]))
        error = error*dz_dc
    if mode in ("joint","direct"):
        opt_c.update(c, np.r_[words.T @ error, error.sum()])


def snapshot(c, ab, oc, oa):
    return (c.copy(), ab.copy(), oc.m.copy(), oc.v.copy(), oa.m.copy(), oa.v.copy(), oc.t, oa.t)


def fit(arm, seed, train, batches):
    a,b,words = train
    c, ab = initial(seed)
    oc, oa = Adam(15), Adam(2)
    records = {"min_000":snapshot(c,ab,oc,oa)}
    for t, rows in enumerate(batches[0],1):
        train_step(c,ab,oc,oa,words[rows],(a[rows] < b[rows]), "direct" if arm=="overwrite" else arm)
        if t in MIN_STEPS:
            records[f"min_{t:03}"] = snapshot(c,ab,oc,oa)
    records["restore_000"] = snapshot(initial(seed)[0], ab, oc, oa)
    oc = Adam(15)
    for t, rows in enumerate(batches[1],1):
        if arm != "frozen":
            train_step(c,ab,oc,oa,words[rows],(a[rows] > b[rows]), "direct")
        if t in MAX_STEPS:
            records[f"max_{t:03}"] = snapshot(c,ab,oc,oa)
    return records


def prepare_panel(triple):
    a,b,words = triple
    mux = prior.load_mux()
    rows = np.arange(len(a))
    # Tabulate both actual threshold-network paths once on the actual decoded words.
    # At scoring time select the corresponding neural output. No truth enters this lookup.
    table = np.stack([prior.mux_forward(mux, words, np.full(len(words),k,dtype=np.uint8))["output_bits"] @ BITS
                      for k in (0,1)]).astype(np.uint8)
    return a,b,words,table,rows


def answers(panel, c, ab, arm):
    a,b,words,table,rows = panel
    old = (words @ c[:-1]+c[-1] >= 0).astype(np.uint8)
    u = np.where(old, 1.,-1.)
    new = old if arm == "overwrite" else (ab[0]*u+ab[1]>=0).astype(np.uint8)
    return np.stack([old, new, table[old,rows], table[new,rows]])


def counts(pred, a, b, baseline):
    return {
        "n":len(a), "max_correct":int((pred[2] == np.maximum(a,b)).sum()),
        "min_correct":int((pred[3] == np.minimum(a,b)).sum()),
        "changed_old_answers":int((pred[2] != baseline[2]).sum()),
        "changed_old_tie_choices":int(((a == b) & (pred[0] != baseline[0])).sum())
    }


def run(out):
    t0 = time.perf_counter()
    out.mkdir(parents=True,exist_ok=False)
    records = {}
    sources = {}
    for seed in SEEDS:
        panels = load_inputs(seed)
        a,b,words = panels["train"]
        schedules_min_max = schedules(seed,a,b)
        np.savez_compressed(out/f"batches_{seed}.npz", min_rows=schedules_min_max[0], max_rows=schedules_min_max[1])
        sources[str(seed)] = {name:{"n":len(a),"correct_operand_pairs":int((bitwords(a,b)==words).all(axis=1).sum())}
                              for name,(a,b,words) in panels.items() if name!="ideal"}
        prepared = {k:prepare_panel(v) for k,v in panels.items()}
        for arm in ARMS:
            run_name = f"{arm}_{seed}"
            run_dir = out / run_name
            run_dir.mkdir()
            checkpoints = fit(arm,seed,panels["train"],schedules_min_max)
            names = list(checkpoints)
            state_arrays = {k:np.array([v[j] for v in checkpoints.values()]) for j,k in
                            enumerate(("comparator","adapter","c_m","c_v","ab_m","ab_v","c_step","ab_step"))}
            np.savez_compressed(run_dir/"states.npz", stages=names, **state_arrays)
            records[run_name] = {k:{} for k in names}
            for panel_name, panel in prepared.items():
                a,b = panel[:2]
                baseline = answers(panel,*initial(seed),arm)
                predictions = []
                for stage, state in checkpoints.items():
                    pred = answers(panel, *state[:2], arm)
                    predictions.append(pred)
                    metrics = records[run_name][stage]
                    metrics[panel_name] = counts(pred,a,b,baseline)
                    if panel_name == "ideal":
                        mask = a+b<128
                        metrics["ideal_in_domain"] = counts(pred[:,mask], a[mask], b[mask], baseline[:,mask])
                np.savez_compressed(run_dir/(panel_name+".npz"), stages=names, predictions=np.stack(predictions))
    dump(out/"metrics.json", records)
    dump(out/"run_receipt.json", {
        "run":"pro_min_transfer_20261119_v1",
        "prereg_git":"e9ee14f24031265f154890fdbf4e00a002b208de",
        "pr133_archive_sha256":"c33c180362cec0e968fa704f3cf2dd55fbff5c36e348ad8e755b201c347cbed2",
        "source":sources, "numpy":np.__version__,"python":platform.python_version(),
        "min_update_steps":3*3*512,"recovery_update_steps":2*3*128,
        "min_presentations":3*3*512*64,"recovery_update_presentations":2*3*128*64,
        "each_receiver_inherited_updates":5120,
        "receiver_forward_rows":3*sum(v["n"] for v in sources["101"].values()),
        "receiver_values":1290,"comparator_values":15,"copy_values":63,
        "expanded_additional_values":2,"expanded_total_values":1370,
        "per_row_MAC_old":1304,"per_row_MAC_new_expanded":1305,"per_row_MAC_direct":1304,
        "assumptions":"One MAC per weighted edge; signs, bias, external task switch excluded. Direct has two placeholder identity numbers in state serialization, never invoked or optimized. restore_000 is a weights-only intervention; old optimizer state there is for provenance only. Max recovery resets comparator optimizer. Frozen received no old updates. Numeric outputs preserve all seven bits losslessly (unsigned integer).",
        "elapsed_s":time.perf_counter()-t0
    })


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=BASE/"results")
    run(parser.parse_args().output)
