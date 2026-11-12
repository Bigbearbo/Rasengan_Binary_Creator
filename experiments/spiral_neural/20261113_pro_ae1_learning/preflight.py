"""Bounded engineering checks without a learned forward pass or optimizer step."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import tempfile
import numpy as np
import learner
import run_trial

HERE = Path(__file__).resolve().parent


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


class FakeLogits:
    """A host-loop fixture, not a network or trained-copy result."""
    def __init__(self, actions):
        self.L = 80
        self.actions = actions
        self.prefixes = []

    def forward(self, text):
        require(set(text) <= {"0", "1"}, "Nonbinary host input")
        action = self.actions[len(self.prefixes)]
        self.prefixes.append(text)
        logits = np.full(3, -1.0)
        logits["01S".index(action)] = 1.0
        return None, None, logits


def main():
    protocol, data, targets, pools = run_trial.inputs()
    serialized = data["teacher_target_pool"]
    require(len(targets) == len(serialized), "Global pool length differs")
    for index, (prefix, target, row_id, position) in enumerate(targets):
        supplied = serialized[index]
        require((supplied["prefix"], supplied["target"], supplied["row_id"], supplied["position"])
                == (prefix, target, row_id, position), "Dataset and runner target pools differ")
    for phase, pool in zip(data["phases"], pools):
        require(pool.tolist() == phase["target_pool_indices"], "Dataset and runner phase pools differ")
    q = next(r["Q"] for r in data["rows"] if r["N"] == r["r"] == 4)
    host_cases = []
    for actions, expected, exhausted in (("S", "S", False),
                                         ("1" * 24 + "S", "1" * 24 + "S", False),
                                         ("0" * 32, "0" * 32, True)):
        fake = FakeLogits(actions)
        generated = learner.generate(fake, q)
        require(generated == {"tokens": expected, "overflow": False, "cap_exhausted": exhausted},
                "Host generation STOP/cap behavior differs")
        require(fake.prefixes == [q + actions[:i] for i in range(len(actions))],
                "Host passed something other than Q plus own output")
        require(max(map(len, fake.prefixes)) <= 70, "cap32 context arithmetic differs")
        host_cases.append({"actions": len(actions), "cap_exhausted": exhausted,
                           "max_prefix": max(map(len, fake.prefixes))})
    # Serialize an untouched random initial state; this does not call forward.
    net = learner.new_student(101)
    state = learner.state_sha(learner.full_state(net))
    with tempfile.TemporaryDirectory(prefix="ae1_state_check_") as directory:
        checkpoint = Path(directory) / "state.npz"
        learner.save_state(checkpoint, net)
        restored = learner.load_state(checkpoint)
        require(learner.state_sha(learner.full_state(restored)) == state, "Full state roundtrip differs")
        try:
            learner.save_state(checkpoint, net)
        except FileExistsError:
            pass
        else:
            raise RuntimeError("Checkpoint overwrite was allowed")
    require(net.inference_calls == net.t == net.train_macs == 0, "Preflight performed neural work")
    result = {"status": "PASS", "teacher_targets_compared": len(targets),
              "phase_pool_sizes": [len(p) for p in pools], "host_loop_cases": host_cases,
              "untouched_initial_full_state_roundtrip": True, "checkpoint_overwrite_rejected": True,
              "actual_neural_forward_calls": 0, "actual_optimizer_updates": 0,
              "synthetic_logit_host_calls": sum(c["actions"] for c in host_cases),
              "external_model_calls": 0,
              "source_sha256": {name: hashlib.sha256((HERE/name).read_bytes()).hexdigest()
                                for name in ("preflight.py", "run_trial.py", "learner.py")}}
    run_trial.write_new(HERE / "preflight_checks.json", result)
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
