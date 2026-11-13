"""Bounded CPU controls: original string NumPy, preencoded NumPy and Numba whole-loop."""
from __future__ import annotations
import os
import sys
import time
_START = time.perf_counter()
sys.dont_write_bytecode = True
import hashlib
import json
import math
from pathlib import Path
import platform
import statistics
import traceback
import bench_common as c
import numpy as np

c.WORK.mkdir(parents=True, exist_ok=True)
os.environ["NUMBA_CACHE_DIR"] = str(c.WORK / "numba-cache")
Path(os.environ["NUMBA_CACHE_DIR"]).mkdir(parents=True, exist_ok=True)
_numba_import = time.perf_counter()
from numba import njit
import numba
NUMBA_IMPORT_SECONDS = time.perf_counter() - _numba_import
BACKENDS = ("original_NumPy_string_CPU", "preencoded_NumPy_CPU", "Numba_njit_CPU_fastmath_false")


def numpy_step(state, x, label):
    x = x.reshape(1, 160)
    h = np.tanh(x @ state["p0"] + state["p1"])
    z = (h @ state["p2"] + state["p3"])[0]
    zz = z.astype(np.float64)
    lp = zz - np.logaddexp.reduce(zz)
    probability = np.exp(lp)
    d = probability.copy()
    d[label] -= 1
    d = d.astype(h.dtype)[None, :]
    dz = (d @ state["p2"].T) * (1 - h * h)
    gradients = [x.T @ dz, dz[0], h.T @ d, d[0]]
    norm = np.sqrt(sum(float((gradient * gradient).sum()) for gradient in gradients))
    scale = min(1., 1 / max(norm, 1e-12))
    state["t"] = np.array(int(state["t"]) + 1, dtype=np.int64)
    for i, gradient in enumerate(gradients):
        gradient *= scale
        state[f"m{i}"] = .9 * state[f"m{i}"] + .1 * gradient
        state[f"v{i}"] = .999 * state[f"v{i}"] + .001 * gradient * gradient
        age = int(state["t"]) - state[f"birth{i}"]
        state[f"p{i}"] -= .003 * (state[f"m{i}"] / (1 - np.power(.9, age))) / (np.sqrt(state[f"v{i}"] / (1 - np.power(.999, age))) + 1e-8)
    return -float(lp[label]), int(z.argmax()), z.copy()


def numpy_run(state, fixture, steps, collect=False):
    logits = np.empty((steps if collect else 0, 3), np.float32)
    losses = np.empty(steps if collect else 0, np.float64)
    predictions = np.empty(steps if collect else 0, np.int64)
    loss_sum, prediction_sum = 0., 0
    for index in range(steps):
        at = index % 32
        loss, pred, z = numpy_step(state, fixture["X"][at], int(fixture["labels"][at]))
        loss_sum += loss
        prediction_sum += pred
        if collect:
            logits[index], losses[index], predictions[index] = z, loss, pred
    return {"logits": logits, "losses": losses, "predictions": predictions}, {"loss_sum": loss_sum, "prediction_sum": prediction_sum}


@njit(cache=True, fastmath=False)
def _adam_update(p, m, v, birth, gradient, t, scale):
    for index in range(p.size):
        # Original clipped gradient is cast back to f32 before both moments.
        g = np.float32(np.float64(gradient.flat[index]) * np.float64(scale))
        mm = np.float32(np.float32(np.float32(.9) * m.flat[index]) + np.float32(np.float32(.1) * g))
        vv_term = np.float32(np.float32(.001) * g)
        vv_term = np.float32(vv_term * g)
        vv = np.float32(np.float32(np.float32(.999) * v.flat[index]) + vv_term)
        m.flat[index], v.flat[index] = mm, vv
        age = np.float64(t - birth.flat[index])
        # DO NOT promote weak-float moment multiplications to f64, or narrow powers.
        bm = np.float64(1.) - math.pow(np.float64(.9), age)
        bv = np.float64(1.) - math.pow(np.float64(.999), age)
        update = (np.float64(.003) * (np.float64(mm) / bm)) / (math.sqrt(np.float64(vv) / bv) + np.float64(1e-8))
        p.flat[index] = np.float32(np.float64(p.flat[index]) - update)


@njit(cache=True, fastmath=False)
def _numba_kernel(p0, p1, p2, p3, m0, m1, m2, m3, v0, v1, v2, v3,
                  b0, b1, b2, b3, clock, X, labels, steps, collect):
    t = clock[()]
    logits = np.empty((steps if collect else 0, 3), np.float32)
    losses = np.empty(steps if collect else 0, np.float64)
    predictions = np.empty(steps if collect else 0, np.int64)
    h, z, d, dz = np.empty(64, np.float32), np.empty(3, np.float32), np.empty(3, np.float32), np.empty(64, np.float32)
    g0, g2 = np.empty((160, 64), np.float32), np.empty((64, 3), np.float32)
    loss_sum, prediction_sum = np.float64(0.), 0
    for iteration in range(steps):
        at = iteration % 32
        # Dense f32 sums, no SciPy/BLAS hidden dependency or fastmath reassociation.
        for j in range(64):
            value = np.float32(0.)
            for i in range(160):
                value = np.float32(value + np.float32(X[at, i] * p0[i, j]))
            h[j] = np.float32(np.tanh(np.float32(value + p1[j])))
        for k in range(3):
            value = np.float32(0.)
            for j in range(64):
                value = np.float32(value + np.float32(h[j] * p2[j, k]))
            z[k] = np.float32(value + p3[k])
        a, b = np.float64(z[0]), np.float64(z[1])
        lse = max(a, b) + math.log1p(math.exp(-abs(a - b)))
        b = np.float64(z[2])
        lse = max(lse, b) + math.log1p(math.exp(-abs(lse - b)))
        label = labels[at]
        loss = -(np.float64(z[label]) - lse)
        pred = 0
        for k in range(1, 3):
            if z[k] > z[pred]:
                pred = k
        for k in range(3):
            probability = math.exp(np.float64(z[k]) - lse)
            d[k] = np.float32(probability - (np.float64(1.) if k == label else np.float64(0.)))
        for j in range(64):
            value = np.float32(0.)
            for k in range(3):
                value = np.float32(value + np.float32(d[k] * p2[j, k]))
            dz[j] = np.float32(value * np.float32(np.float32(1.) - np.float32(h[j] * h[j])))
        norm0, norm1, norm2, norm3 = np.float32(0.), np.float32(0.), np.float32(0.), np.float32(0.)
        for i in range(160):
            for j in range(64):
                value = np.float32(X[at, i] * dz[j])
                g0[i, j] = value
                norm0 = np.float32(norm0 + np.float32(value * value))
        for j in range(64):
            norm1 = np.float32(norm1 + np.float32(dz[j] * dz[j]))
            for k in range(3):
                value = np.float32(h[j] * d[k])
                g2[j, k] = value
                norm2 = np.float32(norm2 + np.float32(value * value))
        for k in range(3):
            norm3 = np.float32(norm3 + np.float32(d[k] * d[k]))
        norm = math.sqrt(np.float64(norm0) + np.float64(norm1) + np.float64(norm2) + np.float64(norm3))
        scale = np.float64(1.) if norm <= 1. else np.float64(1.) / norm
        t += 1
        clock[()] = t  # Durable in-memory accounting, including a failed native call.
        _adam_update(p0, m0, v0, b0, g0, t, scale)
        _adam_update(p1, m1, v1, b1, dz, t, scale)
        _adam_update(p2, m2, v2, b2, g2, t, scale)
        _adam_update(p3, m3, v3, b3, d, t, scale)
        loss_sum += loss
        prediction_sum += pred
        if collect:
            for k in range(3):
                logits[iteration, k] = z[k]
            losses[iteration], predictions[iteration] = loss, pred
    return t, logits, losses, predictions, loss_sum, prediction_sum


def numba_run(state, fixture, steps, collect=False):
    result = _numba_kernel(*(state[f"{group}{i}"] for group in ("p", "m", "v", "birth") for i in range(4)),
                           state["t"], fixture["X"], fixture["labels"], steps, collect)
    state["t"] = np.array(result[0], dtype=np.int64)
    return {"logits": result[1], "losses": result[2], "predictions": result[3]}, {"loss_sum": float(result[4]), "prediction_sum": int(result[5])}


def original_run(model, fixture, steps):
    loss_sum, prediction_sum = 0., 0
    for index in range(steps):
        at = index % 32
        pred, loss = model.step(str(fixture["prefixes"][at]), "01S"[int(fixture["labels"][at])])
        loss_sum += loss
        prediction_sum += "01S".index(pred)
    return {"loss_sum": loss_sum, "prediction_sum": prediction_sum}


def counted_run(counts, name, phase, state, model, runner, fixture, steps, collect=False):
    before = model.t if model is not None else int(state["t"])
    try:
        return original_run(model, fixture, steps) if runner is None else runner(state, fixture, steps, collect=collect)
    finally:
        after = model.t if model is not None else int(state["t"])
        counts[name][phase] += after - before


def main():
    output = c.WORK / "cpu-results.json"
    assert not output.exists(), "This bounded CPU attempt has already produced a result"
    p = c.plan()
    counts = {name: {"compile": 0, "warm": 0, "validation": 0, "timed": 0} for name in BACKENDS}
    result = {"id": p["id"], "status": "running", "scope": "Synthetic engineering only, formal experiment updates0",
              "runtime": {"python": platform.python_version(), "numpy": np.__version__, "numba": numba.__version__,
                          "fastmath": False, "BLAS_threads": 1},
              "imports_seconds": {"common_numpy": c.IMPORT_SECONDS, "numba": NUMBA_IMPORT_SECONDS}, "backends": {},
              "actual_micro_updates": counts, "formal_neural_experiment_updates": 0}
    fixture_path = c.WORK / "fixture.npz"
    source_before, plan_before = c.file_sha(c.REFERENCE), c.file_sha(c.HERE / "plan.json")
    started = time.perf_counter()
    try:
        fixture = c.load_fixture(fixture_path) if fixture_path.exists() else c.make_fixture(fixture_path)
        fixture_before = c.file_sha(fixture_path)
        result["fixture"] = {"file": fixture_path.name, "sha256": fixture_before,
                             "lengths": [len(str(value)) for value in fixture["prefixes"]], "shape": list(fixture["X"].shape),
                             "timing_state_t": int(fixture["t"]), "preparation_seconds": c.LAST_FIXTURE_TIMINGS.copy()}
        refs = {}
        for case in c.CASES:
            begin = time.perf_counter()
            refs[case] = c.reference_trace(fixture, case, steps=64)
            counts[BACKENDS[0]]["validation"] += 64
            result["backends"].setdefault(BACKENDS[0], {"status": "reference", "validation_seconds": {}})["validation_seconds"][case] = time.perf_counter() - begin
        # Compile all arithmetic with a zero-step call; check that no update occurred.
        compiler_state = c.initial_state("timing", fixture)
        before_compile = c.clone_state(compiler_state)
        begin = time.perf_counter()
        numba_run(compiler_state, fixture, 0, collect=True)
        result["numba_compile_seconds"] = time.perf_counter() - begin
        assert c.measure_error(compiler_state, before_compile)["exact_bytes"]
        result["compile_actual_updates"] = 0
        for name, runner in ((BACKENDS[1], numpy_run), (BACKENDS[2], numba_run)):
            entry = {"validation": {}}
            result["backends"][name] = entry
            for case in c.CASES:
                state = c.initial_state(case, fixture)
                begin = time.perf_counter()
                trace, checksum = counted_run(counts, name, "validation", state, None, runner, fixture, 64, collect=True)
                expected_state, expected_trace = refs[case]
                entry["validation"][case] = {"state": c.measure_error(state, expected_state), "trace": c.measure_error(trace, expected_trace),
                                               "seconds": time.perf_counter() - begin, "checksum": checksum}
            entry["status"] = "passed" if all(item["state"]["passed"] and item["trace"]["passed"] for item in entry["validation"].values()) else "parity_failed"
        for name in BACKENDS:
            entry = result["backends"][name]
            if entry["status"] == "parity_failed":
                continue
            runner = None if name == BACKENDS[0] else numpy_run if name == BACKENDS[1] else numba_run
            state = c.initial_state("timing", fixture)
            model = c.original_model(state) if runner is None else None
            begin = time.perf_counter()
            counted_run(counts, name, "warm", state, model, runner, fixture, 32)
            entry["warm_seconds"] = time.perf_counter() - begin
            trials = []
            for trial in range(3):
                begin = time.perf_counter()
                state = c.initial_state("timing", fixture)
                model = c.original_model(state) if runner is None else None
                initialize_seconds = time.perf_counter() - begin
                begin = time.perf_counter()
                raw = counted_run(counts, name, "timed", state, model, runner, fixture, 1024)
                checksum = raw if runner is None else raw[1]
                seconds = time.perf_counter() - begin
                final_t = model.t if runner is None else int(state["t"])
                assert final_t == 401524
                trials.append({"trial": trial + 1, "updates": 1024, "seconds": seconds, "initialize_seconds": initialize_seconds,
                               "final_t": final_t, "checksum": checksum})
            entry["trials"] = trials
            entry["median_seconds"] = statistics.median(trial["seconds"] for trial in trials)
            entry["updates_per_second"] = 1024 / entry["median_seconds"]
        original_seconds = result["backends"][BACKENDS[0]]["median_seconds"]
        for entry in result["backends"].values():
            if "median_seconds" in entry:
                entry["speedup_vs_original"] = original_seconds / entry["median_seconds"]
        assert c.file_sha(c.REFERENCE) == source_before and c.file_sha(c.HERE / "plan.json") == plan_before and c.file_sha(fixture_path) == fixture_before
        assert all(sum(value.values()) <= 7000 for value in counts.values())
        result["actual_micro_updates_total"] = sum(sum(value.values()) for value in counts.values())
        result["reference_update_utility_count"] = c.REFERENCE_UPDATE_COUNT
        result["source_plan_fixture_unchanged"] = True
        result["status"] = "complete" if all(entry["status"] != "parity_failed" for entry in result["backends"].values()) else "completed_with_parity_failure"
    except Exception as error:
        result["status"] = "failed_attempt"
        result["error"] = {"type": type(error).__name__, "message": str(error), "traceback": traceback.format_exc()}
    finally:
        result["actual_micro_updates_total"] = sum(sum(value.values()) for value in counts.values())
        result["wall_seconds_excluding_import"] = time.perf_counter() - started
        result["wall_seconds_including_import"] = time.perf_counter() - _START
        result["source_hashes"] = {"bench_common.py": c.file_sha(c.HERE / "bench_common.py"), "cpu_bench.py": c.file_sha(Path(__file__)),
                                   "plan.json": c.file_sha(c.HERE / "plan.json"), "original_reference": c.file_sha(c.REFERENCE)}
        c.write_json(output, result)
    print(json.dumps({"status": result["status"], "cpu_results": str(output), "actual_micro_updates": counts,
                      "backends": {name: {key: entry[key] for key in ("status", "median_seconds", "speedup_vs_original") if key in entry} for name, entry in result["backends"].items()}}, sort_keys=True))
    if result["status"] == "failed_attempt":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
