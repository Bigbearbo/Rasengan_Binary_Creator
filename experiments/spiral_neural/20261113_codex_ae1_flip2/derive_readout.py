"""One-shot read-only token statistics after F2 science completion. Stdlib only; no NN import."""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import zipfile

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
CLASSES = ("E1", "E2", "F1", "F2")
MANIFEST_SHA = "b8d385db584aec294f5363556f045aecb3ceb8864dc20f4816c30bc591426d95"
SOURCES = {"run_f2.py": "08dcba6ef9074c640e3e94321d56492dc27d1c1a3f0a77f0c09afd17c5215dc6",
           "protocol.json": "7c58a7209b50c20442db78c48e085ff28e5e462840256615b9150e5d4f1e6958",
           "test_f2.py": "41d1f04e9d0fa47ead4df3871131f98dbc409ebc105d58810a8ff53de7ff9e94"}


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def file_sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            digest.update(block)
    return digest.hexdigest()


def inventory(science, prereg, source):
    paths = {"science/" + path.relative_to(science).as_posix(): path for path in science.rglob("*") if path.is_file()}
    paths.update({"prereg/" + name: prereg / name for name in ("manifest.json", "source-freeze.json", "inputs.zip")})
    paths.update({"source/" + name: source / name for name in SOURCES})
    paths["helper/derive_readout.py"] = Path(__file__).resolve()
    return {name: {"sha256": file_sha(path), "bytes": path.stat().st_size} for name, path in sorted(paths.items())}


def output_map(outputs):
    result = {row["question_id"]: row for row in outputs}
    assert len(result) == len(outputs), "Duplicate output QID"
    return result


def correctness(rows, outputs):
    table = output_map(outputs)
    assert set(table) == {row["question_id"] for row in rows}
    return {row["question_id"]: table[row["question_id"]]["tokens"] == row["A"] + "S" for row in rows}


def churn(rows, previous, current):
    old, new = correctness(rows, previous), correctness(rows, current)
    result, changed = {}, {}
    for name in CLASSES:
        selected = [row["question_id"] for row in rows if row["class"] == name]
        lost = [qid for qid in selected if old[qid] and not new[qid]]
        recovered = [qid for qid in selected if not old[qid] and new[qid]]
        result[name] = {"questions": len(selected), "previous_correct_to_wrong": len(lost), "previous_wrong_to_correct": len(recovered),
                        "retained_correct": sum(old[qid] and new[qid] for qid in selected),
                        "retained_wrong": sum(not old[qid] and not new[qid] for qid in selected)}
        changed[name] = {"lost": lost, "recovered": recovered}
    return result, changed


def checked_point(rows, generation, metrics):
    table = output_map(generation["rows"])
    detail = output_map(metrics["metrics"]["per_question"])
    correct = correctness(rows, generation["rows"])
    assert set(detail) == set(table)
    for row in rows:
        qid, expected = row["question_id"], row["A"] + "S"
        output, data = table[qid], detail[qid]
        actual = output["tokens"]
        assert output["class"] == data["class"] == row["class"]
        assert output["pair_id"] == row["pair_id"]
        assert data["whole_correct"] == output["whole_correct"] == correct[qid]
        assert data["answer_bit_correct"] == [actual[i:i + 1] == bit for i, bit in enumerate(row["A"])]
        first = next((i for i in range(max(len(actual), len(expected))) if actual[i:i + 1] != expected[i:i + 1]), None)
        assert data["first_error_position_zero_based"] == first
        assert data["STOP_position_correct"] == (actual.endswith("S") and len(actual) == len(expected))
        assert len(data["words"]) == len(row["A"]) // 6
        for slot, word in enumerate(data["words"]):
            start = slot * 6
            assert word == {"information5_correct": actual[start:start + 5] == row["A"][start:start + 5],
                            "tail0_correct": actual[start + 5:start + 6] == "0",
                            "complete6_correct": actual[start:start + 6] == row["A"][start:start + 6]}
    by_class = metrics["metrics"]["by_class"]
    for name in CLASSES:
        part = [data for data in detail.values() if data["class"] == name]
        assert generation["scores"][name] == {"questions": 900, "whole_correct": sum(data["whole_correct"] for data in part)}
        assert by_class[name]["questions"] == 900 and by_class[name]["whole_correct"] == generation["scores"][name]["whole_correct"]
        for slot in (0, 1):
            word_rows = [data["words"][slot] for data in part if len(data["words"]) > slot]
            expected = {"questions": len(word_rows), **{key: sum(word[key] for word in word_rows) if word_rows else None
                        for key in ("information5_correct", "tail0_correct", "complete6_correct")}}
            assert by_class[name]["words"][f"word{slot + 1}"] == expected
        assert by_class[name]["first_error_kind_histogram"] == dict(Counter(data["first_error_kind"] for data in part))
        assert by_class[name]["termination_kind_histogram"] == dict(Counter(data["termination_kind"] for data in part))
    return table, by_class


def example(row, before, after, source):
    return {"question_id": row["question_id"], "pair_id": row["pair_id"], "class": row["class"], "payload": row["payload"],
            "Q": row["Q"], "expected": row["A"] + "S", "previous_generated": before["tokens"],
            "generated": after["tokens"], "source": source}


def final_TF_readout(rows, final):
    assert len(final["truth"]) == 3600 and final["inference_calls"] == 36000
    result = {}
    for expected, row in zip(rows, final["truth"], strict=True):
        for key in ("question_id", "pair_id", "class", "payload", "Q", "A"):
            assert expected[key] == row[key]
        assert row["expected"] == row["A"] + "S" and len(row["TF"]) == len(row["A"]) + 1
        for position, target in enumerate(row["A"] + "S"):
            token = row["TF"][position]
            assert token["position"] == position and token["target"] == target and token["prefix"] == row["Q"] + row["A"][:position]
    for name in CLASSES:
        selected = [row for row in final["truth"] if row["class"] == name]
        tokens = [point for row in selected for point in row["TF"]]
        result[name] = {"questions": len(selected), "TF_correct": sum(point["prediction"] == point["target"] for point in tokens),
                        "TF_targets": len(tokens), "TF_CE_mean": math.fsum(point["target_CE"] for point in tokens) / len(tokens),
                        "information_bit_correct": sum(point["prediction"] == point["target"] for row in selected for point in row["TF"][:-1] if point["position"] % 6 < 5),
                        "information_bit_targets": sum(len(row["A"]) // 6 * 5 for row in selected),
                        "word_tail0_correct": sum(point["prediction"] == "0" for row in selected for point in row["TF"][:-1] if point["position"] % 6 == 5),
                        "STOP_correct": sum(row["TF"][-1]["prediction"] == "S" for row in selected)}
        assert final["metrics"][name] == {key: result[name][key] for key in ("questions", "TF_correct", "TF_targets")}
    return result


def derive(science, prereg, source):
    assert not (science / "failure.json").exists()
    # All three finalTF files and these last runner writes must exist before readout.
    for name in ("compact.json", "timing.json", "storage.json", "baseline-gate.json"):
        assert (science / name).is_file(), "Science not complete: " + name
    compact, timings = read(science / "compact.json"), read(science / "timing.json")
    assert compact["status"] == "complete" and compact["manifest_sha256"] == MANIFEST_SHA
    assert compact["exact_full_replays"] == []
    assert len(timings["trajectories"]) == 3 and all(item["mode"] == "primary" for item in timings["trajectories"])
    assert read(science / "baseline-gate.json")["all_three_passed"] is True
    for name, expected in SOURCES.items():
        assert file_sha(source / name) == expected
    assert file_sha(prereg / "manifest.json") == MANIFEST_SHA
    manifest = read(prereg / "manifest.json")
    assert read(science / "manifest.json") == manifest
    assert file_sha(prereg / "inputs.zip") == manifest["archive"]["sha256"]
    with zipfile.ZipFile(prereg / "inputs.zip") as archive:
        content = archive.read("questions.json")
    assert hashlib.sha256(content).hexdigest() == manifest["files"]["questions.json"]["sha256"]
    rows = json.loads(content.decode("utf-8"))
    assert len(rows) == 3600 and [row["question_id"] for row in rows] == list(range(3600))
    students = []
    for seed in (101, 202, 303):
        folder = science / f"seed{seed}"
        training, curve = read(folder / "training-summary.json"), read(folder / "curve.json")
        epochs = training["epochs"]
        assert 1 <= epochs <= 40 and len(curve) == epochs and training["new_updates"] == 36000 * epochs
        assert training["new_training_dense_MAC"] == 758016000 * epochs
        baseline, base_generation = read(folder / "baseline.json"), read(folder / "baseline-generation.json")
        base_metrics = read(folder / "baseline-token-metrics.json")
        base_table, base_by_class = checked_point(rows, base_generation, base_metrics)
        assert baseline["scores"] == base_generation["scores"] and baseline["token_metrics"] == base_by_class
        assert base_metrics["churn"]["comparison_available"] is False and baseline["baseline_streak"] == 0
        for counts in base_metrics["churn"]["by_class"].values():
            assert counts["previous_correct_to_wrong"] is counts["previous_wrong_to_correct"] is None
        previous, previous_scores = base_generation["rows"], baseline["scores"]
        points, swaps = [], []
        streak, first_full, stable = 0, None, None
        totals = {name: {"lost": 0, "recovered": 0} for name in CLASSES}
        for epoch in range(1, epochs + 1):
            record = read(folder / f"epoch-{epoch:03}.json")
            free, metric_file = read(folder / f"generation-{epoch:03}.json"), read(folder / f"token-metrics-{epoch:03}.json")
            table, by_class = checked_point(rows, free, metric_file)
            assert curve[epoch - 1] == record and record["epoch"] == epoch
            assert record["scores"] == free["scores"] and record["token_metrics"] == by_class
            assert record["new_updates"] == 36000 * epoch and record["new_training_dense_MAC"] == 758016000 * epoch
            assert record["training"]["targets"] == 36000
            computed_churn, changed = churn(rows, previous, free["rows"])
            assert metric_file["churn"]["by_class"] == computed_churn == record["churn"]["by_class"]
            assert record["churn"]["previous_point"] == ("baseline" if epoch == 1 else epoch - 1)
            previous_table = output_map(previous)
            for name in CLASSES:
                lost, recovered = changed[name]["lost"], changed[name]["recovered"]
                totals[name]["lost"] += len(lost)
                totals[name]["recovered"] += len(recovered)
                if lost and recovered and previous_scores[name]["whole_correct"] == free["scores"][name]["whole_correct"]:
                    swaps.append({"epoch": epoch, "class": name, "unchanged_whole_score": free["scores"][name]["whole_correct"],
                                  "lost": len(lost), "recovered": len(recovered),
                                  "lost_example": example(rows[lost[0]], previous_table[lost[0]], table[lost[0]], f"seed{seed}/generation-{epoch:03}.json"),
                                  "recovered_example": example(rows[recovered[0]], previous_table[recovered[0]], table[recovered[0]], f"seed{seed}/generation-{epoch:03}.json")})
            full = all(free["scores"][name]["whole_correct"] == 900 for name in CLASSES)
            streak = streak + 1 if full else 0
            if full and first_full is None:
                first_full = epoch
            if streak >= 2:
                stable = epoch
            assert record["streak"] == streak and record["first_full_epoch"] == first_full
            expected_stop = "two_consecutive_all_class_passes" if streak >= 2 else "epoch_cap" if epoch == 40 else None
            assert record["stop_reason"] == expected_stop
            if expected_stop is not None:
                assert epoch == epochs, "Saved trajectory continued after its frozen stop decision"
            points.append({"epoch": epoch, "scores": free["scores"], "streak": streak, "stop_reason": record["stop_reason"],
                           "token_metrics": by_class, "churn": computed_churn})
            previous, previous_scores = free["rows"], free["scores"]
        assert training["first_full_epoch"] == first_full and training["stable_pass_epoch"] == stable
        compact_student = next(item for item in compact["students"] if item["seed"] == seed)
        assert all(compact_student[key] == value for key, value in training.items())
        final = read(folder / "final-truth.json")
        tf = final_TF_readout(rows, final)
        final_table = output_map([row["generation"] for row in final["truth"]])
        assert final_table == output_map(previous), "Final TF did not reuse last free outputs"
        final_by_class = points[-1]["token_metrics"]
        minima, retention = {}, {}
        for name in CLASSES:
            minimum = min(point["scores"][name]["whole_correct"] for point in points)
            with_baseline = min(minimum, baseline["scores"][name]["whole_correct"])
            minima[name] = {"training_epoch_minimum": minimum,
                            "epochs_at_minimum": [point["epoch"] for point in points if point["scores"][name]["whole_correct"] == minimum],
                            "minimum_including_baseline": with_baseline,
                            "points_at_minimum_including_baseline": (["baseline"] if baseline["scores"][name]["whole_correct"] == with_baseline else []) + [point["epoch"] for point in points if point["scores"][name]["whole_correct"] == with_baseline]}
            if name != "F2":
                retention[name] = {"baseline_whole_correct": baseline["scores"][name]["whole_correct"],
                                   "ever_below900_during_training": minimum < 900,
                                   "epochs_below900": [point["epoch"] for point in points if point["scores"][name]["whole_correct"] < 900],
                                   "final_whole_correct": previous_scores[name]["whole_correct"], "final_all900_retained": previous_scores[name]["whole_correct"] == 900}
        examples = []
        for qid in (1800, 1830, 2700, 2701, 2730):
            item = example(rows[qid], base_table[qid], final_table[qid], f"seed{seed}/final-truth.json")
            item["literal_control_shapes_are_answer_bits_only"] = True
            examples.append(item)
        pair36 = example(rows[2736], base_table[2736], final_table[2736], f"seed{seed}/final-truth.json")
        assert pair36["pair_id"] == 36 and pair36["payload"][:2] == [1, 6]
        students.append({"seed": seed, "epochs": epochs, "stop_reason": training["stop_reason"],
                         "first_full_all_four_epoch": first_full, "stable_two_epoch_pass": stable,
                         "parent_counters": training["parent_counters"], "baseline_scores": baseline["scores"],
                         "baseline_F2_token_metrics": base_by_class["F2"], "baseline_token_metrics_by_class": base_by_class,
                         "class_whole_minima": minima, "old_three_retention": retention,
                         "new_question_exposures": 3600 * epochs, "new_targets": 36000 * epochs,
                         "exposure_scope": "One complete target-set exposure per Q per epoch; not contiguous questionwise updates",
                         "new_training_dense_MAC": training["new_training_dense_MAC"],
                         "churn_totals_by_class": totals, "net_zero_swap_events_with_examples": swaps,
                         "final_scores": previous_scores, "final_token_metrics_by_class": final_by_class, "final_TF": tf,
                         "literal_control_shape_examples": examples, "pair36_F2": pair36, "curve": points,
                         "formal_training_replay": "not_planned"})
    return {"schema": "ae1-f2-derived-readout-v1", "status": "complete", "author": "Codex fixed statistics helper",
            "manifest_sha256": MANIFEST_SHA, "students": students,
            "new_question_exposures_total": sum(row["new_question_exposures"] for row in students),
            "new_targets_total": sum(row["new_targets"] for row in students),
            "formal_training_replays": [], "helper_new_NN_forward_calls": 0, "helper_new_optimizer_updates": 0,
            "scope": "Derived only from saved tokens, metrics/churn, scores and final TF records; no training replay or new inference"}


def self_test():
    rows = [{"question_id": 1, "class": "F2", "A": "0"}, {"question_id": 2, "class": "F2", "A": "1"}]
    before = [{"question_id": 1, "tokens": "0S"}, {"question_id": 2, "tokens": "0S"}]
    after = [{"question_id": 1, "tokens": "1S"}, {"question_id": 2, "tokens": "1S"}]
    result, changed = churn(rows, before, after)
    assert result["F2"]["previous_correct_to_wrong"] == result["F2"]["previous_wrong_to_correct"] == 1
    assert changed["F2"] == {"lost": [1], "recovered": [2]}
    assert "numpy" not in sys.modules and "torch" not in sys.modules
    print('{"status":"PASS","synthetic_token_cases":1,"NN_calls":0,"optimizer_calls":0,"science_readout_runs":0}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--science", type=Path, default=HERE / "science")
    parser.add_argument("--prereg", type=Path, default=HERE / "prereg")
    parser.add_argument("--source-root", type=Path, default=HERE.parents[1] / "outputs/ae1-flip2")
    parser.add_argument("--out", type=Path, default=HERE / "derived-readout.json")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    science, prereg, source, out = args.science.resolve(), args.prereg.resolve(), args.source_root.resolve(), args.out.resolve()
    assert not out.exists(), "One-shot output already exists"
    assert not any(out.is_relative_to(root) for root in (science, prereg, source)), "Output must not be inside immutable input directories"
    assert all((science / name).is_file() for name in ("compact.json", "timing.json", "storage.json")), "Science is not complete"
    calls = {name: 0 for name in ("forward", "step", "lesson", "loss_grad", "grow")}
    forbidden_events = []
    def profile(frame, event, value):
        if event == "call" and type(frame.f_locals.get("self")).__name__ == "Model" and frame.f_code.co_name in calls:
            calls[frame.f_code.co_name] += 1
            raise AssertionError("NN/optimizer calls prohibited")
    def audit(event, values):
        if event in ("subprocess.Popen", "os.system", "socket.connect", "socket.__new__"):
            forbidden_events.append(event)
            raise AssertionError("External process/network prohibited")
        if event == "import" and values and (str(values[0]).split(".")[0] in {"numpy", "torch", "run_f2", "run_mixed"}):
            forbidden_events.append(event + ":" + str(values[0]))
            raise AssertionError("NN module import prohibited")
        if event == "open" and values and isinstance(values[0], str):
            mode = values[1] if len(values) > 1 else None
            flags = values[2] if len(values) > 2 and isinstance(values[2], int) else 0
            writing = (isinstance(mode, str) and any(char in mode for char in "wax+")) or bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
            if writing:
                assert Path(values[0]).resolve() == out, "Write to original evidence prohibited"
    sys.addaudithook(audit)
    sys.setprofile(profile)
    before = inventory(science, prereg, source)
    result = derive(science, prereg, source)
    after = inventory(science, prereg, source)
    sys.setprofile(None)
    assert before == after and not any(calls.values()) and not forbidden_events
    assert "numpy" not in sys.modules and "torch" not in sys.modules
    result.update(source_hashes_before=before, source_hashes_after=after, source_files_unchanged=True,
                  runtime_guard={"NN_optimizer_method_calls": calls, "NN_modules_imported": False,
                                 "external_process_or_network_events": forbidden_events, "writes_allowed_only_to_readout": True})
    with out.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, sort_keys=True, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"status": "PASS", "readout_file": out.name, "sha256": file_sha(out),
                      "students": len(result["students"]), "NN_calls": 0, "optimizer_calls": 0}, sort_keys=True))


if __name__ == "__main__":
    main()
