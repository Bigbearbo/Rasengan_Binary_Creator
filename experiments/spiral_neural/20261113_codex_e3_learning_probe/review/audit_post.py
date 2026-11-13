"""E3 bounded independent audit. Reuses hash-pinned pure audit defs, never learner/driver code."""
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

if sys.flags.optimize:
    raise RuntimeError("Non-optimized Python required")
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
sys.dont_write_bytecode = True
import numpy as np

HERE = Path(__file__).resolve().parent
VENDOR = HERE / "vendor/f2_stability_audit.py"
VENDOR_SHA = "443ad00cb9cebe94c6cc5e22602f139586c35c7310e48623e21d515b2e72aacc"
APPROVED = "5e2b3e6eb90c20a27c12ff9d743c8f0ab65a759fff4d561c6d156b535497c8bc"
CORE = {"run_probe.py": "2e4033c6b47b1db84a5fa01cd9344622183a22b50178e2ee2f82331781d9b196",
        "protocol.json": "b59735c8933668fbe1ce5b630c01e1c4ffa5b4647ab77c8c786608ca7aaedac8",
        "test_probe.py": "8bf2d56b3b423e842ac1301e30a507ca9bd8c17860e7e9c0bdd6f54883b13a31"}
CLASSES = ("E1", "E2", "F1", "F2", "E3")
SEEDS = (101, 202, 303)
ARMS = ("eta001", "eta003")
FORWARD_MAC, TRAIN_MAC = 10432, 21056
WORD_FIELDS = ("information5_correct", "tail0_correct", "complete6_correct")
CHURN_FIELDS = ("previous_correct_to_wrong", "previous_wrong_to_correct", "retained_correct", "retained_wrong")


def borrow():
    raw = VENDOR.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == VENDOR_SHA
    wanted = {"need", "canonical", "digest", "sha", "finite", "parse", "read", "write", "equal", "inventory", "state_sha",
              "same_state", "Cost", "Forward", "counters", "load_state", "independent_readout"}
    nodes = [node for node in ast.parse(raw).body if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in wanted]
    assert {node.name for node in nodes} == wanted
    changes = 0
    for node in nodes:
        if node.name != "independent_readout":
            continue
        for loop in ast.walk(node):
            if isinstance(loop, ast.For) and isinstance(loop.target, ast.Name) and loop.target.id == "slot" and isinstance(loop.iter, ast.Call) and isinstance(loop.iter.func, ast.Name) and loop.iter.func.id == "range" and len(loop.iter.args) == 1 and isinstance(loop.iter.args[0], ast.Constant) and loop.iter.args[0].value == 2:
                loop.iter = ast.parse("range(max(len(item['words']) for item in part))", mode="eval").body
                changes += 1
    assert changes == 1, "Only aggregate word-slot limit is generalized"
    namespace = dict(globals())
    namespace["__name__"] = "pinned_independent_audit_math"
    exec(compile(ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[])), "<pinned-pure-audit-definitions>", "exec"), namespace)
    return namespace


M = borrow()
for _name in ("need", "canonical", "digest", "sha", "finite", "parse", "read", "write", "equal", "inventory", "state_sha", "same_state", "Cost", "Forward", "counters", "load_state"):
    globals()[_name] = M[_name]


def names(rows):
    return [name for name in CLASSES if any(row["class"] == name for row in rows)]


def readout(rows, outputs):
    M["CLASSES"] = names(rows)
    return M["independent_readout"](rows, outputs)["metrics"]


def generation(state, rows, cost, phase):
    before = state_sha(state)
    forward, outputs = Forward(state, cost, phase), []
    for row in rows:
        result = forward.generate(row["Q"])
        outputs.append({"question_id": row["question_id"], "class": row["class"], "pair_id": row["pair_id"], **result,
                        "whole_correct": result["tokens"] == row["A"] + "S" and not result["context_exhausted"]})
    scores = {name: {"questions": sum(row["class"] == name for row in rows), "whole_correct": sum(x["whole_correct"] for x in outputs if x["class"] == name)} for name in names(rows)}
    equal(state_sha(state), before, "independent generation state immutable")
    return {"rows": outputs, "scores": scores, "inference_calls": forward.calls, "inference_dense_MAC": forward.calls * FORWARD_MAC}


def teacher(state, rows, free, cost, phase):
    before = state_sha(state)
    forward, truth = Forward(state, cost, phase), []
    by_id = {row["question_id"]: row for row in free["rows"]}
    for row in rows:
        points = []
        for pos, label in enumerate(row["A"] + "S"):
            prefix = row["Q"] + row["A"][:pos]
            logits = forward(prefix).astype(np.float64)
            logp = logits - np.logaddexp.reduce(logits)
            points.append({"position": pos, "prefix": prefix, "target": label, "prediction": "01S"[int(np.argmax(logits))],
                           "logits_01S": logits.tolist(), "probabilities_01S": np.exp(logp).tolist(), "target_CE": -float(logp["01S".index(label)])})
        truth.append({**row, "expected": row["A"] + "S", "generation": by_id[row["question_id"]], "TF": points})
    metrics = {}
    for name in names(rows):
        part = [row for row in truth if row["class"] == name]
        length = len(part[0]["A"])
        words = {}
        for slot in range(part[0]["r"]):
            start = 6 * slot
            info = [[point["prediction"] == point["target"] for point in row["TF"][start:start + 5]] for row in part]
            complete = [all(point["prediction"] == point["target"] for point in row["TF"][start:start + 6]) for row in part]
            words[f"word{slot+1}"] = {"questions": len(part), "information5_correct": sum(all(bits) for bits in info),
                "information_bits_correct": sum(sum(bits) for bits in info), "information_bits_total": 5 * len(part),
                "tail0_correct": sum(row["TF"][start + 5]["prediction"] == "0" for row in part), "complete6_correct": sum(complete)}
        metrics[name] = {"questions": len(part), "TF_correct": sum(point["prediction"] == point["target"] for row in part for point in row["TF"]),
            "TF_targets": sum(len(row["TF"]) for row in part), "TF_STOP_correct": sum(row["TF"][-1]["prediction"] == "S" for row in part),
            "CE_loss_sum": sum(point["target_CE"] for row in part for point in row["TF"]), "words": words,
            "answer_position_TF_correct": [sum(row["TF"][i]["prediction"] == row["TF"][i]["target"] for row in part) for i in range(length)],
            "answer_position_TF_total": [len(part)] * length}
    need(forward.calls == sum(len(row["A"]) + 1 for row in rows), "exact TF scope")
    equal(state_sha(state), before, "independent TF state immutable")
    return {"truth": truth, "metrics": metrics, "inference_calls": forward.calls, "inference_dense_MAC": forward.calls * FORWARD_MAC,
            "learning_state_unchanged": True, "free_generation_reused": True}


def churn(rows, before, after):
    a, b = [{row["question_id"]: row["tokens"] for row in part} for part in (before, after)]
    result = {}
    for name in names(rows):
        tasks = {row["question_id"]: row["A"] + "S" for row in rows if row["class"] == name}
        old = {qid for qid, target in tasks.items() if a[qid] == target}
        new = {qid for qid, target in tasks.items() if b[qid] == target}
        groups = {"previous_correct_to_wrong": sorted(old-new), "previous_wrong_to_correct": sorted(new-old), "retained_correct": sorted(old&new), "retained_wrong": sorted(set(tasks)-(old|new))}
        result[name] = {"questions": len(tasks), **{key: len(value) for key, value in groups.items()}, "QIDs": groups}
    return {"by_class": result, "extra_forward_calls": 0}


def feasibility(rows, cold, endpoint):
    changes = churn(rows, cold, endpoint)
    old_lost = {name: changes["by_class"][name]["QIDs"]["previous_correct_to_wrong"] for name in CLASSES[:-1]}
    by_id = lambda values: {x["question_id"]: x["tokens"] for x in values}
    a, b = by_id(cold), by_id(endpoint)
    tasks = {r["question_id"]: r["A"] + "S" for r in rows if r["class"] == "E3"}
    ca, cb = [sum(mapping[qid] == target for qid, target in tasks.items()) for mapping in (a, b)]
    lost = sum(len(x) for x in old_lost.values())
    return {"old_lost_total": lost, "old_lost_QIDs_by_class": old_lost, "cold_E3_whole": ca, "E3_whole": cb,
            "E3_whole_gain": cb-ca, "strict_feasibility": lost == 0 and cb > ca, "baseline_ceiling": ca == len(tasks),
            "learning_gain_identifiability": "ceiling" if ca == len(tasks) else "not_at_ceiling", "churn": changes, "extra_forward_calls": 0}


def paired(rows, cold, low, high):
    a, b = feasibility(rows, cold, low), feasibility(rows, cold, high)
    am, bm = [{row["question_id"]: row["tokens"] for row in part} for part in (low, high)]
    result = {}
    for name in CLASSES:
        tasks = {r["question_id"]: r["A"] + "S" for r in rows if r["class"] == name}
        x = {qid for qid, expected in tasks.items() if am[qid] == expected}
        y = {qid for qid, expected in tasks.items() if bm[qid] == expected}
        groups = {"both_correct": sorted(x&y), "eta001_only_correct": sorted(x-y), "eta003_only_correct": sorted(y-x), "both_wrong": sorted(set(tasks)-(x|y))}
        result[name] = {"questions": len(tasks), "QIDs": groups, "counts": {key: len(value) for key, value in groups.items()}}
    return {"eta001": a, "eta003": b, "axes_eta001_minus_eta003": {"old_lost": a["old_lost_total"]-b["old_lost_total"], "E3_whole_gain": a["E3_whole_gain"]-b["E3_whole_gain"]}, "by_class": result, "extra_forward_calls": 0}


def interpretation(items):
    passed = all(x["strict_feasibility"] for x in items)
    return {"strict_feasibility_all_three": passed, "overall_interpretation": "not_identifiable_ceiling" if any(x["baseline_ceiling"] for x in items) else "pass" if passed else "not_met"}


def without(a, b, fields, label):
    same_state({k:v for k,v in a.items() if k not in fields}, {k:v for k,v in b.items() if k not in fields}, label)


def inputs(a):
    need(sha(a.manifest) == APPROVED, "approved manifest")
    m = read(a.manifest)
    equal(m["source_hashes"], CORE, "manifest core pins")
    equal({name:sha(a.code_dir/name) for name in CORE}, CORE, "current core pins")
    equal(m["runtime"], {"python":platform.python_version(), "numpy":np.__version__, "OPENBLAS_NUM_THREADS":"1", "OMP_NUM_THREADS":"1"}, "runtime")
    raw = (a.manifest.parent/"inputs.zip").read_bytes()
    need(digest(raw) == m["archive"]["sha256"] == "b658716bd3e4bba693ab33c26e429f406fc326fe220bfa1679cb5fb446ff4efc" and len(raw) == 926204, "frozen ZIP")
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        need(len(z.namelist()) == len(set(z.namelist())) == 22 and set(z.namelist()) == set(m["files"]), "ZIP inventory")
        c = {name:z.read(name) for name in z.namelist()}
    for name, data in c.items():
        equal(m["files"][name], {"sha256":digest(data), "bytes":len(data)}, "input member "+name)
    equal(c["plan.json"], (a.code_dir/"protocol.json").read_bytes(), "protocol exact")
    rows, bank = parse(c["questions.json"].decode()), parse(c["payloads.json"].decode())
    old = parse(c["parent-questions.json"].decode())
    need(len(rows) == 4500 and len(bank) == 900 and rows[:3600] == old, "complete old+E3 bank")
    for qid, row in enumerate(rows):
        k, pair = divmod(qid, 900)
        name = CLASSES[k];take = (1,2,1,2,3)[k];op = "100" if k in (2,3) else "010"
        payload = bank[pair];word = lambda v:format(v,"05b")+"0"
        expected = {"question_id":qid,"pair_id":pair,"r":take,"payload":payload,"Q":"01"+op+format(take,"03b")+"0"+"".join(word(v) for v in payload)+"111100","A":"".join(word(31-v if op=="100" else v) for v in payload[:take]),"class":name,"op":op}
        equal(row, expected, "independent grammar")
    pool = np.asarray([(900*k+pair,j) for pair in range(900) for k,count in enumerate((7,13,7,13,19)) for j in range(count)],dtype="<u2")
    parents = {}
    for seed, t in ((101,1017000),(202,1228500),(303,1161900)):
        state = load_state(c[f"initial/seed{seed}.npz"],seed)
        need(int(state["t"]) == t, "parent t")
        equal(state_sha(state),m["parents"][str(seed)]["full_state_sha256"],"parent canonical hash")
        parents[seed] = state
        actual = np.load(io.BytesIO(c[f"orders/seed{seed}.npy"]),allow_pickle=False)
        expected = pool[np.random.default_rng(seed+666000).permutation(53100)]
        need(actual.dtype.str == "<u2" and np.array_equal(actual,expected),"one frozen paired course")
    return m,c,rows,parents


SHARED_FILES = ("initial-state.npz","baseline-old-before.npz","baseline-old-after.npz","baseline-old-generation.json","baseline-old.json","baseline-E3-generation.json","baseline-E3-after-free.npz","baseline-E3-truth.json","baseline-generation.json","baseline-token-metrics.json","baseline-after-TF.npz","baseline.json","paired-metrics.json")
ARM_FILES = ("entry-state.npz","final-state.npz","generation.json","token-metrics.json","training.json","final-truth.json","final-after-TF.npz","feasibility.json")


def preflight(a,bundle):
    m,c,rows,parents = bundle
    science = a.work/"science"
    top = {name:a.work/name for name in ("execution-receipt.json","execution.stdout.log","execution.stderr.log","git-prereg-receipt.json","formal-command-result.json")}
    expected = {"execution-intent.json","compact.json","timing.json"}
    for seed in SEEDS:
        expected.update(f"seed{seed}/{name}" for name in SHARED_FILES)
        expected.update(f"seed{seed}/{arm}/{name}" for arm in ARMS for name in ARM_FILES)
    need(all(p.is_file() for p in top.values()) and all((science/name).is_file() for name in expected),"all metadata/science paths beforeNN")
    inv = inventory(science);equal(set(inv),expected,"all90 actualscience files")
    receipt,compact = read(top["execution-receipt.json"]),read(science/"compact.json")
    equal(receipt["status"],"exit0","actual formal closure")
    for k,v in (("formal_exit",0),("exit_code",0),("session_id",a.formal_session),("command_invocations",1),("new_optimizer_updates",318600),("new_training_dense_MAC",6708441600)):
        need(type(receipt[k]) is int and receipt[k] == v,"receipt "+k)
    equal(receipt["manifest_sha256"],APPROVED,"receipt manifest")
    equal(receipt["preregistration_commit"],a.preregistration_commit,"receipt commit")
    from datetime import datetime
    need(datetime.fromisoformat(receipt["prereg_PR_created_UTC"].replace("Z","+00:00")) < datetime.fromisoformat(receipt["intent_created_UTC"].replace("Z","+00:00")),"prereg before intent")
    need(type(receipt["prereg_PR_number"]) is int,"actual PR number")
    equal(receipt["students"],compact["students"],"full students receipt")
    equal([x["seed"] for x in compact["students"]],list(SEEDS),"all3seed/6arms retained")
    need(compact["status"] == "complete" and compact["new_updates"] == 318600 and compact["new_training_dense_MAC"] == 6708441600,"fixed budget")
    need(compact["new_replay_updates"] == compact["new_replay_training_dense_MAC"] == 0 and compact["exact_full_replays"] == [],"no optimizer replay")
    for k in compact:
        if k.startswith("physical_"):
            equal(receipt[k],compact[k],"physical receipt "+k)
    command = read(top["formal-command-result.json"])
    equal((command["exit_code"],command["command_invocations"],command["formal_seconds"]),(0,1,receipt["formal_seconds"]),"actual subprocess wall/exit")
    git = read(top["git-prereg-receipt.json"])
    need(git["all_actual_bytes_verified"] is True and git["preregistration_commit"] == a.preregistration_commit,"Git actual-byte receipt")
    intent = read(science/"execution-intent.json")
    equal(intent,{"approved_manifest_sha256":APPROVED,"preregistration_commit":a.preregistration_commit,"source_hashes":CORE,"all_three_old_gates_before_E3_or_optimizer":True,"shared_baseline_physical_copies":3,"primary_seeds":list(SEEDS),"arms":{"eta001":.001,"eta003":.003},"replay_seeds":[],"new_updates_all_primary":318600,"auto_retry":False},"native intent")
    logs = [parse(line) for line in top["execution.stdout.log"].read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    equal(logs[-1],compact,"actual stdout compact")
    equal(logs[:-1],[{"seed":seed,"arm":arm,"phase":"one_epoch_primary_complete","new_updates":53100} for seed in SEEDS for arm in ARMS],"six progress events")
    need(top["execution.stderr.log"].stat().st_size == 0,"formal stderr")
    timing = read(science/"timing.json")
    need(len(timing["primary_trajectories"]) == 6,"six timing trajectories")
    states = {}
    for seed in SEEDS:
        folder = science/f"seed{seed}"
        states[seed] = {name:load_state((folder/name).read_bytes(),seed) for name in SHARED_FILES if name.endswith(".npz")}
        for arm in ARMS:
            for name in ARM_FILES:
                if name.endswith(".npz"):
                    states[seed][arm+"/"+name] = load_state((folder/arm/name).read_bytes(),seed)
        for name,n,target in [("baseline-E3-truth.json",900,17100)]+[(arm+"/final-truth.json",4500,53100) for arm in ARMS]:
            truth = read(folder/name)
            need(len(truth["truth"]) == n and truth["inference_calls"] == target,"TF metadata shape "+name)
            need(sum(len(x["TF"]) for x in truth["truth"]) == target,"all actual TF positions")
        for arm in ARMS:
            train = read(folder/arm/"training.json");trace = train["training"]
            need(trace["targets"] == 53100 and 0 <= trace["pre_update_prediction_correct"] <= 53100,"training target aggregate")
            need(trace["CE_loss_mean"] == trace["CE_loss_sum"]/53100 and trace["CE_loss_sum"] >= 0,"recorded aggregate mean")
            need(re.fullmatch("[0-9a-f]{64}",trace["canonical_target_trace_sha256"]) is not None,"recorded digest format")
    guards = {name:{"bytes":p.stat().st_size,"sha256":sha(p)} for name,p in top.items()}
    write(a.out/"metadata-preflight.json",{"status":"passed","manifest_sha256":APPROVED,"source_hashes":CORE,"vendor_SHA256":VENDOR_SHA,"formal_session":a.formal_session,"preregistration_commit":a.preregistration_commit,"root_confirmed_formal_exit0":True,"science_files":len(inv),"science_NPZ":sum(x.endswith('.npz') for x in inv),"all_paths_schema_checked_before_NN":True,"forward_calls":0,"receipt_sha256":guards['execution-receipt.json']['sha256']})
    return compact,receipt,inv,guards,states,timing


def save_proof(a,cost,seed,point,values):
    write(a.out/"numeric-proof"/f"seed{seed}-{point}.json",{"status":"passed","seed":seed,"point":point,"strict_equality":True,**values,"audit_cost_cumulative":cost.record()})
    cost.persist("running")


def check_metrics(a,cost,seed,point,state,rows,saved,phase):
    generated = generation(state,rows,cost,phase)
    equal(generated,saved,"all independent free "+point)
    metrics = readout(rows,generated["rows"])
    save_proof(a,cost,seed,point,{"whole_questions":len(rows),"inference_calls":generated["inference_calls"],"scores":generated["scores"],"state_SHA256":state_sha(state),"metrics":metrics["by_class"],"per_question_readout_SHA256":digest(canonical(metrics["per_question"]).encode())})
    return generated,metrics


def audit_seed(a,cost,seed,bundle,context):
    m,c,rows,parents = bundle
    compact,receipt,inv,guards,allstates,timing = context
    folder = a.work/"science"/f"seed{seed}"
    state = allstates[seed];parent = parents[seed]
    equal((folder/"initial-state.npz").read_bytes(),c[f"initial/seed{seed}.npz"],"parent exactraw")
    same_state(state["initial-state.npz"],parent,"parent fullstate")
    same_state(state["baseline-old-before.npz"],parent,"oldbefore fullparent")
    inf = {"meta_inference_calls","meta_inference_macs"}
    oldrows = rows[:3600];newrows = rows[3600:]
    old,oldmetrics = check_metrics(a,cost,seed,"old",parent,oldrows,read(folder/"baseline-old-generation.json"),f"seed{seed}_old")
    equal(old,parse(c[f"historical/seed{seed}/generation.json"].decode()),"historicalold complete generation")
    need(all(x['whole_correct'] == 900 for x in old['scores'].values()),"old integrity")
    oldafter = state["baseline-old-after.npz"]
    without(parent,oldafter,inf,"oldbaseline immutablelearning")
    need(counters(oldafter)['inference_calls']-counters(parent)['inference_calls'] == old['inference_calls'],"oldcounter delta")
    oldrecord = {"seed":seed,"scores":old['scores'],"integrity_pass":True,"archived_generation_exact":True,"parent_counters":counters(parent),"old_baseline_inference_calls":old['inference_calls'],"old_baseline_inference_MAC":old['inference_dense_MAC'],"learning_state_unchanged":True,"new_optimizer_updates":0}
    equal(read(folder/"baseline-old.json"),oldrecord,"oldbaseline record")
    cold,coldmetrics = check_metrics(a,cost,seed,"cold",oldafter,newrows,read(folder/"baseline-E3-generation.json"),f"seed{seed}_cold")
    afterfree = state["baseline-E3-after-free.npz"]
    without(oldafter,afterfree,inf,"coldfree immutablelearning")
    need(counters(afterfree)['inference_calls']-counters(oldafter)['inference_calls'] == cold['inference_calls'],"coldfree counterdelta")
    baselineTF = teacher(afterfree,newrows,cold,cost,f"seed{seed}_coldTF")
    equal(baselineTF,read(folder/"baseline-E3-truth.json"),"all coldTF logits/probabilities/CE")
    save_proof(a,cost,seed,"coldTF",{"TF_targets":17100,"metrics":baselineTF['metrics']})
    shared = state["baseline-after-TF.npz"]
    without(parent,shared,inf,"whole sharedbaseline immutablelearning")
    need(counters(shared)['inference_calls']-counters(afterfree)['inference_calls'] == 17100,"coldTF counterdelta")
    joined = {"scores":old['scores']|cold['scores'],"rows":old['rows']+cold['rows'],"inference_calls":old['inference_calls']+cold['inference_calls'],"inference_dense_MAC":old['inference_dense_MAC']+cold['inference_dense_MAC']}
    equal(joined,read(folder/"baseline-generation.json"),"joinedbaseline no duplicatefree")
    equal(readout(rows,joined['rows']),read(folder/"baseline-token-metrics.json"),"baseline fullword readout")
    cw = cold['scores']['E3']['whole_correct'];physical = joined['inference_calls']+17100
    baserecord = {**oldrecord,"cold_E3_scores":cold['scores'],"baseline_ceiling":cw == 900,"learning_gain_identifiability":"ceiling" if cw == 900 else "not_at_ceiling","cold_free_inference_calls":cold['inference_calls'],"cold_free_inference_MAC":cold['inference_dense_MAC'],"cold_TF_inference_calls":17100,"cold_TF_inference_MAC":17100*FORWARD_MAC,"physical_shared_baseline_inference_calls":physical,"physical_shared_baseline_inference_MAC":physical*FORWARD_MAC,"shared_end_counters":counters(shared),"shared_full_state_sha256":state_sha(shared),"both_arms_start_from_this_exact_full_state":True,"physical_baseline_copies":1}
    equal(baserecord,read(folder/"baseline.json"),"physicalbaseline once")
    save_proof(a,cost,seed,"shared",{"physical_calls":physical,"cold_whole":cw,"shared_state_SHA256":state_sha(shared)})
    outputs,arm_data = {},{}
    for arm,eta in (("eta001",.001),("eta003",.003)):
        armfolder = folder/arm
        entry,end,final = [state[arm+'/'+name] for name in ('entry-state.npz','final-state.npz','final-after-TF.npz')]
        same_state(entry,shared,"both arms exact sharedstate")
        immutable = {'L','H','meta_seed','meta_events','growth_rng',*(f'birth{i}' for i in range(4))}
        same_state({k:entry[k] for k in immutable},{k:end[k] for k in immutable},"training preserves metadata/birth/RNG")
        need(int(end['t'])-int(entry['t']) == 53100 and int(end['meta_train_macs'])-int(entry['meta_train_macs']) == 1118073600,"one epoch training delta")
        free,metrics = check_metrics(a,cost,seed,arm+'-free',end,rows,read(armfolder/'generation.json'),f'seed{seed}_{arm}_free')
        outputs[arm] = free
        equal(metrics,read(armfolder/'token-metrics.json'),"all endpoint word3 metrics")
        need(counters(end)['inference_calls']-counters(entry)['inference_calls'] == free['inference_calls'],"newprobe counterdelta")
        tf = teacher(end,rows,free,cost,f'seed{seed}_{arm}_TF')
        equal(tf,read(armfolder/'final-truth.json'),"all finalTF logits/probabilities/CE")
        without(end,final,inf,"TF fullstate immutablelearning")
        need(counters(final)['inference_calls']-counters(end)['inference_calls'] == 53100,"finalTF counterdelta")
        save_proof(a,cost,seed,arm+'-TF',{"TF_targets":53100,"metrics":tf['metrics']})
        training = read(armfolder/'training.json')
        expected = {'seed':seed,'arm':arm,'eta':eta,'entry_shared_state_sha256':state_sha(shared),'parent_counters':counters(parent),'entry_counters':counters(entry),'endpoint_counters':counters(end),'new_updates':53100,'new_training_dense_MAC':1118073600,'training':training['training'],'scores':free['scores'],'new_probe_inference_calls':free['inference_calls'],'new_probe_inference_MAC':free['inference_dense_MAC'],'full_state_sha256':state_sha(end),'replay_status':'not_planned','shared_baseline_cost_billed_in_this_arm':False}
        equal(training,expected,"training endpoint/aggregate metadata")
        arm_data[arm] = {**expected,'TF_metrics':tf['metrics'],'final_TF_inference_calls':53100,'final_TF_inference_MAC':53100*FORWARD_MAC,'final_counters_with_logical_shared_ancestry':counters(final)}
    pair = paired(rows,joined['rows'],outputs['eta001']['rows'],outputs['eta003']['rows'])
    equal(pair,read(folder/'paired-metrics.json'),"all QID paired/churn/feasibility axes")
    for arm in ARMS:
        equal(pair[arm],read(folder/arm/'feasibility.json'),"perarm feasibility")
        arm_data[arm]['feasibility'] = pair[arm]
    student = {'seed':seed,'baseline':baserecord,'arms':arm_data,'paired_axes':pair['axes_eta001_minus_eta003'],'paired_metrics_file':f'seed{seed}/paired-metrics.json'}
    equal(student,next(x for x in compact['students'] if x['seed'] == seed),"full student summary")
    save_proof(a,cost,seed,'paired',{'feasibility':{arm:pair[arm] for arm in ARMS},'axes':pair['axes_eta001_minus_eta003'],'no_optimizer_replay':True})
    return student


def run(a,cost):
    bundle = inputs(a);context = preflight(a,bundle);cost.persist('metadata_passed')
    guarded = {str(p):sha(p) for p in [Path(__file__),a.manifest,a.manifest.parent/'inputs.zip',VENDOR,*(a.code_dir/name for name in CORE)]}
    students = [audit_seed(a,cost,seed,bundle,context) for seed in SEEDS]
    compact,receipt,inv,guards,states,timing = context
    feasibility_by_arm = {arm:interpretation([student['arms'][arm]['feasibility'] for student in students]) for arm in ARMS}
    equal(feasibility_by_arm,compact['feasibility_by_arm'],"twoarm same feasibility")
    equal(compact['primary_low_eta_strict_feasibility'],feasibility_by_arm['eta001']['strict_feasibility_all_three'],"primary formula")
    equal(compact['primary_low_eta_interpretation'],feasibility_by_arm['eta001']['overall_interpretation'],"ceiling interpretation")
    baseline = sum(x['baseline']['physical_shared_baseline_inference_calls'] for x in students)
    probe = sum(x['arms'][arm]['new_probe_inference_calls'] for x in students for arm in ARMS)
    expected = {'physical_shared_baseline_inference_calls':baseline,'physical_new_probe_inference_calls':probe,'physical_final_TF_inference_calls':318600,'physical_new_inference_calls_total':baseline+probe+318600,'physical_baseline_copies':3}
    for key,value in list(expected.items()):
        if key.endswith('_calls') or key.endswith('_calls_total'):
            mac = key.replace('_calls','_MAC');expected[mac] = value*FORWARD_MAC
    for key,value in expected.items():equal(compact[key],value,'physical cost '+key)
    equal(inventory(a.work/'science'),inv,'science unchanged')
    equal({p:sha(Path(p)) for p in guarded},guarded,'all source/input/vendor unchanged')
    equal({name:{'bytes':(a.work/name).stat().st_size,'sha256':sha(a.work/name)} for name in guards},guards,'formal receipts/logs unchanged')
    refs = sorted(p.relative_to(a.out).as_posix() for p in (a.out/'numeric-proof').glob('*.json'))
    need(len(refs) == 27,'27 bounded point proofs')
    proof_inventory = {name:{'bytes':(a.out/name).stat().st_size,'sha256':sha(a.out/name)} for name in refs}
    details = {'status':'passed','manifest_sha256':APPROVED,'source_hashes':CORE,'vendor_sha256':VENDOR_SHA,'root_confirmed_formal_exit0':True,'receipt_sha256':guards['execution-receipt.json']['sha256'],'science_file_inventory':inv,'numeric_proof_refs':refs,'numeric_proof_inventory':proof_inventory,'students':students,'audit_cost':cost.record(),'physical_cost_recomputed':expected,'formal_seconds':receipt['formal_seconds'],'timing':timing,'sources_inputs_science_receipts_unchanged':True}
    write(a.out/'post-run-details.json',details)
    summary = {'schema':'e3-independent-post-run-v1','status':'passed','manifest_sha256':APPROVED,'source_hashes':CORE,'vendor_sha256':VENDOR_SHA,'review_source_sha256':sha(Path(__file__)),'root_confirmed_formal_exit0':True,'formal_session':a.formal_session,'preregistration_commit':a.preregistration_commit,'receipt_sha256':details['receipt_sha256'],'free_questions_independently_generated':40500,'TF_targets_independently_recomputed':369900,'strict_equality':True,'optimizer_calls':0,'new_students':0,'actual_training_replays':0,'science_files':len(inv),'proofs':len(refs),'feasibility_by_arm':feasibility_by_arm,'students':[{'seed':x['seed'],'cold_E3':x['baseline']['cold_E3_scores']['E3']['whole_correct'],'arms':{arm:{k:x['arms'][arm]['feasibility'][k] for k in ('old_lost_total','E3_whole','E3_whole_gain','strict_feasibility','baseline_ceiling')} for arm in ARMS}} for x in students],'audit_cost':cost.record(),'details_sha256':sha(a.out/'post-run-details.json'),'limits':['Oneepoch pairedprobe on3inherited exposedbank states; feasibility is not mastery or general rate superiority.','No traininggradient/optimizer replay; aggregate digest form/source provenance only.','Free compares complete tokens/flags/scores; exact logits/probabilities/CE comparisons apply to savedTF positions.']}
    write(a.out/'post-run.json',summary);cost.persist('passed')
    return summary


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('work','code-dir','manifest','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--formal-session',type=int,required=True);p.add_argument('--preregistration-commit',required=True);p.add_argument('--root-confirmed-exit0',action='store_true')
    a = p.parse_args()
    need(a.root_confirmed_exit0 and re.fullmatch('[0-9a-f]{40}',a.preregistration_commit),'explicit root postGO and actualcommit')
    for name in ('work','code_dir','manifest','out'):setattr(a,name,getattr(a,name).resolve())
    need(not any((a.out/name).exists() for name in ('audit-cost.json','metadata-preflight.json','numeric-proof','post-run.json','post-run-details.json')),'oneactualaudit only')
    (a.out/'numeric-proof').mkdir();cost = Cost(a.out);cost.persist('starting_metadata_only')
    try:
        result = run(a,cost)
        print(canonical({'status':result['status'],'students':result['students'],**cost.record()}),flush=True)
    except Exception as error:
        cost.persist('failed');write(a.out/'audit-failure.json',{'status':'failed','type':type(error).__name__,'message':str(error),'actual_cost':cost.record(),'retry_authorized':False});raise


if __name__ == '__main__':main()
