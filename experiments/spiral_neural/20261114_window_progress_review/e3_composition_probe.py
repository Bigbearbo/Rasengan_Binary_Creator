"""Read-only E3 c/d factorial probe on all three actual PR49 final states.

Prepare performs static evidence/codec checks only. Execute requires a Git-frozen
copy of this file and its protocol, verifies every old E3 output first, and never
imports a training runner. No optimizer or checkpoint-writing path exists.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import time
import zipfile

if sys.flags.optimize:
    raise RuntimeError("Run without Python optimization: evidence and baseline guards must remain enabled")

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
import numpy as np

SOURCE_HEAD = "915219a4a787ea1452b798104d2158a6d8c82410"
SOURCE_REL = "experiments/spiral_neural/20261113_codex_e3_continuation"
PUBLICATION_SHA = "526c95e09d38c5a283675954cc0365a4811bddc73381d35fc675e1b9e17e8d5e"
LEARNER_SOURCE_SHA = "db39661a7b16d13e64db7acc5dae22a81ca59dc39cf467ed4c58addbc0654013"
MODEL_AST_SHA = "3cff2fc5cceb6edfbbffc791f37f0eff503a9c7fd778a5d9bc8d22b08402f910"
SEEDS = (101, 202, 303)
CELLS = (("c0_d0", 0, 0), ("c1_d0", 1, 0), ("c0_d1", 0, 1), ("c1_d1", 1, 1))
MAC = 10432


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git_blob(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def state_sha(state):
    h = hashlib.sha256()
    for name, value in sorted(state.items()):
        h.update(canonical([name, value.dtype.str, list(value.shape)]).encode())
        h.update(value.tobytes(order="C"))
    return h.hexdigest()


class Evidence:
    def __init__(self, repo_root):
        self.root = Path(repo_root).resolve()
        self.source = self.root / SOURCE_REL
        raw = (self.source / "publication-manifest.json").read_bytes()
        assert sha(raw) == PUBLICATION_SHA
        pinned = subprocess.check_output([
            "git", "-C", str(self.root), "show",
            SOURCE_HEAD + ":" + SOURCE_REL + "/publication-manifest.json"])
        assert raw == pinned
        self.publication = json.loads(raw)
        self.watched = {"publication-manifest.json": sha(raw)}
        self.archives = {}
        self.members = {}

    def get(self, archive_name, member):
        meta = self.publication["archives"][archive_name]
        if archive_name not in self.archives:
            raw = (self.source / archive_name).read_bytes()
            assert len(raw) == meta["bytes"]
            assert sha(raw) == meta["sha256"] and git_blob(raw) == meta["Git_blob"]
            self.watched[archive_name] = sha(raw)
            archive = zipfile.ZipFile(io.BytesIO(raw))
            assert len(archive.namelist()) == len(set(archive.namelist()))
            self.archives[archive_name] = archive
        raw = self.archives[archive_name].read(member)
        expected = meta["members"][member]
        assert len(raw) == expected["bytes"]
        assert sha(raw) == expected["sha256"] and git_blob(raw) == expected["Git_blob"]
        self.members[archive_name + ":" + member] = sha(raw)
        return raw

    def unchanged(self):
        return all(sha((self.source / name).read_bytes()) == digest
                   for name, digest in self.watched.items())


def word(value):
    assert type(value) is int and 0 <= value < 30
    return f"{value:05b}0"


def encode(payload):
    assert len(payload) == 4
    return "01" + "010" + "0110" + "".join(map(word, payload)) + "111100"


def expected(payload):
    # Teacher-side metric only; forward and generate never receive this value.
    return "".join(map(word, payload[:3])) + "S"


def load_inputs(repo_root):
    ev = Evidence(repo_root)
    bank = json.loads(ev.get("inputs.zip", "payloads.json"))
    old = json.loads(ev.get("inputs.zip", "questions.json"))
    source = ev.get("inputs.zip", "source/p030_binary_continual.py")
    assert sha(source) == LEARNER_SOURCE_SHA
    model = next(n for n in ast.parse(source.decode()).body
                 if isinstance(n, ast.ClassDef) and n.name == "Model")
    assert sha(ast.dump(model, include_attributes=False).encode()) == MODEL_AST_SHA
    assert len(bank) == 900 and {(x[0], x[1]) for x in bank} == {
        (a, b) for a in range(30) for b in range(30)}
    assert all(len(x) == 4 and all(type(v) is int and 0 <= v < 30 for v in x) for x in bank)
    assert len(old) == len({x["Q"] for x in old}) == 4500
    old_e3 = sorted((r for r in old if r["class"] == "E3"), key=lambda r: r["pair_id"])
    assert len(old_e3) == 900
    rows = {}
    for cell_index, (cell, dc, dd) in enumerate(CELLS):
        rows[cell] = []
        for pair, original in enumerate(bank):
            a, b, c, d = original
            payload = [a, b, (c + dc) % 30, (d + dd) % 30]
            q = encode(payload)
            truth = expected(payload)
            assert len(q) == 39 and len(truth) == 19 and set(q) <= {"0", "1"}
            assert truth[5] == truth[11] == truth[17] == "0"
            rows[cell].append({"probe_id": cell_index * 900 + pair,
                               "parent_question_id": old_e3[pair]["question_id"],
                               "pair_id": pair, "cell": cell,
                               "delta_c": dc, "delta_d": dd,
                               "parent_payload": original, "payload": payload,
                               "Q": q, "expected": truth})
            if not dc and not dd:
                parent = old_e3[pair]
                assert parent["pair_id"] == pair and parent["payload"] == payload
                assert parent["Q"] == q and parent["A"] + "S" == truth
                assert parent["op"] == "010" and parent["r"] == 3
    all_rows = [r for cell, _, _ in CELLS for r in rows[cell]]
    assert len({r["Q"] for r in all_rows}) == 3600
    parent_q = {r["Q"] for r in old}
    assert all(r["Q"] not in parent_q for r in all_rows if r["cell"] != "c0_d0")
    for pair in range(900):
        b, c, d, cd = (rows[cell][pair] for cell, _, _ in CELLS)
        assert b["expected"] == d["expected"] and c["expected"] == cd["expected"]
        assert b["expected"][:12] == c["expected"][:12]
        assert b["expected"][12:18] != c["expected"][12:18]
    states, archived = {}, {}
    for seed, archive_number in zip(SEEDS, (1, 3, 5)):
        archive = f"science-{archive_number:03}.zip"
        raw = ev.get(archive, f"science/seed{seed}/final-after-TF.npz")
        with np.load(io.BytesIO(raw), allow_pickle=False) as a:
            state = {name: a[name].copy() for name in a.files}
        for name, value in state.items():
            if value.dtype.kind in "fc":
                assert np.all(np.isfinite(value)), name
            value.setflags(write=False)
        assert (int(state["L"]), int(state["H"])) == (80, 64)
        assert sum(state[f"p{i}"].size for i in range(4)) == 10499
        assert state["p0"].shape == (160, 64) and state["p2"].shape == (64, 3)
        assert all(state[f"p{i}"].dtype == np.dtype("float32") for i in range(4))
        states[seed] = state
        saved = json.loads(ev.get(archive, f"science/seed{seed}/final-generation.json"))["rows"]
        assert len(saved) == 4500
        archived[seed] = sorted((r for r in saved if r["class"] == "E3"), key=lambda r: r["pair_id"])
        assert len(archived[seed]) == 900
        for row, archive_row in zip(rows["c0_d0"], archived[seed]):
            assert row["pair_id"] == archive_row["pair_id"]
            assert row["parent_question_id"] == archive_row["question_id"]
    return ev, rows, states, archived


def make_protocol(repo_root):
    ev, rows, states, _ = load_inputs(repo_root)
    return {
        "id": "WINDOW-E3-CD-FACTORIAL-READONLY-20261114",
        "author": "視窗GPT / delegated independent probe agent",
        "source_PR": 49, "source_commit": SOURCE_HEAD,
        "source_directory": SOURCE_REL,
        "source_publication_manifest_sha256": PUBLICATION_SHA,
        "source_files": ev.watched, "selected_source_members": ev.members,
        "probe_source_sha256": sha(Path(__file__).read_bytes()),
        "profile": "Exact existing SLE-AEM3-n5-v1 Echo r3, Q39, four legal IDs0..29, first three complete six-bit words then externalS",
        "provenance": "F=immutable PR49 actual final checkpoints and archived E3 outputs; A=new c/d factorial diagnostic; new generated output is read-only T, not Codex training",
        "seeds": list(SEEDS), "model": {"L": 80, "H": 64, "parameters": 10499},
        "checkpoint_selection": "All three actual final-after-TF states at the declared eight-new-epoch cap; no historical best-state or seed selection",
        "parent_state_sha256": {str(s): state_sha(states[s]) for s in SEEDS},
        "cells": [{"name": cell, "delta_c_mod30": dc, "delta_d_mod30": dd,
                   "question_count": 900, "questions_sha256": sha(canonical(rows[cell]).encode())}
                  for cell, dc, dd in CELLS],
        "factorial_interpretation": "c is the third requested answer word; changing it changes the last six answer bits. d is outside r3 and should not change the answer. +1 mod30 is a legal value intervention, not necessarily one bit.",
        "order": "All three checkpoints first regenerate all900 archived E3 answers, total2700 exact archive matches required. Only then evaluate each seed in101/202/303 order on c1_d0,c0_d1,c1_d1, each ascending pair_id.",
        "generation": "Independent scalar-prefix NumPy float32 dense forward; one-hot rawQ+own generated bits; greedy0/1/S; cap32; L80 guard; no label, teacher prefix, expected-length cutoff or forcedSTOP",
        "inference_budget": {"baseline_questions": 2700, "new_questions": 8100,
                             "maximum_forward_calls": 10800 * 32, "dense_MAC_per_forward": MAC},
        "learning": "0 optimizer calls and no manual parameter changes; all complete p/m/v/birth/t/RNG/events/counter arrays read-only; no checkpoint written; source archive and state hashes before/after",
        "metrics": "Per seed/cell whole, three words, first two combined, STOP, first error and exact lengths. Paired c edges: changed output versus correctly tracking changed third word, first-two stability, both-whole exact. Paired d edges: output invariance versus both-whole exact; invariance alone can preserve a wrong answer. Raw paired metrics use only already generated tokens.",
        "stopping": "Abort all new intervention inference if any of2700 baseline outputs/flags/exact indicators differs from archive. One execution; no repairs, newseeds, test-driven curriculum or result-driven rerun.",
        "decision_boundary": "Descriptive diagnostic without a fitted success threshold. It does not select checkpoint, change training, or overturn PR49's failed strict-mastery gate. Low transfer motivates a separately preregistered generalization study; high transfer still does not prove a universal copy algorithm.",
        "limits": "All three intervention cells have new Q relative to the fixed900bank. Only c-changing cells have new relevant (a,b,c) combinations; d-only retains (a,b,c) and changes answer-irrelevant context. Numeric values are previously exposed, and this is not a researcher-blind external test. Known source failures are retained. Frozen deterministic +1 interventions do not establish all-context behavior or identify an internal neural mechanism.",
        "preflight": {"unique_probe_questions": 3600, "new_questions_vs_parent4500": 2700,
                      "source_unchanged": ev.unchanged(), "neural_forward_calls": 0, "optimizer_calls": 0}
    }


def forward(state, text):
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
        output += "01S"[int(forward(state, prefix).argmax())]
        calls += 1
        if output[-1] == "S":
            return output, calls, "stop"
    return output, calls, "cap_exhausted"


def make_record(seed, row, output, calls, reason):
    truth = row["expected"]
    first = next((i for i in range(max(len(output), len(truth)))
                  if output[i:i+1] != truth[i:i+1]), None)
    return {"seed": seed, **row, "actual": output, "reason": reason,
            "exact": output == truth,
            "word_correct": [output[i:i+6] == truth[i:i+6] for i in (0, 6, 12)],
            "first_two_correct": output[:12] == truth[:12],
            "stop_position_exact": reason == "stop" and len(output) == 19,
            "first_error_position_zero_based": first, "forward_calls": calls}


def summarize(records):
    return {"questions": len(records), "whole_correct": sum(r["exact"] for r in records),
            "word_correct": [sum(r["word_correct"][i] for r in records) for i in range(3)],
            "first_two_correct": sum(r["first_two_correct"] for r in records),
            "stop_position_correct": sum(r["stop_position_exact"] for r in records),
            "first_error_histogram": dict(sorted(Counter("none" if r["first_error_position_zero_based"] is None
                                               else str(r["first_error_position_zero_based"]) for r in records).items())),
            "output_length_histogram": dict(sorted(Counter(str(len(r["actual"])) for r in records).items())),
            "termination_histogram": dict(Counter(r["reason"] for r in records))}


def segment(record, start, end):
    part = record["actual"][start:end]
    return part if len(part) == end-start and set(part) <= {"0", "1"} else None


def paired_metrics(records_by_cell):
    result = {}
    edges = (("c_effect_d0", "c0_d0", "c1_d0", "c"),
             ("c_effect_d1", "c0_d1", "c1_d1", "c"),
             ("d_effect_c0", "c0_d0", "c0_d1", "d"),
             ("d_effect_c1", "c1_d0", "c1_d1", "d"))
    for name, left, right, factor in edges:
        counts = Counter()
        for a, b in zip(records_by_cell[left], records_by_cell[right]):
            assert a["pair_id"] == b["pair_id"]
            counts["pairs"] += 1
            counts["left_whole_correct"] += a["exact"]
            counts["right_whole_correct"] += b["exact"]
            counts["both_whole_correct"] += a["exact"] and b["exact"]
            counts["whole_output_invariant"] += a["actual"] == b["actual"]
            a12, b12 = segment(a, 0, 12), segment(b, 0, 12)
            a3, b3 = segment(a, 12, 18), segment(b, 12, 18)
            counts["first_two_complete_both"] += a12 is not None and b12 is not None
            counts["first_two_output_stable"] += a12 is not None and a12 == b12
            counts["first_two_correct_both"] += a["first_two_correct"] and b["first_two_correct"]
            counts["third_word_complete_both"] += a3 is not None and b3 is not None
            counts["third_word_output_changed"] += a3 is not None and b3 is not None and a3 != b3
            counts["third_word_output_invariant"] += a3 is not None and a3 == b3
            counts["third_word_correct_both"] += a["word_correct"][2] and b["word_correct"][2]
            counts["stop_position_correct_both"] += a["stop_position_exact"] and b["stop_position_exact"]
            for k in range(12, 18):
                if a["expected"][k] != b["expected"][k]:
                    counts["third_word_target_bit_changes"] += 1
                    counts["target_bit_changes_followed_correctly"] += (
                        a["actual"][k:k+1] == a["expected"][k]
                        and b["actual"][k:k+1] == b["expected"][k])
            if factor == "c":
                assert a["expected"][:12] == b["expected"][:12]
                assert a["expected"][12:18] != b["expected"][12:18]
            else:
                assert a["expected"] == b["expected"]
        result[name] = {"factor": factor, "left_cell": left, "right_cell": right, **dict(counts)}
    return result


def verify_freeze(root, protocol_path, frozen_commit):
    assert re.fullmatch(r"[0-9a-f]{40}", frozen_commit or "")
    for file in (Path(__file__).resolve(), protocol_path.resolve()):
        relative = file.relative_to(root).as_posix()
        pinned = subprocess.check_output(["git", "-C", str(root), "show", frozen_commit + ":" + relative])
        assert file.read_bytes() == pinned, relative


def execute(repo_root, protocol_path, out, frozen_commit):
    root, out = Path(repo_root).resolve(), Path(out).resolve()
    verify_freeze(root, protocol_path, frozen_commit)
    frozen = json.loads(protocol_path.read_text())
    assert frozen == make_protocol(root), "Static protocol/source drift before inference"
    out.mkdir(parents=True, exist_ok=False)
    write_json(out / "execution_intent.json", {
        "protocol_id": frozen["id"], "frozen_commit": frozen_commit,
        "created_at_UTC": datetime.now(timezone.utc).isoformat(),
        "protocol_sha256": sha(protocol_path.read_bytes()),
        "probe_source_sha256": sha(Path(__file__).read_bytes()),
        "new_optimizer_updates": 0, "auto_retry": False})
    ev, rows, states, archived = load_inputs(root)
    initial = {s: state_sha(states[s]) for s in SEEDS}
    results = {s: {} for s in SEEDS}
    calls, baseline_matches, phase = 0, 0, "baseline"
    started = time.perf_counter()
    try:
        with (out / "raw_cases.jsonl").open("x", encoding="utf-8") as stream:
            for seed in SEEDS:
                records = []
                for row, prior in zip(rows["c0_d0"], archived[seed]):
                    output, n, reason = generate(states[seed], row["Q"])
                    calls += n
                    record = make_record(seed, row, output, n, reason)
                    records.append(record)
                    stream.write(canonical(record) + "\n")
                    assert (output, reason == "cap_exhausted", reason == "context_exhausted", record["exact"]) == (
                        prior["tokens"], prior["cap_exhausted"], prior["context_exhausted"], prior["whole_correct"]), (
                            "Baseline archive mismatch", seed, row["pair_id"])
                    baseline_matches += 1
                results[seed]["c0_d0"] = records
            assert baseline_matches == 2700
            phase = "new_interventions"
            for seed in SEEDS:
                for cell, _, _ in CELLS[1:]:
                    records = []
                    for row in rows[cell]:
                        output, n, reason = generate(states[seed], row["Q"])
                        calls += n
                        record = make_record(seed, row, output, n, reason)
                        records.append(record)
                        stream.write(canonical(record) + "\n")
                    results[seed][cell] = records
        elapsed = time.perf_counter() - started
        unchanged = {str(s): initial[s] == state_sha(states[s]) for s in SEEDS}
        assert all(unchanged.values()) and ev.unchanged()
        assert all(not array.flags.writeable for state in states.values() for array in state.values())
        baseline_calls = sum(r["forward_calls"] for s in SEEDS for r in results[s]["c0_d0"])
        report = {"id": frozen["id"], "status": "completed", "frozen_commit": frozen_commit,
                  "source_PR": 49, "source_commit": SOURCE_HEAD,
                  "baseline_archive_exact_matches": baseline_matches,
                  "total_generated_questions": sum(len(v) for cells in results.values() for v in cells.values()),
                  "metrics": {str(s): {cell: summarize(results[s][cell]) for cell, _, _ in CELLS} for s in SEEDS},
                  "paired_metrics": {str(s): paired_metrics(results[s]) for s in SEEDS},
                  "cost": {"baseline_forward_calls": baseline_calls,
                           "new_intervention_forward_calls": calls-baseline_calls,
                           "total_forward_calls": calls, "dense_MAC_per_forward": MAC,
                           "total_inference_dense_MAC": calls*MAC, "new_optimizer_updates": 0,
                           "manual_weight_updates": 0, "inference_wall_seconds": elapsed},
                  "state_sha256_before": {str(s): initial[s] for s in SEEDS},
                  "state_sha256_after": {str(s): state_sha(states[s]) for s in SEEDS},
                  "all_state_arrays_read_only": True, "source_unchanged": ev.unchanged(),
                  "raw_cases_sha256": sha((out/"raw_cases.jsonl").read_bytes()),
                  "raw_cases_bytes": (out/"raw_cases.jsonl").stat().st_size,
                  "runtime": {"python": platform.python_version(), "numpy": np.__version__,
                              "platform": platform.platform(), "OPENBLAS_NUM_THREADS": os.environ["OPENBLAS_NUM_THREADS"]},
                  "limits": frozen["limits"]}
        assert report["total_generated_questions"] == 10800
        assert calls <= frozen["inference_budget"]["maximum_forward_calls"]
        write_json(out/"summary.json", report)
        return report
    except Exception as error:
        write_json(out/"failure.json", {"phase": phase, "error_type": type(error).__name__,
                   "error": str(error), "baseline_archive_exact_matches": baseline_matches,
                   "forward_calls_completed": calls, "new_optimizer_updates": 0,
                   "source_unchanged": ev.unchanged(), "auto_retry": False})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "execute"))
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, default=Path(__file__).with_name("e3_probe_protocol.json"))
    parser.add_argument("--frozen-commit")
    args = parser.parse_args()
    if args.mode == "prepare":
        args.out.mkdir(parents=True, exist_ok=True)
        path = args.out/"e3_probe_protocol.json"
        assert not path.exists(), "Refuse to overwrite an existing protocol"
        protocol = make_protocol(args.repo_root)
        write_json(path, protocol)
        print(canonical({"status": "prepared_no_NN", "protocol_sha256": sha(path.read_bytes()),
                         "probe_source_sha256": protocol["probe_source_sha256"],
                         "preflight": protocol["preflight"]}))
    else:
        report = execute(args.repo_root, args.protocol, args.out, args.frozen_commit)
        print(canonical({"status": report["status"], "baseline_archive_exact_matches": report["baseline_archive_exact_matches"],
                         "metrics": report["metrics"], "cost": report["cost"],
                         "raw_cases_sha256": report["raw_cases_sha256"]}))


if __name__ == "__main__":
    main()
