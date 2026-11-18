"""Actual learned word decoder, tiny comparator, and handfilled neural copy gates.

The decoder's predictions are never repaired from labels.  The copy path is a
stored sparse threshold network, not a Python max/operand-selection shortcut.
No work is performed at import.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent
SEEDS = (101, 202, 303)
ARMS = ("handfilled_frozen", "random_train", "handfilled_train")
TRAINED_ARMS = ARMS[1:]
KEYS = ("w", "b")
BIT_WEIGHTS = np.array([64, 32, 16, 8, 4, 2, 1], dtype=np.int64)
# Source order: op4, a_low5, b_low5, a_high2, b_high2.
# This fixed wiring reorders original readout coordinates; it never parses raw
# frames or substitutes true operand values.
WORD_OUTPUT_INDICES = np.array([14, 15, 4, 5, 6, 7, 8, 16, 17, 9, 10, 11, 12, 13])


def load_source(seed):
    path = ROOT/"sources"/f"receiver_seed{seed}.npz"
    with np.load(path, allow_pickle=False) as z:
        metadata = json.loads(str(z["metadata_json"]))
        if (metadata["schema"] != "growth-channel-checkpoint-v1" or metadata["role"] != "receiver"
                or metadata["shape"] != [34, 24, 18] or metadata["step"] != 4096
                or metadata["model_seed"] != seed):
            raise ValueError("Unexpected source receiver")
        result = {k: z[f"param_{k}"].astype(np.float64, copy=True) for k in ("W1", "b1", "W2", "b2")}
    if sum(v.size for v in result.values()) != 1290:
        raise ValueError("Wrong source size")
    return result


def decode(source, raw_frames):
    raw = np.asarray(raw_frames, dtype=np.float64)
    if raw.ndim != 2 or raw.shape[1] != 34 or np.any((raw != 0) & (raw != 1)):
        raise ValueError("Decoder requires raw 34-bit frames")
    hidden = np.tanh(raw @ source["W1"]+source["b1"])
    logits = hidden @ source["W2"]+source["b2"]
    ordered_logits = logits[:, WORD_OUTPUT_INDICES]
    words = (ordered_logits >= 0).astype(np.uint8)
    return {"hidden": hidden, "logits": logits, "operand_logits": ordered_logits,
            "words": words, "pred_op": logits[:, :4].argmax(axis=1),
            "pred_a": words[:, :7] @ BIT_WEIGHTS, "pred_b": words[:, 7:] @ BIT_WEIGHTS}


def exact_comparator():
    return {"w": np.concatenate((BIT_WEIGHTS, -BIT_WEIGHTS)).astype(np.float64),
            "b": np.array([.5], dtype=np.float64)}


def init_comparator(arm, seed):
    if arm not in ARMS:
        raise ValueError(arm)
    if arm != "random_train":
        return exact_comparator()
    rng = np.random.default_rng(2100000+int(seed))
    return {"w": rng.normal(0, np.sqrt(2/15), 14), "b": np.zeros(1, dtype=np.float64)}


def comparator_logits(params, words):
    x = np.asarray(words, dtype=np.float64)
    if x.ndim != 2 or x.shape[1] != 14 or np.any((x != 0) & (x != 1)):
        raise ValueError("Comparator requires fourteen actual binary word outputs")
    return x @ params["w"]+params["b"][0]


def load_mux():
    with np.load(ROOT/"handfilled_mux.npz", allow_pickle=False) as z:
        return {k: z[k].copy() for k in ("layer1_indices", "layer1_weights", "layer1_bias",
                                        "layer2_indices", "layer2_weights", "layer2_bias")}


def mux_forward(mux, words, selection):
    words = np.asarray(words, dtype=np.uint8)
    selection = np.asarray(selection, dtype=np.uint8)
    if words.ndim != 2 or words.shape[1] != 14 or selection.shape != (len(words),):
        raise ValueError("Bad copy-network input shapes")
    if np.any((words != 0) & (words != 1)) or np.any((selection != 0) & (selection != 1)):
        raise ValueError("Copy network inputs must be bits")
    inputs = np.column_stack((words, selection))
    layer1_logits = np.sum(inputs[:, mux["layer1_indices"]]*mux["layer1_weights"], axis=2)+mux["layer1_bias"]
    layer1_bits = (layer1_logits >= 0).astype(np.uint8)
    output_logits = np.sum(layer1_bits[:, mux["layer2_indices"]]*mux["layer2_weights"], axis=2)+mux["layer2_bias"]
    return {"layer1_logits": layer1_logits, "layer1_bits": layer1_bits,
            "output_logits": output_logits, "output_bits": (output_logits >= 0).astype(np.uint8)}


def hybrid_forward(params, mux, words):
    scores = comparator_logits(params, words)
    selection = (scores >= 0).astype(np.uint8)
    result = mux_forward(mux, words, selection)
    result.update(selector_logits=scores, selection=selection)
    return result


def loss_grads(params, words, targets):
    x = np.asarray(words, dtype=np.float64)
    y = np.asarray(targets, dtype=np.float64)
    z = comparator_logits(params, x)
    if y.shape != (len(x),) or not len(x) or np.any((y != 0) & (y != 1)):
        raise ValueError("Binary supervised selector labels required")
    value = float(np.mean(np.logaddexp(0, z)-y*z))
    dz = (np.exp(-np.logaddexp(0, -z))-y)/len(x)
    return value, {"w": x.T @ dz, "b": np.array([dz.sum()])}


def optimizer_state(params):
    return {k: np.zeros_like(params[k]) for k in KEYS}, {k: np.zeros_like(params[k]) for k in KEYS}, 0


def adam_step(params, m, v, t, grads, lr=.01, beta1=.9, beta2=.999, eps=1e-8, clip=5.0):
    norm = float(np.sqrt(sum(float(np.sum(grads[k]**2)) for k in KEYS)))
    if not np.isfinite(norm):
        raise FloatingPointError("Nonfinite gradient")
    scale = min(1.0, clip/norm) if norm else 1.0
    t = int(t)+1
    for key in KEYS:
        g = grads[key]*scale
        m[key] *= beta1
        m[key] += (1-beta1)*g
        v[key] *= beta2
        v[key] += (1-beta2)*g*g
        params[key] -= lr*(m[key]/(1-beta1**t))/(np.sqrt(v[key]/(1-beta2**t))+eps)
    return t, {"grad_norm_before": norm, "clip_scale": scale}


def save_checkpoint(path, params, m, v, step, arm, seed, extra=None):
    values = {f"param_{k}": params[k] for k in KEYS}
    values.update({f"adam_m_{k}": m[k] for k in KEYS})
    values.update({f"adam_v_{k}": v[k] for k in KEYS})
    metadata = {"schema": "handfill-selector-checkpoint-v1", "arm": arm, "seed": int(seed),
                "step": int(step), "optimizer_step": int(step), "selector_parameters": 15,
                "selector_trainable_parameters": 0 if arm == "handfilled_frozen" else 15,
                "dtype": "float64", **(extra or {})}
    values["metadata_json"] = np.array(json.dumps(metadata, sort_keys=True))
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, **values)


def load_checkpoint(path):
    with np.load(path, allow_pickle=False) as z:
        metadata = json.loads(str(z["metadata_json"]))
        if metadata["schema"] != "handfill-selector-checkpoint-v1":
            raise ValueError("Bad checkpoint schema")
        return {"params": {k: z[f"param_{k}"].astype(np.float64, copy=True) for k in KEYS},
                "m": {k: z[f"adam_m_{k}"].astype(np.float64, copy=True) for k in KEYS},
                "v": {k: z[f"adam_v_{k}"].astype(np.float64, copy=True) for k in KEYS},
                "metadata": metadata}
