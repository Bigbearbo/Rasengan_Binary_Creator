"""Independent read-only PR49 record audit. No model import, forward, or optimizer."""
import ast
import argparse
import hashlib
import io
import json
from pathlib import Path
import zipfile
import zlib
from collections import Counter
import numpy as np

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--repo", type=Path, required=True,
                    help="Repository checkout containing the pinned PR49, PR47 and PR43 experiment directories")
parser.add_argument("--output", type=Path, required=True,
                    help="New JSON report path; existing files are never overwritten")
args = parser.parse_args()
ROOT = args.repo.resolve() / "experiments/spiral_neural"
P = ROOT / "20261113_codex_e3_continuation"
P47 = ROOT / "20261113_codex_e3_learning_probe"
P43 = ROOT / "20261113_codex_f2_one_epoch_stability"
CLASSES = ["E1", "E2", "F1", "F2", "E3"]
SEEDS = [101, 202, 303]

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def loads(raw):
    return json.loads(raw)

def archives(root, pattern):
    out = {}
    for path in sorted(root.glob(pattern)):
        with zipfile.ZipFile(path) as z:
            for name in z.namelist():
                assert name not in out
                out[name] = z.read(name)
    return out

def npz(raw):
    with np.load(io.BytesIO(raw), allow_pickle=False) as z:
        return {k: z[k] for k in z.files}

def equal(a, b, omit=()):
    assert set(a) == set(b)
    return all(np.array_equal(a[k], b[k]) for k in a if k not in omit)

pub = loads((P / "publication-manifest.json").read_bytes())
archive_members = 0
for name, meta in pub["files"].items():
    raw = (P / name).read_bytes()
    assert len(raw) == meta["bytes"] and digest(raw) == meta["sha256"]
    assert hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest() == meta["Git_blob"]
for name, meta in pub["archives"].items():
    with zipfile.ZipFile(P / name) as z:
        assert len(z.namelist()) == len(set(z.namelist())) == meta["member_count"]
        assert set(z.namelist()) == set(meta["members"])
        for member, expected in meta["members"].items():
            raw = z.read(member)
            assert len(raw) == expected["bytes"] and digest(raw) == expected["sha256"]
            assert f"{zlib.crc32(raw):08x}" == expected["CRC32"]
            archive_members += 1

inputs = archives(P, "inputs.zip")
science = archives(P, "science-*.zip")
science47 = archives(P47, "science-*.zip")
science43 = archives(P43, "science-*.zip")
input47 = archives(P47, "inputs.zip")
rows = loads(inputs["questions.json"])
bank = loads(inputs["payloads.json"])
assert len(rows) == 4500 and len({r["Q"] for r in rows}) == 4500
assert len(bank) == len({tuple(x) for x in bank}) == 900
assert {(a,b) for a,b,c,d in bank} == {(a,b) for a in range(30) for b in range(30)}
truth = {}
for qid, r in enumerate(rows):
    q = r["Q"]
    assert len(q) == 39 and q[:2] == "01" and q[-6:] == "111100" and q[8] == "0"
    op, count = q[2:5], int(q[5:8], 2)
    words = [q[9+6*i:15+6*i] for i in range(4)]
    assert all(w[-1] == "0" and int(w[:5],2) < 30 for w in words)
    assert [int(w[:5],2) for w in words] == r["payload"] == bank[r["pair_id"]]
    label = "".join(words[:count]) if op == "010" else "".join("".join("1" if c == "0" else "0" for c in w[:5]) + "0" for w in words[:count])
    assert op in ("010", "100") and r["op"] == op and count == r["r"]
    assert r["A"] == label and r["question_id"] == qid
    assert r["class"] == ("E" if op == "010" else "F") + str(count)
    truth[qid] = label + "S"
assert Counter(r["class"] for r in rows) == {k:900 for k in CLASSES}
pool = np.array([(pair+900*CLASSES.index(c),pos) for pair in range(900) for c in CLASSES for pos in range(len(truth[pair+900*CLASSES.index(c)]))],dtype="<u2")
assert len(pool) == 53100
for seed in SEEDS:
    rng = np.random.default_rng(seed+666000)
    first = np.load(io.BytesIO(inputs[f"first-orders/seed{seed}.npy"]),allow_pickle=False)
    assert np.array_equal(first,pool[rng.permutation(53100)])
    future = np.load(io.BytesIO(inputs[f"orders/seed{seed}.npy"]),allow_pickle=False)
    assert future.shape == (8,53100,2) and future.dtype.str == "<u2"
    assert np.array_equal(future,np.stack([pool[rng.permutation(53100)] for _ in range(8)]))

manifest = loads((P/"manifest.json").read_bytes())
parsed = ast.parse(inputs["vendor/run_probe.py"])
ast_hashes = {n.name:digest(ast.dump(n,include_attributes=False).encode()) for n in parsed.body if isinstance(n,ast.FunctionDef) and n.name in manifest["reused_def_AST_sha256"]}
assert ast_hashes == manifest["reused_def_AST_sha256"]
assert digest(inputs["vendor/run_probe.py"]) == digest((P47/"run_probe.py").read_bytes())

def grade(raw):
    d=loads(raw)
    assert len(d["rows"]) == 4500
    byid={r["question_id"]:r for r in d["rows"]}
    assert set(byid) == set(truth)
    scored={k:0 for k in CLASSES}
    wrong=set()
    for qid,r in byid.items():
        ok = r["tokens"] == truth[qid] and not r["context_exhausted"]
        assert r["whole_correct"] == ok
        assert r["class"] == rows[qid]["class"] and r["pair_id"] == rows[qid]["pair_id"]
        scored[r["class"]] += int(ok)
        if not ok: wrong.add(qid)
    assert d["scores"] == {k:{"questions":900,"whole_correct":v} for k,v in scored.items()}
    calls=sum(len(r["tokens"]) for r in byid.values())
    assert calls == d["inference_calls"] and calls*10432 == d["inference_dense_MAC"]
    return scored,wrong,calls

students=[]
all_calls=0
for seed in SEEDS:
    prefix=f"science/seed{seed}/"
    initial=inputs[f"initial/seed{seed}.npz"]
    assert initial == science47[prefix+"eta001/final-after-TF.npz"] == science[prefix+"initial-state.npz"]
    assert input47[f"initial/seed{seed}.npz"] == science43[prefix+"final-after-TF.npz"]
    before=npz(science[prefix+"baseline-before.npz"])
    after=npz(science[prefix+"baseline-after.npz"])
    assert equal(npz(initial),before)
    assert equal(before,after,omit=("meta_inference_calls","meta_inference_macs"))
    assert science[prefix+"baseline-generation.json"] == inputs[f"historical/seed{seed}.json"]
    startscore,startwrong,calls=grade(science[prefix+"baseline-generation.json"])
    assert int(after["meta_inference_calls"])-int(before["meta_inference_calls"]) == calls
    all_calls+=calls
    trajectory=[]
    previous=after
    prev_wrong=startwrong
    for epoch in range(1,9):
        e=prefix+f"epoch-{epoch:03}/"
        entry=npz(science[e+"entry-state.npz"])
        final=npz(science[e+"final-state.npz"])
        assert equal(entry,previous)
        assert int(final["t"])-int(entry["t"]) == 53100
        assert int(final["meta_train_macs"])-int(entry["meta_train_macs"]) == 53100*21056
        score,wrong,calls=grade(science[e+"generation.json"])
        assert int(final["meta_inference_calls"])-int(entry["meta_inference_calls"]) == calls
        assert int(final["meta_inference_macs"])-int(entry["meta_inference_macs"]) == calls*10432
        old_wrong={q for q in wrong if q<3600}
        trajectory.append({"epoch":epoch,"E3":score["E3"],"old_wrong":len(old_wrong),"all_correct":4500-len(wrong),"lost_vs_previous":len(wrong-prev_wrong),"recovered_vs_previous":len(prev_wrong-wrong)})
        all_calls+=calls
        previous,prev_wrong=final,wrong
    finalpre=npz(science[prefix+"final-state.npz"])
    finalpost=npz(science[prefix+"final-after-TF.npz"])
    assert equal(previous,finalpre)
    assert equal(finalpre,finalpost,omit=("meta_inference_calls","meta_inference_macs"))
    assert int(finalpost["meta_inference_calls"])-int(finalpre["meta_inference_calls"]) == 53100
    all_calls+=53100
    finalscore,finalwrong,_=grade(science[prefix+"final-generation.json"])
    old_start={q for q in startwrong if q<3600}
    old_end={q for q in finalwrong if q<3600}
    tf=loads(science[prefix+"final-truth.json"])
    assert len(tf["truth"]) == 4500
    tf_errors=Counter()
    first_error=Counter()
    wrong_wordvalues=[]
    tf_calls=0
    for r in tf["truth"]:
        qid=r["question_id"]
        assert r["expected"] == truth[qid] and len(r["TF"]) == len(truth[qid])
        tf_calls+=len(r["TF"])
        for point,ch in zip(r["TF"],truth[qid]):
            assert point["target"] == ch
            assert point["prediction"] == "01S"[int(np.argmax(point["logits_01S"]))]
            tf_errors[r["class"]]+=int(point["prediction"]!=ch)
        gen=r["generation"]["tokens"]
        if qid in finalwrong:
            first=next(i for i,(a,b) in enumerate(zip(gen,truth[qid])) if a!=b)
            assert r["TF"][first]["prediction"] != truth[qid][first]
            first_error[(r["class"],first)]+=1
            wrong_wordvalues.append({"qid":qid,"class":r["class"],"payload":r["payload"],"first_error":first,"expected":truth[qid],"actual":gen})
    assert tf_calls==53100
    students.append({"seed":seed,"initial_t":int(before["t"]),"final_t":int(finalpost["t"]),"final_scores":finalscore,"trajectory":trajectory,"final_old_lost_vs_baseline":sorted(old_end-old_start),"final_old_recovered_vs_baseline":sorted(old_start-old_end),"first_E3_full_epoch":next((d["epoch"] for d in trajectory if d["E3"]==900),None),"all_five_full_epochs":[d["epoch"] for d in trajectory if d["all_correct"]==4500],"final_TF_error_counts":dict(tf_errors),"final_first_error_histogram":{f"{k[0]}@{k[1]}":v for k,v in first_error.items()},"final_wrong_records":wrong_wordvalues})

compact=loads(science["science/compact.json"])
assert all_calls==compact["physical_new_inference_calls_total"]==1595382
assert compact["new_updates"]==24*53100==1274400
assert compact["new_training_dense_MAC"]==1274400*21056==26833766400
assert compact["stable_pass_seeds"]==[]
result={"status":"passed","scope":"PR49 archived-record, data, course, source-AST and state-chain audit; no NN executed","head":"915219a4a787ea1452b798104d2158a6d8c82410","new_forward_calls":0,"new_optimizer_updates":0,"public_files_checked":len(pub["files"]),"archive_members_checked":archive_members,"science_members":len(science),"raw_questions_checked":4500,"recorded_generations_rescored":121500,"final_TF_records_checked":159300,"source_functions_AST_checked":len(ast_hashes),"recorded_inference_count":all_calls,"students":students}
args.output.parent.mkdir(parents=True, exist_ok=True)
with args.output.open("x", encoding="utf-8", newline="\n") as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
    stream.write("\n")
print(json.dumps({"status":result["status"],"new_forward_calls":0,"new_optimizer_updates":0,
                 "recorded_generations_rescored":result["recorded_generations_rescored"],
                 "final_TF_records_checked":result["final_TF_records_checked"]}))
