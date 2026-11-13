"""Thin eight-epoch controller around byte-frozen PR47 training and metric definitions."""
from __future__ import annotations
import argparse, ast, copy, hashlib, io, json, os, platform, re, sys, time, types, zipfile, zlib
from collections import Counter
from pathlib import Path
if sys.flags.optimize:
    raise RuntimeError("Exact guards require non-optimized Python")
sys.dont_write_bytecode = True
os.environ["OPENBLAS_NUM_THREADS"] = os.environ["OMP_NUM_THREADS"] = "1"
import numpy as np
HERE = Path(__file__).resolve().parent
CORE = ("run_continue.py", "protocol.json", "test_continue.py")
DEFS = {"canonical", "sha", "git_blob", "read", "write", "runtime", "load_helpers", "model_classes", "probe", "teacher_forced",
        "token_metrics", "churn_metrics", "target_pool", "train_arm", "word", "encode", "expected_answer", "make_rows", "data_checks", "shuffled_order", "learning_unchanged"}
def sha(raw): return hashlib.sha256(raw).hexdigest()
def blob(raw): return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
def read(path): return json.loads(Path(path).read_text(encoding="utf-8"))
def write(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, sort_keys=True, ensure_ascii=False, indent=2, allow_nan=False); stream.write("\n")
def protocol():
    p = read(HERE / "protocol.json")
    assert p["id"] == "E3-CONTINUE8-20261113" and p["max_epochs"] == 8 and p["arms"] == {"eta001": .001}
    assert p["targets_per_epoch"] == 53100 and p["maximum_new_training_dense_MAC_all_primary"] == 24 * 53100 * 21056
    return p
def sources(): return {name: sha((HERE / name).read_bytes()) for name in CORE}
def vendor(raw, cfg):
    assert sha(raw) == cfg["vendor_runner_sha256"]
    nodes = [copy.deepcopy(n) for n in ast.parse(raw.decode("utf-8")).body if isinstance(n, ast.FunctionDef) and n.name in DEFS]
    assert {n.name for n in nodes} == DEFS
    ns = dict(np=np, json=json, ast=ast, copy=copy, hashlib=hashlib, io=io, zipfile=zipfile, Path=Path, platform=platform,
              types=types, Counter=Counter, time=time, protocol=lambda: cfg)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "<unchanged-PR47-selected-definitions>", "exec"), ns)
    return types.SimpleNamespace(**{name: ns[name] for name in DEFS}), {n.name: sha(ast.dump(n, include_attributes=False).encode()) for n in nodes}
def courses(v, rows, first, seed, maximum):
    pool, rng = v.target_pool(rows, protocol()["classes"]), np.random.default_rng(seed + 666000)
    assert np.array_equal(pool[rng.permutation(len(pool))], first), "Historical first permutation mismatch"
    return np.stack([pool[rng.permutation(len(pool))] for _ in range(maximum)])
def stop_update(streak, scores, epoch, maximum):
    full = all(scores[name]["questions"] == scores[name]["whole_correct"] == 900 for name in protocol()["classes"])
    streak = streak + 1 if full else 0
    return streak, full, "two_consecutive_new_epoch_all_class_passes" if streak >= 2 else "epoch_cap" if epoch == maximum else None

def collect_public(parent_root):
    p, root = protocol(), Path(parent_root)
    public = root / "publication/final/public"
    pubraw = (public / "publication-manifest.json").read_bytes()
    assert (sha(pubraw), blob(pubraw)) == (p["parent_publication_manifest_sha256"], p["parent_publication_manifest_Git_blob"])
    pub, receipt = json.loads(pubraw), read(root / "publication-receipt.json")
    assert receipt["status"] == "complete" and receipt["result_commit"] == p["parent_head"]
    checks, used, selected, cache = {r["name"]: r for r in receipt["byte_checks"]}, {}, {}, {}
    def get(name):
        expected = dict(sha256=sha(pubraw), Git_blob=blob(pubraw), bytes=len(pubraw)) if name == "publication-manifest.json" else pub["files"][name]
        check = checks[name]
        assert check["byte_match"] and check["ref_match"] and check["commit"] == p["parent_head"]
        assert all(check[k] == expected[k] for k in ("sha256", "Git_blob", "bytes"))
        candidate = root / "remote-byte-checks" / ("final-" + name)
        raw = candidate.read_bytes() if candidate.is_file() else (public / name).read_bytes()
        assert (sha(raw), blob(raw), len(raw)) == (expected["sha256"], expected["Git_blob"], expected["bytes"])
        used[name] = check
        return raw
    assert get("publication-manifest.json") == pubraw
    oldmanifest_raw, inputs = get("manifest.json"), get("inputs.zip")
    oldmanifest = json.loads(oldmanifest_raw)
    assert sha(inputs) == p["parent_inputs_sha256"] == oldmanifest["archive"]["sha256"]
    c = {"provenance/publication-manifest.json": pubraw, "provenance/parent-manifest.json": oldmanifest_raw,
         "vendor/run_probe.py": get("run_probe.py"), "vendor/protocol.json": get("protocol.json")}
    with zipfile.ZipFile(io.BytesIO(inputs)) as z:
        mapping = [(n, n) for n in ("source/p030_binary_continual.py", "vendor/run_f2.py", "vendor/F2-protocol.json", "questions.json", "payloads.json")]
        mapping += [(f"orders/seed{s}.npy", f"first-orders/seed{s}.npy") for s in p["seeds"]]
        for old, new in mapping:
            raw = z.read(old)
            assert oldmanifest["files"][old] == dict(sha256=sha(raw), bytes=len(raw))
            c[new] = raw
            selected[new] = dict(archive="inputs.zip", member=old, sha256=sha(raw), bytes=len(raw), CRC32=format(z.getinfo(old).CRC, "08x"))
    for seed in p["seeds"]:
        for member, dest in ((f"science/seed{seed}/eta001/final-after-TF.npz", f"initial/seed{seed}.npz"),
                             (f"science/seed{seed}/eta001/generation.json", f"historical/seed{seed}.json")):
            names = [n for n, a in pub["archives"].items() if member in a["members"]]
            assert len(names) == 1
            name = names[0]
            if name not in cache: cache[name] = get(name)
            expected = pub["archives"][name]["members"][member]
            with zipfile.ZipFile(io.BytesIO(cache[name])) as z:
                raw, crc = z.read(member), format(z.getinfo(member).CRC, "08x")
            assert (sha(raw), blob(raw), len(raw), crc) == (expected["sha256"], expected["Git_blob"], expected["bytes"], expected["CRC32"])
            c[dest], selected[dest] = raw, dict(archive=name, member=member, **expected)
    c["provenance/proof.json"] = (json.dumps(dict(parent_head=p["parent_head"], public_byte_checks=used, selected_members=selected), sort_keys=True) + "\n").encode()
    return c

def inspect(c, require_orders=True):
    cfg = protocol()
    pubraw = c["provenance/publication-manifest.json"]
    assert (sha(pubraw), blob(pubraw)) == (cfg["parent_publication_manifest_sha256"], cfg["parent_publication_manifest_Git_blob"])
    pub, proof = json.loads(pubraw), json.loads(c["provenance/proof.json"])
    assert proof["parent_head"] == cfg["parent_head"]
    for name, check in proof["public_byte_checks"].items():
        expected = dict(sha256=sha(pubraw), Git_blob=blob(pubraw), bytes=len(pubraw)) if name == "publication-manifest.json" else pub["files"][name]
        assert all(check[k] == expected[k] for k in ("sha256", "Git_blob", "bytes"))
        assert check["byte_match"] and check["ref_match"] and check["commit"] == cfg["parent_head"]
    oldraw = c["provenance/parent-manifest.json"]
    assert sha(oldraw) == pub["files"]["manifest.json"]["sha256"]
    old = json.loads(oldraw)
    for name, origin in proof["selected_members"].items():
        raw = c[name]
        assert (sha(raw), len(raw), format(zlib.crc32(raw), "08x")) == (origin["sha256"], origin["bytes"], origin["CRC32"])
        expected = old["files"][origin["member"]] if origin["archive"] == "inputs.zip" else pub["archives"][origin["archive"]]["members"][origin["member"]]
        assert all(origin[k] == expected[k] for k in expected)
    assert sha(c["vendor/protocol.json"]) == cfg["vendor_protocol_sha256"]
    v, defs = vendor(c["vendor/run_probe.py"], cfg)
    h, classes = v.load_helpers(c["vendor/run_f2.py"]), v.model_classes(c["source/p030_binary_continual.py"])[0]
    rows, bank = json.loads(c["questions.json"]), json.loads(c["payloads.json"])
    assert rows == v.make_rows(bank, rows[:3600]) and v.data_checks(rows, cfg["classes"])["teacher_targets"] == 53100
    parents, orders, info = {}, {}, {}
    for seed in cfg["seeds"]:
        key, raw = str(seed), c[f"initial/seed{seed}.npz"]
        parent = h.read_npz(raw)
        assert (int(parent["meta_seed"]), int(parent["t"]), int(parent["L"]), int(parent["H"])) == (seed, cfg["parent_t"][key], 80, 64)
        assert h.equal_state(parent, h.full_state(h.restore(classes["eta001"], parent)))
        first = np.load(io.BytesIO(c[f"first-orders/seed{seed}.npy"]), allow_pickle=False)
        expected = courses(v, rows, first, seed, cfg["max_epochs"])
        actual = np.load(io.BytesIO(c[f"orders/seed{seed}.npy"]), allow_pickle=False) if require_orders else expected
        assert actual.dtype.str == "<u2" and actual.shape == (8, 53100, 2) and np.array_equal(actual, expected)
        parents[key], orders[key] = parent, actual
        info[key] = dict(raw_sha256=sha(raw), full_state_sha256=h.state_sha(parent), counters=h.counter_snapshot(parent))
    return cfg, v, h, classes["eta001"], rows, parents, orders, info, defs

def prepare(parent_root, output):
    c = collect_public(parent_root)
    cfg, v, h, _, _, _, orders, info, defs = inspect(c, False)
    for seed in cfg["seeds"]: c[f"orders/seed{seed}.npy"] = h.npy_bytes(orders[str(seed)])
    c["plan.json"] = (HERE / "protocol.json").read_bytes()
    raw = h.make_zip(c)
    m = dict(schema="e3-continuation-v1", protocol=cfg, runtime=v.runtime(), source_hashes=sources(), parents=info, reused_def_AST_sha256=defs,
             schedules={str(s): dict(file=f"orders/seed{s}.npy", shape=[8, 53100, 2], dtype="<u2", rng_seed=s+666000, first_permutation_verified=True) for s in cfg["seeds"]},
             archive=dict(file="inputs.zip", sha256=sha(raw), bytes=len(raw)), files={n: dict(sha256=sha(b), bytes=len(b)) for n,b in sorted(c.items())},
             trained_forward_calls=0, new_optimizer_calls=0)
    output = Path(output); output.mkdir(parents=True, exist_ok=False)
    with (output / "inputs.zip").open("xb") as stream: stream.write(raw)
    write(output / "manifest.json", m)
    freeze = dict(manifest_sha256=sha((output/"manifest.json").read_bytes()), source_hashes=sources(), inputs_zip_sha256=sha(raw), inputs_zip_bytes=len(raw), members=len(c), trained_forward_calls=0, new_optimizer_calls=0)
    write(output/"source-freeze.json", freeze)
    return freeze
def validate_inputs(path, approved):
    path = Path(path)
    assert re.fullmatch("[0-9a-f]{64}", approved or "") and sha(path.read_bytes()) == approved
    m = read(path); raw = (path.parent/m["archive"]["file"]).read_bytes()
    assert m["protocol"] == protocol() and m["source_hashes"] == sources() and (sha(raw),len(raw)) == (m["archive"]["sha256"],m["archive"]["bytes"])
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        assert len(z.namelist()) == len(set(z.namelist())) and set(z.namelist()) == set(m["files"])
        c = {n:z.read(n) for n in z.namelist()}
    assert all(m["files"][n] == dict(sha256=sha(b),bytes=len(b)) for n,b in c.items()) and c["plan.json"] == (HERE/"protocol.json").read_bytes()
    data = inspect(c)
    assert data[1].runtime() == m["runtime"] and data[7] == m["parents"] and data[8] == m["reused_def_AST_sha256"]
    return m,c,data

def all_baselines(v,h,cls,parents,c,rows,output,seeds):
    states, records = {}, {}
    for seed in seeds:
        key, folder = str(seed), output/f"seed{seed}"; folder.mkdir()
        with (folder/"initial-state.npz").open("xb") as stream: stream.write(c[f"initial/seed{seed}.npz"])
        net = h.restore(cls,parents[key]); before = h.full_state(net)
        h.save_state(folder/"baseline-before.npz",net)
        result = v.probe(h,net,rows,protocol()["classes"]); after = h.full_state(net)
        assert v.learning_unchanged(h,before,after)
        h.save_state(folder/"baseline-after.npz",net); write(folder/"baseline-generation.json",result)
        record = dict(seed=seed, archived_generation_exact=result==json.loads(c[f"historical/seed{seed}.json"]), scores=result["scores"],
                      inference_calls=result["inference_calls"],inference_MAC=result["inference_dense_MAC"],baseline_streak=0,new_updates=0,learning_state_unchanged=True)
        write(folder/"baseline.json",record)
        assert record["archived_generation_exact"], "Wholebatch abort: baseline differs before any new optimizer"
        states[key],records[key] = after,record
    return states,records
def run_epochs(cfg,v,h,cls,parent,baseline,order,rows,folder,seed):
    current, previous, streak, curve, timings = baseline, read(folder/"baseline-generation.json")["rows"], 0, [], []
    first_E3 = first_all = stable = reason = None
    for epoch, course in enumerate(order,1):
        cfg["end_t"][str(seed)] = int(parent["t"]) + epoch*53100
        point = folder/f"epoch-{epoch:03}"
        record,timing = v.train_arm(h,cls,parent,current,course,rows,point,seed,"eta001")
        timings.append(dict(epoch=epoch,**timing))
        current = h.read_npz((point/"final-state.npz").read_bytes()); free = read(point/"generation.json")
        assert int(current["t"])-int(parent["t"]) == epoch*53100
        streak,full,reason = stop_update(streak,record["scores"],epoch,cfg["max_epochs"])
        if first_E3 is None and record["scores"]["E3"]["whole_correct"] == 900: first_E3 = epoch
        if first_all is None and full: first_all = epoch
        if streak>=2: stable = epoch
        status = dict(epoch=epoch,streak=streak,all_five_full=full,first_E3_full_epoch=first_E3,first_all_five_full_epoch=first_all,
                      stable_pass_epoch=stable,stop_reason=reason,cumulative_new_updates=epoch*53100,cumulative_new_training_dense_MAC=epoch*1118073600,
                      scores=record["scores"],churn=v.churn_metrics(rows,previous,free["rows"],cfg["classes"]))
        write(point/"controller.json",status); curve.append(status); previous=free["rows"]
        print(v.canonical(dict(seed=seed,epoch=epoch,scores=record["scores"],streak=streak,stop=reason)),flush=True)
        if reason: break
    assert reason is not None
    with (folder/"final-state.npz").open("xb") as stream: stream.write((point/"final-state.npz").read_bytes())
    write(folder/"final-generation.json",free); write(folder/"curve.json",curve)
    summary=dict(seed=seed,epochs=len(curve),stop_reason=reason,first_E3_full_epoch=first_E3,first_all_five_full_epoch=first_all,stable_pass_epoch=stable,
                 streak=streak,new_updates=len(curve)*53100,new_training_dense_MAC=len(curve)*1118073600,final_scores=curve[-1]["scores"],
                 parent_counters=h.counter_snapshot(parent),preTF_final_counters=h.counter_snapshot(current),replay_status="not_planned")
    write(folder/"training-summary.json",summary)
    return summary,timings
def execute(path,approved,commit,output):
    assert re.fullmatch("[0-9a-f]{40}",commit or "")
    started=time.perf_counter(); m,c,(cfg,v,h,cls,rows,parents,orders,_,_)=validate_inputs(path,approved)
    output=Path(output); output.mkdir(parents=True,exist_ok=False)
    write(output/"execution-intent.json",dict(approved_manifest_sha256=approved,preregistration_commit=commit,source_hashes=sources(),replay_seeds=[],auto_retry=False))
    phase,timings,students="all_baselines",[],[]
    try:
        states,baselines=all_baselines(v,h,cls,parents,c,rows,output,cfg["seeds"])
        phase="three_continuations"
        for seed in cfg["seeds"]:
            summary,ts=run_epochs(cfg,v,h,cls,parents[str(seed)],states[str(seed)],orders[str(seed)],rows,output/f"seed{seed}",seed)
            students.append(summary); timings+=ts
        phase="three_final_TF"
        for student in students:
            seed=student["seed"]; folder=output/f"seed{seed}"; net=h.restore(cls,h.read_npz((folder/"final-state.npz").read_bytes()))
            free=read(folder/"final-generation.json"); truth=v.teacher_forced(h,net,rows,free,cfg["classes"])
            assert truth["inference_calls"]==53100
            write(folder/"final-truth.json",truth); h.save_state(folder/"final-after-TF.npz",net)
            student.update(TF_metrics=truth["metrics"],final_TF_inference_calls=truth["inference_calls"],final_TF_inference_MAC=truth["inference_dense_MAC"],
                           baseline=baselines[str(seed)],final_counters=h.counter_snapshot(h.full_state(net)))
        probe_calls=sum(read(output/f"seed{s['seed']}"/f"epoch-{e:03}"/"training.json")["new_probe_inference_calls"] for s in students for e in range(1,s["epochs"]+1))
        base_calls=sum(r["inference_calls"] for r in baselines.values())
        summary=dict(id=cfg["id"],status="complete",students=students,new_updates=sum(s["new_updates"] for s in students),
                     new_training_dense_MAC=sum(s["new_training_dense_MAC"] for s in students),stable_pass_seeds=[s["seed"] for s in students if s["stable_pass_epoch"] is not None],
                     physical_baseline_inference_calls=base_calls,physical_epoch_probe_inference_calls=probe_calls,physical_final_TF_inference_calls=159300,
                     physical_new_inference_calls_total=base_calls+probe_calls+159300,physical_new_inference_MAC_total=(base_calls+probe_calls+159300)*10432,
                     new_replay_updates=0,new_replay_training_dense_MAC=0,exact_full_replays=[],external_model_calls=0)
        write(output/"compact.json",summary); write(output/"timing.json",dict(epoch_trajectories=timings,execute_wall_seconds=time.perf_counter()-started))
        assert sources()==m["source_hashes"] and sha(Path(path).read_bytes())==approved
        return summary
    except Exception as error:
        write(output/"failure.json",dict(phase=phase,type=type(error).__name__,message=str(error),zero_new_updates_guaranteed=phase=="all_baselines",auto_retry=False,completed_epoch_timings=timings)); raise
def main():
    parser=argparse.ArgumentParser(description=__doc__); modes=parser.add_mutually_exclusive_group()
    for name in ("prepare","engineering","validate","execute"): modes.add_argument("--"+name,action="store_true")
    parser.add_argument("--parent-root",type=Path); parser.add_argument("--manifest",type=Path); parser.add_argument("--approved-manifest-sha"); parser.add_argument("--preregistration-commit"); parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    if args.prepare: result=prepare(args.parent_root,args.out)
    elif args.execute: result=execute(args.manifest,args.approved_manifest_sha,args.preregistration_commit,args.out)
    elif args.validate:
        m,_,_=validate_inputs(args.manifest,args.approved_manifest_sha); args.out.mkdir(parents=True,exist_ok=False)
        result=dict(status="passed",manifest_sha256=args.approved_manifest_sha,members=len(m["files"]),trained_forward_calls=0,new_optimizer_calls=0); write(args.out/"checks.json",result)
    else:
        import test_continue
        args.out.mkdir(parents=True,exist_ok=False); result=test_continue.run_checks(args.parent_root); result["source_hashes"]=sources(); write(args.out/"checks.json",result)
    print(json.dumps(result,sort_keys=True),flush=True)
    if result.get("status")=="failed": raise SystemExit(1)
if __name__=="__main__": main()
