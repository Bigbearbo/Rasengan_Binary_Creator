"""Independent F2 continuation audit; no learner/driver imports or optimizer.

All saved-baseline/epoch word, STOP, first-error and QID transition readouts reuse
the planned raw-NumPy free generations. No formal optimizer replay is performed.
"""
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
APPROVED="b8d385db584aec294f5363556f045aecb3ceb8864dc20f4816c30bc591426d95"
ZIP_SHA="eb8869afb02be3f84c2405044bbc294c32cbeba2468c4976b93f9bba3eeb5d3d"
DRIVER="08dcba6ef9074c640e3e94321d56492dc27d1c1a3f0a77f0c09afd17c5215dc6"
PARENT_HEAD="5ceec0c42507bb5646dc0d87089f4a86e0e6269c"
PUBLICATION_SHA="dcf039bf53bcc39669d06daced174dffb133fa75c93e52acbc2fd59433b45a11"
PUBLICATION_BLOB="2f90e963b31486a4ba568b8361976cd2f23f8145"
SEEDS=(101,202,303)
CLASSES=("E1","E2","F1","F2")
PARENT_T={101:297000,202:400500,303:441900}
TRAIN_MAC,FORWARD_MAC=21056,10432
# Coordinator supplies and confirms current-study commit/session before GO.
PREREG=None
FORMAL_SESSION=None

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
BASE_FIELDS={"seed","parent_counters","before_full_state_sha256","after_full_state_sha256","scores","old_three_integrity_pass","token_metrics","churn","baseline_streak","baseline_inference_calls","baseline_inference_MAC","new_optimizer_updates","only_inference_counters_changed"}
EPOCH_FIELDS={"seed","epoch","global_updates","new_updates","total_training_dense_MAC","new_training_dense_MAC","parent_counters","training","scores","streak","stop_reason","first_full_epoch","token_metrics","churn","baseline_inference_calls","baseline_inference_MAC","epoch_probe_inference_calls","epoch_probe_inference_MAC","new_probe_inference_calls_cumulative","new_probe_inference_MAC_cumulative","total_inference_calls","total_inference_MAC","full_state_sha256"}
SUMMARY_FIELDS={"seed","epochs","stop_reason","streak","first_full_epoch","stable_pass_epoch","parent_counters","new_updates","new_training_dense_MAC","baseline_inference_calls","baseline_inference_MAC","new_probe_inference_calls","new_probe_inference_MAC","total_counters_before_finalTF","final_scores","final_token_metrics","final_churn","final_full_state_sha256"}
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
    need(manifest["protocol"]["replay_seeds"]==[] and manifest["protocol"]["maximum_new_training_dense_MAC_all_formal"]==90961920000,"preplanned three-primary budget with zero formal training replay")
    need(freeze["manifest_sha256"]==APPROVED and freeze["source_hashes"]==manifest["source_hashes"],"source freeze")
    need(manifest["source_hashes"]["run_f2.py"]==DRIVER,"frozen driver")
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
    for pair,payload in enumerate(bank):
        rows.append({"question_id":1800+pair,"pair_id":pair,"r":1,"payload":payload,"Q":"01100"+"0010"+"".join(word(v) for v in payload)+"111100","A":"".join(str(1-int(bit)) for bit in format(payload[0],"05b"))+"0","class":"F1","op":"100"})
    equal(parse(raw["parent-questions.json"].decode()),rows,"old2700 complete E1/E2/F1 Q/A bitidentity")
    for pair,payload in enumerate(bank):
        answer="".join("".join(str(1-int(bit)) for bit in format(value,"05b"))+"0" for value in payload[:2])
        rows.append({"question_id":2700+pair,"pair_id":pair,"r":2,"payload":payload,"Q":"01100"+"0100"+"".join(word(v) for v in payload)+"111100","A":answer,"class":"F2","op":"100"})
    equal(parse(raw["questions.json"].decode()),rows,"independent full3600 four-class Q/A grammar")
    need(rows[1800]["A"]+"S"=="111110S" and rows[1830]["A"]+"S"=="111100S","literal UP/END-like answer bits retained")
    need(rows[2700]["A"]+"S"=="111110111110S" and rows[2701]["A"]+"S"=="111110111100S","both F2 output slots preserve literal control-pattern answers")
    prefix_labels={};label_counts=Counter()
    for task in rows:
        need(len(task["Q"])==39 and len(task["A"]+"S")== (13 if task["class"] in ("E2","F2") else 7),"four-class input/answer lengths")
        for pos,label in enumerate(task["A"]+"S"):
            prefix=task["Q"]+task["A"][:pos];need(prefix not in prefix_labels,"unique teacher prefixes")
            prefix_labels[prefix]=label;label_counts[label]+=1
    need(len(prefix_labels)==36000,"all mixed teacher prefixes")
    equal(dict(label_counts),{"0":18900,"1":13500,"S":3600},"mixed label counts")
    pool=np.asarray([(offset+pair,pos) for pair in range(900) for offset in (0,900,1800,2700) for pos in range(len(rows[offset+pair]["A"])+1)],dtype="<u2")
    orders={}
    for seed in SEEDS:
        rng=np.random.default_rng(seed+555000)
        expected=np.stack([pool[rng.permutation(len(pool))] for _ in range(40)])
        actual=np.load(io.BytesIO(raw[f"orders/seed{seed}.npy"]),allow_pickle=False)
        need(actual.dtype.str=="<u2" and actual.shape==(40,36000,2) and np.array_equal(actual,expected),"all40 independently reconstructed mixed target permutations")
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
    need(len(value["rows"])==3600,"all3600 generated outputs")
    for item,task in zip(value["rows"],rows,strict=True):
        keys(item,GEN_ROW_FIELDS,"generation row")
        need((item["question_id"],item["class"],item["pair_id"])==(task["question_id"],task["class"],task["pair_id"]),"generation identity/order")
        need(isinstance(item["tokens"],str) and 1<=len(item["tokens"])<=32 and set(item["tokens"])<=set("01S"),"generated action domain")
        need(all(type(item[name]) is bool for name in ("context_exhausted","cap_exhausted","whole_correct")),"generation flags")
    integer(value["inference_calls"],3600,115200,"generation calls")
    need(value["inference_dense_MAC"]==value["inference_calls"]*FORWARD_MAC,"generation cost")


ERROR_KINDS={"none","content_bit","early_STOP","missing_token","extra_token","STOP_expected_bit_emitted"}
TERMINATIONS={"context_exhausted","cap_exhausted","no_STOP","early_STOP","STOP_at_expected_position","late_STOP","tokens_after_STOP"}
WORD_FIELDS={"information5_correct","tail0_correct","complete6_correct"}
METRIC_ITEM_FIELDS={"question_id","class","whole_correct","answer_bit_correct","words","STOP_position_correct","first_error_position_zero_based","first_error_kind","termination_kind","missing_expected_positions","extra_output_positions","context_exhausted","cap_exhausted"}
METRIC_CLASS_FIELDS={"questions","whole_correct","words","answer_position_bit_correct","answer_position_bit_totals","STOP_position_correct","first_error_position_histogram","first_error_kind_histogram","termination_kind_histogram","missing_expected_positions","extra_output_positions","context_exhausted_questions","cap_exhausted_questions"}
CHURN_FIELDS={"previous_correct_to_wrong","previous_wrong_to_correct","retained_correct","retained_wrong"}


def readout_schema(readout,rows,previous_point):
    keys(readout,{"metrics","churn"},"token readout file")
    metrics,churn=readout["metrics"],readout["churn"]
    keys(metrics,{"by_class","per_question","extra_forward_calls"},"pure token metrics")
    need(metrics["extra_forward_calls"]==0 and len(metrics["per_question"])==3600,"readout0NN/all3600 rows")
    keys(metrics["by_class"],set(CLASSES),"token metric classes")
    for task,item in zip(rows,metrics["per_question"],strict=True):
        keys(item,METRIC_ITEM_FIELDS,"per-question token metric")
        need((item["question_id"],item["class"])==(task["question_id"],task["class"]),"token readout QID order")
        need(len(item["answer_bit_correct"])==len(task["A"]) and all(type(value) is bool for value in item["answer_bit_correct"]),"fixed denominator/missing-bit booleans")
        need(len(item["words"])==task["r"],"only existing output word slots")
        for word in item["words"]:
            keys(word,WORD_FIELDS,"per-word readout")
            need(all(type(value) is bool for value in word.values()),"word readout booleans")
        need(item["first_error_position_zero_based"] is None or type(item["first_error_position_zero_based"]) is int and 0<=item["first_error_position_zero_based"]<32,"first error0-based including0")
        need(item["first_error_kind"] in ERROR_KINDS and item["termination_kind"] in TERMINATIONS,"two-axis error taxonomy")
        for name in ("whole_correct","STOP_position_correct","context_exhausted","cap_exhausted"): need(type(item[name]) is bool,"token metric boolean")
        integer(item["missing_expected_positions"],0,13,"missing expected positions");integer(item["extra_output_positions"],0,32,"extra output positions")
    for name,value in metrics["by_class"].items():
        keys(value,METRIC_CLASS_FIELDS,"aggregate token readout")
        need(value["questions"]==900,"token metric all900 denominator")
        length=12 if name in ("E2","F2") else 6
        need(len(value["answer_position_bit_correct"])==length and value["answer_position_bit_totals"]==[900]*length,"answer-position denominator")
        keys(value["words"],{"word1","word2"},"word slots")
        for slot,word in value["words"].items():
            keys(word,{"questions"}|WORD_FIELDS,"word aggregate")
            count=900 if slot=="word1" or length==12 else 0
            need(word["questions"]==count,"no r1 second-word denominator")
            for field in WORD_FIELDS:
                if count: integer(word[field],0,900,"word aggregate correct")
                else: need(word[field] is None,"r1 nonexistent word metrics N/A")
        for field in ("first_error_position_histogram","first_error_kind_histogram","termination_kind_histogram"):
            need(sum(value[field].values())==900 and all(type(count) is int and count>=0 for count in value[field].values()),"complete error histogram")
    keys(churn,{"comparison_available","previous_point","by_class","extra_forward_calls"},"QID churn")
    need(churn["extra_forward_calls"]==0 and churn["previous_point"]==previous_point and churn["comparison_available"] is (previous_point is not None),"baseline N/A or exact previous-point label")
    keys(churn["by_class"],set(CLASSES),"churn classes")
    for value in churn["by_class"].values():
        keys(value,{"questions"}|CHURN_FIELDS,"churn aggregate")
        need(value["questions"]==900,"churn all900 denominator")
        if previous_point is None: need(all(value[name] is None for name in CHURN_FIELDS),"baseline transitions N/A")
        else: need(all(type(value[name]) is int and value[name]>=0 for name in CHURN_FIELDS) and sum(value[name] for name in CHURN_FIELDS)==900,"all four directional churn cells")


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
    need(compact["status"]=="complete" and compact["primary_continued_students"]==3 and compact["exact_full_replays"]==[],"all three continued trajectories completed with no formal replay")
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
        names={"initial-state.npz","baseline-before.npz","baseline-after.npz","baseline.json","baseline-generation.json","baseline-token-metrics.json","final-state.npz","training-summary.json","curve.json","final-truth.json","final-failures.json"}
        names|={f"{kind}-{epoch:03}.{extension}" for epoch in range(1,count+1) for kind,extension in (("state","npz"),("epoch","json"),("generation","json"),("token-metrics","json"))}
        need(all((folder/name).is_file() for name in names),"all actual baseline/epoch/final files exist")
        expected_files|={f"seed{seed}/{name}" for name in names}
        need((folder/"initial-state.npz").read_bytes()==raw_parents[seed],"original parent NPZ bytes preserved")
        parent_counts=counters(parents[seed])
        before=load_state((folder/"baseline-before.npz").read_bytes(),seed,parent_counts["t"],parent_counts["inference_calls"])
        same_state(before,parents[seed],"before-baseline exact public parent state")
        baseline=read(folder/"baseline.json");keys(baseline,BASE_FIELDS,"baseline record")
        equal(baseline["parent_counters"],parent_counts,"baseline inherited counters")
        need(baseline["seed"]==seed and baseline["new_optimizer_updates"]==baseline["baseline_streak"]==0 and baseline["old_three_integrity_pass"] is True and baseline["only_inference_counters_changed"] is True,"baseline integrity flags/streak0")
        generation=read(folder/"baseline-generation.json");generation_schema(generation,rows)
        baseline_readout=read(folder/"baseline-token-metrics.json");readout_schema(baseline_readout,rows,None)
        equal(baseline["token_metrics"],baseline_readout["metrics"]["by_class"],"baseline token readout aggregate")
        equal(baseline["churn"],baseline_readout["churn"],"baseline transitions N/A")
        equal(baseline["scores"],generation["scores"],"baseline scores")
        need(all(baseline["scores"][name]["whole_correct"]==900 for name in ("E1","E2","F1")),"both old Echo integrity scores")
        need(baseline["baseline_inference_calls"]==generation["inference_calls"] and baseline["baseline_inference_MAC"]==generation["inference_dense_MAC"],"baseline cost")
        after=load_state((folder/"baseline-after.npz").read_bytes(),seed,parent_counts["t"],parent_counts["inference_calls"]+generation["inference_calls"])
        unchanged=set(before)-{"meta_inference_calls","meta_inference_macs"}
        same_state({name:before[name] for name in unchanged},{name:after[name] for name in unchanged},"baseline changes only inference counters")
        need(state_sha(before)==baseline["before_full_state_sha256"] and state_sha(after)==baseline["after_full_state_sha256"],"baseline before/after state hashes")
        equal(gate["baselines"][str(seed)],baseline,"all-three baseline gate member")
        summary,curve=read(folder/"training-summary.json"),read(folder/"curve.json")
        keys(summary,SUMMARY_FIELDS,"training summary")
        need(summary["seed"]==seed and summary["epochs"]==len(curve)==count,"student/curve epoch identity")
        records,generations,states,readouts=[],[],[],[]
        for epoch,point in enumerate(curve,1):
            keys(point,EPOCH_FIELDS,"epoch record")
            equal(read(folder/f"epoch-{epoch:03}.json"),point,"epoch/curve equality")
            need(point["seed"]==seed and point["epoch"]==epoch and point["new_updates"]==epoch*36000 and point["global_updates"]==parent_counts["t"]+epoch*36000,"old/new/global update counters")
            need(point["new_training_dense_MAC"]==epoch*36000*TRAIN_MAC and point["total_training_dense_MAC"]==parent_counts["train_MAC"]+point["new_training_dense_MAC"],"old/new training cost")
            equal(point["parent_counters"],parent_counts,"epoch inherited counters")
            keys(point["training"],TRAIN_FIELDS,"training aggregate")
            train=point["training"]
            need(train["targets"]==36000 and train["CE_loss_sum"]>=0 and train["CE_loss_mean"]==train["CE_loss_sum"]/36000,"complete target and finite sequential loss aggregate")
            integer(train["pre_update_prediction_correct"],0,36000,"pre-update prediction count")
            need(re.fullmatch("[0-9a-f]{64}",train["canonical_target_trace_sha256"]) is not None,"prediction/loss digest form")
            scores_schema(point["scores"])
            gen=read(folder/f"generation-{epoch:03}.json");generation_schema(gen,rows)
            readout=read(folder/f"token-metrics-{epoch:03}.json");readout_schema(readout,rows,"baseline" if epoch==1 else epoch-1)
            equal(point["token_metrics"],readout["metrics"]["by_class"],"epoch token readout aggregate")
            equal(point["churn"],readout["churn"],"epoch directional QID churn metadata")
            state=load_state((folder/f"state-{epoch:03}.npz").read_bytes(),seed,point["global_updates"],point["total_inference_calls"])
            need(state_sha(state)==point["full_state_sha256"],"epoch full state SHA")
            records.append(point);generations.append(gen);states.append(state);readouts.append(readout)
        final=load_state((folder/"final-state.npz").read_bytes(),seed,records[-1]["global_updates"],records[-1]["total_inference_calls"])
        same_state(final,states[-1],"final exact last epoch state")
        equal(summary["final_token_metrics"],readouts[-1]["metrics"]["by_class"],"final token readout metadata")
        equal(summary["final_churn"],readouts[-1]["churn"],"final directional churn metadata")
        truth=read(folder/"final-truth.json")
        keys(truth,{"truth","metrics","inference_calls","inference_dense_MAC","learning_state_unchanged","free_generation_reused"},"final TF file")
        need(len(truth["truth"])==3600,"all3600 final TF questions")
        for task,result in zip(rows,truth["truth"],strict=True):
            keys(result,QUESTION_FIELDS|{"expected","generation","TF"},"final truth row")
            need(all(result[name]==value for name,value in task.items()) and result["expected"]==task["A"]+"S","final truth grammar and identity")
            need(len(result["TF"])==len(task["A"])+1,"all true-prefix targets")
            for pos,label in enumerate(task["A"]+"S"):
                token=result["TF"][pos];keys(token,TF_FIELDS,"TF target")
                need((token["position"],token["prefix"],token["target"])==(pos,task["Q"]+task["A"][:pos],label),"TF true prefix/label")
                need(len(token["prediction"])==1 and token["prediction"] in "01S" and len(token["logits_01S"])==len(token["probabilities_01S"])==3,"TF action/vector shape")
                need(all(0<=value<=1 for value in token["probabilities_01S"]) and token["target_CE"]>=0,"TF probability/CE domain")
        failures=read(folder/"final-failures.json");need(isinstance(failures,list) and len(failures)<=3600,"complete final failures file")
        bundles[seed]={"compact":item,"summary":summary,"baseline":baseline,"baseline_generation":generation,"baseline_readout":baseline_readout,"before":before,"after":after,"records":records,"generations":generations,"readouts":readouts,"states":states,"final":final,"truth":truth,"failures":failures}
    before_inventory=inventory(args.science)
    equal(set(before_inventory),expected_files,"exact science inventory without failure files")
    timing,storage=read(args.science/"timing.json"),read(args.science/"storage.json")
    equal([(row["mode"],row["seed"]) for row in timing["trajectories"]],[("primary",101),("primary",202),("primary",303)],"actual three primary timing records and no formal replay")
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
    for mode,seed in (("primary",101),("primary",202),("primary",303)):
        for point in bundles[seed]["records"]:
            expected_progress.append({"mode":mode,"seed":seed,"epoch":point["epoch"],"scores":point["scores"],"streak":point["streak"],"stop":point["stop_reason"]})
    equal(progress,expected_progress,"actual complete primary/replay epoch stdout")
    equal(terminal,[compact],"actual completed process stdout")
    metadata={"receipt_sha256":sha(args.receipt),"stdout_sha256":sha(args.formal_log),"stdout_bytes":args.formal_log.stat().st_size,"stderr_sha256":sha(args.formal_stderr),"stderr_bytes":args.formal_stderr.stat().st_size,"preregistration_precedes_execution":True,"actual_timing_trajectories":3,"epoch_progress_records":len(progress)}
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
    metrics={name:{"questions":900,"TF_correct":sum(point["prediction"]==point["target"] for row in truth if row["class"]==name for point in row["TF"]),"TF_targets":11700 if name in ("E2","F2") else 6300} for name in CLASSES}
    need(forward.calls==36000 and state_sha(state)==before,"complete TF without state mutation")
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
        rows=[row for row in truth if row["class"]==name];r=2 if name in ("E2","F2") else 1
        info=[pos for pos in range(6*r) if pos%6!=5];tails=[pos for pos in range(6*r) if pos%6==5]
        free_correct=lambda row,pos:pos<len(row["generation"]["tokens"]) and row["generation"]["tokens"][pos]==row["A"][pos]
        result[name]={"questions":900,"info_bit_targets":900*5*r,"tail0_targets":900*r,"STOP_targets":900,"free_whole_correct":sum(row["generation"]["whole_correct"] for row in rows),"free_info_bits_correct":sum(free_correct(row,pos) for row in rows for pos in info),"free_tail0_correct":sum(free_correct(row,pos) for row in rows for pos in tails),"free_STOP_position_correct":sum(row["generation"]["tokens"].endswith("S") and len(row["generation"]["tokens"])==6*r+1 for row in rows),"TF_info_bits_correct":sum(row["TF"][pos]["prediction"]==row["TF"][pos]["target"] for row in rows for pos in info),"TF_tail0_correct":sum(row["TF"][pos]["prediction"]=="0" for row in rows for pos in tails),"TF_STOP_correct":sum(row["TF"][6*r]["prediction"]=="S" for row in rows)}
    return result


def audit_baseline(seed,bundle,parent,rows,output,cost):
    generated=independent_generation(parent,rows,cost,"baseline_free_generation")
    equal(generated,bundle["baseline_generation"],"all baseline raw-NumPy generations exact")
    need(all(generated["scores"][name]["whole_correct"]==900 for name in ("E1","E2","F1")),"independent parent old-three integrity")
    derived=independent_readout(rows,generated["rows"])
    equal(derived,bundle["baseline_readout"],"all baseline per-question words/errors and null churn independently derived")
    expected={"seed":seed,"parent_counters":counters(parent),"before_full_state_sha256":state_sha(parent),"after_full_state_sha256":state_sha(bundle["after"]),"scores":generated["scores"],"old_three_integrity_pass":True,"token_metrics":derived["metrics"]["by_class"],"churn":derived["churn"],"baseline_streak":0,"baseline_inference_calls":generated["inference_calls"],"baseline_inference_MAC":generated["inference_dense_MAC"],"new_optimizer_updates":0,"only_inference_counters_changed":True}
    equal(expected,bundle["baseline"],"complete baseline metadata independently checked")
    proof={"status":"passed","seed":seed,"public_parent_head":PARENT_HEAD,"before_full_state_sha256":state_sha(parent),"after_full_state_sha256":state_sha(bundle["after"]),"scores":generated["scores"],"baseline_streak":0,"new_optimizer_updates":0,"independent_generation_canonical_sha256":digest(canonical(generated).encode()),"generation_exact_equal":True,"parent_counters":counters(parent),"baseline_after_counters":counters(bundle["after"]),"only_inference_counters_changed":True,"literal_F1_input0_1":literal_metrics(rows,generated),"independent_forward_calls":generated["inference_calls"],"independent_dense_MAC":generated["inference_dense_MAC"],"audit_cost_so_far":cost.record()}
    proof.update({"independent_token_readout_canonical_sha256":digest(canonical(derived).encode()),"token_metrics":derived["metrics"]["by_class"],"churn":derived["churn"],"extra_readout_forward_calls":0})
    name=f"seed{seed}-baseline.json";write(output/name,proof);cost.persist("running")
    return generated,proof,"numeric-proof/"+name


def audit_student(seed,bundle,parent,baseline,baseline_proof,rows,order,output,cost):
    started_calls=cost.calls;parent_counts=counters(parent);new_probe_calls=0;streak=0;first_full=None;reason=None;refs=[];points=[];last=None;last_derived=None
    previous=baseline["rows"]
    for epoch,(point,state,actual) in enumerate(zip(bundle["records"],bundle["states"],bundle["generations"],strict=True),1):
        need(reason is None,"continued training after fixed stop")
        generated=independent_generation(state,rows,cost,"mixed_epoch_free_generation")
        equal(generated,actual,"all3600 independent mixed epoch outputs")
        derived=independent_readout(rows,generated["rows"],previous,"baseline" if epoch==1 else epoch-1)
        equal(derived,bundle["readouts"][epoch-1],"all saved per-question word/error and directional QID transition metrics independently derived")
        passed=all(generated["scores"][name]["whole_correct"]==900 for name in CLASSES)
        streak=streak+1 if passed else 0
        if passed and first_full is None: first_full=epoch
        reason="two_consecutive_all_class_passes" if streak>=2 else "epoch_cap" if epoch==40 else None
        new_probe_calls+=generated["inference_calls"]
        total_calls=parent_counts["inference_calls"]+baseline["inference_calls"]+new_probe_calls
        new_updates=epoch*36000
        expected={"seed":seed,"epoch":epoch,"global_updates":parent_counts["t"]+new_updates,"new_updates":new_updates,"total_training_dense_MAC":parent_counts["train_MAC"]+new_updates*TRAIN_MAC,"new_training_dense_MAC":new_updates*TRAIN_MAC,"parent_counters":parent_counts,"training":point["training"],"scores":generated["scores"],"streak":streak,"stop_reason":reason,"first_full_epoch":first_full,"baseline_inference_calls":baseline["inference_calls"],"baseline_inference_MAC":baseline["inference_dense_MAC"],"epoch_probe_inference_calls":generated["inference_calls"],"epoch_probe_inference_MAC":generated["inference_dense_MAC"],"new_probe_inference_calls_cumulative":new_probe_calls,"new_probe_inference_MAC_cumulative":new_probe_calls*FORWARD_MAC,"total_inference_calls":total_calls,"total_inference_MAC":total_calls*FORWARD_MAC,"full_state_sha256":state_sha(state)}
        expected.update({"token_metrics":derived["metrics"]["by_class"],"churn":derived["churn"]})
        equal(point,expected,"epoch global/new counters, baseline exclusion, scores/streak/stop/readout/churn exact")
        teacher=hashlib.sha256()
        for qid,pos in order[epoch-1]:
            task,pos=rows[int(qid)],int(pos)
            teacher.update((canonical([task["question_id"],pos,task["Q"]+task["A"][:pos],(task["A"]+"S")[pos]])+"\n").encode())
        proof={"status":"passed","seed":seed,"epoch":epoch,"full_state_sha256":state_sha(state),"scores":generated["scores"],"streak":streak,"first_full_epoch":first_full,"stop_reason":reason,"global_updates":parent_counts["t"]+new_updates,"new_updates":new_updates,"free_questions_verified":3600,"independent_generation_canonical_sha256":digest(canonical(generated).encode()),"frozen_teacher_order_canonical_sha256":teacher.hexdigest(),"native_prediction_loss_digest_form_checked":point["training"]["canonical_target_trace_sha256"],"unarchived_target_losses_or_gradients_recomputed":False,"independent_epoch_forward_calls":generated["inference_calls"],"independent_epoch_dense_MAC":generated["inference_dense_MAC"],"audit_cost_so_far":cost.record()}
        proof.update({"independent_token_readout_canonical_sha256":digest(canonical(derived).encode()),"token_metrics":derived["metrics"]["by_class"],"churn":derived["churn"],"extra_readout_forward_calls":0})
        name=f"seed{seed}-epoch{epoch:03}.json";write(output/name,proof);refs.append("numeric-proof/"+name);points.append(proof);cost.persist("running");last=generated;last_derived=derived;previous=generated["rows"]
    need(reason is not None,"actual fixed complete termination")
    total={"t":parent_counts["t"]+len(points)*36000,"train_MAC":parent_counts["train_MAC"]+len(points)*36000*TRAIN_MAC,"inference_calls":parent_counts["inference_calls"]+baseline["inference_calls"]+new_probe_calls,"inference_MAC":parent_counts["inference_MAC"]+baseline["inference_dense_MAC"]+new_probe_calls*FORWARD_MAC}
    summary={"seed":seed,"epochs":len(points),"stop_reason":reason,"streak":streak,"first_full_epoch":first_full,"stable_pass_epoch":len(points) if streak>=2 else None,"parent_counters":parent_counts,"new_updates":len(points)*36000,"new_training_dense_MAC":len(points)*36000*TRAIN_MAC,"baseline_inference_calls":baseline["inference_calls"],"baseline_inference_MAC":baseline["inference_dense_MAC"],"new_probe_inference_calls":new_probe_calls,"new_probe_inference_MAC":new_probe_calls*FORWARD_MAC,"total_counters_before_finalTF":total,"final_scores":last["scores"],"final_full_state_sha256":state_sha(bundle["final"])}
    summary.update({"final_token_metrics":last_derived["metrics"]["by_class"],"final_churn":last_derived["churn"]})
    equal(summary,bundle["summary"],"entire independent continuation summary")
    tf=independent_tf(bundle["final"],rows,last,cost)
    equal(tf,bundle["truth"],"all final36000 TF logits/probabilities/CE exact")
    failures=[row for row in tf["truth"] if not row["generation"]["whole_correct"]]
    equal(failures,bundle["failures"],"all final failures exact")
    result={**summary,"replay_status":"not_planned","final_TF_metrics":tf["metrics"],"final_TF_inference_calls":36000,"final_TF_inference_MAC":36000*FORWARD_MAC}
    equal(result,bundle["compact"],"complete compact continuation row")
    student_calls=baseline["inference_calls"]+cost.calls-started_calls
    proof={"status":"passed","seed":seed,"epochs":len(points),"first_full_epoch":first_full,"stable_pass_epoch":summary["stable_pass_epoch"],"stop_reason":reason,"summary":summary,"baseline_proof_ref":f"numeric-proof/seed{seed}-baseline.json","epoch_proof_refs":refs.copy(),"baseline_scores":baseline["scores"],"final_scores":last["scores"],"final_TF_logits_probabilities_CE_verified":36000,"final_decomposed_metrics":decomposed_metrics(tf["truth"]),"final_literal_F1_input0_1":literal_metrics(rows,last),"final_truth_independent_canonical_sha256":digest(canonical(tf).encode()),"final_failures_independent_canonical_sha256":digest(canonical(failures).encode()),"final_failure_question_ids":[row["question_id"] for row in failures],"independent_baseline_forward_calls":baseline["inference_calls"],"independent_mixed_epoch_and_TF_forward_calls":cost.calls-started_calls,"independent_total_student_forward_calls":student_calls,"independent_total_student_dense_MAC":student_calls*FORWARD_MAC,"audit_cost_so_far":cost.record(),"optimizer_calls":0}
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
    expected={
        "id":manifest["id"],"status":"complete","author":"Codex","manifest_sha256":APPROVED,"preregistration_commit":args.prereg_commit,
        "students":results,"primary_continued_students":3,"exact_full_replays":[],
        "new_primary_updates":updates,"new_primary_training_dense_MAC":train_mac,"new_replay_updates":0,"new_replay_training_dense_MAC":0,
        "baseline_inference_calls":baseline_calls,"baseline_inference_MAC":baseline_calls*FORWARD_MAC,
        "mixed_probe_inference_calls":probe_calls,"mixed_probe_inference_MAC":probe_calls*FORWARD_MAC,
        "replay_baseline_inference_calls":0,"replay_baseline_inference_MAC":0,"replay_probe_inference_calls":0,"replay_probe_inference_MAC":0,
        "final_TF_inference_calls":108000,"final_TF_inference_MAC":108000*FORWARD_MAC,
        "all_confirmed_four_class_fit":all(row["streak"]>=2 for row in results),"array_bytes_per_student":209980,
        "external_model_calls":0,"limits":manifest["protocol"]["limits"],
    }
    equal(compact,expected,"entire independently reconstructed new-delta compact")
    need(cost.calls==baseline_calls+probe_calls+108000,"independent actual new forward accounting")
    equal(before,inventory(args.science),"science unchanged after independent audit")
    equal(prereg_before,inventory(args.manifest.parent),"frozen inputs unchanged after independent audit")
    for name,pin in manifest["source_hashes"].items(): need(sha(args.code_root/name)==pin,"frozen core unchanged after audit")
    need(sha(Path(__file__))==cost.script_sha256,"auditor source unchanged")
    need(sha(args.receipt)==metadata["receipt_sha256"] and sha(args.formal_log)==metadata["stdout_sha256"] and sha(args.formal_stderr)==metadata["stderr_sha256"],"execution metadata unchanged after audit")
    proof_inventory={ref:{"bytes":(args.output_root/ref).stat().st_size,"sha256":sha(args.output_root/ref)} for ref in refs}
    write(args.output_root/"post-run-details.json",{"status":"passed","manifest_sha256":APPROVED,"source_hashes":manifest["source_hashes"],"students":details,"baseline_proofs":{str(seed):baseline_proofs[seed] for seed in SEEDS},"science_file_inventory":before,"prereg_file_inventory":prereg_before,"numeric_proof_refs":refs,"numeric_proof_inventory":proof_inventory})
    epochs=sum(row["epochs"] for row in results)
    result={
        "status":"passed","root_confirmed_formal_exit0":True,"formal_session":args.formal_session,"preregistration_commit":args.prereg_commit,
        "manifest_sha256":APPROVED,"inputs_zip_sha256":ZIP_SHA,"source_hashes":manifest["source_hashes"],"receipt_sha256":metadata["receipt_sha256"],
        "parent_result_commit":PARENT_HEAD,"public_parent_states_exact_retained":3,"baseline_questions_independently_generated":10800,
        "all3_old_three_class_baseline_integrity_verified_before_auditing_epochs":True,
        "baseline_scores_by_seed":{str(seed):baseline_results[seed]["scores"] for seed in SEEDS},
        "baseline_token_metrics_by_seed":{str(seed):baseline_proofs[seed]["token_metrics"] for seed in SEEDS},
        "baseline_only_inference_counters_changed":True,"baseline_excluded_from_training_streak":True,
        "actual_primary_continuations":3,"actual_full_replay_seeds":[],"not_replayed_seeds":[101,202,303],
        "actual_epochs_by_seed":{str(row["seed"]):row["epochs"] for row in results},
        "first_full_epochs_by_seed":{str(row["seed"]):row["first_full_epoch"] for row in results},
        "stable_pass_epochs_by_seed":{str(row["seed"]):row["stable_pass_epoch"] for row in results},
        "stop_reasons_by_seed":{str(row["seed"]):row["stop_reason"] for row in results},
        "all_confirmed_four_class_fit":expected["all_confirmed_four_class_fit"],"all_continuations_including_failures_retained":True,
        "actual_primary_epochs_verified":epochs,"epoch_free_questions_verified":epochs*3600,
        "total_baseline_and_mixed_free_questions_verified":(epochs+3)*3600,"final_TF_logits_probabilities_CE_verified":108000,
        "all_baseline_epoch_per_question_word_bit_STOP_two_axis_first_error_and_QID_churn_readouts_exact":True,
        "extra_readout_forward_calls":0,
        "full_science_NPZ_verified":sum(name.endswith(".npz") for name in before),"frozen_target_permutations_independently_verified":120,
        "parent_inherited_counters_by_seed":{str(seed):counters(parents[seed]) for seed in SEEDS},
        "new_primary_updates":updates,"new_primary_training_dense_MAC":train_mac,"new_replay_updates":0,"new_replay_training_dense_MAC":0,
        "new_primary_baseline_forward_calls":baseline_calls,"new_primary_epoch_probe_forward_calls":probe_calls,
        "new_replay_baseline_forward_calls":0,"new_replay_epoch_probe_forward_calls":0,"new_final_TF_forward_calls":108000,
        "parent_old_costs_not_rebilled":True,"final_scores_by_seed":{str(row["seed"]):row["final_scores"] for row in results},
        "final_decomposed_metrics_by_seed":{str(row["seed"]):row["final_decomposed_metrics"] for row in details},
        "audit_extra_forward_calls":cost.calls,"audit_extra_dense_MAC":cost.calls*FORWARD_MAC,"audit_attempt_count":1,
        "metadata_checked_before_any_trained_forward":True,"each_baseline_epoch_student_numeric_proof_and_cost_persisted":True,
        "numeric_proof_count":len(refs),"all_source_parent_frozen_inputs_science_and_execution_metadata_unchanged":True,
        "all_generation_TF_failures_curves_stops_costs_exact":True,"formal_wall_seconds":timing["total_seconds"],"metadata":metadata,
        "replay_scope":"No formal optimizer training replay was planned or performed. All three students are not_planned and replay counters are0; timing/stdout must contain three primary trajectories only.",
        "independent_limit":"All archived parent/baseline/primary states, generations, word/error/churn readouts, final TF, frozen inputs/orders, aggregate/digest form, gates and costs were verified. Per-target raw losses, intermediate gradients and optimizer trajectories were not archived or independently reconstructed.",
        "timing_scope":"Formal total includes all baselines, three primary trainings/probes, I/O, guards and final TF. Individual train_one durations exclude baseline_one. No formal replay.",
        "interpretation_limit":"Three PR28 models continued on an exposed900-payload bank with target weights6300/11700/6300/11700. Prior Pro30 F2 baseline is background; no causal continuation advantage, blind/new-bank/arbitrary-r/length or internal algorithm/control-execution claim.",
        "optimizer_calls":0,"new_students":0,"external_model_calls":0,"legacy_or_driver_modules_imported":False,"details":"review/post-run-details.json",
    }
    write(args.output_root/"post-run.json",result)
    print(canonical({"status":"passed","actual_epochs":epochs,"baseline_and_epoch_free_questions":result["total_baseline_and_mixed_free_questions_verified"],"TF_targets":108000,"all_confirmed_four_class_fit":result["all_confirmed_four_class_fit"],"audit_cost":cost.record()}),flush=True)


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
