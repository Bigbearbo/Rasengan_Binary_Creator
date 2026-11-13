"""Independent mixed-flip continuation audit; no learner/driver imports or optimizer."""
import argparse
import ast
from collections import Counter
import datetime
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
sys.dont_write_bytecode=True
os.environ["OPENBLAS_NUM_THREADS"]="1"
os.environ["OMP_NUM_THREADS"]="1"
import numpy as np
HERE=Path(__file__).resolve().parent
APPROVED="a85457a3d7a6e06d7b20ad608d695a6f322a9b3daf38e714ff974fb7d7b6d218"
ZIP_SHA="fa8168e7029b5f0d0892bd8b73c7f4e05b0293d3fc56f6956eb38671de9d5d36"
DRIVER="3ad223a4f11d82d2c4ede86a97093d03a604bd22677c5c327936b393334037f0"
PARENT_HEAD="7213cce112a8411b13dc128c49f9e88acfc9d65f"
PUBLICATION_SHA="660390547db4dc014e094de2e1b03ca851cb511502f68c3d04975962baa32a6c"
PUBLICATION_BLOB="30200c222b0086d02db7044269877501cd3d2d4d"
SEEDS=(101,202,303)
CLASSES=("E1","E2","F1")
PARENT_T={101:151200,202:181800,303:223200}
TRAIN_MAC,FORWARD_MAC=21056,10432
# Coordinator supplies and confirms current-study commit/session before GO.
PREREG="6b9df16cb593c422426f6cb093a8ecfbe18d1e13"
FORMAL_SESSION=20420

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

def keys(value, expected, label):
    need(isinstance(value, dict) and set(value) == set(expected), label + " schema")

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


TRAIN_FIELDS={"targets","pre_update_prediction_correct","CE_loss_sum","CE_loss_mean","canonical_target_trace_sha256"}
BASE_FIELDS={"seed","parent_counters","before_full_state_sha256","after_full_state_sha256","scores","old_Echo_integrity_pass","baseline_streak","baseline_inference_calls","baseline_inference_MAC","new_optimizer_updates","only_inference_counters_changed"}
EPOCH_FIELDS={"seed","epoch","global_updates","new_updates","total_training_dense_MAC","new_training_dense_MAC","parent_counters","training","scores","streak","stop_reason","first_full_epoch","baseline_inference_calls","baseline_inference_MAC","epoch_probe_inference_calls","epoch_probe_inference_MAC","new_probe_inference_calls_cumulative","new_probe_inference_MAC_cumulative","total_inference_calls","total_inference_MAC","full_state_sha256"}
SUMMARY_FIELDS={"seed","epochs","stop_reason","streak","first_full_epoch","stable_pass_epoch","parent_counters","new_updates","new_training_dense_MAC","baseline_inference_calls","baseline_inference_MAC","new_probe_inference_calls","new_probe_inference_MAC","total_counters_before_finalTF","final_scores","final_full_state_sha256"}
GEN_FIELDS={"scores","rows","inference_calls","inference_dense_MAC"}
GEN_ROW_FIELDS={"question_id","class","pair_id","tokens","context_exhausted","cap_exhausted","whole_correct"}
QUESTION_FIELDS={"question_id","pair_id","r","payload","Q","A","class","op"}
TF_FIELDS={"position","prefix","target","prediction","logits_01S","probabilities_01S","target_CE"}


def blob(raw):
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()


def counters(state):
    return {"t":int(state["t"]),"train_MAC":int(state["meta_train_macs"]),"inference_calls":int(state["meta_inference_calls"]),"inference_MAC":int(state["meta_inference_macs"])}


def load_state(raw,seed,updates,calls):
    with np.load(io.BytesIO(raw),allow_pickle=False) as archive:
        state={name:archive[name].copy() for name in archive.files}
    names={f"{label}{index}" for label in ("p","m","v","birth") for index in range(4)}
    names|={"t","L","H","growth_rng","meta_seed","meta_events","meta_train_macs","meta_inference_macs","meta_inference_calls"}
    need(set(state)==names,"all25 fullstate fields")
    for label in ("p","m","v","birth"):
        for index,shape in enumerate(((160,64),(64,),(64,3),(3,))):
            value=state[f"{label}{index}"]
            need(value.shape==shape and value.dtype==(np.int64 if label=="birth" else np.float32),"parameter/moment shape and dtype")
            need(bool(np.isfinite(value).all()),"finite state arrays")
            if label=="birth": need(not np.any(value),"no parameter growth/birth")
            if label=="v": need(bool((value>=0).all()),"nonnegative Adam second moment")
    for name in ("t","L","H","meta_seed","meta_train_macs","meta_inference_macs","meta_inference_calls"):
        need(state[name].shape==() and state[name].dtype==np.int64,"integer state scalar dtype")
    need((int(state["L"]),int(state["H"]),int(state["meta_seed"]))==(80,64,seed),"state identity")
    need(int(state["t"])==updates and int(state["meta_train_macs"])==updates*TRAIN_MAC,"global inherited-plus-new training counters")
    need(int(state["meta_inference_calls"])==calls and int(state["meta_inference_macs"])==calls*FORWARD_MAC,"global inherited-plus-new probe counters")
    need(str(state["meta_events"])=="[]","no growth events")
    equal(parse(str(state["growth_rng"])),np.random.default_rng(seed+73000).bit_generator.state,"growth RNG retained")
    need(sum(state[f"{label}{index}"].nbytes for label in ("p","m","v","birth") for index in range(4))==209980,"array bytes")
    for value in state.values(): value.setflags(write=False)
    return state


def inputs(args):
    need(sha(args.manifest)==APPROVED,"approved manifest")
    manifest=read(args.manifest);freeze=read(args.manifest.parent/"source-freeze.json")
    need(freeze["manifest_sha256"]==APPROVED and freeze["source_hashes"]==manifest["source_hashes"],"source freeze")
    need(manifest["source_hashes"]["run_mixed.py"]==DRIVER,"frozen driver")
    for name,pin in manifest["source_hashes"].items(): need(sha(args.code_root/name)==pin,"frozen core source")
    need((platform.python_version(),np.__version__)==("3.12.14","2.3.5"),"audit runtime")
    need(manifest["runtime"]["python"]==platform.python_version() and manifest["runtime"]["numpy"]==np.__version__,"frozen runtime")
    archive_path=args.manifest.parent/manifest["archive"]["file"]
    need(sha(archive_path)==manifest["archive"]["sha256"]==ZIP_SHA,"frozen portable ZIP")
    names={"payloads.json","parent-questions.json","questions.json","source/p030_binary_continual.py","plan.json","provenance/parent-publication-manifest.json","provenance/parent-provenance.json"}
    names|={f"initial/seed{seed}.npz" for seed in SEEDS}|{f"orders/seed{seed}.npy" for seed in SEEDS}
    with zipfile.ZipFile(archive_path) as archive:
        need(len(archive.namelist())==13 and set(archive.namelist())==names==set(manifest["files"]),"13 unique portable members")
        raw={name:archive.read(name) for name in names}
    for name,value in raw.items(): equal({"bytes":len(value),"sha256":digest(value)},manifest["files"][name],"frozen member bytes/hash")
    need(raw["plan.json"]==(args.code_root/"protocol.json").read_bytes(),"exact protocol bytes")
    equal(parse(raw["plan.json"].decode()),manifest["protocol"],"full embedded protocol")
    need(manifest["protocol"]["parent_head"]==PARENT_HEAD,"specified public result parent")
    need(digest(raw["source/p030_binary_continual.py"])==manifest["protocol"]["source_sha256"],"native source SHA")
    node=next(node for node in ast.parse(raw["source/p030_binary_continual.py"].decode()).body if isinstance(node,ast.ClassDef) and node.name=="Model")
    need(digest(ast.dump(node,include_attributes=False).encode())==manifest["protocol"]["Model_AST_sha256"],"native Model AST hash only, never imported/executed")
    publication_raw=raw["provenance/parent-publication-manifest.json"]
    need((digest(publication_raw),blob(publication_raw))==(PUBLICATION_SHA,PUBLICATION_BLOB),"public parent manifest SHA/Git blob")
    publication=parse(publication_raw.decode());proof=parse(raw["provenance/parent-provenance.json"].decode())
    need(proof["parent_head"]==proof["prior_receipt_public_fields"]["result_commit"]==PARENT_HEAD,"public parent commit lineage")
    equal(proof["parents"],manifest["parents"],"frozen public parent metadata")
    data=proof["data_archive"]
    need(all(data[key]==publication["files"]["inputs.zip"][key] for key in ("bytes","sha256","Git_blob")),"public parent data archive binding")
    need(data["payloads_member_sha256"]==digest(raw["payloads.json"]) and data["old_questions_member_sha256"]==digest(raw["parent-questions.json"]),"public parent data member pins")
    parents,raw_parents={},{}
    for seed in SEEDS:
        meta=manifest["parents"][str(seed)];source,member=meta["source_archive"],meta["source_member"]
        public_archive=publication["archives"][source["file"]]
        need(all(source[key]==public_archive[key] for key in ("bytes","sha256","Git_blob")),"public parent result archive binding")
        need(member["path"]==f"science/seed{seed}/final-state.npz","trained parent final member")
        equal({key:value for key,value in member.items() if key!="path"},public_archive["members"][member["path"]],"public parent member metadata")
        content=raw[meta["file"]]
        need((len(content),digest(content),blob(content))==(member["bytes"],member["sha256"],member["Git_blob"]),"original parent NPZ container bytes/Git blob")
        need(format(zlib.crc32(content)&0xffffffff,"08x")==member["CRC32"],"original parent NPZ CRC")
        state=load_state(content,seed,PARENT_T[seed],meta["counters"]["inference_calls"])
        need(state_sha(state)==meta["full_state_sha256"] and digest(content)==meta["raw_sha256"],"original complete parent state")
        equal(counters(state),meta["counters"],"parent inherited counters")
        parents[seed],raw_parents[seed]=state,content
    suffix=np.random.default_rng(331000).integers(0,30,size=(900,2))
    bank=[[pair//30,pair%30,int(suffix[pair,0]),int(suffix[pair,1])] for pair in range(900)]
    equal(parse(raw["payloads.json"].decode()),bank,"same frozen900 payload bank")
    word=lambda value:format(value,"05b")+"0"
    old,rows=[],[]
    for r in (1,2):
        for pair,payload in enumerate(bank):
            task={"question_id":(r-1)*900+pair,"pair_id":pair,"r":r,"payload":payload,"Q":"01010"+format(r,"03b")+"0"+"".join(word(v) for v in payload)+"111100","A":"".join(word(v) for v in payload[:r])}
            old.append(task);rows.append({**task,"class":"E1" if r==1 else "E2","op":"010"})
    equal(parse(raw["parent-questions.json"].decode()),old,"old1800 Echo Q/A bitidentity")
    for pair,payload in enumerate(bank):
        rows.append({"question_id":1800+pair,"pair_id":pair,"r":1,"payload":payload,"Q":"01100"+"0010"+"".join(word(v) for v in payload)+"111100","A":"".join(str(1-int(bit)) for bit in format(payload[0],"05b"))+"0","class":"F1","op":"100"})
    equal(parse(raw["questions.json"].decode()),rows,"independent full2700 mixed Q/A grammar")
    need(rows[1800]["A"]+"S"=="111110S" and rows[1830]["A"]+"S"=="111100S","literal UP/END-like answer bits retained")
    prefix_labels={};label_counts=Counter()
    for task in rows:
        need(len(task["Q"])==39 and len(task["A"]+"S")== (13 if task["class"]=="E2" else 7),"mixed input/answer lengths")
        for pos,label in enumerate(task["A"]+"S"):
            prefix=task["Q"]+task["A"][:pos];need(prefix not in prefix_labels,"unique teacher prefixes")
            prefix_labels[prefix]=label;label_counts[label]+=1
    need(len(prefix_labels)==24300,"all mixed teacher prefixes")
    equal(dict(label_counts),{"0":12840,"1":8760,"S":2700},"mixed label counts")
    pool=np.asarray([(offset+pair,pos) for pair in range(900) for offset in (0,900,1800) for pos in range(len(rows[offset+pair]["A"])+1)],dtype="<u2")
    orders={}
    for seed in SEEDS:
        rng=np.random.default_rng(seed+444000)
        expected=np.stack([pool[rng.permutation(len(pool))] for _ in range(40)])
        actual=np.load(io.BytesIO(raw[f"orders/seed{seed}.npy"]),allow_pickle=False)
        need(actual.dtype.str=="<u2" and actual.shape==(40,24300,2) and np.array_equal(actual,expected),"all40 independently reconstructed mixed target permutations")
        equal(manifest["schedules"][str(seed)]["final_schedule_RNG"],rng.bit_generator.state,"mixed schedule RNG endpoint")
        orders[seed]=actual
    return manifest,rows,parents,raw_parents,orders


def scores_schema(value):
    keys(value,set(CLASSES),"all three class scores")
    for score in value.values():
        keys(score,{"questions","whole_correct"},"class score row")
        need(score["questions"]==900,"all900 class questions")
        integer(score["whole_correct"],0,900,"class whole-correct count")


def generation_schema(value,rows):
    keys(value,GEN_FIELDS,"generation file");scores_schema(value["scores"])
    need(len(value["rows"])==2700,"all2700 generated outputs")
    for item,task in zip(value["rows"],rows,strict=True):
        keys(item,GEN_ROW_FIELDS,"generation row")
        need((item["question_id"],item["class"],item["pair_id"])==(task["question_id"],task["class"],task["pair_id"]),"generation identity/order")
        need(isinstance(item["tokens"],str) and 1<=len(item["tokens"])<=32 and set(item["tokens"])<=set("01S"),"generated action domain")
        need(all(type(item[name]) is bool for name in ("context_exhausted","cap_exhausted","whole_correct")),"generation flags")
    integer(value["inference_calls"],2700,86400,"generation calls")
    need(value["inference_dense_MAC"]==value["inference_calls"]*FORWARD_MAC,"generation cost")


def preflight(args,manifest,rows,parents,raw_parents):
    required=[args.receipt,args.formal_log,args.formal_stderr]+[args.science/name for name in ("manifest.json","execution-start.json","baseline-gate.json","compact.json","timing.json","storage.json")]
    need(all(path.is_file() for path in required),"all top metadata/log/receipt paths exist")
    receipt=read(args.receipt);compact=read(args.science/"compact.json");start=read(args.science/"execution-start.json")
    need(receipt["status"]=="exit0" and receipt["formal_exit"]==receipt["exit_code"]==0 and receipt["session_id"]==args.formal_session and receipt["command_invocations"]==1,"actual unique formal exit0 receipt")
    need(receipt["manifest_sha256"]==APPROVED and receipt["preregistration_commit"]==args.prereg_commit,"receipt identity")
    stamp=lambda value:datetime.datetime.fromisoformat(value.replace("Z","+00:00"))
    need(stamp(receipt["PR_created_UTC"])<stamp(receipt["execution_start_file_creation_UTC"]),"public prereg before execution")
    equal(read(args.science/"manifest.json"),manifest,"actual scientific manifest")
    need(start["manifest_sha256"]==compact["manifest_sha256"]==APPROVED and start["preregistration_commit"]==compact["preregistration_commit"]==args.prereg_commit,"actual execution identity")
    need(start["all_parent_baselines_before_any_optimizer"] is True and start["auto_retry"] is False,"whole-batch baseline and no retry declarations")
    need(compact["status"]=="complete" and compact["primary_continued_students"]==3 and compact["exact_full_replays"]==[101],"all continued trajectories completed")
    need([row["seed"] for row in compact["students"]]==list(SEEDS),"all fixed continuation seeds retained")
    gate=read(args.science/"baseline-gate.json")
    keys(gate,{"all_three_passed","new_optimizer_updates_at_gate","baselines"},"whole-batch baseline gate")
    need(gate["all_three_passed"] is True and gate["new_optimizer_updates_at_gate"]==0,"baseline integrity before first new optimizer")
    expected_files={"manifest.json","execution-start.json","baseline-gate.json","compact.json","timing.json","storage.json"}
    bundles={}
    for item in compact["students"]:
        keys(item,SUMMARY_FIELDS|{"replay_status","final_TF_metrics","final_TF_inference_calls","final_TF_inference_MAC"},"compact student")
        seed,count=item["seed"],item["epochs"];integer(count,1,40,"actual epoch count")
        folder=args.science/f"seed{seed}"
        names={"initial-state.npz","baseline-before.npz","baseline-after.npz","baseline.json","baseline-generation.json","final-state.npz","training-summary.json","curve.json","final-truth.json","final-failures.json"}
        names|={f"{kind}-{epoch:03}.{extension}" for epoch in range(1,count+1) for kind,extension in (("state","npz"),("epoch","json"),("generation","json"))}
        need(all((folder/name).is_file() for name in names),"all actual baseline/epoch/final files exist")
        expected_files|={f"seed{seed}/{name}" for name in names}
        need((folder/"initial-state.npz").read_bytes()==raw_parents[seed],"original parent NPZ bytes preserved")
        parent_counts=counters(parents[seed])
        before=load_state((folder/"baseline-before.npz").read_bytes(),seed,parent_counts["t"],parent_counts["inference_calls"])
        same_state(before,parents[seed],"before-baseline exact public parent state")
        baseline=read(folder/"baseline.json");keys(baseline,BASE_FIELDS,"baseline record")
        equal(baseline["parent_counters"],parent_counts,"baseline inherited counters")
        need(baseline["seed"]==seed and baseline["new_optimizer_updates"]==baseline["baseline_streak"]==0 and baseline["old_Echo_integrity_pass"] is True and baseline["only_inference_counters_changed"] is True,"baseline integrity flags/streak0")
        generation=read(folder/"baseline-generation.json");generation_schema(generation,rows)
        equal(baseline["scores"],generation["scores"],"baseline scores")
        need(all(baseline["scores"][name]["whole_correct"]==900 for name in ("E1","E2")),"both old Echo integrity scores")
        need(baseline["baseline_inference_calls"]==generation["inference_calls"] and baseline["baseline_inference_MAC"]==generation["inference_dense_MAC"],"baseline cost")
        after=load_state((folder/"baseline-after.npz").read_bytes(),seed,parent_counts["t"],parent_counts["inference_calls"]+generation["inference_calls"])
        unchanged=set(before)-{"meta_inference_calls","meta_inference_macs"}
        same_state({name:before[name] for name in unchanged},{name:after[name] for name in unchanged},"baseline changes only inference counters")
        need(state_sha(before)==baseline["before_full_state_sha256"] and state_sha(after)==baseline["after_full_state_sha256"],"baseline before/after state hashes")
        equal(gate["baselines"][str(seed)],baseline,"all-three baseline gate member")
        summary,curve=read(folder/"training-summary.json"),read(folder/"curve.json")
        keys(summary,SUMMARY_FIELDS,"training summary")
        need(summary["seed"]==seed and summary["epochs"]==len(curve)==count,"student/curve epoch identity")
        records,generations,states=[],[],[]
        for epoch,point in enumerate(curve,1):
            keys(point,EPOCH_FIELDS,"epoch record")
            equal(read(folder/f"epoch-{epoch:03}.json"),point,"epoch/curve equality")
            need(point["seed"]==seed and point["epoch"]==epoch and point["new_updates"]==epoch*24300 and point["global_updates"]==parent_counts["t"]+epoch*24300,"old/new/global update counters")
            need(point["new_training_dense_MAC"]==epoch*24300*TRAIN_MAC and point["total_training_dense_MAC"]==parent_counts["train_MAC"]+point["new_training_dense_MAC"],"old/new training cost")
            equal(point["parent_counters"],parent_counts,"epoch inherited counters")
            keys(point["training"],TRAIN_FIELDS,"training aggregate")
            train=point["training"]
            need(train["targets"]==24300 and train["CE_loss_sum"]>=0 and train["CE_loss_mean"]==train["CE_loss_sum"]/24300,"complete target and finite sequential loss aggregate")
            integer(train["pre_update_prediction_correct"],0,24300,"pre-update prediction count")
            need(re.fullmatch("[0-9a-f]{64}",train["canonical_target_trace_sha256"]) is not None,"prediction/loss digest form")
            scores_schema(point["scores"])
            gen=read(folder/f"generation-{epoch:03}.json");generation_schema(gen,rows)
            state=load_state((folder/f"state-{epoch:03}.npz").read_bytes(),seed,point["global_updates"],point["total_inference_calls"])
            need(state_sha(state)==point["full_state_sha256"],"epoch full state SHA")
            records.append(point);generations.append(gen);states.append(state)
        final=load_state((folder/"final-state.npz").read_bytes(),seed,records[-1]["global_updates"],records[-1]["total_inference_calls"])
        same_state(final,states[-1],"final exact last epoch state")
        truth=read(folder/"final-truth.json")
        keys(truth,{"truth","metrics","inference_calls","inference_dense_MAC","learning_state_unchanged","free_generation_reused"},"final TF file")
        need(len(truth["truth"])==2700,"all2700 final TF questions")
        for task,result in zip(rows,truth["truth"],strict=True):
            keys(result,QUESTION_FIELDS|{"expected","generation","TF"},"final truth row")
            need(all(result[name]==value for name,value in task.items()) and result["expected"]==task["A"]+"S","final truth grammar and identity")
            need(len(result["TF"])==len(task["A"])+1,"all true-prefix targets")
            for pos,label in enumerate(task["A"]+"S"):
                token=result["TF"][pos];keys(token,TF_FIELDS,"TF target")
                need((token["position"],token["prefix"],token["target"])==(pos,task["Q"]+task["A"][:pos],label),"TF true prefix/label")
                need(len(token["prediction"])==1 and token["prediction"] in "01S" and len(token["logits_01S"])==len(token["probabilities_01S"])==3,"TF action/vector shape")
                need(all(0<=value<=1 for value in token["probabilities_01S"]) and token["target_CE"]>=0,"TF probability/CE domain")
        failures=read(folder/"final-failures.json");need(isinstance(failures,list) and len(failures)<=2700,"complete final failures file")
        bundles[seed]={"compact":item,"summary":summary,"baseline":baseline,"baseline_generation":generation,"before":before,"after":after,"records":records,"generations":generations,"states":states,"final":final,"truth":truth,"failures":failures}
    before_inventory=inventory(args.science)
    equal(set(before_inventory),expected_files,"exact science inventory without failure files")
    timing,storage=read(args.science/"timing.json"),read(args.science/"storage.json")
    equal([(row["mode"],row["seed"]) for row in timing["trajectories"]],[("primary",101),("primary",202),("primary",303),("replay",101)],"actual continued primary/replay timing records")
    need(all(row["seconds"]>0 for row in timing["trajectories"]) and timing["total_seconds"]>=sum(row["seconds"] for row in timing["trajectories"]),"finite formal total timing")
    if "formal_seconds" in receipt: need(receipt["formal_seconds"]==timing["total_seconds"],"receipt actual formal walltime")
    for name in compact:
        if name in receipt and name not in ("status","id","author"):
            equal(receipt[name],compact[name],"receipt scientific field")
    need(storage["input_archive_bytes"]==manifest["archive"]["bytes"] and storage["output_bytes_before_this_record"]==sum(meta["bytes"] for name,meta in before_inventory.items() if name!="storage.json"),"input/output storage bytes")
    progress,terminal=[],[]
    for line in args.formal_log.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip(): continue
        item=parse(line)
        if item.get("mode") in ("primary","replay"): progress.append(item)
        elif item.get("status")=="complete": terminal.append(item)
        else: need(False,"unknown formal stdout row")
    expected_progress=[]
    for mode,seed in (("primary",101),("primary",202),("primary",303),("replay",101)):
        for point in bundles[seed]["records"]:
            expected_progress.append({"mode":mode,"seed":seed,"epoch":point["epoch"],"scores":point["scores"],"streak":point["streak"],"stop":point["stop_reason"]})
    equal(progress,expected_progress,"actual complete primary/replay epoch stdout")
    equal(terminal,[compact],"actual completed process stdout")
    metadata={"receipt_sha256":sha(args.receipt),"stdout_sha256":sha(args.formal_log),"stdout_bytes":args.formal_log.stat().st_size,"stderr_sha256":sha(args.formal_stderr),"stderr_bytes":args.formal_stderr.stat().st_size,"preregistration_precedes_execution":True,"actual_timing_trajectories":4,"epoch_progress_records":len(progress)}
    return compact,bundles,before_inventory,timing,metadata


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
    metrics={name:{"questions":900,"TF_correct":sum(point["prediction"]==point["target"] for row in truth if row["class"]==name for point in row["TF"]),"TF_targets":11700 if name=="E2" else 6300} for name in CLASSES}
    need(forward.calls==24300 and state_sha(state)==before,"complete TF without state mutation")
    return {"truth":truth,"metrics":metrics,"inference_calls":forward.calls,"inference_dense_MAC":forward.calls*FORWARD_MAC,"learning_state_unchanged":True,"free_generation_reused":True}


def literal_metrics(rows,free):
    by_id={row["question_id"]:row for row in free["rows"]};result={}
    for value,expected in ((0,"111110S"),(1,"111100S")):
        tasks=[row for row in rows if row["class"]=="F1" and row["payload"][0]==value]
        need(len(tasks)==30 and all(row["A"]+"S"==expected for row in tasks),"all literal-control-pattern input0/1 tasks retained")
        result[str(value)]={"questions":30,"expected_literal_answer":expected,"whole_correct":sum(by_id[row["question_id"]]["whole_correct"] for row in tasks)}
    return result


def decomposed_metrics(truth):
    result={}
    for name in CLASSES:
        rows=[row for row in truth if row["class"]==name];r=2 if name=="E2" else 1
        info=[pos for pos in range(6*r) if pos%6!=5];tails=[pos for pos in range(6*r) if pos%6==5]
        free_correct=lambda row,pos:pos<len(row["generation"]["tokens"]) and row["generation"]["tokens"][pos]==row["A"][pos]
        result[name]={"questions":900,"info_bit_targets":900*5*r,"tail0_targets":900*r,"STOP_targets":900,"free_whole_correct":sum(row["generation"]["whole_correct"] for row in rows),"free_info_bits_correct":sum(free_correct(row,pos) for row in rows for pos in info),"free_tail0_correct":sum(free_correct(row,pos) for row in rows for pos in tails),"free_STOP_position_correct":sum(row["generation"]["tokens"].endswith("S") and len(row["generation"]["tokens"])==6*r+1 for row in rows),"TF_info_bits_correct":sum(row["TF"][pos]["prediction"]==row["TF"][pos]["target"] for row in rows for pos in info),"TF_tail0_correct":sum(row["TF"][pos]["prediction"]=="0" for row in rows for pos in tails),"TF_STOP_correct":sum(row["TF"][6*r]["prediction"]=="S" for row in rows)}
    return result


def audit_baseline(seed,bundle,parent,rows,output,cost):
    generated=independent_generation(parent,rows,cost,"baseline_free_generation")
    equal(generated,bundle["baseline_generation"],"all baseline raw-NumPy generations exact")
    need(all(generated["scores"][name]["whole_correct"]==900 for name in ("E1","E2")),"independent parent Echo integrity")
    expected={"seed":seed,"parent_counters":counters(parent),"before_full_state_sha256":state_sha(parent),"after_full_state_sha256":state_sha(bundle["after"]),"scores":generated["scores"],"old_Echo_integrity_pass":True,"baseline_streak":0,"baseline_inference_calls":generated["inference_calls"],"baseline_inference_MAC":generated["inference_dense_MAC"],"new_optimizer_updates":0,"only_inference_counters_changed":True}
    equal(expected,bundle["baseline"],"complete baseline metadata independently checked")
    proof={"status":"passed","seed":seed,"public_parent_head":PARENT_HEAD,"before_full_state_sha256":state_sha(parent),"after_full_state_sha256":state_sha(bundle["after"]),"scores":generated["scores"],"baseline_streak":0,"new_optimizer_updates":0,"independent_generation_canonical_sha256":digest(canonical(generated).encode()),"generation_exact_equal":True,"parent_counters":counters(parent),"baseline_after_counters":counters(bundle["after"]),"only_inference_counters_changed":True,"literal_F1_input0_1":literal_metrics(rows,generated),"independent_forward_calls":generated["inference_calls"],"independent_dense_MAC":generated["inference_dense_MAC"],"audit_cost_so_far":cost.record()}
    name=f"seed{seed}-baseline.json";write(output/name,proof);cost.persist("running")
    return generated,proof,"numeric-proof/"+name


def audit_student(seed,bundle,parent,baseline,baseline_proof,rows,order,output,cost):
    started_calls=cost.calls;parent_counts=counters(parent);new_probe_calls=0;streak=0;first_full=None;reason=None;refs=[];points=[];last=None
    for epoch,(point,state,actual) in enumerate(zip(bundle["records"],bundle["states"],bundle["generations"],strict=True),1):
        need(reason is None,"continued training after fixed stop")
        generated=independent_generation(state,rows,cost,"mixed_epoch_free_generation")
        equal(generated,actual,"all2700 independent mixed epoch outputs")
        passed=all(generated["scores"][name]["whole_correct"]==900 for name in CLASSES)
        streak=streak+1 if passed else 0
        if passed and first_full is None: first_full=epoch
        reason="two_consecutive_all_class_passes" if streak>=2 else "epoch_cap" if epoch==40 else None
        new_probe_calls+=generated["inference_calls"]
        total_calls=parent_counts["inference_calls"]+baseline["inference_calls"]+new_probe_calls
        new_updates=epoch*24300
        expected={"seed":seed,"epoch":epoch,"global_updates":parent_counts["t"]+new_updates,"new_updates":new_updates,"total_training_dense_MAC":parent_counts["train_MAC"]+new_updates*TRAIN_MAC,"new_training_dense_MAC":new_updates*TRAIN_MAC,"parent_counters":parent_counts,"training":point["training"],"scores":generated["scores"],"streak":streak,"stop_reason":reason,"first_full_epoch":first_full,"baseline_inference_calls":baseline["inference_calls"],"baseline_inference_MAC":baseline["inference_dense_MAC"],"epoch_probe_inference_calls":generated["inference_calls"],"epoch_probe_inference_MAC":generated["inference_dense_MAC"],"new_probe_inference_calls_cumulative":new_probe_calls,"new_probe_inference_MAC_cumulative":new_probe_calls*FORWARD_MAC,"total_inference_calls":total_calls,"total_inference_MAC":total_calls*FORWARD_MAC,"full_state_sha256":state_sha(state)}
        equal(point,expected,"epoch global/new counters, baseline exclusion, scores/streak/stop exact")
        teacher=hashlib.sha256()
        for qid,pos in order[epoch-1]:
            task,pos=rows[int(qid)],int(pos)
            teacher.update((canonical([task["question_id"],pos,task["Q"]+task["A"][:pos],(task["A"]+"S")[pos]])+"\n").encode())
        proof={"status":"passed","seed":seed,"epoch":epoch,"full_state_sha256":state_sha(state),"scores":generated["scores"],"streak":streak,"first_full_epoch":first_full,"stop_reason":reason,"global_updates":parent_counts["t"]+new_updates,"new_updates":new_updates,"free_questions_verified":2700,"independent_generation_canonical_sha256":digest(canonical(generated).encode()),"frozen_teacher_order_canonical_sha256":teacher.hexdigest(),"native_prediction_loss_digest_form_checked":point["training"]["canonical_target_trace_sha256"],"unarchived_target_losses_or_gradients_recomputed":False,"independent_epoch_forward_calls":generated["inference_calls"],"independent_epoch_dense_MAC":generated["inference_dense_MAC"],"audit_cost_so_far":cost.record()}
        name=f"seed{seed}-epoch{epoch:03}.json";write(output/name,proof);refs.append("numeric-proof/"+name);points.append(proof);cost.persist("running");last=generated
    need(reason is not None,"actual fixed complete termination")
    total={"t":parent_counts["t"]+len(points)*24300,"train_MAC":parent_counts["train_MAC"]+len(points)*24300*TRAIN_MAC,"inference_calls":parent_counts["inference_calls"]+baseline["inference_calls"]+new_probe_calls,"inference_MAC":parent_counts["inference_MAC"]+baseline["inference_dense_MAC"]+new_probe_calls*FORWARD_MAC}
    summary={"seed":seed,"epochs":len(points),"stop_reason":reason,"streak":streak,"first_full_epoch":first_full,"stable_pass_epoch":len(points) if streak>=2 else None,"parent_counters":parent_counts,"new_updates":len(points)*24300,"new_training_dense_MAC":len(points)*24300*TRAIN_MAC,"baseline_inference_calls":baseline["inference_calls"],"baseline_inference_MAC":baseline["inference_dense_MAC"],"new_probe_inference_calls":new_probe_calls,"new_probe_inference_MAC":new_probe_calls*FORWARD_MAC,"total_counters_before_finalTF":total,"final_scores":last["scores"],"final_full_state_sha256":state_sha(bundle["final"])}
    equal(summary,bundle["summary"],"entire independent continuation summary")
    tf=independent_tf(bundle["final"],rows,last,cost)
    equal(tf,bundle["truth"],"all final24300 TF logits/probabilities/CE exact")
    failures=[row for row in tf["truth"] if not row["generation"]["whole_correct"]]
    equal(failures,bundle["failures"],"all final failures exact")
    result={**summary,"replay_status":"complete_exact" if seed==101 else "not_planned","final_TF_metrics":tf["metrics"],"final_TF_inference_calls":24300,"final_TF_inference_MAC":24300*FORWARD_MAC}
    equal(result,bundle["compact"],"complete compact continuation row")
    student_calls=baseline["inference_calls"]+cost.calls-started_calls
    proof={"status":"passed","seed":seed,"epochs":len(points),"first_full_epoch":first_full,"stable_pass_epoch":summary["stable_pass_epoch"],"stop_reason":reason,"summary":summary,"baseline_proof_ref":f"numeric-proof/seed{seed}-baseline.json","epoch_proof_refs":refs.copy(),"baseline_scores":baseline["scores"],"final_scores":last["scores"],"final_TF_logits_probabilities_CE_verified":24300,"final_decomposed_metrics":decomposed_metrics(tf["truth"]),"final_literal_F1_input0_1":literal_metrics(rows,last),"final_truth_independent_canonical_sha256":digest(canonical(tf).encode()),"final_failures_independent_canonical_sha256":digest(canonical(failures).encode()),"final_failure_question_ids":[row["question_id"] for row in failures],"independent_baseline_forward_calls":baseline["inference_calls"],"independent_mixed_epoch_and_TF_forward_calls":cost.calls-started_calls,"independent_total_student_forward_calls":student_calls,"independent_total_student_dense_MAC":student_calls*FORWARD_MAC,"audit_cost_so_far":cost.record(),"optimizer_calls":0}
    name=f"seed{seed}-student.json";write(output/name,proof);refs.append("numeric-proof/"+name);cost.persist("running")
    print(canonical({"phase":"independent_continued_student_complete","seed":seed,"epochs":len(points),"baseline_scores":baseline["scores"],"final_scores":last["scores"],"audit_student_forward_calls":student_calls}),flush=True)
    return result,proof,refs


def run(args,cost):
    need(args.root_confirmed_exit0,"explicit coordinator postrun GO required")
    need(PREREG is not None and FORMAL_SESSION is not None and args.prereg_commit==PREREG and args.formal_session==FORMAL_SESSION,"current-study coordinator prereg/session pins required")
    for path in (args.manifest,args.manifest.parent/"source-freeze.json",args.manifest.parent/"inputs.zip",args.receipt,args.formal_log,args.formal_stderr): need(path.is_file(),"all external input/log/receipt paths exist")
    manifest,rows,parents,raw_parents,orders=inputs(args)
    compact,bundles,before,timing,metadata=preflight(args,manifest,rows,parents,raw_parents)
    prereg_before=inventory(args.manifest.parent)
    write(args.output_root/"metadata-preflight.json",{"status":"passed","manifest_sha256":APPROVED,"source_hashes":manifest["source_hashes"],"all_required_paths_and_schemas_checked_before_any_trained_forward":True,"model_forward_calls":0,"science_files":len(before),"actual_epochs_by_seed":{str(seed):len(bundle["records"]) for seed,bundle in bundles.items()},**metadata})
    output=args.output_root/"numeric-proof";output.mkdir(exist_ok=False)
    baseline_results,baseline_proofs,refs={},{},[]
    for seed in SEEDS:
        generated,proof,ref=audit_baseline(seed,bundles[seed],parents[seed],rows,output,cost)
        baseline_results[seed],baseline_proofs[seed]=generated,proof;refs.append(ref)
    results,details=[],[]
    for seed in SEEDS:
        result,proof,new_refs=audit_student(seed,bundles[seed],parents[seed],baseline_results[seed],baseline_proofs[seed],rows,orders[seed],output,cost)
        results.append(result);details.append(proof);refs.extend(new_refs)
    updates=sum(row["new_updates"] for row in results);train_mac=sum(row["new_training_dense_MAC"] for row in results)
    baseline_calls=sum(row["baseline_inference_calls"] for row in results);probe_calls=sum(row["new_probe_inference_calls"] for row in results)
    expected={"id":manifest["id"],"status":"complete","author":"Codex","manifest_sha256":APPROVED,"preregistration_commit":args.prereg_commit,"students":results,"primary_continued_students":3,"exact_full_replays":[101],"new_primary_updates":updates,"new_primary_training_dense_MAC":train_mac,"new_replay_updates":results[0]["new_updates"],"new_replay_training_dense_MAC":results[0]["new_training_dense_MAC"],"baseline_inference_calls":baseline_calls,"baseline_inference_MAC":baseline_calls*FORWARD_MAC,"mixed_probe_inference_calls":probe_calls,"mixed_probe_inference_MAC":probe_calls*FORWARD_MAC,"replay_baseline_inference_calls":results[0]["baseline_inference_calls"],"replay_baseline_inference_MAC":results[0]["baseline_inference_MAC"],"replay_probe_inference_calls":results[0]["new_probe_inference_calls"],"replay_probe_inference_MAC":results[0]["new_probe_inference_MAC"],"final_TF_inference_calls":72900,"final_TF_inference_MAC":72900*FORWARD_MAC,"all_confirmed_three_class_fit":all(row["streak"]>=2 for row in results),"array_bytes_per_student":209980,"external_model_calls":0,"limits":manifest["protocol"]["limits"]}
    equal(compact,expected,"entire independently reconstructed new-delta compact")
    need(cost.calls==baseline_calls+probe_calls+72900,"independent actual new forward accounting")
    equal(before,inventory(args.science),"science unchanged after independent audit")
    equal(prereg_before,inventory(args.manifest.parent),"frozen inputs unchanged after independent audit")
    for name,pin in manifest["source_hashes"].items(): need(sha(args.code_root/name)==pin,"frozen core unchanged after audit")
    need(sha(Path(__file__))==cost.script_sha256,"auditor source unchanged")
    need(sha(args.receipt)==metadata["receipt_sha256"] and sha(args.formal_log)==metadata["stdout_sha256"] and sha(args.formal_stderr)==metadata["stderr_sha256"],"execution metadata unchanged after audit")
    proof_inventory={ref:{"bytes":(args.output_root/ref).stat().st_size,"sha256":sha(args.output_root/ref)} for ref in refs}
    write(args.output_root/"post-run-details.json",{"status":"passed","manifest_sha256":APPROVED,"source_hashes":manifest["source_hashes"],"students":details,"baseline_proofs":{str(seed):baseline_proofs[seed] for seed in SEEDS},"science_file_inventory":before,"prereg_file_inventory":prereg_before,"numeric_proof_refs":refs,"numeric_proof_inventory":proof_inventory})
    epochs=sum(row["epochs"] for row in results)
    result={"status":"passed","root_confirmed_formal_exit0":True,"formal_session":args.formal_session,"preregistration_commit":args.prereg_commit,"manifest_sha256":APPROVED,"inputs_zip_sha256":ZIP_SHA,"source_hashes":manifest["source_hashes"],"receipt_sha256":metadata["receipt_sha256"],"parent_result_commit":PARENT_HEAD,"public_parent_states_exact_retained":3,"baseline_questions_independently_generated":8100,"all3_old_Echo_baseline_integrity_verified_before_auditing_mixed_epochs":True,"baseline_scores_by_seed":{str(seed):baseline_results[seed]["scores"] for seed in SEEDS},"baseline_only_inference_counters_changed":True,"baseline_excluded_from_training_streak":True,"actual_primary_continuations":3,"actual_full_replay_seeds":[101],"not_replayed_seeds":[202,303],"actual_epochs_by_seed":{str(row["seed"]):row["epochs"] for row in results},"first_full_epochs_by_seed":{str(row["seed"]):row["first_full_epoch"] for row in results},"stable_pass_epochs_by_seed":{str(row["seed"]):row["stable_pass_epoch"] for row in results},"stop_reasons_by_seed":{str(row["seed"]):row["stop_reason"] for row in results},"all_confirmed_three_class_fit":expected["all_confirmed_three_class_fit"],"all_continuations_including_failures_retained":True,"actual_primary_epochs_verified":epochs,"mixed_epoch_free_questions_verified":epochs*2700,"total_baseline_and_mixed_free_questions_verified":(epochs+3)*2700,"final_TF_logits_probabilities_CE_verified":72900,"full_science_NPZ_verified":sum(name.endswith(".npz") for name in before),"frozen_target_permutations_independently_verified":120,"parent_inherited_counters_by_seed":{str(seed):counters(parents[seed]) for seed in SEEDS},"new_primary_updates":updates,"new_primary_training_dense_MAC":train_mac,"new_replay_updates_seed101":results[0]["new_updates"],"new_replay_training_dense_MAC_seed101":results[0]["new_training_dense_MAC"],"new_primary_baseline_forward_calls":baseline_calls,"new_primary_mixed_probe_forward_calls":probe_calls,"new_replay_baseline_forward_calls_seed101":results[0]["baseline_inference_calls"],"new_replay_mixed_probe_forward_calls_seed101":results[0]["new_probe_inference_calls"],"new_final_TF_forward_calls":72900,"parent_old_costs_not_rebilled":True,"final_scores_by_seed":{str(row["seed"]):row["final_scores"] for row in results},"final_decomposed_metrics_by_seed":{str(row["seed"]):row["final_decomposed_metrics"] for row in details},"final_literal_F1_input0_1_by_seed":{str(row["seed"]):row["final_literal_F1_input0_1"] for row in details},"audit_extra_forward_calls":cost.calls,"audit_extra_dense_MAC":cost.calls*FORWARD_MAC,"audit_attempt_count":1,"metadata_checked_before_any_trained_forward":True,"each_baseline_epoch_student_numeric_proof_and_cost_persisted":True,"numeric_proof_count":len(refs),"all_source_parent_frozen_inputs_science_and_execution_metadata_unchanged":True,"all_generation_TF_failures_curves_stops_costs_exact":True,"formal_wall_seconds":timing["total_seconds"],"metadata":metadata,"replay_scope":"Frozen driver/exit0 establish seed101 full baseline and epoch replay with matching probe, digest and complete state assertions. Stdout/timing record its epoch trajectory; separate replay state copies and raw target losses are not stored, so their absent internals are not independently re-audited. Seeds202/303 are not replayed.","independent_limit":"All archived public-parent/baseline/primary states, actual generated outputs, final TF, frozen data/orders, aggregate/digest form, gates and delta/cumulative costs were checked. No unarchived per-target loss, gradient or intermediate optimizer trajectory reconstruction.","timing_scope":"Formal total includes all baselines, training, probes, I/O, seed101 replay baseline, guards and final TF. Individual train_one trajectory durations exclude baseline_one calls.","interpretation_limit":"Three existing PR26 models continued on an exposed900-payload finite bank with unequal6300/11700/6300 target weights. No causal isolation of Flip, new-bank/arbitrary-r/length generalization or control-execution claim.","optimizer_calls":0,"new_students":0,"external_model_calls":0,"legacy_or_driver_modules_imported":False,"details":"review/post-run-details.json"}
    write(args.output_root/"post-run.json",result)
    print(canonical({"status":"passed","actual_epochs":epochs,"baseline_and_epoch_free_questions":result["total_baseline_and_mixed_free_questions_verified"],"TF_targets":72900,"all_confirmed_three_class_fit":result["all_confirmed_three_class_fit"],"audit_cost":cost.record()}),flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("manifest","science","code-root","formal-log","formal-stderr","receipt"): parser.add_argument("--"+name,type=Path,required=True)
    parser.add_argument("--prereg-commit",required=True);parser.add_argument("--formal-session",type=int,required=True)
    parser.add_argument("--root-confirmed-exit0",action="store_true");parser.add_argument("--output-root",type=Path,default=HERE)
    args=parser.parse_args()
    need(not any((args.output_root/name).exists() for name in ("metadata-preflight.json","numeric-proof","post-run.json","audit-cost.json","audit-cost.json.tmp","audit-failure.json")),"new audit attempt output required")
    args.output_root.mkdir(parents=True,exist_ok=True);cost=Cost(args.output_root);status="failed";cost.persist("metadata_preflight_pending")
    try:
        run(args,cost);status="passed"
    except Exception as error:
        message=str(error) if isinstance(error,AssertionError) else "Unexpected processing error; full traceback stays in local tool evidence."
        write(args.output_root/"audit-failure.json",{"status":"failed","error_type":type(error).__name__,"message":message,"cost":cost.record(),"script_sha256":sha(Path(__file__)),"completed_numeric_proofs_retained":True})
        raise
    finally: cost.persist(status)


if __name__=="__main__": main()
