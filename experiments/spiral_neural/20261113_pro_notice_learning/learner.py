"""Original P030 learner; only generation is driven by an external fixed cap."""
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
from dataset import canonical, file_sha

REFERENCE_PATH = Path(__file__).resolve().parent.parent / "20261112_p035/reference/p030_reference.py"
REFERENCE_SHA = "db39661a7b16d13e64db7acc5dae22a81ca59dc39cf467ed4c58addbc0654013"
L, H, GENERATION_CAP = 80, 64, 24


def load_reference():
    if file_sha(REFERENCE_PATH) != REFERENCE_SHA:
        raise ValueError("Pinned P030 learner source differs")
    spec = importlib.util.spec_from_file_location("pro_notice_frozen_p030", REFERENCE_PATH)
    result = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = result
    spec.loader.exec_module(result)
    return result


reference = load_reference()


def new_student(seed):
    return reference.Model(seed, L=L, H=H)


def full_state(net):
    return net.state() | {"meta_seed": np.array(net.seed),
                          "meta_train_macs": np.array(net.train_macs),
                          "meta_inference_macs": np.array(net.inference_macs),
                          "meta_inference_calls": np.array(net.inference_calls),
                          "meta_events": np.array(canonical(net.events))}


def state_sha(state):
    digest = hashlib.sha256()
    for name, value in sorted(state.items()):
        digest.update(canonical([name, value.dtype.str, list(value.shape)]).encode())
        digest.update(value.tobytes(order="C"))
    return digest.hexdigest()


def save_state(path, net):
    with Path(path).open("xb") as stream:
        np.savez(stream, **full_state(net))


def load_state(path):
    with np.load(path, allow_pickle=False) as archive:
        saved = {name: archive[name].copy() for name in archive.files}
    net = new_student(int(saved["meta_seed"]))
    assert (int(saved["L"]), int(saved["H"])) == (L, H)
    for label in ("p", "m", "v", "birth"):
        setattr(net, label, [saved[f"{label}{i}"].copy() for i in range(4)])
    net.t = int(saved["t"])
    net.growth_rng.bit_generator.state = json.loads(str(saved["growth_rng"]))
    for label in ("train_macs", "inference_macs", "inference_calls"):
        setattr(net, label, int(saved["meta_" + label]))
    net.events = json.loads(str(saved["meta_events"]))
    assert reference.equal_state(saved, full_state(net))
    return net


def generate(net, q, cap=GENERATION_CAP):
    """No parser, output-length oracle, forced STOP, or hidden task features."""
    tokens, details = "", []
    for _ in range(cap):
        prefix = q + tokens
        if len(prefix) > net.L:
            return {"tokens": tokens, "overflow": True, "cap_exhausted": False, "steps": details}
        logits = net.forward(prefix)[2].copy()
        token = "01S"[int(logits.argmax())]
        details.append({"prefix": prefix, "prediction": token, "logits": logits.tolist()})
        tokens += token
        if token == "S":
            return {"tokens": tokens, "overflow": False, "cap_exhausted": False, "steps": details}
    return {"tokens": tokens, "overflow": False, "cap_exhausted": True, "steps": details}


def evaluate(net, rows):
    before = net.state()
    output = []
    for row in rows:
        q, a = row["Q"], row["A"]
        generation = generate(net, q)
        actual, expected = generation["tokens"], a + "S"
        tf = []
        for i, target in enumerate(expected):
            logits = net.forward(q + a[:i])[2].astype(np.float64)
            logp = logits - np.logaddexp.reduce(logits)
            tf.append({"position": i, "target": target,
                       "prediction": "01S"[int(logits.argmax())], "logits": logits.tolist(),
                       "probabilities_01S": np.exp(logp).tolist(),
                       "target_CE": -float(logp["01S".index(target)])})
        address_length = len(row["address_bits"])
        error = next((i for i, pair in enumerate(zip_longest(actual, expected))
                      if pair[0] != pair[1]), None)
        output.append({"id": row["id"], "split": row["split"], "path": row["path"],
                       "target_n": row["target_n"], "Q": q, "target": expected,
                       "generated": actual, "whole_correct": actual == expected,
                       "address_correct": actual[:address_length] == row["address_bits"],
                       "UP_correct_at_expected_position": actual[address_length:len(a)] == row["up_bits"],
                       "STOP_position_correct": actual.endswith("S") and len(actual) == len(expected),
                       "first_error_position_zero_based": error,
                       "overflow": generation["overflow"], "cap_exhausted": generation["cap_exhausted"],
                       "teacher_forcing": tf, "free_run": generation["steps"]})
    assert reference.equal_state(before, net.state()), "Evaluation changed learning state"
    return output


def metrics(rows):
    result = {}
    for split in ("train", "heldout"):
        part = [row for row in rows if row["split"] == split]
        if not part:
            continue
        tf = [token for row in part for token in row["teacher_forcing"]]
        result[split] = {"total": len(part),
                        **{key: sum(bool(row[key]) for row in part) for key in
                           ("whole_correct", "address_correct", "UP_correct_at_expected_position",
                            "STOP_position_correct", "overflow", "cap_exhausted")},
                        "teacher_targets": len(tf),
                        "teacher_correct": sum(t["prediction"] == t["target"] for t in tf),
                        "teacher_CE_mean": sum(t["target_CE"] for t in tf) / len(tf)}
    return result
