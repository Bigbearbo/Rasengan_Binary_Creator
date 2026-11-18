"""Fixed real/random/raw feature banks and a small newly trained MAX head.

No source predictions are substituted with ground truth.  This module performs
no work at import.  The established PR130 Adam implementation is reused.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
from sources.neural_growth import PARAMETER_KEYS, optimizer_state, adam_step

ROOT = Path(__file__).resolve().parent
ARMS = ("mature_hidden", "random_hidden", "raw_projection")


def load_bank(arm, seed):
    if arm not in ARMS:
        raise ValueError(arm)
    if arm == "mature_hidden":
        path = ROOT/"sources"/f"receiver_seed{seed}.npz"
        with np.load(path, allow_pickle=False) as z:
            metadata = json.loads(str(z["metadata_json"]))
            if (metadata["schema"] != "growth-channel-checkpoint-v1" or metadata["role"] != "receiver" or
                    metadata["shape"] != [34, 24, 18] or metadata["step"] != 4096 or metadata["model_seed"] != seed):
                raise ValueError("Unexpected mature source checkpoint")
            bank = {k: z[f"param_{k}"].astype(np.float64, copy=True) for k in PARAMETER_KEYS}
    else:
        path = ROOT/"banks"/(f"random_seed{seed}.npz" if arm == "random_hidden" else "raw_projection.npz")
        with np.load(path, allow_pickle=False) as z:
            metadata = json.loads(str(z["metadata_json"]))
            if metadata["schema"] != "feature-bank-v1" or metadata["kind"] != arm:
                raise ValueError("Unexpected fixed feature bank")
            bank = {k: z[k].astype(np.float64, copy=True) for k in ("W1", "b1")}
    if bank["W1"].shape != (34, 24) or bank["b1"].shape != (24,):
        raise ValueError("Feature encoder shape mismatch")
    bank.update(arm=arm, seed=int(seed), path=path, metadata=metadata)
    return bank


def extract_features(bank, x):
    x = np.asarray(x, dtype=np.float64)
    if x.ndim != 2 or x.shape[1] != 34 or np.any((x != 0) & (x != 1)):
        raise ValueError("Raw34 binary frames required")
    z = x @ bank["W1"]+bank["b1"]
    return z if bank["arm"] == "raw_projection" else np.tanh(z)


def fit_normalizer(features):
    features = np.asarray(features, dtype=np.float64)
    if features.ndim != 2 or features.shape[1] != 24 or not len(features):
        raise ValueError("Nonempty24dim training features required")
    mean = features.mean(axis=0)
    raw_rms = float(np.sqrt(np.mean((features-mean)**2)))
    scale = max(raw_rms, 1e-8)
    return {"mean": mean, "scale": scale, "unclamped_global_rms": raw_rms,
            "fit_rows": len(features), "fixed_values": 25}


def normalize(features, normalizer):
    return (np.asarray(features, dtype=np.float64)-normalizer["mean"])/float(normalizer["scale"])


def init_head(seed):
    rng = np.random.default_rng(1900000+int(seed))
    return {"W1": rng.normal(0, np.sqrt(2/(24+8)), (24, 8)), "b1": np.zeros(8),
            "W2": rng.normal(0, np.sqrt(2/(8+7)), (8, 7)), "b2": np.zeros(7)}


def forward(params, x):
    x = np.asarray(x, dtype=np.float64)
    if x.ndim != 2 or x.shape[1] != 24:
        raise ValueError("Head needs24dim features")
    return np.tanh(x @ params["W1"]+params["b1"]) @ params["W2"]+params["b2"]


def loss_output_grad(logits, target):
    logits, target = np.asarray(logits, dtype=np.float64), np.asarray(target, dtype=np.float64)
    if logits.shape != target.shape or logits.ndim != 2 or logits.shape[1] != 7 or not len(logits):
        raise ValueError("Nonempty matching seven-bit targets required")
    if np.any((target != 0) & (target != 1)):
        raise ValueError("Targets must be binary")
    value = float(np.mean(np.logaddexp(0, logits)-target*logits))
    sigmoid = np.exp(-np.logaddexp(0, -logits))
    return value, (sigmoid-target)/target.size


def loss_grads(params, x, target):
    h = np.tanh(x @ params["W1"]+params["b1"])
    value, dz = loss_output_grad(h @ params["W2"]+params["b2"], target)
    dh = (dz @ params["W2"].T)*(1-h*h)
    return value, {"W1": x.T @ dh, "b1": dh.sum(axis=0), "W2": h.T @ dz, "b2": dz.sum(axis=0)}


def source_readout(bank, raw_hidden):
    if bank["arm"] != "mature_hidden":
        raise ValueError("Only a real mature source has its original semantic readout")
    logits = raw_hidden @ bank["W2"]+bank["b2"]
    bits = (logits[:, 4:] >= 0).astype(np.uint8)
    low = np.array([16, 8, 4, 2, 1], dtype=np.int64)
    high = np.array([64, 32], dtype=np.int64)
    return {"logits": logits, "pred_op": logits[:, :4].argmax(axis=1),
        "pred_a": bits[:, :5] @ low+bits[:, 10:12] @ high,
        "pred_b": bits[:, 5:10] @ low+bits[:, 12:14] @ high, "operand_bits": bits}


def save_checkpoint(path, params, m, v, t, seed, arm, step, extra):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    metadata = {"schema": "feature-transfer-head-v1", "seed": int(seed), "arm": arm,
        "step": int(step), "optimizer_step": int(t), "shape": [24, 8, 7], "trainable_parameters": 263,
        "dtype": "float64", "optimizer": {"name": "Adam", "lr": .01, "beta1": .9,
            "beta2": .999, "eps": 1e-8, "clip_global_norm": 5.0}, **extra}
    arrays = {f"param_{k}": params[k] for k in PARAMETER_KEYS}
    arrays.update({f"adam_m_{k}": m[k] for k in PARAMETER_KEYS})
    arrays.update({f"adam_v_{k}": v[k] for k in PARAMETER_KEYS})
    arrays["metadata_json"] = np.array(json.dumps(metadata, sort_keys=True))
    np.savez_compressed(path, **arrays)


def load_checkpoint(path):
    with np.load(path, allow_pickle=False) as z:
        metadata = json.loads(str(z["metadata_json"]))
        if metadata["schema"] != "feature-transfer-head-v1":
            raise ValueError("Unexpected new-head checkpoint")
        params = {k: z[f"param_{k}"].astype(np.float64, copy=True) for k in PARAMETER_KEYS}
        m = {k: z[f"adam_m_{k}"].astype(np.float64, copy=True) for k in PARAMETER_KEYS}
        v = {k: z[f"adam_v_{k}"].astype(np.float64, copy=True) for k in PARAMETER_KEYS}
    return {"params": params, "m": m, "v": v, "t": metadata["optimizer_step"], "metadata": metadata}
