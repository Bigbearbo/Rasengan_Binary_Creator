"""Independently rescore saved E3 factorial outputs; no model code or NN execution."""
import argparse
from collections import Counter
from datetime import datetime
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import zipfile
import numpy as np

if sys.flags.optimize:
    raise RuntimeError("Audit assertions require non-optimized Python")

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--repo", type=Path, required=True)
p.add_argument("--results", type=Path, required=True, help="Probe results directory or ZIP containing its three files")
p.add_argument("--output", type=Path, required=True, help="New JSON report, never overwritten")
args = p.parse_args()
repo = args.repo.resolve()
relative = "experiments/spiral_neural/20261114_window_progress_review"
freeze = "898a385b33cf25ca6cd75f34fddf6b09812e3bfb"
source_head = "915219a4a787ea1452b798104d2158a6d8c82410"
seeds = (101, 202, 303)
cells = ("c0_d0", "c1_d0", "c0_d1", "c1_d1")

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)

def result_bytes(name):
    if args.results.is_dir():
        return (args.results / name).read_bytes()
    with zipfile.ZipFile(args.results) as z:
        found = [n for n in z.namelist() if n == name or n.endswith("/" + name)]
        assert len(found) == 1
        return z.read(found[0])

raw = result_bytes("raw_cases.jsonl")
summary = json.loads(result_bytes("summary.json"))
intent = json.loads(result_bytes("execution_intent.json"))
protocol_raw = (repo / relative / "e3_probe_protocol.json").read_bytes()
script_raw = (repo / relative / "e3_composition_probe.py").read_bytes()
protocol = json.loads(protocol_raw)
for name, data in (("e3_probe_protocol.json", protocol_raw), ("e3_composition_probe.py", script_raw)):
    assert data == subprocess.check_output(["git", "-C", str(repo), "show", freeze + ":" + relative + "/" + name])
assert sha(protocol_raw) == intent["protocol_sha256"]
assert sha(script_raw) == intent["probe_source_sha256"] == protocol["probe_source_sha256"]
assert summary["frozen_commit"] == intent["frozen_commit"] == freeze
assert summary["source_commit"] == protocol["source_commit"] == source_head
committed = subprocess.check_output(["git", "-C", str(repo), "show", "-s", "--format=%cI", freeze]).decode().strip()
assert datetime.fromisoformat(intent["created_at_UTC"]) >= datetime.fromisoformat(committed)
assert sha(raw) == summary["raw_cases_sha256"] and len(raw) == summary["raw_cases_bytes"]

source = repo / protocol["source_directory"]
for name, digest in protocol["source_files"].items():
    assert sha((source/name).read_bytes()) == digest
members = {}
for location, digest in protocol["selected_source_members"].items():
    archive, member = location.split(":", 1)
    with zipfile.ZipFile(source/archive) as z:
        data = z.read(member)
    assert sha(data) == digest
    members[location] = data
bank = json.loads(members["inputs.zip:payloads.json"])
parent_rows = json.loads(members["inputs.zip:questions.json"])
parent_q = {r["Q"] for r in parent_rows}
assert len(parent_q) == 4500 and len(bank) == 900
archived = {}
source_states = {}
for seed, number in zip(seeds, (1,3,5)):
    prefix = f"science-{number:03}.zip:science/seed{seed}/"
    archived[seed] = {r["pair_id"]:r for r in json.loads(members[prefix+"final-generation.json"])["rows"] if r["class"] == "E3"}
    with np.load(io.BytesIO(members[prefix+"final-after-TF.npz"]), allow_pickle=False) as z:
        h = hashlib.sha256()
        for name in sorted(z.files):
            a = z[name]
            h.update(canonical([name, a.dtype.str, list(a.shape)]).encode())
            h.update(a.tobytes(order="C"))
        source_states[str(seed)] = h.hexdigest()
assert source_states == protocol["parent_state_sha256"] == summary["state_sha256_before"] == summary["state_sha256_after"]

records = [json.loads(line) for line in raw.splitlines()]
assert len(records) == len({(r["seed"],r["probe_id"]) for r in records}) == 10800
order = [(s,c,i) for s in seeds for c in cells[:1] for i in range(900)] + [(s,c,i) for s in seeds for c in cells[1:] for i in range(900)]
assert [(r["seed"],r["cell"],r["pair_id"]) for r in records] == order
groups = {(s,c):[] for s in seeds for c in cells}
baseline_matches = 0
new_q = set()
new_relevant = set()
for r in records:
    s,c,pair = r["seed"],r["cell"],r["pair_id"]
    q,a = r["Q"],r["actual"]
    dc,dd = int(c[1]),int(c[4])
    expected_payload = [*bank[pair][:2],(bank[pair][2]+dc)%30,(bank[pair][3]+dd)%30]
    assert r["payload"] == expected_payload and r["parent_payload"] == bank[pair]
    assert r["delta_c"] == dc and r["delta_d"] == dd
    assert r["probe_id"] == cells.index(c)*900+pair
    assert r["parent_question_id"] == 3600+pair
    assert len(q)==39 and q[:9]=="010100110" and q[-6:]=="111100"
    words = [q[9+i*6:15+i*6] for i in range(4)]
    assert all(w[-1]=="0" and int(w[:5],2)<30 for w in words)
    assert [int(w[:5],2) for w in words] == expected_payload
    target = "".join(words[:3])+"S"
    assert r["expected"]==target
    assert 1<=len(a)<=32 and set(a.rstrip("S"))<={"0","1"} and a.count("S")<=1
    reason = "stop" if a.endswith("S") else "cap_exhausted"
    assert reason==r["reason"] and (reason=="stop" or len(a)==32)
    assert len(a)==r["forward_calls"]
    first = next((i for i in range(max(len(a),len(target))) if a[i:i+1]!=target[i:i+1]),None)
    actual_metrics = {"exact":a==target,"word_correct":[a[k:k+6]==target[k:k+6] for k in (0,6,12)],
                      "first_two_correct":a[:12]==target[:12],"stop_position_exact":reason=="stop" and len(a)==19,
                      "first_error_position_zero_based":first}
    assert all(r[k]==v for k,v in actual_metrics.items())
    if c=="c0_d0":
        old=archived[s][pair]
        assert q in parent_q
        assert (a,reason=="cap_exhausted",False,a==target)==(old["tokens"],old["cap_exhausted"],old["context_exhausted"],old["whole_correct"])
        baseline_matches+=1
    else:
        assert q not in parent_q
        new_q.add(q)
        if dc: new_relevant.add(tuple(expected_payload[:3]))
    groups[s,c].append(r)

def summarize(rs):
    return {"questions":len(rs),"whole_correct":sum(r["exact"] for r in rs),
            "word_correct":[sum(r["word_correct"][k] for r in rs) for k in range(3)],
            "first_two_correct":sum(r["first_two_correct"] for r in rs),
            "stop_position_correct":sum(r["stop_position_exact"] for r in rs),
            "first_error_histogram":dict(Counter("none" if r["first_error_position_zero_based"] is None else str(r["first_error_position_zero_based"]) for r in rs)),
            "output_length_histogram":dict(Counter(str(len(r["actual"])) for r in rs)),
            "termination_histogram":dict(Counter(r["reason"] for r in rs))}

metrics={str(s):{c:summarize(groups[s,c]) for c in cells} for s in seeds}
assert metrics==summary["metrics"]
def valid_part(r,start,end):
    part=r["actual"][start:end]
    return part if len(part)==end-start and set(part)<={"0","1"} else None
paired={}
for s in seeds:
    paired[str(s)]={}
    for name,left,right,factor in (("c_effect_d0",cells[0],cells[1],"c"),("c_effect_d1",cells[2],cells[3],"c"),("d_effect_c0",cells[0],cells[2],"d"),("d_effect_c1",cells[1],cells[3],"d")):
        count=Counter()
        for a,b in zip(groups[s,left],groups[s,right]):
            a12,b12=valid_part(a,0,12),valid_part(b,0,12)
            a3,b3=valid_part(a,12,18),valid_part(b,12,18)
            checks={"pairs":1,"left_whole_correct":a["exact"],"right_whole_correct":b["exact"],"both_whole_correct":a["exact"] and b["exact"],
                    "whole_output_invariant":a["actual"]==b["actual"],"first_two_complete_both":a12 is not None and b12 is not None,
                    "first_two_output_stable":a12 is not None and a12==b12,"first_two_correct_both":a["first_two_correct"] and b["first_two_correct"],
                    "third_word_complete_both":a3 is not None and b3 is not None,"third_word_output_changed":a3 is not None and b3 is not None and a3!=b3,
                    "third_word_output_invariant":a3 is not None and a3==b3,"third_word_correct_both":a["word_correct"][2] and b["word_correct"][2],
                    "stop_position_correct_both":a["stop_position_exact"] and b["stop_position_exact"]}
            count.update({k:int(v) for k,v in checks.items()})
            for k in range(12,18):
                if a["expected"][k]!=b["expected"][k]:
                    count["third_word_target_bit_changes"]+=1
                    count["target_bit_changes_followed_correctly"]+=int(a["actual"][k:k+1]==a["expected"][k] and b["actual"][k:k+1]==b["expected"][k])
        paired[str(s)][name]={"factor":factor,"left_cell":left,"right_cell":right,**dict(count)}
assert paired==summary["paired_metrics"]
calls=sum(r["forward_calls"] for r in records)
base_calls=sum(r["forward_calls"] for r in records[:2700])
assert baseline_matches==summary["baseline_archive_exact_matches"]==2700
assert summary["cost"]["baseline_forward_calls"]==base_calls
assert summary["cost"]["new_intervention_forward_calls"]==calls-base_calls
assert summary["cost"]["total_forward_calls"]==calls==205448
assert summary["cost"]["total_inference_dense_MAC"]==calls*10432==2143233536
assert summary["cost"]["new_optimizer_updates"]==summary["cost"]["manual_weight_updates"]==0
assert len(new_q)==2700 and len(new_relevant)==900
assert new_relevant.isdisjoint({tuple(r[:3]) for r in bank})
result={"status":"passed","scope":"Independent saved-record/source/state-hash/cost audit; no NN regeneration or optimizer execution",
        "source_head":source_head,"frozen_probe_commit":freeze,"probe_source_sha256":sha(script_raw),"protocol_sha256":sha(protocol_raw),
        "raw_cases_sha256":sha(raw),"raw_cases_checked":10800,"baseline_exact_archive_matches_including_errors":baseline_matches,
        "baseline_correct_answers":{str(s):metrics[str(s)]["c0_d0"]["whole_correct"] for s in seeds},
        "new_distinct_Q_per_model":len(new_q),"new_relevant_abc_combinations_per_model":len(new_relevant),
        "whole_correct":{str(s):{c:metrics[str(s)][c]["whole_correct"] for c in cells} for s in seeds},
        "paired_metrics_exact":True,"source_state_hashes_match_reported_before_and_after":True,"source_archives_unchanged":True,
        "original_probe_forward_calls":calls,"original_probe_dense_MAC":calls*10432,"new_audit_forward_calls":0,"new_audit_optimizer_updates":0,
        "limits":"This audit verifies saved outputs and accounting; it does not independently regenerate model outputs or observe past in-memory state. Runtime and readonly-array claims remain the executed probe's observations."}
args.output.parent.mkdir(parents=True,exist_ok=True)
with args.output.open("x",encoding="utf-8",newline="\n") as stream:
    json.dump(result,stream,ensure_ascii=False,indent=2);stream.write("\n")
print(json.dumps(result,ensure_ascii=False))
