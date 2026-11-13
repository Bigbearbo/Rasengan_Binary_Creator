"""Shared synthetic fixture, unmodified P030 reference and bounded parity utilities."""
from __future__ import annotations
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
WORK = HERE.parents[1] / "work/gpu-training-review-20261113"
for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[name] = "1"
os.environ.setdefault("NUMBA_CACHE_DIR", str(WORK / "numba-cache"))
_import_start = time.perf_counter()
import numpy as np
IMPORT_SECONDS = time.perf_counter() - _import_start

SEED, L, H = 20261113, 80, 64
ATOL = RTOL = 2e-5
REFERENCE = HERE.parent / "sle-research-review/p030_binary_continual.py"
REFERENCE_SHA = "db39661a7b16d13e64db7acc5dae22a81ca59dc39cf467ed4c58addbc0654013"
STATE_KEYS = tuple(f"{group}{i}" for group in ("p", "m", "v", "birth") for i in range(4)) + ("t", "L", "H")
CASES = ("fresh_t0_allbirth0", "aged_t400500_heterogeneous_birth")
LAST_FIXTURE_TIMINGS = {}
REFERENCE_UPDATE_COUNT = 0
_MODEL = None


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, sort_keys=True, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def plan():
    value = json.loads((HERE / "plan.json").read_text(encoding="utf-8"))
    assert value["shape"] == {"L": 80, "input": 160, "H": 64, "output": 3, "parameters": 10499}
    assert value["seed"] == SEED and value["validation_updates_per_case"] == 64
    assert value["timed_updates_per_trial"] == 1024 and value["timed_trials_per_backend"] == 3
    assert value["maximum_actual_micro_updates_per_backend"] == 7000
    return value


def model_class():
    global _MODEL
    if _MODEL is None:
        assert file_sha(REFERENCE) == REFERENCE_SHA
        spec = importlib.util.spec_from_file_location("gpu_review_original_p030", REFERENCE)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)  # No old main/checks/run is invoked.
        _MODEL = module.Model
    return _MODEL


def state_from_model(model):
    raw = model.state()
    return {key: raw[key].copy() for key in STATE_KEYS}


def clone_state(state):
    return {key: np.array(state[key], copy=True) for key in STATE_KEYS}


def original_model(state):
    model = model_class()(SEED, L=int(state["L"]), H=int(state["H"]))
    for name in ("p", "m", "v", "birth"):
        setattr(model, name, [np.array(state[f"{name}{i}"], copy=True) for i in range(4)])
    model.t = int(state["t"])
    assert all(np.array_equal(state_from_model(model)[key], state[key]) for key in STATE_KEYS)
    return model


def encode_prefixes(prefixes):
    X = np.zeros((len(prefixes), 160), dtype=np.float32)
    for row, prefix in enumerate(prefixes):
        assert 39 <= len(prefix) <= 51 and set(str(prefix)) <= {"0", "1"}
        for position, bit in enumerate(str(prefix)):
            X[row, 2 * position + int(bit)] = 1
    return X


def make_fixture(path=None):
    """Return flat np.ndarray dict; timing state in the NPZ has t400500/birth0."""
    global LAST_FIXTURE_TIMINGS
    started = time.perf_counter()
    rng = np.random.default_rng(SEED)
    lengths = rng.integers(39, 52, size=32)
    prefixes = np.asarray(["".join(str(int(bit)) for bit in rng.integers(0, 2, size=int(length))) for length in lengths])
    labels = rng.integers(0, 3, size=32, dtype=np.int64)
    generation_seconds = time.perf_counter() - started
    begin = time.perf_counter()
    X = encode_prefixes(prefixes)
    encoding_seconds = time.perf_counter() - begin
    begin = time.perf_counter()
    cls = model_class()
    reference_import_seconds = time.perf_counter() - begin
    begin = time.perf_counter()
    state = state_from_model(cls(SEED, L=L, H=H))
    state["t"] = np.array(400500, dtype=np.int64)
    initialization_seconds = time.perf_counter() - begin
    result = {"prefixes": prefixes, "X": X, "labels": labels, **state}
    LAST_FIXTURE_TIMINGS = {"prefix_labels_generation_seconds": generation_seconds, "encoding_seconds": encoding_seconds,
                           "reference_import_seconds": reference_import_seconds, "original_initialization_seconds": initialization_seconds}
    if path is not None:
        begin = time.perf_counter()
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with Path(path).open("xb") as stream:
            np.savez(stream, **result)
        LAST_FIXTURE_TIMINGS["fixture_write_seconds"] = time.perf_counter() - begin
    return result


def load_fixture(path=WORK / "fixture.npz"):
    with np.load(path, allow_pickle=False) as archive:
        fixture = {name: archive[name].copy() for name in archive.files}
    assert fixture["X"].shape == (32, 160) and fixture["X"].dtype == np.float32
    assert fixture["labels"].shape == (32,) and fixture["labels"].dtype == np.int64
    assert np.array_equal(fixture["X"], encode_prefixes(fixture["prefixes"]))
    return fixture


def initial_state(case="timing", fixture=None):
    fixture = load_fixture() if fixture is None else fixture
    result = clone_state(fixture)
    for group in ("m", "v"):
        for i in range(4):
            result[f"{group}{i}"][:] = 0
    result["t"] = np.array(0 if case in ("fresh", CASES[0]) else 400500, dtype=np.int64)
    assert case in ("timing", "fresh", "aged", *CASES)
    for i in range(4):
        birth = result[f"birth{i}"]
        if case in ("aged", CASES[1]):
            birth[:] = np.asarray([0, 400499, 400489], dtype=np.int64)[np.arange(birth.size).reshape(birth.shape) % 3]
        else:
            birth[:] = 0
    return result


def reference_trace(fixture, case, steps=64):
    """One original .step per target; capture its existing forward, never extra F."""
    global REFERENCE_UPDATE_COUNT
    model = original_model(initial_state(case, fixture))
    logits = np.empty((steps, 3), np.float32)
    losses = np.empty(steps, np.float64)
    predictions = np.empty(steps, np.int64)
    native_forward, observed = model.forward, [None]
    def forward(text, training=False):
        result = native_forward(text, training)
        observed[0] = result[2].copy()
        return result
    model.forward = forward
    try:
        for index in range(steps):
            position = index % 32
            pred, loss = model.step(str(fixture["prefixes"][position]), "01S"[int(fixture["labels"][position])])
            REFERENCE_UPDATE_COUNT += 1
            logits[index], losses[index], predictions[index] = observed[0], loss, "01S".index(pred)
    finally:
        del model.forward
    return state_from_model(model), {"logits": logits, "losses": losses, "predictions": predictions}


def measure_error(actual, expected, atol=ATOL, rtol=RTOL):
    assert atol == ATOL and rtol == RTOL, "Frozen tolerance cannot be changed"
    if not isinstance(actual, dict):
        actual, expected = {"array": actual}, {"array": expected}
    assert set(actual) == set(expected)
    fields = {}
    for name in expected:
        a, b = np.asarray(actual[name]), np.asarray(expected[name])
        compatible = a.shape == b.shape and a.dtype == b.dtype
        exact = compatible and a.tobytes(order="C") == b.tobytes(order="C")
        if compatible and b.dtype.kind in "fc":
            difference = np.abs(a.astype(np.float64) - b.astype(np.float64))
            absolute = float(difference.max()) if difference.size else 0.
            relative = float((difference / np.maximum(np.abs(b.astype(np.float64)), 1e-30)).max()) if difference.size else 0.
            passed = bool(np.isfinite(a).all() and np.isfinite(b).all() and np.allclose(a, b, atol=atol, rtol=rtol))
        else:
            absolute = relative = 0. if exact else None
            passed = exact
        fields[name] = {"passed": passed, "exact_bytes": exact, "max_abs": absolute, "max_rel": relative,
                        "actual_dtype": a.dtype.str, "expected_dtype": b.dtype.str}
    return {"passed": all(item["passed"] for item in fields.values()), "exact_bytes": all(item["exact_bytes"] for item in fields.values()),
            "atol": atol, "rtol": rtol, "max_abs": max((item["max_abs"] for item in fields.values() if item["max_abs"] is not None), default=None),
            "fields": fields}
