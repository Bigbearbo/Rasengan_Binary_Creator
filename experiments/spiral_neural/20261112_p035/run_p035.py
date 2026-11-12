"""P035 fixed-clock input-codec x capacity-timing comparison.

Default is synthetic engineering preflight. --execute runs the preregistered
twelve new students exactly once and independently replays every target update.
The pinned P030 Model, its optimizer and its growth implementation are unchanged.
"""
import os
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
import argparse
from collections import Counter
import copy
from dataclasses import asdict
from datetime import datetime, timezone
import gzip
import hashlib
import importlib.util
from itertools import zip_longest
import json
from pathlib import Path
import sys
import time
import traceback

sys.dont_write_bytecode = True
import numpy as np
import codec_course as course

HERE = Path(__file__).resolve().parent
REFERENCE_SHA = "db39661a7b16d13e64db7acc5dae22a81ca59dc39cf467ed4c58addbc0654013"
PROTOCOL_SHA = "68dac62882e8983945beb9b705cca6c34817f605d7f97b711dff345310c988ec"
POLICIES = ("F", "G")
FRACTIONS = (0, 25, 50, 75, 100)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def dump(path, value):
    path = Path(path)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2,
                  allow_nan=False)
        stream.write("\n")


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for data in iter(lambda: stream.read(1024*1024), b""):
            digest.update(data)
    return digest.hexdigest()


def json_sha(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def load_reference():
    path = HERE/"reference/p030_reference.py"
    if sha(path) != REFERENCE_SHA:
        raise ValueError("Pinned PR9 P030 Model source SHA mismatch")
    spec = importlib.util.spec_from_file_location("p035_frozen_p030", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    assert Path(module.__file__).resolve() == path.resolve()
    return module


ref = load_reference()


def source_hashes(protocol_path):
    files = {"run_p035.py": HERE/"run_p035.py", "codec_course.py": HERE/"codec_course.py",
             "protocol.json": Path(protocol_path)}
    for name in course.REFERENCE_PINS:
        files["reference/"+name] = HERE/"reference"/name
    for name in ("reference/lineage.json", "P035-事前規格-2026-11-12.md"):
        if (HERE/name).exists():
            files[name] = HERE/name
    return {name: sha(path) for name, path in files.items()}


def validate_protocol(protocol_path):
    if sha(protocol_path) != PROTOCOL_SHA:
        raise ValueError("Preregistered protocol SHA mismatch")
    protocol = read(protocol_path)
    assert protocol["students"] == 12 and protocol["seeds"] == [101, 202, 303]
    assert protocol["codecs"] == list(course.CODEC_NAMES.values())
    assert protocol["policies"] == list(POLICIES)
    assert protocol["model"]["sha256"] == REFERENCE_SHA
    assert protocol["curriculum"]["fixed_external_stage_clock"]
    assert protocol["curriculum"]["promotion_not_conditioned_on_success"]
    assert protocol["budget"]["per_student_cap"] == 277794000
    assert protocol["budget"]["F_expected_target_updates"] == 66000
    assert protocol["budget"]["G_expected_target_updates"] == 76337
    for stage, declared in zip(course.STAGES, protocol["stages"], strict=True):
        assert (stage.name, stage.n_op, stage.n_data, stage.L, stage.H, stage.mac_cap) == (
            declared["id"], declared["n_op"], declared["n_data"], declared["L"],
            declared["H"], declared["training_MAC_cap"])
        assert stage.split == {k: declared[k] for k in ("train", "val", "test")}
        assert [course.OP_NAMES[op] for op in stage.ops] == declared["ops"]
        assert stage.targets_per_lesson == declared["targets_per_lesson"]
        assert max(course.max_context(codec, stage) for codec in course.CODECS) == stage.L
    course.verify_references()
    return protocol


def state_hash(state):
    digest = hashlib.sha256()
    for name, array in sorted(state.items()):
        digest.update(canonical([name, array.dtype.str, list(array.shape)]).encode("utf-8"))
        digest.update(array.tobytes(order="C"))
    return digest.hexdigest()


def save_state(path, state):
    with Path(path).open("xb") as stream:
        np.savez(stream, **state)


def load_state(path, seed):
    with np.load(path, allow_pickle=False) as saved:
        state = {name: saved[name].copy() for name in saved.files}
    net = ref.Model(seed, int(state["L"]), int(state["H"]))
    for label in ("p", "m", "v", "birth"):
        setattr(net, label, [state[f"{label}{i}"].copy() for i in range(4)])
    net.t = int(state["t"])
    net.growth_rng.bit_generator.state = json.loads(str(state["growth_rng"]))
    assert ref.equal_state(state, net.state())
    return net


def finite_state(net):
    for label in ("p", "m", "v"):
        assert all(a.dtype == np.float32 and np.isfinite(a).all()
                   for a in getattr(net, label)), label
    assert all(a.dtype == np.int64 and np.all((a >= 0) & (a <= net.t)) for a in net.birth)
    assert net.parameters == net.H*(2*net.L+4)+3


def array_bytes(net):
    return {"parameter_optimizer_birth_arrays": sum(a.nbytes for label in
            ("p", "m", "v", "birth") for a in getattr(net, label)),
            "scope": "persistent p/m/v/birth arrays; not process peak or temporary activations"}


def raw_probes(codec, stage):
    return sorted({course.encode(codec, stage, op, value)+course.answer(stage, op, value)[:i]
                   for op in stage.ops for value in range(2**stage.n_data)
                   for i in range(stage.targets_per_lesson)})


def grow_verified(net, L, H, probes, reason):
    before = net.state()
    oldL, oldH = net.L, net.H
    logits = [net.forward(text)[2].copy() for text in probes]
    net.grow(L, H, reason)
    slices = [(slice(0, 2*oldL), slice(0, oldH)), (slice(0, oldH),),
              (slice(0, oldH), slice(None)), (slice(None),)]
    for label in ("p", "m", "v", "birth"):
        for i, selection in enumerate(slices):
            assert np.array_equal(getattr(net, label)[i][selection], before[f"{label}{i}"])
            mask = np.zeros(getattr(net, label)[i].shape, dtype=bool)
            mask[selection] = True
            if label in ("m", "v"):
                assert not np.any(getattr(net, label)[i][~mask])
            if label == "birth":
                assert np.all(net.birth[i][~mask] == int(before["t"]))
    assert net.t == int(before["t"])
    assert not np.any(net.p[2][oldH:])
    differences = [float(np.max(abs(z-net.forward(text)[2]))) for text, z in zip(probes, logits)]
    maximum = max(differences, default=0.)
    assert maximum < 2e-6, (reason, maximum)
    finite_state(net)
    return {"reason": reason, "from": [oldL, oldH], "to": [L, H],
            "grew": (oldL, oldH) != (L, H), "at_global_update": net.t,
            "old_arrays_moments_birth_and_step_exact": True,
            "new_moments_zero_new_birth_is_current_step": True,
            "new_hidden_outgoing_zero": True, "all_coordinates_trainable_afterward": True,
            "same_raw_prefixes": len(probes), "max_same_raw_logit_difference": maximum,
            "growth_rng_before": str(before["growth_rng"]),
            "growth_rng_after": str(net.state()["growth_rng"]),
            "not_a_zero_token_or_reencoded_semantic_invariance_claim": True}


def initialize(seed, policy):
    net = ref.Model(seed, course.STAGES[0].L, course.STAGES[0].H)
    events = []
    if policy == "F":
        probes = sorted(set(raw_probes("S", course.STAGES[0])+raw_probes("H", course.STAGES[0])))
        for stage in course.STAGES:
            events.append(grow_verified(net, stage.L, stage.H, probes,
                                        "fixed_final_t0_sequence_"+stage.name))
    assert net.t == 0
    return net, events


def quarter_points(stage, budget):
    # Floor to the nearest complete lesson that does not exceed the threshold.
    return {fraction: (budget["MAC_cap"]*fraction//100)//budget["MAC_per_lesson"]
            for fraction in FRACTIONS}


def first_error(actual, expected):
    return next((i for i, pair in enumerate(zip_longest(actual, expected))
                 if pair[0] != pair[1]), None)


def truth_table(net, codec, stage, *, include_test=True):
    rows, saved = [], net.state()
    values = list(range(2**stage.n_data)) if include_test else list(stage.train+stage.val)
    for op in stage.ops:
        for value in values:
            q, a = course.encode(codec, stage, op, value), course.answer(stage, op, value)
            generated, overflow = net.generate(q)
            tf, free = [], []
            for i, target in enumerate(a+"S"):
                z = net.forward(q+a[:i])[2].astype(np.float64)
                lp = z-np.logaddexp.reduce(z)
                tf.append({"position": i, "target": target, "prediction": "01S"[int(z.argmax())],
                           "logits": z.tolist(), "probabilities_01S": np.exp(lp).tolist(),
                           "target_CE": -float(lp["01S".index(target)])})
            prefix = ""
            for token in generated:
                z = net.forward(q+prefix)[2].astype(np.float64)
                lp = z-np.logaddexp.reduce(z)
                free.append({"prefix": prefix, "prediction": token, "logits": z.tolist(),
                             "probabilities_01S": np.exp(lp).tolist()})
                if token == "S":
                    break
                prefix += token
            stopped = generated.endswith("S")
            bits = generated[:-1] if stopped else generated
            syntax_valid = stopped and len(bits) == len(a) and not set(bits)-set("01") and bits.endswith("0")
            subset = next(name for name in ("train", "val", "test") if value in getattr(stage, name))
            rows.append({"codec": codec, "stage": stage.name, "operator": op,
                         "operator_name": course.OP_NAMES[op], "value": value, "subset": subset,
                         "Q": q, "target": a+"S", "generated": generated, "overflow": bool(overflow),
                         "whole_correct": generated == a+"S" and not overflow,
                         "STOP_position_correct": stopped and len(generated) == len(a)+1,
                         "malformed": not syntax_valid,
                         "decoded_result": int(bits[:-1], 2) if syntax_valid else None,
                         "information_bit_correct": [i < len(bits) and bits[i] == a[i] for i in range(stage.n_data)],
                         "syntax_tail_correct": len(bits) > stage.n_data and bits[stage.n_data] == "0",
                         "first_error_position_zero_based": first_error(generated, a+"S"),
                         "teacher_forcing": tf, "free_run": free})
    assert ref.equal_state(saved, net.state())
    return rows


def metrics(rows, stage):
    result = {}
    for subset in ("train", "val", "test", "all"):
        selected = [r for r in rows if subset == "all" or r["subset"] == subset]
        by_op = {}
        for op in stage.ops:
            own = [r for r in selected if r["operator"] == op]
            targets = sum(len(r["teacher_forcing"]) for r in own)
            by_op[course.OP_NAMES[op]] = {
                "whole": sum(r["whole_correct"] for r in own), "total": len(own),
                "STOP_position_correct": sum(r["STOP_position_correct"] for r in own),
                "overflow": sum(r["overflow"] for r in own), "malformed": sum(r["malformed"] for r in own),
                "information_bit_correct": [sum(r["information_bit_correct"][i] for r in own)
                                            for i in range(stage.n_data)],
                "syntax_tail_correct": sum(r["syntax_tail_correct"] for r in own),
                "teacher_correct": sum(t["target"] == t["prediction"] for r in own for t in r["teacher_forcing"]),
                "teacher_targets": targets,
                "teacher_whole": sum(all(t["target"] == t["prediction"] for t in r["teacher_forcing"]) for r in own),
                "CE_mean": sum(t["target_CE"] for r in own for t in r["teacher_forcing"])/targets if targets else None,
            }
        result[subset] = {"by_op": by_op, "whole": sum(r["whole_correct"] for r in selected),
                          "total": len(selected)}
    return result


def drift(before, net):
    result = {}
    for label in ("p", "m", "v", "birth"):
        changes = []
        for i, current in enumerate(getattr(net, label)):
            previous = before[f"{label}{i}"]
            selection = tuple(slice(0, n) for n in previous.shape)
            now = current[selection]
            difference = now.astype(np.float64)-previous.astype(np.float64)
            changes.append({"array": i, "old_shape": list(previous.shape),
                            "changed_coordinates": int(np.count_nonzero(now != previous)),
                            "L2": float(np.linalg.norm(difference)),
                            "relative_L2": float(np.linalg.norm(difference))/max(float(np.linalg.norm(previous.astype(np.float64))), 1e-12),
                            "max_absolute_change": float(np.max(abs(difference)))})
        result[label] = changes
    assert all(row["changed_coordinates"] == 0 for row in result["birth"])
    return result


class TokenTrace:
    def __init__(self, path, replay):
        self.path, self.replay, self.count = path, replay, 0
        self.stream = gzip.open(path, "rt" if replay else "xt", encoding="utf-8", newline="\n")

    def observe(self, record):
        if self.replay:
            expected = self.stream.readline()
            assert expected and json.loads(expected) == record, ("target replay mismatch", self.count)
        else:
            self.stream.write(canonical(record)+"\n")
        self.count += 1

    def close(self):
        if self.replay:
            assert not self.stream.readline(), "Replay omitted a target record"
        self.stream.close()


def target_record(net, stage, ordinal, position, prefix, target, prediction, loss):
    assert np.isfinite(loss)
    return {"stage": stage.index, "lesson": ordinal, "position": position,
            "prefix": prefix, "target": target, "prediction": prediction, "loss": loss,
            "global_update": net.t, "training_dense_MACs": net.train_macs,
            "L": net.L, "H": net.H, "full_state_sha256": state_hash(net.state())}


def execute_lesson(net, stage, ordinal, q, a, observe, *, replay=False):
    # Primary observes native Model.lesson. Replay uses an independent explicit
    # teacher-prefix loop through the unchanged native Model.step.
    if replay:
        predictions, total = "", 0.
        for i, target in enumerate(a+"S"):
            prefix = q+a[:i]
            prediction, loss = net.step(prefix, target)
            observe(target_record(net, stage, ordinal, i, prefix, target, prediction, loss))
            predictions += prediction
            total += loss
        return predictions, total
    native_step, observed = net.step, []

    def recorded_step(prefix, target):
        i = len(observed)
        assert prefix == q+a[:i] and target == (a+"S")[i]
        assert not set(prefix)-set("01") and len(prefix) <= net.L
        prediction, loss = native_step(prefix, target)
        observe(target_record(net, stage, ordinal, i, prefix, target, prediction, loss))
        observed.append((prediction, loss))
        return prediction, loss

    net.step = recorded_step
    try:
        predictions, total = net.lesson(q, a)
    finally:
        net.step = native_step
    assert len(observed) == stage.targets_per_lesson
    observed_total = 0.
    for _, loss in observed:
        observed_total += loss
    assert predictions == "".join(p for p, _ in observed) and total == observed_total
    return predictions, total


def interface_exposure(codec, courses):
    history, rows = {}, []
    for stage, lessons in zip(course.STAGES, courses, strict=True):
        counts = Counter(lessons)
        for (op, value), count in sorted(counts.items()):
            q, a = course.encode(codec, stage, op, value), course.answer(stage, op, value)
            labels = []
            for i, target in enumerate(a+"S"):
                prefix = q+a[:i]
                prior = history.get(prefix, {})
                labels.append({"position": i, "prefix": prefix, "target": target,
                               "prior_targets_counts": dict(prior),
                               "prior_different_target_seen": bool(set(prior)-{target})})
            rows.append({"stage": stage.name, "operator": op, "value": value,
                         "Q": q, "target": a+"S", "presentations": count, "prefix_labels": labels})
        # Prior-stage history is computed before adding any label from this stage.
        for (op, value), count in counts.items():
            q, a = course.encode(codec, stage, op, value), course.answer(stage, op, value)
            for i, target in enumerate(a+"S"):
                hist = history.setdefault(q+a[:i], {})
                hist[target] = hist.get(target, 0)+count
    return rows


def stage_run(net, codec, policy, seed, stage, lessons, folder, *, replay=False,
              engineering_budget_override=None):
    if not replay:
        folder.mkdir()
    budget = course.lesson_budget(stage, policy)
    if engineering_budget_override is not None:
        # Only engineering_checks calls this bounded path probe. Formal student
        # trials always use the unmodified registered course.lesson_budget.
        assert engineering_budget_override["engineering_only"] is True
        assert stage.index == 0 and len(lessons) == 4 and seed == 17035
        budget = engineering_budget_override
    assert len(lessons) == budget["lessons"]
    old_state = net.state()
    previous = course.STAGES[max(0, stage.index-1)]
    probes = raw_probes(codec, previous)
    target_capacity = course.STAGES[-1] if policy == "F" else stage
    growth = grow_verified(net, target_capacity.L, target_capacity.H, probes, "stage_entry_"+stage.name)
    if replay:
        assert growth == read(folder/"growth.json")
    else:
        dump(folder/"growth.json", growth)
    start_t, start_mac, start_inf, start_calls = net.t, net.train_macs, net.inference_macs, net.inference_calls
    points = quarter_points(stage, budget)
    fixed = {}
    for fraction, ordinal in points.items():
        fixed.setdefault(ordinal, []).append(fraction)
    curve, snapshots, streak, first_three = [], [], 0, None
    trace = TokenTrace(folder/"token-trace.jsonl.gz", replay)
    started, update_seconds = time.perf_counter(), 0.
    entry_metrics = final_metrics = None
    final_rows = None

    def diagnose(ordinal):
        nonlocal streak, first_three, entry_metrics, final_metrics, final_rows
        finite_state(net)
        is_fixed = ordinal in fixed
        rows = truth_table(net, codec, stage, include_test=is_fixed)
        score = metrics(rows, stage)
        is_fit = ordinal > 0 and (ordinal % 100 == 0 or ordinal == len(lessons))
        passed = score["train"]["whole"] == score["train"]["total"] and (
            score["val"]["whole"] == score["val"]["total"])
        record = {"lessons": ordinal, "stage_target_updates": net.t-start_t,
                  "global_target_updates": net.t, "stage_train_MACs": net.train_macs-start_mac,
                  "cumulative_train_MACs": net.train_macs, "is_fit_check": is_fit,
                  "metrics": score, "train_and_available_val_all_correct": passed,
                  "validation_holdout_exists": bool(stage.val),
                  "initial_snapshot_not_counted_toward_three_pass_streak": ordinal == 0}
        if ordinal == 0:
            entry_metrics = score
        if is_fit:
            streak = streak+1 if passed else 0
            if streak >= 3 and first_three is None:
                first_three = {"lessons": ordinal, "stage_target_updates": net.t-start_t,
                               "stage_train_MACs": net.train_macs-start_mac,
                               "cumulative_train_MACs": net.train_macs}
        if is_fit or ordinal == 0:
            curve.append(record)
        if is_fixed:
            saved = net.state()
            for fraction in fixed[ordinal]:
                snapshot = {"fraction_percent": fraction, "lesson": ordinal,
                            "MAC_threshold": budget["MAC_cap"]*fraction//100,
                            "stage_train_MACs": net.train_macs-start_mac,
                            "rounding": "nearest complete lesson not exceeding threshold",
                            "state_sha256": state_hash(saved), "metrics": score}
                assert snapshot["stage_train_MACs"] <= snapshot["MAC_threshold"]
                snapshots.append(snapshot)
                state_path, truth_path = folder/f"state-{fraction}.npz", folder/f"truth-{fraction}.json"
                if replay:
                    assert ref.equal_state(saved, load_state(state_path, seed).state())
                    assert rows == read(truth_path)
                else:
                    save_state(state_path, saved)
                    dump(truth_path, rows)
            if ordinal == len(lessons):
                final_metrics, final_rows = score, rows

    try:
        diagnose(0)
        for ordinal, (op, value) in enumerate(lessons, 1):
            q, a = course.encode(codec, stage, op, value), course.answer(stage, op, value)
            before = time.perf_counter()
            execute_lesson(net, stage, ordinal, q, a, trace.observe, replay=replay)
            update_seconds += time.perf_counter()-before
            assert net.train_macs-start_mac == ordinal*budget["MAC_per_lesson"]
            if ordinal in fixed or ordinal % 100 == 0 or ordinal == len(lessons):
                diagnose(ordinal)
            if ordinal % 1000 == 0:
                print(canonical({"phase": "replay" if replay else "primary", "codec": codec,
                                 "policy": policy, "seed": seed, "stage": stage.index,
                                 "lessons": ordinal, "stage_lessons": len(lessons)}), flush=True)
        trace.close()
        assert trace.count == budget["target_updates"]
        assert net.train_macs-start_mac == budget["executed_train_MACs"] <= budget["MAC_cap"]
        assert budget["MAC_cap"]-(net.train_macs-start_mac) == budget["unused_MACs"]
        assert net.t-start_t == budget["target_updates"]
        finite_state(net)
    except Exception:
        trace.stream.close()
        save_state(folder/("replay-failure-state.npz" if replay else "primary-failure-state.npz"), net.state())
        raise
    forward_mac = budget["target_updates"]*net.H*(2*net.L+3)
    backward_mac = budget["target_updates"]*net.H*(2*net.L+6)
    assert forward_mac+backward_mac == budget["executed_train_MACs"]
    summary = {
        "stage": asdict(stage), "policy": policy, "codec": codec, "seed": seed,
        "budget": budget, "global_updates_at_start": start_t, "global_updates_at_end": net.t,
        "target_updates": net.t-start_t, "first_observed_three_consecutive_fit_passes": first_three,
        "metrics_entry": entry_metrics, "metrics_final": final_metrics,
        "growth": growth, "drift_old_overlapping_blocks": drift(old_state, net),
        "train_forward_dense_MACs": forward_mac, "train_backward_dense_MACs": backward_mac,
        "train_dense_MACs": net.train_macs-start_mac,
        "diagnostic_forward_dense_MACs_after_growth": net.inference_macs-start_inf,
        "diagnostic_inference_calls_after_growth": net.inference_calls-start_calls,
        "array_bytes": array_bytes(net), "parameters": net.parameters,
        "training_softmax_output_elements": 3*budget["target_updates"],
        "training_tanh_elements_forward": net.H*budget["target_updates"],
        "training_tanh_elements_backward": net.H*budget["target_updates"],
        "trace_targets": trace.count, "trace_sha256": sha(trace.path),
        "course_sha256": json_sha(lessons), "snapshots": snapshots,
        "stage_clock_fixed_success_does_not_change_budget_or_promotion": True,
        "unused_MACs_carried": False,
    }
    if replay:
        assert canonical(summary) == canonical(read(folder/"summary.json")), (
            codec, policy, seed, stage.index, "stage replay summary")
        assert curve == read(folder/"curve.json")
    else:
        dump(folder/"summary.json", summary)
        dump(folder/"curve.json", curve)
    print(canonical({"phase": "replay" if replay else "primary", "codec": codec,
                     "policy": policy, "seed": seed, "stage": stage.index, "stage_complete": True,
                     "target_updates": net.t, "training_dense_MACs": net.train_macs}), flush=True)
    timing = {"seconds_stage_loop": time.perf_counter()-started,
              "seconds_updates_prefix_checks_and_full_state_fingerprints": update_seconds}
    return summary, final_rows, timing


def prepare_courses(out):
    (out/"courses").mkdir()
    courses, records = {}, []
    for policy in POLICIES:
        for seed in course.SEEDS:
            folder = out/"courses"/f"{policy}-seed{seed}"
            folder.mkdir()
            stage_courses = []
            for stage in course.STAGES:
                budget = course.lesson_budget(stage, policy)
                lessons = course.semantic_course(stage, seed, budget["lessons"])
                stage_courses.append(lessons)
                dump(folder/(stage.name+".json"), lessons)
                records.append({"policy": policy, "seed": seed, "stage": stage.name,
                                "course_sha256_canonical": json_sha(lessons), "lessons": len(lessons),
                                "budget": budget,
                                "target_stream_sha256": json_sha([course.answer(stage, op, v)+"S" for op, v in lessons])})
            courses[(policy, seed)] = stage_courses
    for seed in course.SEEDS:
        for i in range(len(course.STAGES)):
            shorter, longer = courses[("F", seed)][i], courses[("G", seed)][i]
            assert shorter == longer[:len(shorter)]
    return courses, records


def student_trial(out, codec, policy, seed, initial, init_events, courses):
    folder = out/f"{codec}-{policy}-seed{seed}"
    folder.mkdir()
    net = copy.deepcopy(initial)
    save_state(folder/"initial-state.npz", net.state())
    dump(folder/"initialization.json", {"policy": policy, "seed": seed,
                                       "initial_state_sha256": state_hash(net.state()),
                                       "fixed_t0_growth_events": init_events,
                                       "initialization_diagnostic_MACs": net.inference_macs,
                                       "initialization_diagnostic_calls": net.inference_calls})
    stages, timings, final_rows = [], [], None
    started = time.perf_counter()
    for stage, lessons in zip(course.STAGES, courses, strict=True):
        result, final_rows, timing = stage_run(net, codec, policy, seed, stage, lessons, folder/stage.name)
        stages.append(result)
        timings.append(timing)
    primary_seconds = time.perf_counter()-started
    frozen = net.state()
    save_state(folder/"final-state.npz", frozen)
    dump(folder/"final-truth.json", final_rows)
    dump(folder/"final-failures.json", [r for r in final_rows if not r["whole_correct"]])
    replay, replay_timings = copy.deepcopy(initial), []
    replay_started = time.perf_counter()
    for stage, lessons in zip(course.STAGES, courses, strict=True):
        _, _, timing = stage_run(replay, codec, policy, seed, stage, lessons, folder/stage.name, replay=True)
        replay_timings.append(timing)
    assert ref.equal_state(frozen, replay.state())
    assert net.events == replay.events and (
        net.train_macs, net.inference_macs, net.inference_calls) == (
        replay.train_macs, replay.inference_macs, replay.inference_calls)
    expected_t = 66000 if policy == "F" else 76337
    expected_mac = 277794000 if policy == "F" else 277772868
    assert net.t == expected_t and net.train_macs == expected_mac
    exposure = course.exposure_ledger(courses)
    dump(folder/"exposure-ledger.json", exposure)
    dump(folder/"interface-exposure.json", interface_exposure(codec, courses))
    primary = course.milestone_score({(r["operator"], r["value"]): r["whole_correct"] for r in final_rows})
    result = {
        "codec": codec, "codec_name": course.CODEC_NAMES[codec], "policy": policy,
        "seed": seed, "primary": primary, "stages": stages,
        "target_updates": net.t, "training_dense_MAC_cap": 277794000,
        "executed_training_dense_MACs": net.train_macs,
        "unused_training_MACs_not_carried": 277794000-net.train_macs,
        "inference_dense_MACs_including_initialization_and_growth": net.inference_macs,
        "inference_calls": net.inference_calls, "final_parameters": net.parameters,
        "array_bytes": array_bytes(net), "initial_state_sha256": state_hash(initial.state()),
        "final_state_sha256": state_hash(frozen),
        "primary_seconds": primary_seconds, "replay_seconds": time.perf_counter()-replay_started,
        "primary_stage_timings": timings, "replay_stage_timings": replay_timings,
        "all_targets_losses_states_snapshots_curves_optimizer_rng_replayed_exact": True,
        "new_student_count": 1, "deterministic_replay_is_not_another_student": True,
        "growth_and_inference_MACs_excluded_from_training_cap": True,
    }
    dump(folder/"result.json", result)
    return result


def engineering_checks(out, protocol_path):
    protocol = validate_protocol(protocol_path)
    sources = source_hashes(protocol_path)
    checked = {}
    for policy in POLICIES:
        budgets = [course.lesson_budget(stage, policy) for stage in course.STAGES]
        counts = [b["lessons"] for b in budgets]
        assert counts == protocol["budget"]["F_lessons" if policy == "F" else "G_expected_lessons"]
        assert sum(b["target_updates"] for b in budgets) == (66000 if policy == "F" else 76337)
        assert sum(b["executed_train_MACs"] for b in budgets) == (277794000 if policy == "F" else 277772868)
        for stage, budget in zip(course.STAGES, budgets, strict=True):
            for fraction, n in quarter_points(stage, budget).items():
                threshold = stage.mac_cap*fraction//100
                assert n*budget["MAC_per_lesson"] <= threshold < (n+1)*budget["MAC_per_lesson"]
            assert 0 <= budget["unused_MACs"] < budget["MAC_per_lesson"]
        checked[policy] = {"budgets": budgets, "quarter_points": {
            s.name: quarter_points(s, b) for s, b in zip(course.STAGES, budgets, strict=True)}}
    # No official seed or scientific semantic fit is used in these updates.
    synthetic = [("0010", "010"), ("110010", "11"), ("0001110", "010"),
                 ("10110101", "00"), ("0010110", "101")]
    seed, records, saved_states = 17035, [], []
    primary = ref.Model(seed, 8, 64)
    for stage, (q, a) in zip(course.STAGES, synthetic, strict=True):
        grow_verified(primary, stage.L, stage.H, ["0", "1", "001001"], "synthetic"+stage.name)
        before_mac, before_t = primary.train_macs, primary.t
        # Synthetic answer length is independent of a semantic stage profile.
        synthetic_stage = type("SyntheticStage", (), {"index": stage.index, "targets_per_lesson": len(a)+1})()
        execute_lesson(primary, synthetic_stage, 1, q, a, records.append)
        assert primary.train_macs-before_mac == (len(a)+1)*stage.H*(4*stage.L+9)
        assert primary.t-before_t == len(a)+1
        saved_states.append(primary.state())
    save_state(out/"synthetic-final.npz", primary.state())
    restored = load_state(out/"synthetic-final.npz", seed)
    assert ref.equal_state(restored.state(), primary.state())
    replay, repeated = ref.Model(seed, 8, 64), []
    for stage, (q, a), saved in zip(course.STAGES, synthetic, saved_states, strict=True):
        grow_verified(replay, stage.L, stage.H, ["0", "1", "001001"], "synthetic"+stage.name)
        synthetic_stage = type("SyntheticStage", (), {"index": stage.index, "targets_per_lesson": len(a)+1})()
        execute_lesson(replay, synthetic_stage, 1, q, a, repeated.append, replay=True)
        assert ref.equal_state(saved, replay.state())
    assert repeated == records and primary.events == replay.events
    resumed_expected = copy.deepcopy(primary)
    assert resumed_expected.step("001001", "0") == restored.step("001001", "0")
    assert ref.equal_state(resumed_expected.state(), restored.state())
    # Exercise actual gzip/quarter-snapshot/curve/summary/replay I/O using only
    # four d1 training examples, engineering seed17035 and an explicit tiny cap.
    # No official seed, heldout outcome or scientific budget is altered.
    micro_stage = course.STAGES[0]
    micro_lessons = [(0, 0), (0, 1), (0, 0), (0, 1)]
    micro_budget = dict(course.lesson_budget(micro_stage, "G"))
    micro_cap = 4*micro_budget["MAC_per_lesson"]
    micro_budget.update(lessons=4, target_updates=12, MAC_cap=micro_cap,
                        executed_train_MACs=micro_cap, unused_MACs=0, engineering_only=True)
    micro_primary, micro_replay = ref.Model(seed, 8, 64), ref.Model(seed, 8, 64)
    micro_summary, _, _ = stage_run(micro_primary, "S", "G", seed, micro_stage,
        micro_lessons, out/"synthetic-stage-path", engineering_budget_override=micro_budget)
    stage_run(micro_replay, "S", "G", seed, micro_stage, micro_lessons,
              out/"synthetic-stage-path", replay=True, engineering_budget_override=micro_budget)
    assert ref.equal_state(micro_primary.state(), micro_replay.state())
    fixed, events = initialize(seed, "F")
    untrained_growing = ref.Model(seed, 8, 64)
    for stage in course.STAGES:
        untrained_growing.grow(stage.L, stage.H, "engineering_untrained_sequence")
    assert ref.equal_state(fixed.state(), untrained_growing.state())
    assert fixed.parameters == 2073 and fixed.t == 0
    # Old coordinates remain trainable; zero outgoing initialization opens new
    # incoming gradients after the first update, with per-coordinate birth age.
    g = ref.Model(seed, 8, 64)
    g.lesson("0010", "01")
    oldH = g.H
    grow_verified(g, 10, 66, ["0", "0010"], "synthetic_gradient_path")
    before = [a.copy() for a in g.p]
    g.step("0010010010", "0")
    assert np.any(g.p[2][oldH:] != before[2][oldH:])
    after_one = g.p[0].copy()
    g.step("0010010010", "1")
    assert np.any(g.p[0][:, oldH:] != after_one[:, oldH:])
    assert np.any(g.p[2][:oldH] != before[2][:oldH])
    # Raw tensors are different; teachers/semantic streams are shared.
    tensor_cases = 0
    for stage in course.STAGES:
        for op in stage.ops:
            for value in range(2**stage.n_data):
                a = course.answer(stage, op, value)
                raw = [course.encode(c, stage, op, value) for c in course.CODECS]
                for c, q in zip(course.CODECS, raw):
                    assert course.decode_syntax(c, stage, q) == (op, value)
                    actual = fixed.forward(q+a)[0]
                    np.testing.assert_array_equal(actual, course.tensor_prefix(q+a, fixed.L))
                assert not np.array_equal(course.tensor_prefix(raw[0], fixed.L),
                                          course.tensor_prefix(raw[1], fixed.L))
                tensor_cases += 1
    guard = ref.Model(seed, 8, 64)
    guard.p[2][:] = 0.
    guard.p[3][:] = [50., 0., 0.]
    assert guard.generate("0"*8) == ("0", True)
    assert guard.generate("0") == ("0"*8, False)
    guard.p[3][:] = [0., 0., 50.]
    assert guard.generate("0"*8) == ("S", False)
    frozen = guard.state()
    native_answer = course.answer
    def forbidden(*args, **kwargs):
        raise AssertionError("Teacher/oracle called from native free inference")
    course.answer = forbidden
    try:
        assert guard.generate("0010") == ("S", False)
    finally:
        course.answer = native_answer
    assert ref.equal_state(frozen, guard.state())
    assert source_hashes(protocol_path) == sources
    result = {
        "status": "passed", "scope": "synthetic engineering only; no scientific student fitting",
        "scientific_updates": 0, "synthetic_primary_targets": len(records),
        "synthetic_replay_targets": len(repeated), "source_sha256": sources,
        "synthetic_stage_path_primary_targets": 12, "synthetic_stage_path_replay_targets": 12,
        "synthetic_auxiliary_gradient_path_and_checkpoint_resume_targets": 7,
        "gzip_trace_fixed_snapshot_curve_summary_full_path_replay": True,
        "synthetic_stage_path_snapshot_count": len(micro_summary["snapshots"]),
        "budget_and_snapshot_checks": checked, "paired_F_sequential_growth_and_untrained_G_state_equal": True,
        "old_arrays_moments_birth_step_and_same_raw_growth_checks": True,
        "new_hidden_gradient_path_and_old_coordinates_trainable": True,
        "synthetic_checkpoint_all_array_optimizer_RNG_replay_exact": True,
        "S_H_raw_tensor_audits": tensor_cases, "generation_no_oracle_or_forced_STOP": True,
        "p030_model_source_commit": protocol["model"]["source_commit"],
        "p030_model_source_path": protocol["model"]["source_path"],
        "numpy": np.__version__, "python": sys.version,
        "first_three_pass_policy": "Only positive each100/endpoint fit checks qualify; initial0 snapshot does not qualify",
    }
    dump(out/"checks.json", result)
    return result


def execute(out, protocol_path):
    protocol = validate_protocol(protocol_path)
    sources = source_hashes(protocol_path)
    courses, course_records = prepare_courses(out)
    templates, initial_events, initial_records = {}, {}, []
    for policy in POLICIES:
        for seed in course.SEEDS:
            initial, events = initialize(seed, policy)
            templates[(policy, seed)], initial_events[(policy, seed)] = initial, events
            initial_records.append({"policy": policy, "seed": seed,
                                    "state_sha256": state_hash(initial.state()),
                                    "t": initial.t, "L": initial.L, "H": initial.H,
                                    "parameters": initial.parameters, "fixed_t0_growth_events": events})
    manifest = {"id": "P035", "registered_UTC_before_first_scientific_update": datetime.now(timezone.utc).isoformat(),
                "protocol": protocol, "source_sha256": sources, "courses": course_records,
                "initial_states": initial_records, "numpy": np.__version__, "python": sys.version,
                "initialization": "F follows every prescribed grow at t0; G grows at stage entry; codec pair starts exact same runtime state",
                "training_budget": "dense matrix MAC cap only; complete lessons; no carry; fixed external stage clock",
                "trace": "native lesson observer primary; independent native step target loop replay; full state SHA every target",
                "first_three_pass_policy": "Only positive each100/endpoint fit checks qualify; initial0 snapshot does not qualify",
                "scope": "12 newly initialized MLP students, not a B1 attention continuation",
                "execution_author": "Codex T", "no_holdout_driven_decisions": True}
    dump(out/"manifest.json", manifest)
    results, started, current = [], time.perf_counter(), None
    try:
        for codec in course.CODECS:
            for policy in POLICIES:
                for seed in course.SEEDS:
                    current = {"codec": codec, "policy": policy, "seed": seed}
                    results.append(student_trial(out, codec, policy, seed, templates[(policy, seed)],
                                                 initial_events[(policy, seed)], courses[(policy, seed)]))
                    dump(out/f"progress-{len(results):02d}.json", {"completed": len(results), "required": 12,
                                                               "latest": current, "all_completed_replay_exact": True})
        assert len(results) == 12 and source_hashes(protocol_path) == sources
        interactions = []
        for seed in course.SEEDS:
            own = {(r["codec"], r["policy"]): r for r in results if r["seed"] == seed}
            values = {c+p: own[(c, p)]["primary"]["score"] for c in course.CODECS for p in POLICIES}
            interactions.append({"seed": seed, "scores": values,
                                 "S_growth_minus_fixed": values["SG"]-values["SF"],
                                 "H_growth_minus_fixed": values["HG"]-values["HF"],
                                 "interaction": (values["SG"]-values["SF"])-(values["HG"]-values["HF"])})
            for policy in POLICIES:
                assert own[("S", policy)]["initial_state_sha256"] == own[("H", policy)]["initial_state_sha256"]
                assert [s["course_sha256"] for s in own[("S", policy)]["stages"]] == [s["course_sha256"] for s in own[("H", policy)]["stages"]]
        compact = {"id": "P035", "status": "passed", "meaning": "execution and exact replay accepted; inspect skill scores separately",
                   "new_students": 12, "deterministic_replays": 12, "all_students_retained": True,
                   "all_targets_states_snapshots_curves_Adam_birth_rng_replayed_exact": True,
                   "primary_target_updates": sum(r["target_updates"] for r in results),
                   "additional_replay_target_updates": sum(r["target_updates"] for r in results),
                   "primary_training_dense_MACs": sum(r["executed_training_dense_MACs"] for r in results),
                   "additional_replay_training_dense_MACs": sum(r["executed_training_dense_MACs"] for r in results),
                   "primary_inference_dense_MACs": sum(r["inference_dense_MACs_including_initialization_and_growth"] for r in results),
                   "per_seed_interactions": interactions, "results": results,
                   "wall_seconds_primary_replay_evidence": time.perf_counter()-started,
                   "limitations": protocol["limitations"], "source_sha256": sources}
        dump(out/"results.json", results)
        dump(out/"compact.json", compact)
        print(canonical({key: value for key, value in compact.items() if key not in ("results", "source_sha256")}), flush=True)
    except Exception:
        dump(out/"failure.json", {"status": "stopped_failure_no_restart_or_tuning", "current": current,
                                   "completed_students": len(results), "traceback": traceback.format_exc()})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="Fresh output directory; never overwritten")
    parser.add_argument("--protocol", type=Path, default=HERE/"protocol.json")
    parser.add_argument("--execute", action="store_true", help="Run the frozen12 students after source review approval")
    args = parser.parse_args()
    out = args.out.resolve()
    if out.exists():
        raise FileExistsError("Use a fresh P035 output; do not restart/select a scientific attempt")
    out.mkdir(parents=True)
    if args.execute:
        execute(out, args.protocol.resolve())
    else:
        checks = engineering_checks(out, args.protocol.resolve())
        print(canonical({"status": checks["status"], "scientific_updates": 0,
                         "synthetic_primary_targets": checks["synthetic_primary_targets"],
                         "source_sha256": checks["source_sha256"], "checks": str(out/"checks.json")}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
