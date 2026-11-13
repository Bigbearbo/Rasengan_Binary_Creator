"""Read-only composition probe of the immutable PR28 final checkpoints.

This module has no optimizer or training path. F2 is a new researcher-proposed
interpretation (Flip the first two words), not an existing PR28 test result.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import time
import zipfile

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SOURCE = HERE.parent / "20261113_codex_ae1_mixed_flip"
PROTO = HERE / "f2_probe_protocol.json"
RESULT = HERE / "f2_results.json"
HEAD = "5ceec0c42507bb5646dc0d87089f4a86e0e6269c"
PUB_SHA = "dcf039bf53bcc39669d06daced174dffb133fa75c93e52acbc2fd59433b45a11"
SEEDS = (101, 202, 303)
FINAL_EPOCHS = {101: 6, 202: 9, 303: 9}


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git_blob(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def state_sha(state):
    h = hashlib.sha256()
    for name, value in sorted(state.items()):
        h.update(canonical([name, value.dtype.str, list(value.shape)]).encode())
        h.update(value.tobytes(order="C"))
    return h.hexdigest()


class Evidence:
    """Verify the published manifest, ZIP bytes and every selected member."""

    def __init__(self):
        raw = (SOURCE / "publication-manifest.json").read_bytes()
        assert sha(raw) == PUB_SHA
        self.publication = json.loads(raw)
        self.watched = {"publication-manifest.json": sha(raw)}
        self.archives = {}
        self.members = {}

    def get(self, archive_name, member):
        meta = self.publication["archives"][archive_name]
        if archive_name not in self.archives:
            raw = (SOURCE / archive_name).read_bytes()
            assert len(raw) == meta["bytes"]
            assert sha(raw) == meta["sha256"] and git_blob(raw) == meta["Git_blob"]
            self.watched[archive_name] = sha(raw)
            self.archives[archive_name] = zipfile.ZipFile(io.BytesIO(raw))
        raw = self.archives[archive_name].read(member)
        expected = meta["members"][member]
        assert len(raw) == expected["bytes"]
        assert sha(raw) == expected["sha256"] and git_blob(raw) == expected["Git_blob"]
        self.members[archive_name + ":" + member] = sha(raw)
        return raw

    def unchanged(self):
        return all(sha((SOURCE / name).read_bytes()) == digest
                   for name, digest in self.watched.items())


def input_word(value):
    assert type(value) is int and 0 <= value < 30
    return f"{value:05b}0"


def encode(op, r, payload):
    assert op in ("010", "100") and r in (1, 2) and len(payload) == 4
    return "01" + op + f"{r:03b}0" + "".join(map(input_word, payload)) + "111100"


def expected(op, r, payload):
    # Teacher-side labels only. The neural forward receives only Q+its own output.
    return "".join(f"{(31 ^ v) if op == '100' else v:05b}0"
                   for v in payload[:r]) + "S"


def load_inputs():
    ev = Evidence()
    bank = json.loads(ev.get("inputs.zip", "payloads.json"))
    old_rows = json.loads(ev.get("inputs.zip", "questions.json"))
    source = ev.get("inputs.zip", "source/p030_binary_continual.py")
    assert sha(source) == "db39661a7b16d13e64db7acc5dae22a81ca59dc39cf467ed4c58addbc0654013"
    model = next(n for n in ast.parse(source.decode()).body
                 if isinstance(n, ast.ClassDef) and n.name == "Model")
    assert sha(ast.dump(model, include_attributes=False).encode()) == "3cff2fc5cceb6edfbbffc791f37f0eff503a9c7fd778a5d9bc8d22b08402f910"
    assert len(bank) == 900 and {(v[0], v[1]) for v in bank} == {
        (a, b) for a in range(30) for b in range(30)}
    assert len(old_rows) == 2700
    for index, row in enumerate(old_rows):
        op, r = (("010", 1), ("010", 2), ("100", 1))[index // 900]
        payload = bank[index % 900]
        assert row["Q"] == encode(op, r, payload)
        assert row["A"] + "S" == expected(op, r, payload)
    new_rows = [{"question_id": 2700 + pair, "pair_id": pair, "class": "F2",
                 "op": "100", "r": 2, "payload": payload,
                 "Q": encode("100", 2, payload), "A": expected("100", 2, payload)[:-1]}
                for pair, payload in enumerate(bank)]
    assert len({r["Q"] for r in old_rows + new_rows}) == 3600
    assert all(len(r["Q"]) == 39 and len(r["A"]) == 12 for r in new_rows)
    assert all(r["A"][5] == r["A"][11] == "0" for r in new_rows)
    assert new_rows[0]["A"] == "111110111110"
    assert new_rows[1]["A"] == "111110111100"
    states, archived = {}, {}
    for seed in SEEDS:
        archive = f"science-seed{seed}-001.zip"
        raw = ev.get(archive, f"science/seed{seed}/final-state.npz")
        with np.load(io.BytesIO(raw), allow_pickle=False) as a:
            state = {name: a[name].copy() for name in a.files}
        for name, value in state.items():
            if value.dtype.kind in "fc":
                assert np.all(np.isfinite(value))
            value.setflags(write=False)
        assert (int(state["L"]), int(state["H"])) == (80, 64)
        assert sum(state[f"p{i}"].size for i in range(4)) == 10499
        assert state["p0"].shape == (160, 64) and state["p2"].shape == (64, 3)
        states[seed] = state
        raw_g = ev.get(archive, f"science/seed{seed}/generation-{FINAL_EPOCHS[seed]:03}.json")
        archived[seed] = json.loads(raw_g)["rows"]
        assert len(archived[seed]) == 2700
    return ev, old_rows, new_rows, states, archived


def make_protocol():
    ev, old, new, states, _ = load_inputs()
    return {
        "id": "WINDOW-F2-FROZEN-CHECKPOINT-PROBE-20261113",
        "author": "視窗GPT / delegated read-only probe agent",
        "source_commit": HEAD, "source_PR": 28,
        "source_publication_manifest_sha256": PUB_SHA,
        "source_files": ev.watched, "selected_source_members": ev.members,
        "probe_source_sha256": sha(Path(__file__).read_bytes()),
        "candidate_profile": "SLE-AEM2-probe: extend op100 to r2, complement five information bits in each of the first two words; retain both tail0; literal answer30/31 permitted; externalS only stops",
        "provenance": "F=immutable PR28 evidence; A=proposed F2 semantics and probe; future output is new read-only T, not Codex training",
        "seeds": list(SEEDS), "model": {"L": 80, "H": 64, "parameters": 10499},
        "parent_state_sha256": {str(s): state_sha(states[s]) for s in SEEDS},
        "old_questions_sha256": sha(canonical(old).encode()),
        "new_questions_sha256": sha(canonical(new).encode()),
        "order": "All three checkpoints must first regenerate all2700 old E1/E2/F1 answers and exactly match their archived outputs. Only then probe each checkpoint on all900 F2 questions in ascending pair_id.",
        "generation": "Independent scalar-prefix NumPy float32 dense forward, same one-hot/tanh/matmul order as the pinned original; own generated prefix only; greedy0/1/S; cap32; L80 guard; no expected-length cutoff",
        "inference_budget": {"baseline_questions": 8100, "F2_questions": 2700,
                             "maximum_forward_calls": 10800 * 32, "dense_MAC_per_forward": 10432},
        "learning": "0 optimizer calls; no manual weight changes; p/m/v/birth/t/RNG/events/counters arrays read-only; no checkpoint written; all source files hashed before/after",
        "outputs": "All10800 raw Q/expected/generated records; full-answer, first/second-word and STOP-position metrics; error pattern counts; actual forward/MAC and wall time; per-seed state and archive hash invariance",
        "stopping": "Abort before F2 if any old answer fails or differs from its archive; no repair, additional seed, training or result-driven rerun",
        "interpretation": "F2 is a previously untrained op/r combination on already exposed values and payloads. Success only shows this bounded combination transfer; failure does not invalidate old finite-bank learning or establish a model/encoding limit.",
        "preflight": {"questions_checked_without_NN": 3600, "F2_targets": 11700,
                      "old_rows_preserved": 2700, "neural_forward_calls": 0, "optimizer_calls": 0,
                      "literal_control_answer_cases": True, "source_unchanged": ev.unchanged()},
    }


def forward(state, text):
    # Independent implementation; never import the learner or expose labels here.
    L = int(state["L"])
    if not text or set(text) - {"0", "1"} or len(text) > L:
        raise ValueError("raw binary prefix outside model input domain")
    slots = np.zeros((L, 2), dtype=state["p0"].dtype)
    for i, bit in enumerate(text):
        slots[i, int(bit)] = 1
    hidden = np.tanh(slots.reshape(1, -1) @ state["p0"] + state["p1"])
    return (hidden @ state["p2"] + state["p3"])[0]


def generate(state, q):
    output, calls = "", 0
    for _ in range(32):
        prefix = q + output
        if len(prefix) > int(state["L"]):
            return output, calls, "context_exhausted"
        token = "01S"[int(forward(state, prefix).argmax())]
        output += token
        calls += 1
        if token == "S":
            return output, calls, "stop"
    return output, calls, "cap_exhausted"


def evaluate(state, rows):
    records, total_calls = [], 0
    for row in rows:
        output, calls, reason = generate(state, row["Q"])
        total_calls += calls
        truth = row["A"] + "S"
        records.append({"question_id": row["question_id"], "pair_id": row["pair_id"],
                        "class": row["class"], "payload": row["payload"], "Q": row["Q"],
                        "expected": truth, "actual": output, "reason": reason,
                        "exact": output == truth,
                        "first_word_exact": output[:6] == truth[:6],
                        "second_word_exact": output[6:12] == truth[6:12] if len(row["A"]) == 12 else None,
                        "stop_position_exact": reason == "stop" and len(output) == len(truth),
                        "forward_calls": calls})
    return records, total_calls


def summarise(records):
    metrics = {}
    for name in sorted({r["class"] for r in records}):
        selected = [r for r in records if r["class"] == name]
        errors = Counter()
        patterns = Counter()
        for r in selected:
            if not r["exact"]:
                if r["reason"] != "stop":
                    errors[r["reason"]] += 1
                elif len(r["actual"]) < len(r["expected"]):
                    errors["early_stop"] += 1
                elif len(r["actual"]) > len(r["expected"]):
                    errors["late_stop"] += 1
                else:
                    errors["correct_stop_wrong_content"] += 1
            if name == "F2":
                a, b = r["payload"][:2]
                echo_a, echo_b = input_word(a), input_word(b)
                flip_a, flip_b = f"{31 ^ a:05b}0", f"{31 ^ b:05b}0"
                candidates = {"flip_then_echo": flip_a + echo_b + "S",
                              "echo_then_flip": echo_a + flip_b + "S",
                              "echo_both": echo_a + echo_b + "S",
                              "flip_first_then_stop": flip_a + "S"}
                for key, value in candidates.items():
                    patterns[key] += r["actual"] == value
        metrics[name] = {"questions": len(selected), "whole_correct": sum(r["exact"] for r in selected),
                         "first_word_correct": sum(r["first_word_exact"] for r in selected),
                         "second_word_correct": sum(r["second_word_exact"] is True for r in selected) if name in ("E2", "F2") else None,
                         "stop_position_correct": sum(r["stop_position_exact"] for r in selected),
                         "error_categories": dict(errors), "descriptive_output_patterns": dict(patterns)}
    return metrics


def execute(frozen_commit):
    assert re.fullmatch(r"[0-9a-f]{40}", frozen_commit or "")
    assert not RESULT.exists(), "Refuse to overwrite or silently repeat a completed probe"
    for file in (Path(__file__), PROTO):
        relative = file.relative_to(ROOT).as_posix()
        committed = subprocess.check_output(["git", "show", f"{frozen_commit}:{relative}"], cwd=ROOT)
        assert committed == file.read_bytes(), "Code/protocol differ from recorded preregistration"
    protocol = json.loads(PROTO.read_text())
    assert protocol == make_protocol(), "Frozen preflight no longer matches inputs/code"
    ev, old_rows, new_rows, states, archived = load_inputs()
    before = {s: state_sha(states[s]) for s in SEEDS}
    start = time.perf_counter()
    old_records, new_records, baseline_calls, new_calls = {}, {}, {}, {}
    for seed in SEEDS:
        records, calls = evaluate(states[seed], old_rows)
        assert all(r["exact"] for r in records), f"Baseline failed for seed{seed}"
        assert all(r["actual"] == archived[seed][i]["tokens"] for i, r in enumerate(records))
        old_records[seed], baseline_calls[seed] = records, calls
        print(f"BASELINE seed{seed} 2700/2700 exact archived outputs; forwards={calls}", flush=True)
    for seed in SEEDS:
        records, calls = evaluate(states[seed], new_rows)
        new_records[seed], new_calls[seed] = records, calls
        print("F2", seed, canonical(summarise(records)), flush=True)
    after = {s: state_sha(states[s]) for s in SEEDS}
    assert before == after and ev.unchanged()
    total_calls = sum(baseline_calls.values()) + sum(new_calls.values())
    report = {"id": protocol["id"], "author": "視窗GPT", "status": "complete",
              "source_commit": HEAD, "frozen_commit": frozen_commit,
              "protocol_sha256": sha(PROTO.read_bytes()), "probe_source_sha256": sha(Path(__file__).read_bytes()),
              "environment": {"python": platform.python_version(), "numpy": np.__version__,
                              "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1"},
              "baseline_gate": {"all_three_passed_before_F2": True, "archive_outputs_exact": 8100},
              "neural_forward_calls": total_calls, "inference_dense_MAC": total_calls * 10432,
              "optimizer_calls": 0, "manual_parameter_updates": 0, "wall_seconds": time.perf_counter() - start,
              "source_files_unchanged": True, "all_state_arrays_unchanged": before == after,
              "source_file_sha256": ev.watched, "source_member_sha256": ev.members,
              "students": [{"seed": s, "parent_state_sha256": before[s], "final_state_sha256": after[s],
                            "baseline_metrics": summarise(old_records[s]), "F2_metrics": summarise(new_records[s])["F2"],
                            "baseline_forward_calls": baseline_calls[s], "F2_forward_calls": new_calls[s],
                            "baseline_records": old_records[s], "F2_records": new_records[s]} for s in SEEDS],
              "limits": protocol["interpretation"],
              "nvidia_status": "skipped_unavailable", "nvidia_calls": 0}
    with RESULT.open("x", encoding="utf-8") as out:
        json.dump(report, out, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        out.write("\n")
    print("RESULT", RESULT.name, sha(RESULT.read_bytes()), "forwards", total_calls,
          "wall_seconds", report["wall_seconds"], flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("prepare", "check", "execute"))
    parser.add_argument("--frozen-commit")
    args = parser.parse_args()
    if args.command == "prepare":
        p = make_protocol()
        with PROTO.open("x", encoding="utf-8") as out:
            json.dump(p, out, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
            out.write("\n")
        print("PREPARED", canonical(p["preflight"]), sha(PROTO.read_bytes()))
    elif args.command == "check":
        assert json.loads(PROTO.read_text()) == make_protocol()
        print("PASS preflight: 3600 Q, source/member/checkpoint hashes; 0 NN forward, 0 optimizer")
    else:
        execute(args.frozen_commit)


if __name__ == "__main__":
    main()
