"""Couple the independently fitted arithmetic and stride readouts during each live tick."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from arithmetic import student_step
from policy.stride import action, encode, test_sets


ROOT = Path(__file__).resolve().parent


def rollout(model, policy, width, tags_a, tags_b, a, b, record=False):
    """Variable-length actual rollout; for record=True store emitted rows plus STOP marks."""
    a, b, ta, tb = [np.atleast_1d(t).flatten() for t in np.broadcast_arrays(a, b, tags_a, tags_b)]
    pos = np.zeros(a.size, dtype=np.int16)
    partial = np.zeros(a.size, dtype=np.int64)
    carry = np.zeros_like(pos)
    rounds = np.zeros_like(pos)
    active = np.ones(a.size, dtype=bool)
    legal_stop = np.zeros_like(active)
    valid_prefix = np.ones_like(active)
    trace_rows = []
    for _ in range(width + 1):
        decision = action(policy, width - pos, encode(ta, tb, pos, width))
        move = np.where(active, decision, -1)
        stopped = active & (decision == 0)
        legal_stop |= stopped & (pos == width)
        old_pos = pos.copy()
        same_a = ((ta >> pos) & 1) == ((ta >> (pos + 1)) & 1)
        same_b = ((tb >> pos) & 1) == ((tb >> (pos + 1)) & 1)
        fine = active & (decision == 1) & (pos < width)
        wide = active & (decision == 2) & (pos + 2 <= width) & same_a & same_b
        for n, idx in ((1, fine), (2, wide)):
            if not idx.any():
                continue
            mask = (1 << n) - 1
            da, db = (a[idx] >> pos[idx]) & mask, (b[idx] >> pos[idx]) & mask
            digit, cout = student_step(model, n, da, db, carry[idx])
            partial[idx] |= digit.astype(np.int64) << pos[idx]
            carry[idx] = cout
            pos[idx] += n
        advance = fine | wide
        rounds += advance
        prefix_mask = (np.int64(1) << pos.astype(np.int64)) - 1
        reference = (a & prefix_mask) + (b & prefix_mask)
        valid_prefix &= (~advance) | ((carry == (reference >> pos)) & (partial == (reference & prefix_mask)))
        if record:
            trace_rows.append({"move": move.copy(), "from": old_pos,
                               "pos": pos.copy(), "partial": partial.copy(), "carry": carry.copy(),
                               "legal": (advance | (stopped & legal_stop)).copy()})
        active = advance
        if not active.any():
            break
    endpoint = (partial | (carry.astype(np.int64) << width)) == a + b
    return {"legal_stop": legal_stop, "complete": legal_stop & endpoint,
            "trace_complete": legal_stop & valid_prefix & endpoint,
            "cycles": rounds, "trace_rows": trace_rows}


def score(run, distance):
    trace_count = run["trace_complete"]
    values, numbers = np.unique(run["cycles"][trace_count], return_counts=True)
    return {"n": len(trace_count), "normal_stop": int(run["legal_stop"].sum()),
            "endpoint_and_stop": int(run["complete"].sum()), "all_rows_and_stop": int(trace_count.sum()),
            "all_rows_stop_and_minimal": int((trace_count & (run["cycles"] == distance)).sum()),
            "arithmetic_rounds_among_fully_correct":
                {str(v): int(n) for v, n in zip(values, numbers)}}


def signature(model, policy):
    arithmetic = [model['fine'], model['hardware'], model['weights']]
    return json.dumps([arithmetic, policy], separators=(',', ':'), sort_keys=True)


def evaluate(arith, policies):
    pairs = [(a, p) for a, p in zip(arith['trials'], policies['trials'], strict=True)]
    cell_options = (("linear_4", "4", "self_linear"), ("lut_4", "4", "self_lut"),
                    ("lut_64", "64", "self_lut"), ("linear_1", "1", "self_linear"))
    choices = {}
    cohorts = []
    for a_trial, p_trial in pairs:
        ids = {}
        for label, n, kind in cell_options:
            for arm in ("E", "EC", "I", "fixed_two"):
                cell, readout = a_trial["checkpoints"][n][kind], p_trial["models"][arm]
                key = signature(cell, readout)
                if key not in choices:
                    choices[key] = (len(choices), cell, readout)
                ids[label + "_" + arm] = choices[key][0]
        cohorts.append({"arithmetic_seed": a_trial['seed'], "policy_seed": p_trial['seed'],
                        "model_ids": ids})
    evaluations = {}
    examples = np.arange(65536, dtype=np.int64)
    dataset_names = []
    for ds, d in test_sets():
        dataset_names.append(ds)
        # Fully score every coupled checkpoint on flat operands, and every learned four-example
        # linear model/its control policies on the independent mixed-layout and width tests.
        primary = {i for row in cohorts for name, i in row["model_ids"].items()
                   if name.startswith("linear_4_")}
        evaluations[ds] = {}
        for ident, cell, readout in choices.values():
            if ds != "flat_8_operand_exhaustive" and ident not in primary:
                continue
            r = rollout(cell, readout, d.width, d.a_bank, d.b_bank, d.a, d.b)
            evaluations[ds][str(ident)] = score(r, d.optimum)
    cell = pairs[0][0]["checkpoints"]["4"]["self_linear"]
    readout = pairs[0][1]["models"]["EC"]
    probes = {}
    costs = {0:4, 2:5, 4:5}
    for ta in (0,2,4):
        run = rollout(cell, readout, 8, ta, 0, examples >> 8, examples & 255)
        probes[str(ta)] = score(run, costs[ta])
    samples = {}
    for a, b, ta, tb in ((255,1,0,0),(255,1,2,0),(255,1,4,0),(170,85,85,170)):
        run = rollout(cell, readout, 8, ta, tb, a, b, True)
        rows = [{k:int(v[0]) for k,v in row.items()} for row in run["trace_rows"]]
        samples[str((a,b,ta,tb))] = rows
    spec = {
        "order": "one separate terminal STOP decision after arithmetic rounds; illegal moves terminate immediately as failure.",
        "states": "cursor, partial low-bit sum and own carry. Scores check every actual row at its emitted cursor and final 9-bit (W+1) output.",
        "coupling": "Policy action uses current cursor, remaining and tags. A learned digit readout consumes only selected data columns and its own carry next to clock. No arithmetic oracle used for inference.",
        "mixed_layout_scope": "Enumerates all 65536 W8 tag pairs and 16384 W7 tag pairs with one deterministic operand pair/layout, not operand-layout Cartesian product. Other widths sampled. All operands crossed with three fixed W8 tag layouts independently on seed pair 0.",
        "teaching": "Arithmetic and policy trained separately. Paired by trial position for end-to-end inference, no joint end-to-end gradient training.",
    }
    return {"protocol": spec, "cohorts": cohorts, "scores": evaluations,
            "all_operands_at_three_W8_layouts_primary": probes, "example_actual_traces": samples}


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--arith", type=Path, default=ROOT / "arithmetic_results.json")
    p.add_argument("--policy", type=Path, default=ROOT / "policy/result.json")
    p.add_argument("--out", type=Path, default=ROOT / "joint_results.json")
    args = p.parse_args()
    output = evaluate(json.loads(args.arith.read_bytes()), json.loads(args.policy.read_bytes()))
    output["sources_sha256"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in (args.arith, args.policy)}
    args.out.write_text(json.dumps(output, separators=(",", ":"), sort_keys=True) + "\n")
