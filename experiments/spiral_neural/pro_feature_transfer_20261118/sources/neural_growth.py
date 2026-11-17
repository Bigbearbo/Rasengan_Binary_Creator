"""Raw-frame, function-preserving growth learners; NumPy float64 only.

The sender's first twelve inputs and first twenty-eight outputs retain the
parent layout.  The receiver sees raw left-aligned frames, never parsed words.
No automatic training takes place when this module is imported.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np

PARAMETER_KEYS = ("W1", "b1", "W2", "b2")
IO_SHAPES = {"speaker": (17, 34), "receiver": (34, 18)}
PARENT_SHAPES = {"speaker": (12, 16, 28), "receiver": (28, 16, 14)}


def init(role, seed, hidden=32):
    n_in, n_out = IO_SHAPES[role]
    rng = np.random.default_rng(int(seed))
    return {"W1": rng.normal(0, np.sqrt(2/(n_in+hidden)), (n_in, hidden)),
            "b1": np.zeros(hidden, dtype=np.float64),
            "W2": rng.normal(0, np.sqrt(2/(hidden+n_out)), (hidden, n_out)),
            "b2": np.zeros(n_out, dtype=np.float64)}


def load_parent(path, role):
    with np.load(Path(path), allow_pickle=False) as z:
        metadata = json.loads(str(z["metadata_json"]))
        if metadata.get("schema") != "bit-channel-neural-checkpoint-v1" or metadata.get("role") != role:
            raise ValueError("Unexpected parent checkpoint")
        params = {k: z[f"param_{k}"].astype(np.float64, copy=True) for k in PARAMETER_KEYS}
        # Retain and expose complete inherited optimizer state as provenance.
        m = {k: z[f"adam_m_{k}"].astype(np.float64, copy=True) for k in PARAMETER_KEYS}
        v = {k: z[f"adam_v_{k}"].astype(np.float64, copy=True) for k in PARAMETER_KEYS}
    n_in, hidden, n_out = PARENT_SHAPES[role]
    expected = {"W1": (n_in, hidden), "b1": (hidden,), "W2": (hidden, n_out), "b2": (n_out,)}
    if any(params[k].shape != expected[k] for k in PARAMETER_KEYS):
        raise ValueError("Parent shape mismatch")
    if int(metadata["optimizer_step"]) != 1024:
        raise ValueError("Expected the completed PR129 parent")
    return {"params": params, "m": m, "v": v, "t": int(metadata["optimizer_step"]), "metadata": metadata}


def morph_parent(parent_params, role):
    """Embed the exact old function; added outputs initially have logit -2."""
    n_in, n_out = IO_SHAPES[role]
    old_in, hidden, old_out = PARENT_SHAPES[role]
    params = {"W1": np.zeros((n_in, hidden), dtype=np.float64),
              "b1": parent_params["b1"].copy(),
              "W2": np.zeros((hidden, n_out), dtype=np.float64),
              "b2": np.full(n_out, -2.0, dtype=np.float64)}
    params["W1"][:old_in] = parent_params["W1"]
    params["W2"][:, :old_out] = parent_params["W2"]
    params["b2"][:old_out] = parent_params["b2"]
    return params


def expand_hidden(params, rng, amount=8):
    """Append live incoming connections and zero outgoing connections.

    Initial outputs are unchanged.  Incoming weights can acquire gradients
    after the new outgoing weights move; zeroing both blocks would kill cells.
    """
    n_in, old_hidden = params["W1"].shape
    n_out = params["W2"].shape[1]
    new_hidden = old_hidden+int(amount)
    if int(amount) <= 0:
        raise ValueError("Positive growth required")
    incoming = rng.normal(0, np.sqrt(2/(n_in+new_hidden)), (n_in, int(amount)))
    return {"W1": np.concatenate([params["W1"], incoming], axis=1),
            "b1": np.concatenate([params["b1"], np.zeros(int(amount))]),
            "W2": np.concatenate([params["W2"], np.zeros((int(amount), n_out))], axis=0),
            "b2": params["b2"].copy()}


def optimizer_state(params):
    return ({k: np.zeros_like(params[k]) for k in PARAMETER_KEYS},
            {k: np.zeros_like(params[k]) for k in PARAMETER_KEYS}, 0)


def forward(params, x):
    x = np.asarray(x, dtype=np.float64)
    if x.ndim != 2 or x.shape[1] != params["W1"].shape[0]:
        raise ValueError("Input shape mismatch")
    return np.tanh(x @ params["W1"]+params["b1"]) @ params["W2"]+params["b2"]


def sigmoid(z):
    return np.exp(-np.logaddexp(0, -np.asarray(z, dtype=np.float64)))


def loss_output_grad(logits, target, role, mask=None):
    logits, target = np.asarray(logits, dtype=np.float64), np.asarray(target, dtype=np.float64)
    if (logits.ndim != 2 or logits.shape != target.shape or not len(logits)
            or logits.shape[1] != IO_SHAPES[role][1] or np.any((target != 0) & (target != 1))):
        raise ValueError("Nonempty logits and binary targets must match role shape")
    if role == "speaker":
        if mask is None:
            raise ValueError("Sender requires the raw-profile output mask")
        mask = np.asarray(mask, dtype=np.float64)
        if mask.shape != logits.shape or np.any((mask != 0) & (mask != 1)) or np.any(mask.sum(1) <= 0):
            raise ValueError("Invalid sender mask")
        scale = mask/mask.sum(axis=1, keepdims=True)/len(logits)
        value = np.sum((np.logaddexp(0, logits)-target*logits)*scale)
        grad = (sigmoid(logits)-target)*scale
    else:
        if not np.all(target[:, :4].sum(axis=1) == 1):
            raise ValueError("Receiver op targets must be one-hot")
        z = logits[:, :4]-logits[:, :4].max(axis=1, keepdims=True)
        logp = z-np.log(np.exp(z).sum(axis=1, keepdims=True))
        ce = -np.sum(target[:, :4]*logp)/len(target)
        bits = np.mean(np.logaddexp(0, logits[:, 4:])-target[:, 4:]*logits[:, 4:])
        value = ce+bits
        grad = np.empty_like(logits)
        grad[:, :4] = (np.exp(logp)-target[:, :4])/len(target)
        grad[:, 4:] = (sigmoid(logits[:, 4:])-target[:, 4:])/target[:, 4:].size
    if not np.isfinite(value) or not np.isfinite(grad).all():
        raise FloatingPointError("Nonfinite loss or derivative")
    return float(value), grad


def loss(params, x, target, role, mask=None):
    return loss_output_grad(forward(params, x), target, role, mask)[0]


def loss_grads(params, x, target, role, mask=None):
    x = np.asarray(x, dtype=np.float64)
    h = np.tanh(x @ params["W1"]+params["b1"])
    value, dz = loss_output_grad(h @ params["W2"]+params["b2"], target, role, mask)
    dh = (dz @ params["W2"].T)*(1-h*h)
    return value, {"W1": x.T @ dh, "b1": dh.sum(axis=0), "W2": h.T @ dz, "b2": dz.sum(axis=0)}


def clip_grads(grads, limit=5.0):
    norm = float(np.sqrt(sum(float(np.sum(grads[k]**2)) for k in PARAMETER_KEYS)))
    if not np.isfinite(norm):
        raise FloatingPointError("Nonfinite gradient norm")
    scale = min(1.0, limit/norm) if norm else 1.0
    return {k: grads[k]*scale for k in PARAMETER_KEYS}, {"grad_norm_before": norm, "clip_scale": scale}


def adam_step(params, m, v, t, grads, lr=.01, beta1=.9, beta2=.999, eps=1e-8, clip=5.0):
    clipped, info = clip_grads(grads, clip)
    t = int(t)+1
    for key in PARAMETER_KEYS:
        m[key] *= beta1
        m[key] += (1-beta1)*clipped[key]
        v[key] *= beta2
        v[key] += (1-beta2)*clipped[key]**2
        params[key] -= lr*(m[key]/(1-beta1**t))/(np.sqrt(v[key]/(1-beta2**t))+eps)
    return t, info


def hard_predictions(logits, role):
    logits = np.asarray(logits)
    if role == "speaker":
        return {"hard_bits": (logits >= 0).astype(np.uint8)}
    bits = (logits[:, 4:] >= 0).astype(np.uint8)
    low_weights = np.array([16, 8, 4, 2, 1], dtype=np.int64)
    high_weights = np.array([64, 32], dtype=np.int64)
    return {"pred_op": logits[:, :4].argmax(axis=1).astype(np.int64), "operand_bits": bits,
            "pred_a": bits[:, :5] @ low_weights+bits[:, 10:12] @ high_weights,
            "pred_b": bits[:, 5:10] @ low_weights+bits[:, 12:14] @ high_weights}


def dimensions(params):
    n_in, hidden = params["W1"].shape
    n_out = params["W2"].shape[1]
    count = int(sum(v.size for v in params.values()))
    return {"shape": [n_in, hidden, n_out], "parameters": count, "parameter_bytes_float64": 8*count,
            "adam_values": 2*count, "adam_bytes_float64": 16*count,
            "forward_dense_mac_per_row": n_in*hidden+hidden*n_out}


def save(path, params, m, v, t, role, seed, step, arm, extra_metadata=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    metadata = {"schema": "growth-channel-checkpoint-v1", "role": role, "model_seed": int(seed),
                "step": int(step), "optimizer_step": int(t), "arm": arm, "dtype": "float64",
                **dimensions(params), "optimizer": {"name": "Adam", "lr": .01, "beta1": .9,
                "beta2": .999, "eps": 1e-8, "clip_global_norm": 5.0}}
    if extra_metadata:
        metadata["run_metadata"] = extra_metadata
    values = {f"param_{k}": params[k] for k in PARAMETER_KEYS}
    values.update({f"adam_m_{k}": m[k] for k in PARAMETER_KEYS})
    values.update({f"adam_v_{k}": v[k] for k in PARAMETER_KEYS})
    values["metadata_json"] = np.array(json.dumps(metadata, sort_keys=True))
    np.savez_compressed(path, **values)


def load(path):
    with np.load(Path(path), allow_pickle=False) as z:
        metadata = json.loads(str(z["metadata_json"]))
        if metadata.get("schema") != "growth-channel-checkpoint-v1":
            raise ValueError("Unexpected checkpoint schema")
        params = {k: z[f"param_{k}"].astype(np.float64, copy=True) for k in PARAMETER_KEYS}
        m = {k: z[f"adam_m_{k}"].astype(np.float64, copy=True) for k in PARAMETER_KEYS}
        v = {k: z[f"adam_v_{k}"].astype(np.float64, copy=True) for k in PARAMETER_KEYS}
    return {"params": params, "m": m, "v": v, "t": int(metadata["optimizer_step"]),
            "role": metadata["role"], "seed": int(metadata["model_seed"]),
            "step": int(metadata["step"]), "metadata": metadata}
