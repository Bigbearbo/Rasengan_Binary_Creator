"""AE1 evaluation wrapper around the pinned, unchanged P030 student.

Only raw Q plus the student's own generated bits enter autonomous inference.
Teacher metadata is used for scoring, never as an input feature.  The external
generation cap is fixed at 32 actions, including a model-generated STOP.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
from itertools import zip_longest

sys.dont_write_bytecode = True
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
import numpy as np

REFERENCE_PATH = Path(__file__).resolve().parent.parent / "20261112_p035/reference/p030_reference.py"
REFERENCE_SHA = "db39661a7b16d13e64db7acc5dae22a81ca59dc39cf467ed4c58addbc0654013"
L, H, GENERATION_CAP = 80, 64, 32
INFERENCE_COUNTER_KEYS = frozenset(("meta_inference_macs", "meta_inference_calls"))


def _canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False)


def load_reference():
    if hashlib.sha256(REFERENCE_PATH.read_bytes()).hexdigest() != REFERENCE_SHA:
        raise ValueError("Pinned P030 learner source differs")
    spec = importlib.util.spec_from_file_location("pro_ae1_frozen_p030", REFERENCE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load pinned P030 learner")
    result = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = result
    spec.loader.exec_module(result)
    return result


reference = load_reference()


def new_student(seed):
    """Fresh random P030 model; no old checkpoint or hand-written weights."""
    return reference.Model(seed, L=L, H=H)


def full_state(net):
    """Copy p/m/v/birth/t, shape, growth RNG, seed, counters and events."""
    return net.state() | {
        "meta_seed": np.array(net.seed),
        "meta_train_macs": np.array(net.train_macs),
        "meta_inference_macs": np.array(net.inference_macs),
        "meta_inference_calls": np.array(net.inference_calls),
        "meta_events": np.array(_canonical(net.events)),
    }


def state_sha(state):
    digest = hashlib.sha256()
    for name, value in sorted(state.items()):
        digest.update(_canonical([name, value.dtype.str, list(value.shape)]).encode())
        digest.update(value.tobytes(order="C"))
    return digest.hexdigest()


def save_state(path, net):
    """Write exclusively: an existing checkpoint is never overwritten."""
    with Path(path).open("xb") as stream:
        np.savez(stream, **full_state(net))


def load_state(path):
    with np.load(path, allow_pickle=False) as archive:
        saved = {name: archive[name].copy() for name in archive.files}
    if (int(saved["L"]), int(saved["H"])) != (L, H):
        raise ValueError("AE1 checkpoint must have the frozen L80/H64 shape")
    net = new_student(int(saved["meta_seed"]))
    if set(saved) != set(full_state(net)):
        raise ValueError("Checkpoint has missing or unexpected state fields")
    for label in ("p", "m", "v", "birth"):
        restored = []
        for i, expected in enumerate(getattr(net, label)):
            value = saved[f"{label}{i}"]
            if value.shape != expected.shape or value.dtype != expected.dtype:
                raise ValueError(f"Checkpoint shape/dtype mismatch: {label}{i}")
            restored.append(value.copy())
        setattr(net, label, restored)
    net.t = int(saved["t"])
    net.growth_rng.bit_generator.state = json.loads(str(saved["growth_rng"]))
    for label in ("train_macs", "inference_macs", "inference_calls"):
        setattr(net, label, int(saved["meta_" + label]))
    net.events = json.loads(str(saved["meta_events"]))
    if state_sha(saved) != state_sha(full_state(net)):
        raise RuntimeError("Checkpoint did not restore the exact full state")
    return net


def generate(net, q):
    """Fixed-cap free run; no parser, teacher answer, cursor or forced STOP."""
    tokens = ""
    for _ in range(GENERATION_CAP):
        prefix = q + tokens
        if len(prefix) > net.L:
            return {"tokens": tokens, "overflow": True, "cap_exhausted": False}
        logits = net.forward(prefix)[2]
        if not np.isfinite(logits).all():
            raise RuntimeError("Non-finite logits in autonomous generation")
        token = "01S"[int(logits.argmax())]
        tokens += token
        if token == "S":
            return {"tokens": tokens, "overflow": False, "cap_exhausted": False}
    return {"tokens": tokens, "overflow": False, "cap_exhausted": True}


def _learning_state_sha(net):
    # Inference accounting is intentionally allowed to increase. Everything
    # else, including training MAC, seed, events and RNG, must be unchanged.
    return state_sha({name: value for name, value in full_state(net).items()
                      if name not in INFERENCE_COUNTER_KEYS})


def evaluate(net, rows):
    """Compact free-run and teacher-prefix records; first_error is zero-based.

    free_info_total is all 5*r expected information bits. A missing output bit
    counts as wrong; the denominator is never shortened to the emitted prefix.
    Word-tail zeros and STOP are excluded only from the information-bit metric.
    tf_predictions includes STOP. Whole correctness includes every bit and STOP.
    """
    before = _learning_state_sha(net)
    output = []
    try:
        for row in rows:
            q, a = row["Q"], row["A"]
            n, r = row["N"], row["r"]
            if not (1 <= r <= n <= 4 and len(a) == 6 * r
                    and len(row["payload_ids"]) == n and set(a) <= {"0", "1"}):
                raise ValueError("Malformed frozen AE1 evaluation row")
            generation = generate(net, q)
            actual, expected = generation["tokens"], a + "S"
            tf_predictions, tf_losses = [], []
            for i, target in enumerate(expected):
                logits = net.forward(q + a[:i])[2].astype(np.float64)
                if not np.isfinite(logits).all():
                    raise RuntimeError("Non-finite logits in teacher-prefix evaluation")
                logp = logits - np.logaddexp.reduce(logits)
                tf_predictions.append("01S"[int(logits.argmax())])
                tf_losses.append(-float(logp["01S".index(target)]))
            tf_predictions = "".join(tf_predictions)
            information_positions = [i for i in range(len(a)) if i % 6 < 5]
            error = next((i for i, pair in enumerate(zip_longest(actual, expected))
                          if pair[0] != pair[1]), None)
            output.append({
                "id": row["id"], "N": n, "r": r, "split": row["split"],
                "payload_ids": list(row["payload_ids"]), "target": expected,
                "generated": actual, "whole_correct": actual == expected,
                "STOP_position_correct": actual.endswith("S") and len(actual) == len(expected),
                "early_STOP": actual.endswith("S") and len(actual) < len(expected),
                "late_STOP": actual.endswith("S") and len(actual) > len(expected),
                "no_STOP": not actual.endswith("S"),
                "first_error": error, "overflow": generation["overflow"],
                "cap_exhausted": generation["cap_exhausted"],
                "free_info_correct": sum(i < len(actual) and actual[i] == a[i]
                                         for i in information_positions),
                "free_info_total": len(information_positions),
                "tf_predictions": tf_predictions,
                "tf_correct": sum(pred == target for pred, target in zip(tf_predictions, expected)),
                "tf_targets": len(expected),
                "tf_info_correct": sum(tf_predictions[i] == a[i] for i in information_positions),
                "tf_info_total": len(information_positions),
                "tf_CE_mean": sum(tf_losses) / len(tf_losses),
                "END_at_expected_boundary": actual[len(a):len(a) + 6] == "111100",
            })
    finally:
        if _learning_state_sha(net) != before:
            raise RuntimeError("Evaluation changed learning state")
    return output


def _aggregate(rows):
    total = len(rows)
    result = {"total": total}
    for key in ("whole_correct", "STOP_position_correct", "early_STOP", "late_STOP", "no_STOP", "overflow",
                "cap_exhausted", "END_at_expected_boundary"):
        result[key] = sum(bool(row[key]) for row in rows)
    for key in ("free_info_correct", "free_info_total", "tf_correct", "tf_targets",
                "tf_info_correct", "tf_info_total"):
        result[key] = sum(row[key] for row in rows)
    result["tf_CE_mean"] = (
        sum(row["tf_CE_mean"] * row["tf_targets"] for row in rows) / result["tf_targets"]
        if result["tf_targets"] else None)
    return result


def _quartets(rows):
    groups = {}
    for row in rows:
        if row["N"] != 4:
            continue
        group = groups.setdefault(tuple(row["payload_ids"]), {})
        if row["r"] in group:
            raise ValueError("Duplicate N4 payload/r in evaluated rows")
        group[row["r"]] = row
    complete = [group for group in groups.values() if set(group) == {1, 2, 3, 4}]
    boundary_correct = 0
    boundary_quartets_correct = 0
    for group in complete:
        successes = []
        for r in (1, 2, 3):
            position = 6 * r
            # The two questions share the payload and correct answer prefix;
            # only count changes. These predictions were already recorded by TF.
            successes.append(group[r]["tf_predictions"][position] == "S"
                             and group[r + 1]["tf_predictions"][position]
                             == group[r + 1]["target"][position])
        boundary_correct += sum(successes)
        boundary_quartets_correct += int(all(successes))
    return {
        "payload_groups": len(groups), "complete_quartets": len(complete),
        "incomplete_payload_groups": len(groups) - len(complete),
        "whole_correct": sum(all(row["whole_correct"] for row in group.values())
                             for group in complete),
        "whole_total": len(complete),
        "STOP_quartet_correct": sum(all(row["STOP_position_correct"] for row in group.values())
                                    for group in complete),
        "STOP_quartet_total": len(complete),
        "TF_adjacent_count_boundary_correct": boundary_correct,
        "TF_adjacent_count_boundary_total": 3 * len(complete),
        "TF_all_three_boundaries_correct": boundary_quartets_correct,
        "TF_all_three_boundaries_total": len(complete),
    }


def metrics(evaluated_rows):
    """Explicit numerators/denominators, grouped by split and N/r.

    Question-level booleans use ``total`` as their denominator. Information-bit
    and teacher-target counts carry their own denominators. N4 quartet counts
    include only groups containing exactly r=1,2,3,4, within one split. The TF
    boundary metric is a conditional next-action diagnostic, not free-run success.
    """
    rows = list(evaluated_rows)
    result = {"overall": _aggregate(rows), "by_split": {}}
    for split in sorted({row["split"] for row in rows}):
        part = [row for row in rows if row["split"] == split]
        summary = _aggregate(part)
        summary["by_N"] = {
            str(n): _aggregate([row for row in part if row["N"] == n])
            for n in sorted({row["N"] for row in part})}
        summary["by_r"] = {
            str(r): _aggregate([row for row in part if row["r"] == r])
            for r in sorted({row["r"] for row in part})}
        summary["by_N_r"] = {
            f"{n}/{r}": _aggregate([row for row in part if (row["N"], row["r"]) == (n, r)])
            for n, r in sorted({(row["N"], row["r"]) for row in part})}
        summary["N4_quartets"] = _quartets(part)
        result["by_split"][split] = summary
    return result
