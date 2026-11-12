#!/usr/bin/env python3
"""Bounded P030 growth audit. No checkpoint/source file is modified.

Requires Python and NumPy plus the original repository archive at commit
9118abf4e895204588f7c5aa1bfc2615d0ab52b8. Imports its hash-guarded Model.
Only two optimizer updates per seed are made on disposable in-memory copies;
these inspect gradient flow and are not a new learning-performance experiment.
"""
import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import sys

sys.dont_write_bytecode = True
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
import numpy as np

SOURCE_COMMIT = "9118abf4e895204588f7c5aa1bfc2615d0ab52b8"
SOURCE_SHA256 = "287f4c243b6c7e75a38b6b23c6833aa0064974956f16b481277ad693b14fb1de"
CHECKPOINT_SHA256 = {
    101: "fac69f382dc163589c2fc1ebae8f63d7c08565c7e8a5a7ded45ce32a9350f692",
    202: "753ab48481910fc56775338547b0751caf055428db0539cdf02df1d91db31f82",
    303: "15aa4c9238d387a312ef0379e96376121cdc0c23437c16a58b88c25495fd8ece",
}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_model(module, path, seed):
    with np.load(path, allow_pickle=False) as state:
        model = module.Model(seed, int(state["L"]), int(state["H"]))
        for label in ("p", "m", "v", "birth"):
            setattr(model, label, [state[f"{label}{i}"].copy() for i in range(4)])
        model.t = int(state["t"])
        model.growth_rng.bit_generator.state = json.loads(str(state["growth_rng"]))
    return model


def audit(module, archive, seed):
    relative = Path(f"evidence/p030-binary-continual-20261112/dynamic-{seed}/1b_echo_n3/state.npz")
    checkpoint = archive / relative
    digest = sha256(checkpoint)
    if digest != CHECKPOINT_SHA256[seed]:
        raise ValueError(f"Checkpoint hash mismatch for seed {seed}")
    model = load_model(module, checkpoint, seed)
    old = module.REGISTRY["1b_echo_n3"]
    new = module.REGISTRY["2a_echo_op2"]
    old_l, old_h = model.L, model.H
    prefixes = [module.encode(old, 0, value) + module.answer(0, old.nd, value)[:i]
                for value in range(8) for i in range(old.nd + 2)]
    before = model.state()
    before_logits = [model.forward(text)[2].copy() for text in prefixes]
    model.grow(new.context, old_h + new.context - old_l, "review_probe_only")
    slices = [(slice(0, 2 * old_l), slice(0, old_h)), (slice(0, old_h),),
              (slice(0, old_h), slice(None)), (slice(None),)]
    preserved = all(np.array_equal(getattr(model, label)[i][sl], before[f"{label}{i}"])
                    for label in ("p", "m", "v", "birth") for i, sl in enumerate(slices))
    maximum_delta = max(float(np.max(np.abs(model.forward(text)[2] - logits)))
                        for text, logits in zip(prefixes, before_logits))
    rows = []
    for value in range(8):
        expected = module.answer(0, old.nd, value) + "S"
        old_q, new_q = module.encode(old, 0, value), module.encode(new, 0, value)
        old_tokens, old_overflow = model.generate(old_q)
        new_tokens, new_overflow = model.generate(new_q)
        rows.append({"value": value, "expected": expected,
                     "old_q": old_q, "new_q": new_q,
                     "old_tokens": old_tokens, "old_overflow": old_overflow,
                     "new_tokens": new_tokens, "new_overflow": new_overflow,
                     "old_correct": old_tokens == expected and not old_overflow,
                     "new_correct": new_tokens == expected and not new_overflow})
    # A tiny gradient-flow check; no model-performance conclusion is drawn.
    q = module.encode(old, 0, 1)
    target = module.answer(0, old.nd, 1)[0]
    before_steps = [p.copy() for p in model.p]
    _, first_g, _ = model.loss_grad(q, target)
    model.step(q, target)
    _, second_g, _ = model.loss_grad(q, target)
    model.step(q, target)
    result = {
        "seed": seed, "checkpoint_relative_path": str(relative), "checkpoint_sha256": digest,
        "from_shape": [old_l, old_h], "to_shape": [model.L, model.H],
        "old_prefix_count": len(prefixes), "same_prefix_max_logit_delta": maximum_delta,
        "old_weights_moments_birth_preserved": preserved,
        "global_step_preserved_on_growth": model.t - 2 == int(before["t"]),
        "old_correct": sum(row["old_correct"] for row in rows),
        "new_profile_correct_before_relearning": sum(row["new_correct"] for row in rows),
        "generation_rows": rows,
        "gradient_probe": {
            "q": q, "target": target, "optimizer_updates_on_disposable_copy": 2,
            "new_hidden_first_incoming_grad_norm": float(np.linalg.norm(first_g[0][:, old_h:])),
            "new_hidden_first_outgoing_grad_norm": float(np.linalg.norm(first_g[2][old_h:, :])),
            "new_hidden_second_incoming_grad_norm": float(np.linalg.norm(second_g[0][:, old_h:])),
            "old_weights_changed_by_two_steps": any(not np.array_equal(model.p[i][sl], before_steps[i][sl])
                                                     for i, sl in enumerate(slices)),
            "new_incoming_weights_changed_by_two_steps": not np.array_equal(model.p[0][:, old_h:], before_steps[0][:, old_h:]),
        },
        "original_file_unchanged": sha256(checkpoint) == digest,
    }
    assert preserved and maximum_delta < 2e-6
    assert result["global_step_preserved_on_growth"] and result["original_file_unchanged"]
    assert result["gradient_probe"]["new_hidden_first_incoming_grad_norm"] == 0
    assert result["gradient_probe"]["new_hidden_first_outgoing_grad_norm"] > 0
    assert result["gradient_probe"]["new_hidden_second_incoming_grad_norm"] > 0
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--p030-dir", type=Path, required=True,
                        help="Original repo's experiments/spiral_neural/20261112_p024_p030 directory")
    parser.add_argument("--out", type=Path, required=True, help="New output directory outside the source archive")
    args = parser.parse_args()
    archive = args.p030_dir.resolve()
    out = args.out.resolve()
    if out == archive or archive in out.parents:
        raise ValueError("Output must be outside the immutable source archive")
    source = archive / "src/p030_binary_continual.py"
    if sha256(source) != SOURCE_SHA256:
        raise ValueError("P030 source hash mismatch")
    sys.path.insert(0, str(archive / "src"))
    module = importlib.import_module("p030_binary_continual")
    result = {
        "status": "PASS", "source_commit": SOURCE_COMMIT,
        "source_sha256": SOURCE_SHA256,
        "scope": "Original saved checkpoints; no complete retraining; two gradient-flow optimizer steps per seed on disposable in-memory copies only.",
        "limitations": [
            "The position-change comparison is an immediate pre-adaptation diagnostic, not a claim that zero-shot transfer was required.",
            "Function preservation applies to identical old raw prefixes, not reencoded new-profile inputs.",
            "Gradient nonzero checks establish learnability, not useful convergence or a growth-performance benefit.",
            "Three checkpoints from the same tiny binary task do not establish encoding superiority or population accuracy.",
        ],
        "runtime": {"python": sys.version.split()[0], "numpy": np.__version__},
        "results": [audit(module, archive, seed) for seed in CHECKPOINT_SHA256],
    }
    out.mkdir(parents=True, exist_ok=False)
    (out / "results.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"status": "PASS", "source_commit": SOURCE_COMMIT,
                      "seeds": [{"seed": row["seed"], "old_correct": row["old_correct"],
                                 "new_profile_correct_before_relearning": row["new_profile_correct_before_relearning"],
                                 "same_prefix_max_logit_delta": row["same_prefix_max_logit_delta"]}
                                for row in result["results"]]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
