"""One fixed hand-weight construction, exhaustively tested without training."""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import sys
import time

if sys.flags.optimize:
    raise RuntimeError("Run without -O/-OO: all construction checks are required")
sys.dont_write_bytecode = True
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
PLAN = HERE / "construction_plan.json"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, value, *, compact=False):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True,
                  indent=None if compact else 2, separators=(",", ":") if compact else None,
                  allow_nan=False)
        stream.write("\n")


def reference(plan):
    path = REPO / plan["reference_path"]
    if sha(path) != plan["reference_sha256"]:
        raise ValueError("Historical P030 reference SHA mismatch")
    spec = importlib.util.spec_from_file_location("echo_construction_original_p030", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module, path


def install_fixed_weights(net, N, gain):
    """Set one global set of weights, independent of the evaluated question."""
    for array in net.p:
        array.fill(0)
    W, b, V, a = net.p
    for i in range(N):
        end_position = N + i
        for channel in (0, 1):
            W[2 * (end_position - 1) + channel, i] += gain
            W[2 * end_position + channel, i] -= gain
        W[2 * i + 1, i] += gain
        b[i] = -1.5 * gain
        V[i, 0] = -1
        V[i, 1] = 1
    for channel in (0, 1):
        W[2 * (2 * N - 1) + channel, N] += gain
        W[2 * (2 * N) + channel, N] -= gain
    b[N] = -0.5 * gain
    V[N, 2] = 2
    a[0], a[1] = -(N - 1), N - 1


def generate_via_original_forward(net, question, cap):
    """No expected output, source-bit lookup, cursor feature or forced STOP."""
    generated, trace = "", []
    for _ in range(cap):
        prefix = question + generated
        if len(prefix) > net.L:
            return generated, trace, True, False
        logits = net.forward(prefix)[2].copy()
        action = "01S"[int(logits.argmax())]
        trace.append({"prefix": prefix, "logits_01S": logits.tolist(), "action": action})
        generated += action
        if action == "S":
            return generated, trace, False, False
    return generated, trace, False, True


def run(output):
    output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    assert (plan["N"], plan["L"], plan["H"], plan["gain"], plan["generation_safety_cap"]) == (8, 80, 64, 10.0, 16)
    dump(output / "frozen-plan.json", plan)
    base = {"id": plan["id"], "author": plan["author"], "scope": plan["scope"],
            "plan_sha256": sha(PLAN), "construction_source_sha256": sha(__file__),
            "runtime": {"python": platform.python_version(), "numpy": np.__version__,
                        "OPENBLAS_NUM_THREADS": os.environ["OPENBLAS_NUM_THREADS"],
                        "OMP_NUM_THREADS": os.environ["OMP_NUM_THREADS"]},
            "construction_attempts": 1, "optimizer_updates": 0}
    rows, net = [], None
    try:
        original, source_path = reference(plan)
        source_before = sha(source_path)
        net = original.Model(plan["construction_seed"], L=plan["L"], H=plan["H"])
        install_fixed_weights(net, plan["N"], plan["gain"])
        fixed = net.state()
        with (output / "constructed-state.npz").open("xb") as stream:
            np.savez_compressed(stream, **fixed)
        assert net.t == 0 and net.train_macs == 0
        assert all(not np.any(a) for group in (net.m, net.v, net.birth) for a in group)
        inference_started = time.perf_counter()
        for value in range(256):
            question = format(value, "08b")
            generated, trace, overflow, exhausted = generate_via_original_forward(net, question, plan["generation_safety_cap"])
            # The expected string is used only after autonomous generation, for scoring.
            expected = question + "S"
            rows.append({"value": value, "Q": question, "expected_for_scoring": expected,
                         "generated": generated, "whole_correct": generated == expected,
                         "STOP_position_correct": generated.endswith("S") and len(generated) == 9,
                         "overflow": overflow, "cap_exhausted": exhausted, "steps": trace})
        inference_seconds = time.perf_counter() - inference_started
        unchanged = original.equal_state(fixed, net.state())
        assert unchanged and net.t == 0 and net.train_macs == 0
        assert sha(source_path) == source_before
        correct = sum(row["whole_correct"] for row in rows)
        margins = [max(step["logits_01S"]) - sorted(step["logits_01S"])[-2]
                   for row in rows for step in row["steps"]]
        result = base | {"status": "PASS" if correct == 256 else "FAIL", "cases": len(rows),
                         "whole_correct": correct,
                         "correct_STOP_position": sum(row["STOP_position_correct"] for row in rows),
                         "overflow": sum(row["overflow"] for row in rows),
                         "cap_exhausted": sum(row["cap_exhausted"] for row in rows),
                         "L": net.L, "H": net.H, "physical_parameters": net.parameters,
                         "active_hidden_units": 9, "nonzero_parameters": sum(int(np.count_nonzero(a)) for a in net.p),
                         "p_m_v_birth_array_bytes": sum(a.nbytes for group in (net.p, net.m, net.v, net.birth) for a in group),
                         "parameters_optimizer_birth_t_RNG_unchanged_during_evaluation": unchanged,
                         "historical_source_unchanged": True, "reference_sha256": source_before,
                         "inference_calls": net.inference_calls, "forward_dense_MAC": net.inference_macs,
                         "training_dense_MAC": net.train_macs, "minimum_argmax_margin": min(margins),
                         "maximum_actual_visible_prefix_bits": max(len(step["prefix"]) for row in rows for step in row["steps"]),
                         "inference_seconds": inference_seconds,
                         "forward_cost_scope": "Original dense matrix MAC counter; excludes nonlinearity, feature construction, I/O and full process costs"}
        assert net.inference_calls == sum(len(row["steps"]) for row in rows)
    except Exception as error:
        result = base | {"status": "TECHNICAL_FAILURE", "completed_cases": len(rows),
                         "error_type": type(error).__name__, "error": str(error),
                         "inference_calls": None if net is None else net.inference_calls}
    dump(output / "truth.json", rows, compact=True)
    result["truth_sha256"] = sha(output / "truth.json")
    result["total_seconds_through_truth_write"] = time.perf_counter() - started
    dump(output / "summary.json", result)
    print(json.dumps(result, sort_keys=True))
    return result["status"] == "PASS"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(0 if run(args.out) else 1)


if __name__ == "__main__":
    main()
