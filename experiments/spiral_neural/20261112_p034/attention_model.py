"""P034 B1: fixed 2,596-parameter, binary-only causal attention learner.

This module contains no SLE parser, oracle, curriculum, or scientific experiment.
Normal forward computes the shared 3-class head at the last visible token only.
``forward_all`` exposes every causal state and applies that same head to each.
"""
import json
import os
from pathlib import Path
import sys

sys.dont_write_bytecode = True
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
import numpy as np


PARAMETER_NAMES = (
    "embedding", "position", "Wq", "bq", "Wk", "bk", "Wv", "bv",
    "Wo", "bo", "ln1_scale", "ln1_bias", "ln2_scale", "ln2_bias",
    "W1", "b1", "W2", "b2", "Wh", "bh",
)
SHAPES = (
    (2, 16), (16, 16), (16, 16), (16,), (16, 16), (16,),
    (16, 16), (16,), (16, 16), (16,), (16,), (16,), (16,), (16,),
    (16, 33), (33,), (33, 16), (16,), (16, 3), (3,),
)


class Model:
    """Manual NumPy backprop; float32 for training, optional float64 for checks."""

    PARAMETER_NAMES = PARAMETER_NAMES
    parameter_index = {name: i for i, name in enumerate(PARAMETER_NAMES)}
    architecture = "p034-b1-causal-single-head-preln-d16-ff33-v1"
    ln_epsilon = 1e-5
    learning_rate = .003
    beta1 = .9
    beta2 = .999
    adam_epsilon = 1e-8
    clip_norm = 1.

    def __init__(self, seed, L=16, H=16, *, dtype=np.float32):
        if (L, H) != (16, 16):
            raise ValueError("Frozen B1 requires L=16 and d=16")
        self.dtype = np.dtype(dtype)
        if self.dtype not in (np.dtype(np.float32), np.dtype(np.float64)):
            raise ValueError("Only float32 training or float64 numerical checks")
        self.seed = int(seed)
        self.L, self.H, self.F, self.t = 16, 16, 33, 0
        self.rng = np.random.default_rng(self.seed)
        # Unused by this fixed architecture, retained for reference API parity.
        self.growth_rng = np.random.default_rng(self.seed + 73000)
        self.p = []
        for name, shape in zip(PARAMETER_NAMES, SHAPES):
            if name in ("embedding", "position"):
                value = self.rng.normal(0., .02, shape)
            elif name.startswith("W"):
                bound = np.sqrt(6. / sum(shape))
                value = self.rng.uniform(-bound, bound, shape)
            elif name.endswith("_scale"):
                value = np.ones(shape)
            else:
                value = np.zeros(shape)
            self.p.append(np.asarray(value, dtype=self.dtype))
        self.m = [np.zeros_like(a) for a in self.p]
        self.v = [np.zeros_like(a) for a in self.p]
        self.birth = [np.zeros(a.shape, dtype=np.int64) for a in self.p]
        self.inference_calls = 0
        self.costs = {phase: {} for phase in
                      ("train_forward", "train_backward", "inference_forward")}
        self.last_gradient_norm = 0.
        self.last_gradient_scale = 1.
        assert self.parameters == 2596

    @property
    def parameters(self):
        return sum(a.size for a in self.p)

    @property
    def train_macs(self):
        return sum(self.costs[phase].get("dense_macs", 0) +
                   self.costs[phase].get("attention_macs", 0)
                   for phase in ("train_forward", "train_backward"))

    @property
    def inference_macs(self):
        cost = self.costs["inference_forward"]
        return cost.get("dense_macs", 0) + cost.get("attention_macs", 0)

    @property
    def parameter_optimizer_arrays_bytes(self):
        return sum(a.nbytes for group in (self.p, self.m, self.v, self.birth)
                   for a in group)

    def array_bytes(self):
        """Persistent numeric arrays, not peak RSS or temporary activation memory."""
        result = {name: sum(a.nbytes for a in arrays) for name, arrays in
                  (("parameters", self.p), ("adam_m", self.m),
                   ("adam_v", self.v), ("birth_int64", self.birth))}
        result["total"] = sum(result.values())
        return result

    @staticmethod
    def cost_for_prefix(n, *, backward=False, all_positions=False):
        """Count executed dense matmuls, including masked attention cells.

        One MAC is one multiply-accumulate; biases, residuals, nonlinearities,
        optimizer, masking and reductions are not MACs. Softmax/LN element
        counts are separate workload descriptors, not FLOP or time estimates.
        The backward path is defined for the last-token training loss only.
        """
        if not isinstance(n, (int, np.integer)) or not 1 <= n <= 16:
            raise ValueError("Prefix length must be 1..16")
        if backward and all_positions:
            raise ValueError("No all-position loss/backward path is implemented")
        head_positions = n if all_positions else 1
        multiplier = 2 if backward else 1
        return {
            "calls": 1,
            "visible_tokens": int(n),
            "head_positions": int(head_positions),
            "dense_macs": int(multiplier * (2080 * n + 48 * head_positions)),
            "attention_macs": int(multiplier * 32 * n * n),
            "attention_softmax_elements": int(n * n),
            "attention_softmax_valid_elements": int(n * (n + 1) // 2),
            "layernorm_token_elements": int(2 * n * 16),
            # Output softmax is executed in loss_grad only, not raw forward.
            "output_softmax_elements": 3 if backward else 0,
        }

    def _charge(self, n, *, training=False, backward=False, all_positions=False):
        phase = "train_backward" if backward else (
            "train_forward" if training else "inference_forward")
        cost = self.cost_for_prefix(n, backward=backward,
                                    all_positions=all_positions)
        for key, value in cost.items():
            self.costs[phase][key] = self.costs[phase].get(key, 0) + value
        if not training and not backward:
            self.inference_calls += 1

    def _validate_text(self, text, *, allow_overflow=False):
        if not isinstance(text, str) or not text or set(text) - set("01"):
            raise ValueError("Only a nonempty actual binary prefix is accepted")
        if not allow_overflow and len(text) > self.L:
            raise ValueError("Visible prefix exceeds L=16")

    def _ln(self, x, scale, bias):
        centered = x - x.mean(axis=1, keepdims=True)
        inv = 1. / np.sqrt((centered * centered).mean(axis=1, keepdims=True)
                           + self.ln_epsilon)
        normalized = centered * inv
        return normalized * scale + bias, normalized, inv

    @staticmethod
    def _ln_backward(gradient, normalized, inv, scale):
        dnormalized = gradient * scale
        dx = inv * (dnormalized - dnormalized.mean(axis=1, keepdims=True)
                    - normalized * (dnormalized * normalized).mean(
                        axis=1, keepdims=True))
        return dx, (gradient * normalized).sum(axis=0), gradient.sum(axis=0)

    def _forward(self, text, *, training=False, all_positions=False):
        self._validate_text(text)
        (embedding, position, Wq, bq, Wk, bk, Wv, bv, Wo, bo,
         g1, b1, g2, b2, W1, bf1, W2, bf2, Wh, bh) = self.p
        n = len(text)
        ids = np.fromiter((int(c) for c in text), dtype=np.int64, count=n)
        x = embedding[ids] + position[:n]
        u1, norm1, inv1 = self._ln(x, g1, b1)
        q, k, v = u1 @ Wq + bq, u1 @ Wk + bk, u1 @ Wv + bv
        scores = (q @ k.T) * .25
        mask = np.tri(n, dtype=bool)
        scores = np.where(mask, scores, -np.inf)
        weights = np.exp(scores - scores.max(axis=1, keepdims=True))
        weights /= weights.sum(axis=1, keepdims=True)
        context = weights @ v
        residual = x + context @ Wo + bo
        u2, norm2, inv2 = self._ln(residual, g2, b2)
        pre = u2 @ W1 + bf1
        activated = np.maximum(pre, 0.)
        states = residual + activated @ W2 + bf2
        logits = states @ Wh + bh if all_positions else states[-1] @ Wh + bh
        self._charge(n, training=training, all_positions=all_positions)
        return {
            "ids": ids, "embeddings": x, "ln1": u1, "norm1": norm1,
            "inv1": inv1, "q": q, "k": k, "v": v,
            "attention_weights": weights, "attention_context": context,
            "attention_residual": residual, "ln2": u2, "norm2": norm2,
            "inv2": inv2, "ffn_pre": pre, "ffn_hidden": activated,
            "states": states, "logits": logits,
        }

    def forward(self, text, training=False):
        cache = self._forward(text, training=training)
        return cache["embeddings"], cache["states"], cache["logits"]

    def forward_all(self, text, training=False):
        """All-position causal states/logits; same shared head, no teacher input."""
        return self._forward(text, training=training, all_positions=True)

    def loss_grad(self, text, target):
        if not isinstance(target, str) or len(target) != 1 or target not in "01S":
            raise ValueError("Target must be one of 0, 1, S")
        c = self._forward(text, training=True)
        n = len(text)
        index = "01S".index(target)
        z = c["logits"]
        lp = z - np.logaddexp.reduce(z)
        dz = np.exp(lp)
        dz[index] -= 1.
        (embedding, position, Wq, bq, Wk, bk, Wv, bv, Wo, bo,
         g1, b1, g2, b2, W1, bf1, W2, bf2, Wh, bh) = self.p
        grads = [np.zeros_like(a) for a in self.p]
        grads[18] = c["states"][-1, :, None] * dz[None, :]
        grads[19] = dz.copy()
        dh = np.zeros_like(c["states"])
        dh[-1] = dz @ Wh.T
        grads[16] = c["ffn_hidden"].T @ dh
        grads[17] = dh.sum(axis=0)
        dpre = (dh @ W2.T) * (c["ffn_pre"] > 0.)
        grads[14] = c["ln2"].T @ dpre
        grads[15] = dpre.sum(axis=0)
        dr, grads[12], grads[13] = self._ln_backward(
            dpre @ W1.T, c["norm2"], c["inv2"], g2)
        dr += dh
        grads[8] = c["attention_context"].T @ dr
        grads[9] = dr.sum(axis=0)
        dc = dr @ Wo.T
        da = dc @ c["v"].T
        dv = c["attention_weights"].T @ dc
        ds = c["attention_weights"] * (
            da - (da * c["attention_weights"]).sum(axis=1, keepdims=True))
        ds *= .25
        dq, dk = ds @ c["k"], ds.T @ c["q"]
        grads[2], grads[3] = c["ln1"].T @ dq, dq.sum(axis=0)
        grads[4], grads[5] = c["ln1"].T @ dk, dk.sum(axis=0)
        grads[6], grads[7] = c["ln1"].T @ dv, dv.sum(axis=0)
        du1 = dq @ Wq.T + dk @ Wk.T + dv @ Wv.T
        dx, grads[10], grads[11] = self._ln_backward(
            du1, c["norm1"], c["inv1"], g1)
        dx += dr
        # Scatter-add is essential: a binary token may occur repeatedly.
        np.add.at(grads[0], c["ids"], dx)
        grads[1][:n] = dx
        self._charge(n, training=True, backward=True)
        return -float(lp[index]), grads, "01S"[int(z.argmax())]

    def step(self, text, target):
        loss, grads, prediction = self.loss_grad(text, target)
        norm_squared = np.asarray(0., dtype=self.dtype)
        for grad in grads:
            norm_squared += np.sum(grad * grad, dtype=self.dtype)
        norm = np.sqrt(norm_squared)
        if not np.isfinite(loss) or not np.isfinite(norm):
            raise FloatingPointError("Nonfinite loss or gradient")
        scale = min(1., self.clip_norm / max(norm, 1e-12))
        self.last_gradient_norm, self.last_gradient_scale = float(norm), float(scale)
        self.t += 1
        for i, grad in enumerate(grads):
            grad *= scale
            self.m[i] *= self.beta1
            self.m[i] += (1. - self.beta1) * grad
            self.v[i] *= self.beta2
            self.v[i] += (1. - self.beta2) * grad * grad
            age = self.t - self.birth[i]
            bc1 = 1. - np.power(np.asarray(self.beta1, dtype=self.dtype), age,
                                dtype=self.dtype)
            bc2 = 1. - np.power(np.asarray(self.beta2, dtype=self.dtype), age,
                                dtype=self.dtype)
            self.p[i] -= self.learning_rate * (self.m[i] / bc1) / (
                np.sqrt(self.v[i] / bc2) + self.adam_epsilon)
        return prediction, loss

    def lesson(self, q, a):
        self._validate_text(q)
        if not isinstance(a, str) or set(a) - set("01"):
            raise ValueError("Teacher answer must contain binary tokens only")
        if len(q) + len(a) > self.L:
            raise ValueError("Full teacher prefix would exceed L=16")
        predictions, total_loss = "", 0.
        for i, target in enumerate(a + "S"):
            prediction, loss = self.step(q + a[:i], target)
            predictions += prediction
            total_loss += loss
        return predictions, total_loss

    def generate(self, q):
        self._validate_text(q, allow_overflow=True)
        tokens = ""
        for _ in range(8):
            prefix = q + tokens
            if len(prefix) > self.L:
                return tokens, True
            token = "01S"[int(self.forward(prefix)[2].argmax())]
            tokens += token
            if token == "S":
                return tokens, False
        # As in the frozen reference, action exhaustion does not force STOP.
        # The overflow flag means a forward request was blocked by context.
        return tokens, False

    def state(self):
        """Full reproducible learner state; diagnostic cost counters excluded."""
        arrays = {f"{label}{i}": a.copy() for label, group in
                  (("p", self.p), ("m", self.m), ("v", self.v),
                   ("birth", self.birth)) for i, a in enumerate(group)}
        arrays.update({
            "t": np.array(self.t), "L": np.array(self.L),
            "H": np.array(self.H), "F": np.array(self.F),
            "seed": np.array(self.seed), "dtype": np.array(self.dtype.str),
            "architecture": np.array(self.architecture),
            "rng": np.array(json.dumps(self.rng.bit_generator.state, sort_keys=True)),
            "growth_rng": np.array(json.dumps(self.growth_rng.bit_generator.state,
                                              sort_keys=True)),
            "optimizer": np.array(json.dumps({
                "lr": self.learning_rate, "beta1": self.beta1,
                "beta2": self.beta2, "eps": self.adam_epsilon,
                "clip_norm": self.clip_norm, "ln_eps": self.ln_epsilon,
            }, sort_keys=True)),
        })
        return arrays

    def load_state(self, state):
        """Restore validated arrays and both RNG states without pickle."""
        expected = self.state()
        if set(state) != set(expected):
            raise ValueError("Checkpoint keys do not match this architecture")
        for key in ("L", "H", "F", "architecture", "optimizer", "dtype"):
            if not np.array_equal(state[key], expected[key]):
                raise ValueError(f"Checkpoint configuration mismatch: {key}")
        t = int(state["t"])
        if t < 0:
            raise ValueError("Negative optimizer step")
        replacement = {}
        for label in ("p", "m", "v", "birth"):
            group = []
            for i, shape in enumerate(SHAPES):
                a = np.array(state[f"{label}{i}"], copy=True)
                wanted_dtype = np.dtype(np.int64) if label == "birth" else self.dtype
                if a.shape != shape or a.dtype != wanted_dtype or not np.isfinite(a).all():
                    raise ValueError(f"Invalid checkpoint array: {label}{i}")
                if label == "v" and np.any(a < 0):
                    raise ValueError("Negative Adam second moment")
                if label == "birth" and (np.any(a < 0) or np.any(a > t)):
                    raise ValueError("Invalid parameter birth step")
                group.append(a)
            replacement[label] = group
        rng = np.random.default_rng()
        rng.bit_generator.state = json.loads(str(state["rng"]))
        growth_rng = np.random.default_rng()
        growth_rng.bit_generator.state = json.loads(str(state["growth_rng"]))
        self.p, self.m, self.v, self.birth = (
            replacement[k] for k in ("p", "m", "v", "birth"))
        self.t, self.seed = t, int(state["seed"])
        self.rng, self.growth_rng = rng, growth_rng
        return self

    @classmethod
    def from_state(cls, state):
        model = cls(int(state["seed"]), dtype=np.dtype(str(state["dtype"])))
        return model.load_state(state)

    def save_checkpoint(self, path):
        with Path(path).open("wb") as stream:
            np.savez(stream, **self.state())

    @classmethod
    def load_checkpoint(cls, path):
        with np.load(Path(path), allow_pickle=False) as state:
            return cls.from_state(state)
