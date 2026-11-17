"""Bounded zero-update preflight; never reads test rows for model inference.

Checks a fixed source-feature fixture, raw isometry, paired initial heads, and
the new seven-bit BCE gradient by finite differences.  Counts verification
forward work separately from the later experiment.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import numpy as np
from feature_model import (ARMS, PARAMETER_KEYS, load_bank, extract_features,
    fit_normalizer, normalize, init_head, forward, loss_grads, loss_output_grad)

ROOT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    destination = ROOT/"preflight.json"
    if destination.exists():
        raise FileExistsError(destination)
    manifest = json.loads((ROOT/"source_manifest.json").read_text(encoding="utf-8"))
    for source in manifest["copied_sources"]:
        if sha(ROOT/source["path"]) != source["sha256"]:
            raise AssertionError("Copied source hash changed")
    for name, expected in manifest["generated_files"].items():
        if sha(ROOT/name) != expected["sha256"]:
            raise AssertionError("Prepared input changed: "+name)
    data = json.loads((ROOT/"data.json").read_text(encoding="utf-8"))
    # Only a small training fixture is passed to any feature bank.
    fixture_rows = data["panels"]["train"][:16]
    x = np.asarray([[int(bit) for bit in row["frame_bits"]] for row in fixture_rows], dtype=np.float64)
    feature_checks = []
    for seed in (101, 202, 303):
        initial = init_head(seed)
        for arm in ARMS:
            candidate = init_head(seed)
            if any(not np.array_equal(initial[key], candidate[key]) for key in PARAMETER_KEYS):
                raise AssertionError("Head initialization is not paired")
            bank = load_bank(arm, seed)
            before = {key: bank[key].copy() for key in PARAMETER_KEYS if key in bank}
            actual = extract_features(bank, x)
            if actual.shape != (16, 24) or not np.isfinite(actual).all():
                raise AssertionError("Invalid source features")
            norm = fit_normalizer(actual)
            normalized = normalize(actual, norm)
            if float(np.max(np.abs(normalized.mean(axis=0)))) > 1e-11:
                raise AssertionError("Training mean not removed")
            if abs(float(np.mean(normalized**2))-1) > 1e-11:
                raise AssertionError("Single RMS does not normalize variance")
            if any(not np.array_equal(bank[key], value) for key, value in before.items()):
                raise AssertionError("Feature extraction mutated its bank")
            check = {"arm": arm, "seed": seed, "training_fixture_rows": 16,
                "global_rms": norm["scale"], "fixed_bank_unchanged": True}
            if arm == "raw_projection":
                variable = np.asarray(json.loads((ROOT/"projection_receipt.json").read_text())["variable_zero_based_positions"])
                basis = bank["W1"][variable]
                sv = np.linalg.svd(basis, compute_uv=False)
                after = np.linalg.svd(basis/norm["scale"], compute_uv=False)
                if np.max(np.abs(basis @ basis.T-np.eye(18))) > 1e-12:
                    raise AssertionError("Raw variable-coordinate projection is not isometric")
                if sv.max()/sv.min() > 1+1e-12 or after.max()/after.min() > 1+1e-12:
                    raise AssertionError("Scalar normalization changed conditioning")
                delta = x[::2]-x[1::2]
                distances = np.sum(delta*delta, axis=1)
                mapped = np.sum((delta @ bank["W1"])**2, axis=1)
                if not np.allclose(distances, mapped, atol=1e-11, rtol=0):
                    raise AssertionError("Raw projection lost a training-frame difference")
                check.update(rank=int(np.linalg.matrix_rank(basis)), condition=float(sv.max()/sv.min()),
                    normalized_condition=float(after.max()/after.min()),
                    max_pair_distance_squared_error=float(np.max(np.abs(distances-mapped))))
            feature_checks.append(check)
    # Independent scalar perturbation of every new trainable parameter, using
    # deterministic synthetic features rather than any validation/test labels.
    rng = np.random.default_rng(2026111809)
    gx = rng.normal(size=(6, 24))
    gy = rng.integers(0, 2, size=(6, 7)).astype(np.float64)
    params = init_head(101)
    analytic_loss, gradients = loss_grads(params, gx, gy)
    eps, maximum, tested = 1e-5, 0.0, 0
    for key in PARAMETER_KEYS:
        for index in np.ndindex(params[key].shape):
            original = params[key][index]
            params[key][index] = original+eps
            plus = loss_output_grad(forward(params, gx), gy)[0]
            params[key][index] = original-eps
            minus = loss_output_grad(forward(params, gx), gy)[0]
            params[key][index] = original
            error = abs((plus-minus)/(2*eps)-gradients[key][index])
            maximum = max(maximum, float(error))
            tested += 1
    if tested != 263 or maximum > 2e-8:
        raise AssertionError("New head BCE gradient check failed")
    result = {"schema": "feature-transfer-preflight-v1", "status": "PASS",
        "new_training_updates": 0, "fresh_test_feature_rows": 0, "feature_checks": feature_checks,
        "new_head_gradient": {"parameters_checked": tested, "central_difference_epsilon": eps,
            "max_abs_error": maximum, "analytic_loss": analytic_loss, "fixture_rows": 6},
        "verification_forward_work": {"feature_rows": 144, "feature_dense_mac": 144*816,
            "head_forward_rows_including_analytic_gradient": (2*263+1)*6,
            "head_forward_dense_mac": (2*263+1)*6*248,
            "optimizer_updates": 0, "note": "Preflight work only, not experimental training or fresh-test inference"},
        "source_hashes_checked": len(manifest["copied_sources"])+len(manifest["generated_files"])}
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "gradient_parameters": tested, "gradient_max_error": maximum,
        "new_training_updates": 0, "fresh_test_feature_rows": 0}))


if __name__ == "__main__":
    main()
