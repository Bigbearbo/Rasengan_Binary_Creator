"""Independent read-only endpoint audit. No learner/driver imports or optimizer implementation."""
from __future__ import annotations
import argparse
import ast
from collections import Counter
import hashlib
import io
import json
import math
import os
from pathlib import Path
import platform
import re
import sys
import time
import zipfile
import zlib

if sys.flags.optimize:
    raise RuntimeError("Assertions must remain enabled")
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
sys.dont_write_bytecode = True
import numpy as np

APPROVED = "1079366438d667f7bce2ac8fce983792b6c7bf935f4a200fb9eda4e9612e328c"
CORE = {"run_stability.py": "2e11066e065103f6d8c211718fc4a3271b79876b52af00f49241fe79577cf6e3",
        "protocol.json": "8f4452756a63d3665d85ec2b319d8d902a5038cca047223c5d32154b37499854",
        "test_stability.py": "2262e781c3e1c32e0dafe58d3af38bef8e1bbd082d90f33087bfa60c4c6b5486"}
CLASSES = ("E1", "E2", "F1", "F2")
START = {101: (19, 981000), 202: (22, 1192500), 303: (19, 1125900)}
TRAIN_MAC, FORWARD_MAC = 21056, 10432
WORD_FIELDS = ("information5_correct", "tail0_correct", "complete6_correct")
CHURN_FIELDS = ("previous_correct_to_wrong", "previous_wrong_to_correct", "retained_correct", "retained_wrong")

def need(value, label):
    if not value:
        raise AssertionError(label)

def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def sha(path):
    return digest(path.read_bytes())

def finite(value):
    if isinstance(value, float):
        need(math.isfinite(value), "nonfinite JSON value")
    elif isinstance(value, dict):
        for item in value.values():
            finite(item)
    elif isinstance(value, list):
        for item in value:
            finite(item)

def parse(text):
    def pairs(items):
        result = {}
        for key, value in items:
            need(key not in result, "duplicate JSON key")
            result[key] = value
        return result
    result = json.loads(text, object_pairs_hook=pairs)
    finite(result)
    return result

def read(path):
    return parse(path.read_text(encoding="utf-8-sig"))

def write(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, sort_keys=True, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")

def equal(left, right, label):
    need(left == right, label + " differs")

def integer(value, lower, upper, label):
    need(type(value) is int and lower <= value <= upper, label + " integer range")

def inventory(root):
    return {path.relative_to(root).as_posix(): {"bytes": path.stat().st_size, "sha256": sha(path)} for path in sorted(root.rglob("*")) if path.is_file()}

def state_sha(state):
    result = hashlib.sha256()
    for name, value in sorted(state.items()):
        result.update(canonical([name, value.dtype.str, list(value.shape)]).encode())
        result.update(value.tobytes(order="C"))
    return result.hexdigest()

def same_state(left, right, label):
    need(left.keys() == right.keys(), label + " keys")
    for name in left:
        a, b = left[name], right[name]
        need(a.dtype == b.dtype and a.shape == b.shape and np.array_equal(a, b), label + " " + name)

class Cost:
    def __init__(self, output):
        self.output, self.started = output, time.perf_counter()
        self.calls, self.phases = 0, Counter()
        self.script_sha256 = sha(Path(__file__))

    def increment(self, phase):
        self.calls += 1
        self.phases[phase] += 1

    def record(self):
        return {"forward_calls": self.calls, "dense_MAC": self.calls * FORWARD_MAC, "calls_by_phase": dict(self.phases), "optimizer_calls": 0, "new_students": 0, "external_model_calls": 0}

    def persist(self, status):
        value = {"status": status, **self.record(), "seconds": time.perf_counter() - self.started, "script_sha256": self.script_sha256, "attempts": 1}
        target = self.output / "audit-cost.json"
        temporary = self.output / "audit-cost.json.tmp"
        temporary.write_text(json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n")
        os.replace(temporary, target)

class Forward:
    def __init__(self, state, cost, phase):
        self.state, self.cost, self.phase, self.calls = state, cost, phase, 0

    def __call__(self, text):
        need(0 < len(text) <= 80 and set(text) <= set("01"), "only binary Q plus prefix within fixed80")
        x = np.zeros((80, 2), np.float32)
        for index, bit in enumerate(text):
            x[index, int(bit)] = 1
        hidden = np.tanh(x.reshape(1, 160) @ self.state["p0"] + self.state["p1"])
        logits = (hidden @ self.state["p2"] + self.state["p3"])[0]
        self.calls += 1
        self.cost.increment(self.phase)
        need(bool(np.isfinite(logits).all()), "finite independent logits")
        return logits

    def generate(self, q):
        tokens = ""
        for _ in range(32):
            if len(q + tokens) > 80:
                return {"tokens": tokens, "context_exhausted": True, "cap_exhausted": False}
            token = "01S"[int(np.argmax(self(q + tokens)))]
            tokens += token
            if token == "S":
                return {"tokens": tokens, "context_exhausted": False, "cap_exhausted": False}
        return {"tokens": tokens, "context_exhausted": False, "cap_exhausted": True}

def blob(raw):
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def counters(state):
    return {"t":int(state["t"]),"train_MAC":int(state["meta_train_macs"]),"inference_calls":int(state["meta_inference_calls"]),"inference_MAC":int(state["meta_inference_macs"])}

def independent_readout(rows,outputs,previous=None,previous_point=None):
    from itertools import zip_longest
    actual_by_id={item["question_id"]:item for item in outputs}
    equal(set(actual_by_id),{row["question_id"] for row in rows},"independent readout QID identity")
    items=[]
    for task in rows:
        output=actual_by_id[task["question_id"]];actual=output["tokens"];expected=task["A"]+"S"
        alignment=list(zip_longest(actual,expected,fillvalue=None))
        bad=[index for index,(observed,target) in enumerate(alignment) if observed!=target]
        first=bad[0] if bad else None
        if first is None: kind="none"
        else:
            observed,target=alignment[first]
            kind="missing_token" if observed is None else "extra_token" if target is None else "early_STOP" if observed=="S" else "STOP_expected_bit_emitted" if target=="S" else "content_bit"
        flags={"context_exhausted":bool(output.get("context_exhausted",False)),"cap_exhausted":bool(output.get("cap_exhausted",False))}
        stops=[index for index,char in enumerate(actual) if char=="S"]
        if flags["context_exhausted"]: termination="context_exhausted"
        elif flags["cap_exhausted"]: termination="cap_exhausted"
        elif not stops: termination="no_STOP"
        elif stops[0]!=len(actual)-1: termination="tokens_after_STOP"
        elif stops[0]<len(task["A"]): termination="early_STOP"
        elif stops[0]>len(task["A"]): termination="late_STOP"
        else: termination="STOP_at_expected_position"
        correct=[index<len(actual) and actual[index]==target for index,target in enumerate(task["A"])]
        words=[]
        for slot in range(task["r"]):
            offset=slot*6
            words.append({"information5_correct":all(correct[offset:offset+5]),"tail0_correct":correct[offset+5],"complete6_correct":all(correct[offset:offset+6])})
        items.append({"question_id":task["question_id"],"class":task["class"],"whole_correct":not bad,"answer_bit_correct":correct,"words":words,"STOP_position_correct":len(actual)==len(expected) and actual[-1:]=="S","first_error_position_zero_based":first,"first_error_kind":kind,"termination_kind":termination,"missing_expected_positions":sum(observed is None and target is not None for observed,target in alignment),"extra_output_positions":sum(observed is not None and target is None for observed,target in alignment),**flags})
    aggregates={}
    for name in CLASSES:
        part=[item for item in items if item["class"]==name];n=len(part);length=len(part[0]["answer_bit_correct"])
        word_scores={}
        for slot in range(2):
            selected=[item["words"][slot] for item in part if slot<len(item["words"])]
            word_scores[f"word{slot+1}"]={"questions":len(selected),**{field:sum(item[field] for item in selected) if selected else None for field in WORD_FIELDS}}
        aggregates[name]={"questions":n,"whole_correct":sum(item["whole_correct"] for item in part),"words":word_scores,"answer_position_bit_correct":[sum(item["answer_bit_correct"][index] for item in part) for index in range(length)],"answer_position_bit_totals":[n]*length,"STOP_position_correct":sum(item["STOP_position_correct"] for item in part),"first_error_position_histogram":dict(Counter("none" if item["first_error_position_zero_based"] is None else str(item["first_error_position_zero_based"]) for item in part)),"first_error_kind_histogram":dict(Counter(item["first_error_kind"] for item in part)),"termination_kind_histogram":dict(Counter(item["termination_kind"] for item in part)),"missing_expected_positions":sum(item["missing_expected_positions"] for item in part),"extra_output_positions":sum(item["extra_output_positions"] for item in part),"context_exhausted_questions":sum(item["context_exhausted"] for item in part),"cap_exhausted_questions":sum(item["cap_exhausted"] for item in part)}
    old=None if previous is None else {item["question_id"]:item["tokens"] for item in previous}
    churn={}
    for name in CLASSES:
        selected={task["question_id"]:task["A"]+"S" for task in rows if task["class"]==name}
        if old is None: counts={field:None for field in CHURN_FIELDS}
        else:
            before={qid for qid,target in selected.items() if old[qid]==target}
            current={qid for qid,target in selected.items() if actual_by_id[qid]["tokens"]==target}
            counts={"previous_correct_to_wrong":len(before-current),"previous_wrong_to_correct":len(current-before),"retained_correct":len(before&current),"retained_wrong":len(set(selected)-(before|current))}
        churn[name]={"questions":len(selected),**counts}
    return {"metrics":{"by_class":aggregates,"per_question":items,"extra_forward_calls":0},"churn":{"comparison_available":old is not None,"previous_point":previous_point,"by_class":churn,"extra_forward_calls":0}}

def independent_generation(state,rows,cost,phase):
    before=state_sha(state);forward=Forward(state,cost,phase);outputs=[]
    for task in rows:
        generated=forward.generate(task["Q"])
        outputs.append({"question_id":task["question_id"],"class":task["class"],"pair_id":task["pair_id"],**generated,"whole_correct":generated["tokens"]==task["A"]+"S" and not generated["context_exhausted"]})
    scores={name:{"questions":900,"whole_correct":sum(row["whole_correct"] for row in outputs if row["class"]==name)} for name in CLASSES}
    need(state_sha(state)==before,"full state unchanged by independent generation")
    return {"scores":scores,"rows":outputs,"inference_calls":forward.calls,"inference_dense_MAC":forward.calls*FORWARD_MAC}

def independent_tf(state,rows,free,cost):
    before=state_sha(state);forward=Forward(state,cost,"final_TF");truth=[]
    for task,output in zip(rows,free["rows"],strict=True):
        targets=[]
        for pos,label in enumerate(task["A"]+"S"):
            prefix=task["Q"]+task["A"][:pos]
            logits=forward(prefix).astype(np.float64);logp=logits-np.logaddexp.reduce(logits)
            targets.append({"position":pos,"prefix":prefix,"target":label,"prediction":"01S"[int(logits.argmax())],"logits_01S":logits.tolist(),"probabilities_01S":np.exp(logp).tolist(),"target_CE":-float(logp["01S".index(label)])})
        truth.append({**task,"expected":task["A"]+"S","generation":output,"TF":targets})
    metrics={name:{"questions":900,"TF_correct":sum(point["prediction"]==point["target"] for row in truth if row["class"]==name for point in row["TF"]),"TF_targets":11700 if name in ("E2","F2") else 6300} for name in CLASSES}
    need(forward.calls==36000 and state_sha(state)==before,"complete TF without state mutation")
    return {"truth":truth,"metrics":metrics,"inference_calls":forward.calls,"inference_dense_MAC":forward.calls*FORWARD_MAC,"learning_state_unchanged":True,"free_generation_reused":True}

def decomposed_metrics(truth):
    result={}
    for name in CLASSES:
        rows=[row for row in truth if row["class"]==name];r=2 if name in ("E2","F2") else 1
        info=[pos for pos in range(6*r) if pos%6!=5];tails=[pos for pos in range(6*r) if pos%6==5]
        free_correct=lambda row,pos:pos<len(row["generation"]["tokens"]) and row["generation"]["tokens"][pos]==row["A"][pos]
        result[name]={"questions":900,"info_bit_targets":900*5*r,"tail0_targets":900*r,"STOP_targets":900,"free_whole_correct":sum(row["generation"]["whole_correct"] for row in rows),"free_info_bits_correct":sum(free_correct(row,pos) for row in rows for pos in info),"free_tail0_correct":sum(free_correct(row,pos) for row in rows for pos in tails),"free_STOP_position_correct":sum(row["generation"]["tokens"].endswith("S") and len(row["generation"]["tokens"])==6*r+1 for row in rows),"TF_info_bits_correct":sum(row["TF"][pos]["prediction"]==row["TF"][pos]["target"] for row in rows for pos in info),"TF_tail0_correct":sum(row["TF"][pos]["prediction"]=="0" for row in rows for pos in tails),"TF_STOP_correct":sum(row["TF"][6*r]["prediction"]=="S" for row in rows)}
    return result


def load_state(raw, seed):
    with np.load(io.BytesIO(raw), allow_pickle=False) as z:
        state = {name: z[name].copy() for name in z.files}
    expected = {f"{group}{i}" for group in ("p", "m", "v", "birth") for i in range(4)}
    expected |= {"t", "L", "H", "growth_rng", "meta_seed", "meta_events", "meta_train_macs", "meta_inference_macs", "meta_inference_calls"}
    equal(set(state), expected, "all25 fullstate fields")
    for i, shape in enumerate(((160, 64), (64,), (64, 3), (3,))):
        for group in ("p", "m", "v", "birth"):
            value = state[f"{group}{i}"]
            need(value.shape == shape and value.dtype == (np.int64 if group == "birth" else np.float32), "array shape/dtype")
            need(bool(np.isfinite(value).all()), "finite learning state")
        need(bool((state[f"v{i}"] >= 0).all()), "nonnegative second moment")
        need(bool((state[f"birth{i}"] <= state["t"]).all()), "birth not after t")
    for key in ("t", "L", "H", "meta_seed", "meta_train_macs", "meta_inference_macs", "meta_inference_calls"):
        need(state[key].shape == () and state[key].dtype == np.int64, "integer scalar " + key)
    equal((int(state["L"]), int(state["H"]), int(state["meta_seed"])), (80, 64, seed), "state identity")
    need(int(state["meta_train_macs"]) == int(state["t"]) * TRAIN_MAC, "total training counters")
    need(int(state["meta_inference_macs"]) == int(state["meta_inference_calls"]) * FORWARD_MAC, "total inference counters")
    parse(str(state["growth_rng"]))
    parse(str(state["meta_events"]))
    for value in state.values():
        value.setflags(write=False)
    return state


def inputs(args):
    need(sha(args.manifest) == APPROVED, "approved manifest pin")
    manifest = read(args.manifest)
    equal(manifest["source_hashes"], CORE, "frozen source hashes")
    equal({name: sha(args.code_dir / name) for name in CORE}, CORE, "current sources")
    equal(manifest["runtime"], {"python": platform.python_version(), "numpy": np.__version__, "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1"}, "runtime")
    raw = (args.manifest.parent / "inputs.zip").read_bytes()
    need(digest(raw) == manifest["archive"]["sha256"] == "46f14f6e233ed6f6304c9c0a01779c653647c2f40ae60c57ab4e5d7661f0dc79", "input ZIP pin")
    need(len(raw) == manifest["archive"]["bytes"] == 1272100, "input ZIP bytes")
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        names = z.namelist()
        need(len(names) == len(set(names)) == 36 and set(names) == set(manifest["files"]), "36 ZIP members")
        content = {name: z.read(name) for name in names}
    for name, data in content.items():
        equal(manifest["files"][name], {"sha256": digest(data), "bytes": len(data)}, "frozen member " + name)
    equal(content["plan.json"], (args.code_dir / "protocol.json").read_bytes(), "protocol bytes")
    p = manifest["protocol"]
    publication_raw = content["provenance/publication-manifest.json"]
    equal((digest(publication_raw), blob(publication_raw)), (p["parent_publication_manifest_sha256"], p["parent_publication_manifest_Git_blob"]), "published parent manifest")
    publication = parse(publication_raw.decode("utf-8"))
    proof = parse(content["provenance/public-proof.json"].decode("utf-8"))
    equal(proof["parent_head"], p["parent_head"], "parent commit")
    for name, check in proof["public_byte_checks"].items():
        expected = {"sha256": digest(publication_raw), "Git_blob": blob(publication_raw), "bytes": len(publication_raw)} if name == "publication-manifest.json" else publication["files"][name]
        need(check["byte_match"] and check["ref_match"] and check["commit"] == p["parent_head"], "public byte receipt")
        for key in ("sha256", "Git_blob", "bytes"):
            equal(check[key], expected[key], "public receipt " + key)
    for name, source in proof["selected_members"].items():
        if source["archive"] == "inputs.zip":
            equal(source["slice_sha256"], digest(content[name]), "selected course bytes")
        else:
            expected = publication["archives"][source["archive"]]["members"][source["member"]]
            raw = content[name]
            equal((digest(raw), blob(raw), len(raw), format(zlib.crc32(raw), "08x")),
                  (expected["sha256"], expected["Git_blob"], expected["bytes"], expected["CRC32"]), "public source member")
    source = content["source/p030_binary_continual.py"]
    need(digest(source) == p["source_sha256"], "original learner source pin")
    node = next(n for n in ast.parse(source).body if isinstance(n, ast.ClassDef) and n.name == "Model")
    original = ast.dump(node, include_attributes=False)
    need(digest(original.encode()) == p["Model_AST_sha256"], "Model AST pin")
    step = next(n for n in node.body if isinstance(n, ast.FunctionDef) and n.name == "step")
    leaves = [n for n in ast.walk(step) if isinstance(n, ast.Constant) and type(n.value) is float and n.value == .003]
    need(len(leaves) == 1, "single eta leaf")
    leaves[0].value = .001
    changed = ast.dump(node, include_attributes=False)
    equal(content["source/Model-original.ast"], (original + "\n").encode(), "original AST dump")
    equal(content["source/Model-eta001.ast"], (changed + "\n").encode(), "changed AST dump")
    rows = parse(content["questions.json"].decode("utf-8"))
    bank = parse(content["payloads.json"].decode("utf-8"))
    need(len(rows) == 3600 and len(bank) == 900, "fixed exposed bank")
    for qid, row in enumerate(rows):
        class_index, pair = divmod(qid, 900)
        name, r = CLASSES[class_index], 2 if class_index in (1, 3) else 1
        payload = bank[pair]
        need(payload[:2] == [pair // 30, pair % 30] and len(payload) == 4 and all(type(x) is int and 0 <= x < 30 for x in payload), "payload IDs")
        word = lambda x: format(x, "05b") + "0"
        op = "010" if name.startswith("E") else "100"
        question = "01" + op + format(r, "03b") + "0" + "".join(word(x) for x in payload) + "111100"
        answer = "".join(word(x if op == "010" else 31 - x) for x in payload[:r])
        equal(row, {"question_id": qid, "pair_id": pair, "r": r, "payload": payload, "Q": question, "A": answer, "class": name, "op": op}, "independent Q/A grammar")
    old = parse(content["provenance/F2-manifest.json"].decode("utf-8"))
    need(digest(content["provenance/F2-manifest.json"]) == publication["files"]["manifest.json"]["sha256"], "historical manifest pin")
    pool = np.asarray([(offset + pair, pos) for pair in range(900) for offset in (0, 900, 1800, 2700)
                       for pos in range(7 if offset in (0, 1800) else 13)], dtype="<u2")
    parents, controls, orders = {}, {}, {}
    for seed, (epoch, start_t) in START.items():
        key = str(seed)
        equal(content[f"initial/seed{seed}.npz"], content[f"historical/seed{seed}/start-state.npz"], "exact start raw container")
        parents[seed] = load_state(content[f"initial/seed{seed}.npz"], seed)
        controls[seed] = load_state(content[f"historical/seed{seed}/control-state.npz"], seed)
        need(int(parents[seed]["t"]) == start_t and int(controls[seed]["t"]) == start_t + 36000, "paired t")
        equal(state_sha(parents[seed]), manifest["parents"][key]["full_state_sha256"], "starting fullstate hash")
        rng = np.random.default_rng(seed + 555000)
        whole = np.stack([pool[rng.permutation(36000)] for _ in range(40)])
        temp = io.BytesIO(); np.save(temp, whole, allow_pickle=False)
        need(digest(temp.getvalue()) == old["files"][old["schedules"][key]["file"]]["sha256"], "original40course raw hash")
        orders[seed] = np.load(io.BytesIO(content[f"orders/seed{seed}.npy"]), allow_pickle=False)
        need(orders[seed].dtype.str == "<u2" and orders[seed].shape == (36000, 2), "nextcourse schema")
        need(np.array_equal(orders[seed], whole[epoch]), "exact historical nextcourse slice")
    return manifest, content, rows, parents, controls, orders


def generation_schema(value, rows):
    need(len(value["rows"]) == len(rows) == 3600, "complete generation")
    for expected, actual in zip(rows, value["rows"], strict=True):
        for key in ("question_id", "pair_id", "class"):
            equal(actual[key], expected[key], "generation identity")
        need(isinstance(actual["tokens"], str) and set(actual["tokens"]) <= set("01S") and len(actual["tokens"]) <= 32, "raw generated tokens")
        for key in ("whole_correct", "cap_exhausted", "context_exhausted"):
            need(type(actual[key]) is bool, "boolean generation flag")
        equal(actual["whole_correct"], actual["tokens"] == expected["A"] + "S" and not actual["context_exhausted"], "whole flag")
    need(type(value["inference_calls"]) is int and value["inference_calls"] >= 0, "generation calls")
    equal(value["inference_dense_MAC"], value["inference_calls"] * FORWARD_MAC, "generation MAC")


def preflight(args, bundle):
    manifest, content, rows, parents, controls, orders = bundle
    work, science = args.work, args.work / "science"
    required = {name: work / name for name in ("execution.stdout.log", "execution.stderr.log", "execution-receipt.json", "git-prereg-receipt.json", "formal-command-result.json")}
    required |= {"compact": science / "compact.json", "intent": science / "execution-intent.json", "timing": science / "timing.json"}
    names = ("initial-state.npz", "baseline-before.npz", "baseline-after.npz", "baseline-generation.json", "baseline.json", "new-final-state.npz", "new-generation.json", "new-token-metrics.json", "training.json", "historical-control-state.npz", "historical-control-generation.json", "historical-control-record.json", "paired-metrics.json", "final-truth.json", "final-after-TF.npz")
    expected_files = {"compact.json", "execution-intent.json", "timing.json"}
    for seed in START:
        for name in names:
            required[f"seed{seed}/{name}"] = science / f"seed{seed}/{name}"
            expected_files.add(f"seed{seed}/{name}")
    need(all(path.is_file() for path in required.values()), "all actual metadata/science paths exist before any forward")
    science_before = inventory(science)
    equal(set(science_before), expected_files, "all actual scientific files, no omitted student/failure")
    receipt = read(required["execution-receipt.json"])
    equal(receipt["status"], "exit0", "root actual process status")
    for key, value in (("formal_exit", 0), ("exit_code", 0), ("session_id", args.formal_session), ("command_invocations", 1), ("new_optimizer_updates", 108000), ("new_training_dense_MAC", 2274048000)):
        need(type(receipt[key]) is int and receipt[key] == value, "receipt " + key)
    equal(receipt["manifest_sha256"], APPROVED, "receipt manifest")
    equal(receipt["preregistration_commit"], args.preregistration_commit, "receipt commit")
    need(type(receipt["prereg_PR_number"]) is int and receipt["prereg_PR_number"] > 0, "prereg PR")
    from datetime import datetime
    dates = [datetime.fromisoformat(receipt[key].replace("Z", "+00:00")) for key in ("prereg_PR_created_UTC", "intent_created_UTC")]
    need(dates[0] < dates[1], "prereg predates formal intent")
    command = read(required["formal-command-result.json"])
    equal((command["exit_code"], command["command_invocations"], command["formal_seconds"]), (0, 1, receipt["formal_seconds"]), "actual subprocess wrapper result")
    need(isinstance(receipt["formal_seconds"], (float, int)) and receipt["formal_seconds"] > 0, "positive formal wall time")
    git_receipt = read(required["git-prereg-receipt.json"])
    need(git_receipt["all_actual_bytes_verified"] is True and git_receipt["preregistration_commit"] == args.preregistration_commit, "Git prereg receipt")
    intent = read(required["intent"])
    equal(intent, {"approved_manifest_sha256": APPROVED, "preregistration_commit": args.preregistration_commit,
                   "source_hashes": CORE, "all_baselines_before_any_optimizer": True, "primary_seeds": [101, 202, 303],
                   "replay_seeds": [], "new_updates_all_primary": 108000, "auto_retry": False}, "native execution intent")
    compact = read(required["compact"])
    equal(compact["status"], "complete", "completed command")
    equal([item["seed"] for item in compact["students"]], [101, 202, 303], "all3 students retained")
    equal(receipt["students"], compact["students"], "receipt retains full students")
    equal((compact["new_updates"], compact["new_training_dense_MAC"], compact["new_replay_updates"], compact["new_replay_training_dense_MAC"], compact["exact_full_replays"]), (108000, 2274048000, 0, 0, []), "fixed training budget and no replay")
    logs = [parse(line) for line in required["execution.stdout.log"].read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    need(len(logs) == 4, "three progress events and final compact")
    equal(logs[-1], compact, "actual stdout complete result")
    equal(logs[:3], [{"seed": seed, "phase": "one_epoch_primary_complete", "new_updates": 36000} for seed in START], "three progress events")
    need(required["execution.stderr.log"].stat().st_size == 0, "empty successful formal stderr")
    timings = read(required["timing"])
    need(len(timings) == 3 and [x["seed"] for x in timings] == list(START), "three primary timings")
    need(all(x["mode"] == "primary" and x["seconds"] > 0 for x in timings), "primary timing scope")
    states, saved = {}, {}
    for seed, (epoch, start_t) in START.items():
        folder, prefix = science / f"seed{seed}", f"historical/seed{seed}"
        need((folder / "initial-state.npz").read_bytes() == content[f"initial/seed{seed}.npz"], "initial rawbytes")
        need((folder / "historical-control-state.npz").read_bytes() == content[f"{prefix}/control-state.npz"], "control rawbytes")
        for suffix in ("generation.json", "record.json"):
            equal((folder / ("historical-control-" + suffix)).read_bytes(), content[f"{prefix}/control-{suffix}"], "historical raw file")
        states[seed] = {name: load_state((folder / name).read_bytes(), seed) for name in ("initial-state.npz", "baseline-before.npz", "baseline-after.npz", "new-final-state.npz", "final-after-TF.npz", "historical-control-state.npz")}
        values = saved[seed] = {name: read(folder / name) for name in names if name.endswith(".json")}
        for name in ("baseline-generation.json", "new-generation.json", "historical-control-generation.json"):
            generation_schema(values[name], rows)
        equal(values["baseline-generation.json"], parse(content[f"{prefix}/start-generation.json"].decode("utf-8")), "fresh baseline equals old complete generation")
        need(all(x["whole_correct"] == 900 for x in values["baseline-generation.json"]["scores"].values()), "all3baseline integrity")
        truth = values["final-truth.json"]
        need(len(truth["truth"]) == 3600 and truth["inference_calls"] == 36000, "all new finalTF points")
        for row, target in zip(truth["truth"], rows, strict=True):
            equal(row["question_id"], target["question_id"], "TF question identity")
            need(len(row["TF"]) == len(target["A"]) + 1, "all TF positions")
        trace = values["training.json"]["training"]
        need(trace["targets"] == 36000 and 0 <= trace["pre_update_prediction_correct"] <= 36000, "training aggregate targets")
        need(trace["CE_loss_sum"] >= 0 and trace["CE_loss_mean"] == trace["CE_loss_sum"] / 36000, "training aggregate mean")
        need(re.fullmatch("[0-9a-f]{64}", trace["canonical_target_trace_sha256"]) is not None, "recorded target digest format")
    metadata = {"status": "passed", "manifest_sha256": APPROVED, "root_confirmed_formal_exit0": True,
                "formal_session": args.formal_session, "preregistration_commit": args.preregistration_commit,
                "source_hashes": CORE, "required_paths_exist": len(required), "science_files": len(science_before),
                "science_npz": sum(name.endswith(".npz") for name in science_before), "all3baseline_integrity": True,
                "full_TF_shape_checked_before_NN": True, "reviewer_forward_calls_at_preflight": 0,
                "formal_command_seconds": receipt["formal_seconds"], "primary_timing_sum_seconds": sum(x["seconds"] for x in timings),
                "timing_scope": "root wrapper wall includes command; primary timing list excludes baseline/finalTF/validation; not required to be equal",
                "receipt_sha256": sha(required["execution-receipt.json"])}
    write(args.out / "metadata-preflight.json", metadata)
    guards = {str(path.relative_to(args.work)): {"bytes": path.stat().st_size, "sha256": sha(path)} for path in required.values() if path.is_relative_to(args.work) and not path.is_relative_to(science)}
    return compact, receipt, timings, states, saved, science_before, guards


def paired(rows, baseline, new, control):
    maps = [{x["question_id"]: x["tokens"] for x in gen["rows"]} for gen in (baseline, new, control)]
    result = {}
    for name in CLASSES:
        tasks = {r["question_id"]: r["A"] + "S" for r in rows if r["class"] == name}
        old, a, b = [{qid for qid, target in tasks.items() if mapping[qid] == target} for mapping in maps]
        equal(len(old), 900, "paired all-correct start")
        lost_a, lost_b = sorted(old - a), sorted(old - b)
        result[name] = {"questions": 900, "new_lost_QIDs": lost_a, "control_lost_QIDs": lost_b,
                        "new_lost": len(lost_a), "control_lost": len(lost_b), "new_minus_control_lost": len(lost_a) - len(lost_b),
                        "between_arm_QIDs": {"both_correct": sorted(a & b), "new_only_correct": sorted(a - b), "control_only_correct": sorted(b - a), "both_wrong": sorted(set(tasks) - (a | b))}}
    n, c = sum(x["new_lost"] for x in result.values()), sum(x["control_lost"] for x in result.values())
    return {"by_class": result, "new_total_lost": n, "historical_control_total_lost": c, "new_minus_control_lost": n - c,
            "directional_hypothesis_pass": n < c, "new_all_four_classes_full": n == 0,
            "new_churn": independent_readout(rows, new["rows"], baseline["rows"])["churn"],
            "historical_churn": independent_readout(rows, control["rows"], baseline["rows"])["churn"], "extra_forward_calls": 0}


def unchanged_except(a, b, except_fields, label):
    same_state({k: v for k, v in a.items() if k not in except_fields}, {k: v for k, v in b.items() if k not in except_fields}, label)


def proof(args, cost, seed, point, data):
    path = args.out / "numeric-proof" / f"seed{seed}-{point}.json"
    write(path, {"status": "passed", "seed": seed, "point": point, "strict_equality": True, **data, "audit_cost_cumulative": cost.record()})
    cost.persist("running")


def audit_student(args, seed, bundle, context, cost):
    manifest, content, rows, parents, controls, orders = bundle
    compact, receipt, timings, all_states, all_saved, science_before, guards = context
    states, saved = all_states[seed], all_saved[seed]
    parent = parents[seed]
    before, after = states["baseline-before.npz"], states["baseline-after.npz"]
    new_state, final_state = states["new-final-state.npz"], states["final-after-TF.npz"]
    same_state(states["initial-state.npz"], parent, "raw initial fullstate")
    same_state(before, parent, "baseline before exactparent")
    same_state(states["historical-control-state.npz"], controls[seed], "exact historicalcontrol")
    inf = {"meta_inference_calls", "meta_inference_macs"}
    unchanged_except(before, after, inf, "baseline learning/RNG/events unchanged")
    unchanged_except(new_state, final_state, inf, "finalTF learning/RNG/events unchanged")
    immutable = {"L", "H", "growth_rng", "meta_seed", "meta_events", *(f"birth{i}" for i in range(4))}
    same_state({k: parent[k] for k in immutable}, {k: new_state[k] for k in immutable}, "new training immutable fields")
    need(int(new_state["t"]) - int(parent["t"]) == 36000, "one epoch new t")
    need(int(new_state["meta_train_macs"]) - int(parent["meta_train_macs"]) == 758016000, "new training MAC delta")
    generated = {}
    for point, state, source in (("baseline", before, "baseline-generation.json"), ("control", controls[seed], "historical-control-generation.json"), ("new", new_state, "new-generation.json")):
        result = independent_generation(state, rows, cost, f"seed{seed}_{point}")
        equal(result, saved[source], "independent complete generation " + point)
        generated[point] = result
        readout = independent_readout(rows, result["rows"])["metrics"]
        if point == "new":
            equal(readout, saved["new-token-metrics.json"], "all new token/word/STOP/firsterror metrics")
        else:
            record = parse(content[f"historical/seed{seed}/{'start' if point == 'baseline' else 'control'}-record.json"].decode("utf-8"))
            equal(readout["by_class"], record["token_metrics"], "historical independent token metrics")
            equal(state_sha(state), record["full_state_sha256"], "historical endpoint canonical hash")
        proof(args, cost, seed, point, {"whole_questions": 3600, "free_inference_calls": result["inference_calls"],
                                       "state_sha256": state_sha(state), "scores": result["scores"], "token_metrics": readout["by_class"],
                                       "per_question_token_metrics_sha256": digest(canonical(readout["per_question"]).encode())})
    baseline, control, new = generated["baseline"], generated["control"], generated["new"]
    need(int(after["meta_inference_calls"]) - int(before["meta_inference_calls"]) == baseline["inference_calls"], "fresh baseline calls")
    need(int(new_state["meta_inference_calls"]) - int(after["meta_inference_calls"]) == new["inference_calls"], "new probe calls")
    need(int(final_state["meta_inference_calls"]) - int(new_state["meta_inference_calls"]) == 36000, "new TF calls")
    record = saved["baseline.json"]
    equal(record, {"seed": seed, "scores": baseline["scores"], "all_four_integrity_pass": True,
                   "archived_start_generation_exact": True, "before_state_sha256": state_sha(before), "after_state_sha256": state_sha(after),
                   "baseline_inference_calls": baseline["inference_calls"], "baseline_inference_MAC": baseline["inference_dense_MAC"],
                   "new_optimizer_updates": 0, "only_inference_counters_changed": True}, "baseline record")
    truth = independent_tf(new_state, rows, new, cost)
    equal(truth, saved["final-truth.json"], "all finalTF logits/probabilities/CE/prefixes/labels")
    proof(args, cost, seed, "TF", {"TF_questions": 3600, "TF_targets": 36000, "metrics": truth["metrics"],
                                  "decomposed_metrics": decomposed_metrics(truth["truth"]), "new_free_reused": True})
    pair = paired(rows, baseline, new, control)
    equal(pair, saved["paired-metrics.json"], "all QID-paired lost/churn/readout")
    train = saved["training.json"]
    equal({k: train[k] for k in ("seed", "eta", "source_epoch", "start_counters", "final_counters", "new_updates", "new_training_dense_MAC", "scores", "new_probe_inference_calls", "new_probe_inference_MAC", "full_state_sha256", "replay_status")},
          {"seed": seed, "eta": .001, "source_epoch": START[seed][0] + 1, "start_counters": counters(parent), "final_counters": counters(new_state),
           "new_updates": 36000, "new_training_dense_MAC": 758016000, "scores": new["scores"], "new_probe_inference_calls": new["inference_calls"],
           "new_probe_inference_MAC": new["inference_dense_MAC"], "full_state_sha256": state_sha(new_state), "replay_status": "not_planned"}, "training endpoint metadata/counters")
    expected = {"seed": seed, "start_epoch": START[seed][0], "source_epoch": START[seed][0] + 1,
                "start_counters": counters(parent), "final_counters": counters(final_state), "new_updates": 36000,
                "new_training_dense_MAC": 758016000, "scores": new["scores"], "primary_pair": pair,
                "baseline_inference_calls": baseline["inference_calls"], "baseline_inference_MAC": baseline["inference_dense_MAC"],
                "new_probe_inference_calls": new["inference_calls"], "new_probe_inference_MAC": new["inference_dense_MAC"],
                "final_TF_inference_calls": truth["inference_calls"], "final_TF_inference_MAC": truth["inference_dense_MAC"],
                "TF_metrics": truth["metrics"], "replay_status": "not_planned"}
    equal(expected, next(x for x in compact["students"] if x["seed"] == seed), "complete student summary")
    proof(args, cost, seed, "student", {"primary_pair": pair, "state_and_counter_checks": "all25fields validated; all inference-only transitions exact", "optimizer_replay_performed": False})
    return expected


def run(args, cost):
    bundle = inputs(args)
    context = preflight(args, bundle)
    cost.persist("metadata_passed")
    before_inputs = {str(path): sha(path) for path in (args.manifest, args.manifest.parent / "inputs.zip", *(args.code_dir / n for n in CORE))}
    students = [audit_student(args, seed, bundle, context, cost) for seed in START]
    compact, receipt, timings, states, saved, science_before, guards = context
    equal(compact["primary_hypothesis_all_three_fewer_lost"], all(x["primary_pair"]["directional_hypothesis_pass"] for x in students), "strict all3 hypothesis including failures/ties")
    equal(compact["new_four_class_full_seeds"], [x["seed"] for x in students if x["primary_pair"]["new_all_four_classes_full"]], "new fullfit seeds")
    equal(compact["final_TF_inference_calls"], 108000, "new finalTF target count")
    equal(inventory(args.work / "science"), science_before, "science unchanged through independent audit")
    equal({str(path): sha(path) for path in (args.manifest, args.manifest.parent / "inputs.zip", *(args.code_dir / n for n in CORE))}, before_inputs, "source/manifest/inputs unchanged")
    equal({name: {"bytes": (args.work / name).stat().st_size, "sha256": sha(args.work / name)} for name in guards}, guards, "receipt/stdout/stderr/command metadata unchanged")
    refs = sorted(path.relative_to(args.out).as_posix() for path in (args.out / "numeric-proof").glob("*.json"))
    need(len(refs) == 15, "all12numeric point proofs plus3student proofs")
    proof_inventory = {name: {"bytes": (args.out / name).stat().st_size, "sha256": sha(args.out / name)} for name in refs}
    details = {"status": "passed", "manifest_sha256": APPROVED, "source_hashes": CORE,
               "root_confirmed_formal_exit0": True, "receipt_sha256": sha(args.work / "execution-receipt.json"),
               "science_file_inventory": science_before, "numeric_proof_refs": refs, "numeric_proof_inventory": proof_inventory,
               "students": students, "audit_cost": cost.record(), "formal_command_wall_seconds": receipt["formal_seconds"],
               "three_primary_segment_seconds": timings, "source_inputs_science_receipt_unchanged": True}
    write(args.out / "post-run-details.json", details)
    summary = {"schema": "f2-stability-independent-post-run-v1", "status": "passed", "manifest_sha256": APPROVED,
               "source_hashes": CORE, "review_source_sha256": sha(Path(__file__)), "root_confirmed_formal_exit0": True,
               "formal_session": args.formal_session, "preregistration_commit": args.preregistration_commit,
               "receipt_sha256": details["receipt_sha256"], "reviewer_optimizer_calls": 0, "reviewer_new_students": 0,
               "free_questions_independently_generated": 32400, "finalTF_targets_independently_recomputed": 108000,
               "strict_equality": True, "proofs": len(refs), "science_files": len(science_before),
               "baseline_new_historical_control_audited": True, "actual_optimizer_replay": False,
               "students": [{"seed": x["seed"], "new_lost": x["primary_pair"]["new_total_lost"],
                             "historical_lost": x["primary_pair"]["historical_control_total_lost"],
                             "strict_directional_pass": x["primary_pair"]["directional_hypothesis_pass"], "scores": x["scores"]} for x in students],
               "all3_strict_hypothesis": compact["primary_hypothesis_all_three_fewer_lost"], "audit_cost": cost.record(),
               "details_sha256": sha(args.out / "post-run-details.json"),
               "limitations": ["Posthoc first-full historical starts, one fixed next epoch, exposed900bank and3inherited students.",
                               "No independent optimizer/gradient replay. Training aggregate digest form/source provenance checked, not raw pertarget losses or intermediate weights.",
                               "Formal root whole-command wall and primary-only timing list have different scopes; independent inference audit cost separate."]}
    write(args.out / "post-run.json", summary)
    cost.persist("passed")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--code-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--formal-session", type=int, required=True)
    parser.add_argument("--preregistration-commit", required=True)
    parser.add_argument("--root-confirmed-exit0", action="store_true")
    args = parser.parse_args()
    need(args.root_confirmed_exit0 and re.fullmatch("[0-9a-f]{40}", args.preregistration_commit), "explicit root postrunGO and actualcommit required")
    for attr in ("work", "code_dir", "manifest", "out"):
        setattr(args, attr, getattr(args, attr).resolve())
    args.out.mkdir(parents=True, exist_ok=True)
    need(not any((args.out / name).exists() for name in ("audit-cost.json", "post-run.json", "post-run-details.json", "metadata-preflight.json", "numeric-proof")), "one actual audit only; preserve previous attempts")
    (args.out / "numeric-proof").mkdir()
    cost = Cost(args.out)
    cost.persist("starting_metadata_only")
    try:
        result = run(args, cost)
        print(canonical({"status": result["status"], "students": result["students"], **cost.record()}), flush=True)
    except Exception as error:
        cost.persist("failed")
        write(args.out / "audit-failure.json", {"status": "failed", "type": type(error).__name__, "message": str(error),
                                              "actual_cost": cost.record(), "retry_authorized": False})
        raise


if __name__ == "__main__":
    main()
