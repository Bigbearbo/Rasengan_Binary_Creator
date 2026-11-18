"""Fixed automated hybrid study; no test/challenge or exhaustive audit before barrier."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import time
import numpy as np
from hybrid_model import (ROOT, SEEDS, ARMS, TRAINED_ARMS, KEYS, BIT_WEIGHTS, load_source,
    decode, init_comparator, load_mux, mux_forward, hybrid_forward, loss_grads,
    optimizer_state, adam_step, save_checkpoint, load_checkpoint)

UPDATES = 4096
CHECKPOINTS = (0,16,64,128,256,512,1024,2048,4096)


def utc():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf-8")


def verify_lock(path):
    lock = json.loads(Path(path).read_text(encoding="utf-8"))
    expected = lock["source_sha256"]
    mandatory = {"protocol.json","data.json","hybrid_model.py","run_train.py","handfilled_mux.npz","source_manifest.json"}
    mandatory.update(f"sources/receiver_seed{s}.npz" for s in SEEDS)
    mandatory.update(f"batches/seed{s}.npz" for s in SEEDS)
    if not mandatory <= set(expected):
        raise ValueError("Source lock missing mandatory inputs")
    for name,wanted in expected.items():
        relative = Path(name)
        if relative.is_absolute() or ".." in relative.parts or sha(ROOT/relative) != wanted:
            raise ValueError("Locked input changed: "+name)
    return expected


def labels(rows):
    a=np.asarray([r["a"] for r in rows],dtype=np.int64)
    b=np.asarray([r["b"] for r in rows],dtype=np.int64)
    target=np.asarray([[int(c) for c in r["target_bits"]] for r in rows],dtype=np.uint8)
    return a,b,target,(a>=b).astype(np.uint8)


def source_cache(output, panel, rows, seed):
    path=output/"source_cache"/f"seed{seed}"/(panel+".npz")
    if path.exists():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    raw=np.asarray([[int(c) for c in r["frame_bits"]] for r in rows],dtype=np.float64)
    source=load_source(seed)
    original={k:v.copy() for k,v in source.items()}
    decoded=decode(source,raw)
    if any(not np.array_equal(source[k],v) for k,v in original.items()):
        raise AssertionError("Source mutated")
    a,b,_,_=labels(rows)
    truth_words=np.column_stack((((a[:,None] >> np.arange(6,-1,-1))&1),((b[:,None] >> np.arange(6,-1,-1))&1)))
    operand_correct=(decoded["pred_a"]==a)&(decoded["pred_b"]==b)
    tuple_correct=operand_correct&(decoded["pred_op"]==np.asarray([r["op"] for r in rows]))
    margin=decoded["operand_logits"]*(2*truth_words.astype(np.float64)-1)
    audit={"seed":seed,"panel":panel,"cases":len(rows),"operand_correct":int(operand_correct.sum()),
        "tuple_correct":int(tuple_correct.sum()),"operand_accuracy":float(operand_correct.mean()),
        "tuple_accuracy":float(tuple_correct.mean()),"minimum_signed_operand_bit_margin":float(margin.min()),
        "median_minimum_row_operand_margin":float(np.median(margin.min(axis=1))),
        "source_parameter_values":1290,"source_dense_mac_per_row":1248,"source_forward_rows":len(rows),
        "source_forward_mac":len(rows)*1248,"source_path":f"sources/receiver_seed{seed}.npz",
        "source_sha256":sha(ROOT/"sources"/f"receiver_seed{seed}.npz"),"source_weights_unchanged":True,
        "created_utc":utc(),"truth_role":"Offline source audit only; cached words are uncorrected actual outputs"}
    np.savez_compressed(path,**decoded,case_ids=np.asarray([r["case_id"] for r in rows]),
        source_operand_correct=operand_correct,source_tuple_correct=tuple_correct,signed_operand_bit_margin=margin,
        metadata_json=np.array(json.dumps(audit,sort_keys=True)))
    return decoded,audit


def subset_metric(correct, selected):
    n=int(selected.sum())
    return {"cases":n,"correct":int(correct[selected].sum()),"accuracy":float(correct[selected].mean()) if n else None}


def save_prediction(path, params, mux, words, rows, arm, seed, step, panel, source=None):
    result=hybrid_forward(params,mux,words)
    a,b,target,selector_target=labels(rows)
    correct=np.all(result["output_bits"]==target,axis=1)
    selector_correct=result["selection"]==selector_target
    answer=result["output_bits"]@BIT_WEIGHTS
    decoded_a=words[:,:7]@BIT_WEIGHTS
    decoded_b=words[:,7:]@BIT_WEIGHTS
    source_ok=(decoded_a==a)&(decoded_b==b)
    z=result["selector_logits"]
    metric={"cases":len(rows),"complete_correct":int(correct.sum()),"complete_accuracy":float(correct.mean()),
        "bit_accuracy":float(np.mean(result["output_bits"]==target)),
        "selector_correct":int(selector_correct.sum()),"selector_accuracy":float(selector_correct.mean()),
        "selector_bce":float(np.mean(np.logaddexp(0,z)-selector_target*z)),
        "minimum_signed_selector_margin":float(np.min(z*(2*selector_target.astype(np.float64)-1))),
        "output_neither_decoded_operand":int(((answer!=decoded_a)&(answer!=decoded_b)).sum()),
        "output_neither_true_operand":int(((answer!=a)&(answer!=b)).sum()),
        "source_operand_correct_cases":int(source_ok.sum()),
        "answer_when_source_correct":subset_metric(correct,source_ok),
        "answer_when_source_incorrect":subset_metric(correct,~source_ok),
        "strata":{name:{"answer":subset_metric(correct,chosen),"selector":subset_metric(selector_correct,chosen)}
            for name,chosen in [("a_lt_b",a<b),("a_gt_b",a>b),("ties",a==b),
                ("source_domain_a_plus_b_lt128",a+b<128),("outside_source_domain",a+b>=128)]+[
                (f"opcode_{op}",np.asarray([r.get("op",-1)==op for r in rows])) for op in range(4)]}}
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(path,**result,targets=target,selector_targets=selector_target,predicted_answer=answer,
        complete_correct=correct,selector_correct=selector_correct,decoded_a=decoded_a,decoded_b=decoded_b,
        case_ids=np.asarray([r["case_id"] for r in rows]),
        metadata_json=np.array(json.dumps({"schema":"handfill-selector-predictions-v1","arm":arm,"seed":seed,
            "step":step,"panel":panel,"metrics":metric,"created_utc":utc()},sort_keys=True)))
    return metric


def run_one(output, arm, seed, panels, caches, mux, batches, lock_hashes):
    folder=output/arm/f"seed{seed}"
    if folder.exists():
        raise FileExistsError(folder)
    folder.mkdir(parents=True)
    params=init_comparator(arm,seed)
    m,v,t=optimizer_state(params)
    _,_,_,selector_train=labels(panels["train"])
    trace=[]
    validation={}
    trained=arm in TRAINED_ARMS
    updates=UPDATES if trained else 0
    schedule=CHECKPOINTS if trained else (0,)
    begun=time.perf_counter()

    def checkpoint(step):
        save_checkpoint(folder/"checkpoints"/f"step_{step:04d}.npz",params,m,v,step,arm,seed,
            {"source_sha256":sha(ROOT/"sources"/f"receiver_seed{seed}.npz"),
             "batch_sha256":sha(ROOT/"batches"/f"seed{seed}.npz"),"lock_hashes":lock_hashes})
        validation[str(step)]=save_prediction(folder/"validation"/f"val_{step:04d}.npz",params,mux,
            caches["val"]["words"],panels["val"],arm,seed,step,"val")
        dump(folder/"training_trace.json",trace)

    checkpoint(0)
    for step in range(1,updates+1):
        ids=batches[step-1]
        value,grads=loss_grads(params,caches["train"]["words"][ids],selector_train[ids])
        t,info=adam_step(params,m,v,t,grads)
        trace.append({"step":step,"optimizer_step":t,"loss":value,**info})
        if step in schedule:
            checkpoint(step)
    first=next((s for s in schedule if validation[str(s)]["complete_accuracy"]>=.95),None)
    confirmed=next((s for prior,s in zip(schedule[:-1],schedule[1:]) if validation[str(prior)]["complete_accuracy"]>=.95 and validation[str(s)]["complete_accuracy"]>=.95),None)
    scores=np.asarray([validation[str(s)]["complete_accuracy"] for s in schedule])
    final_path=folder/"checkpoints"/f"step_{updates:04d}.npz"
    result={"arm":arm,"seed":seed,"status":"trained_test_not_evaluated","gradient_updates":updates,
        "training_presentations":updates*128,"selector_training_forward_mac":updates*128*14,
        "validation":validation,"first_validation_95":first,"first_two_consecutive_validation_95_ending_at":confirmed,
        "validation_accuracy_auc_by_update":float(np.trapezoid(scores,np.asarray(schedule))/UPDATES) if trained else None,
        "minimum_recorded_validation_accuracy":float(scores.min()),"validation_degraded_from_initial_at_recorded_checkpoint":bool(np.any(scores<scores[0])),
        "selector_parameter_values":15,"selector_trainable_parameters":15 if trained else 0,"fixed_copy_numeric_values":63,
        "retained_source_model_values":1290,"retained_inference_model_values":1368,"new_inference_numeric_values":78,
        "gate_connectivity_indices":42,"source_output_reordering_indices":14,
        "new_optimizer_values":30 if trained else 0,"active_new_optimizer_values":30 if trained else 0,
        "checkpoint_serialized_optimizer_values":30,"allocated_optimizer_values":30,
        "frozen_optimizer_note":"The frozen control serializes/allocates30zero optimizer placeholders; no optimizer update is performed." if not trained else None,
        "source_optimizer_provenance_values":2580,
        "validation_inference_rows":len(schedule)*len(panels["val"]),
        "final_checkpoint_path":str(final_path.relative_to(ROOT)),"final_checkpoint_sha256":sha(final_path),
        "source_weights_trained":False,"copy_weights_trained":False,"elapsed_seconds":time.perf_counter()-begun}
    dump(folder/"summary.json",result)
    print(json.dumps({"completed_training":arm,"seed":seed,"updates":updates,"first_validation95":first,
        "validation_final":validation[str(updates)]["complete_accuracy"],"test_evaluated":False}),flush=True)
    return result


def exhaustive_components(output, models, mux):
    # This is an explicit ideal-bit capacity/rule diagnostic, never a source
    # decoding result. It occurs after all models have finished learning.
    a=np.repeat(np.arange(128,dtype=np.int64),128)
    b=np.tile(np.arange(128,dtype=np.int64),128)
    words=np.column_stack(((a[:,None]>>np.arange(6,-1,-1))&1,(b[:,None]>>np.arange(6,-1,-1))&1)).astype(np.uint8)
    rows=[{"case_id":f"ideal_a{int(x):03d}_b{int(y):03d}","a":int(x),"b":int(y),
        "target_bits":format(max(int(x),int(y)),"07b"),"op":-1} for x,y in zip(a,b)]
    dataset_path=output/"component_capacity"/"ideal_words.npz"
    dataset_path.parent.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(dataset_path,a=a,b=b,words=words,case_ids=np.asarray([r["case_id"] for r in rows]))
    endpoints=[]
    for model in models:
        arm,seed=model["arm"],model["seed"]
        steps=(0,UPDATES) if arm in TRAINED_ARMS else (0,)
        for step in steps:
            state=load_checkpoint(output/arm/f"seed{seed}"/"checkpoints"/f"step_{step:04d}.npz")
            metrics=save_prediction(output/"component_capacity"/arm/f"seed{seed}"/f"step_{step:04d}.npz",
                state["params"],mux,words,rows,arm,seed,step,"ideal_component_exhaustive")
            endpoints.append({"arm":arm,"seed":seed,"step":step,"metrics":metrics})
    both_words=np.repeat(words,2,axis=0)
    selection=np.tile(np.asarray([0,1],dtype=np.uint8),len(words))
    gates=mux_forward(mux,both_words,selection)
    # np.where is an audit oracle here only. Model execution above uses gates.
    expected=np.where(selection[:,None]==1,both_words[:,:7],both_words[:,7:])
    correct=np.all(gates["output_bits"]==expected,axis=1)
    np.savez_compressed(output/"component_capacity"/"mux_truth_table.npz",words=both_words,selection=selection,
        **gates,targets=expected,complete_correct=correct)
    report={"scope":"Oracle ideal-word component audit, not actual raw-source generalization; no training feedback",
        "cases_per_endpoint":16384,"endpoints":endpoints,"endpoint_files":len(endpoints),
        "endpoint_forward_rows":len(endpoints)*16384,"endpoint_forward_mac":len(endpoints)*16384*56,
        "mux_only_cases":len(correct),"mux_only_correct":int(correct.sum()),"mux_only_sparse_mac":len(correct)*42,
        "source_decoder_forward_rows":0,"created_utc":utc()}
    dump(output/"component_capacity"/"summary.json",report)
    return report


def run(output, lock_path):
    output=Path(output).resolve()
    lock_hashes=verify_lock(lock_path)
    protocol=json.loads((ROOT/"protocol.json").read_text(encoding="utf-8"))
    config=protocol["training"]
    for key,wanted in {"trained_models":6,"zero_update_controls":3,"updates_per_model":4096,"batch_size":128,
                       "lr":.01,"beta1":.9,"beta2":.999,"eps":1e-8,"clip_global_norm":5.0}.items():
        if config[key]!=wanted:
            raise ValueError("Protocol mismatch: "+key)
    if tuple(config["seeds"])!=SEEDS or tuple(config["checkpoints"])!=CHECKPOINTS or tuple(config["trained_arms"])!=TRAINED_ARMS:
        raise ValueError("Schedule mismatch")
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(output)
    output.mkdir(parents=True,exist_ok=True)
    begun=time.perf_counter()
    metadata={"schema":"handfill-selector-run-v1","status":"running","started_utc":utc(),
        "python":platform.python_version(),"numpy":np.__version__,"source_lock_sha256":sha(lock_path),
        "source_sha256":lock_hashes,"new_source_training_updates":0,"manual_training_interventions":0,
        "external_model_calls":0,"W_calls":0,"test_tuned_continuations":0,"fresh_challenge_inference_before_barrier":0,
        "reused_test_inference_before_barrier":0,"pr132_test_already_known":True,"new_head_updates_budget":24576}
    dump(output/"run_metadata.json",metadata)
    data=json.loads((ROOT/"data.json").read_text(encoding="utf-8"))
    panels=data["panels"]
    mux=load_mux()
    models=[]
    caches={}
    source_audits=[]
    for seed in SEEDS:
        caches[seed]={}
        for panel in ("train","val"):
            caches[seed][panel],audit=source_cache(output,panel,panels[panel],seed)
            source_audits.append(audit)
        with np.load(ROOT/"batches"/f"seed{seed}.npz",allow_pickle=False) as z:
            batches=z["indices"].astype(np.int64)
        if batches.shape!=(4096,128) or batches.min()<0 or batches.max()>=len(panels["train"]):
            raise ValueError("Bad batch stream")
        for arm in ARMS:
            models.append(run_one(output,arm,seed,panels,caches[seed],mux,batches,lock_hashes))
    training_finished=utc()
    barrier={"schema":"handfill-selector-test-barrier-v1","trained_models":6,"zero_update_controls":3,
        "actual_gradient_updates":sum(m["gradient_updates"] for m in models),"training_finished_utc":training_finished,
        "fresh_challenge_inference_rows_so_far":0,"reused_test_inference_rows_this_run_so_far":0,
        "checkpoint_sha256":{m["final_checkpoint_path"]:m["final_checkpoint_sha256"] for m in models}}
    if barrier["actual_gradient_updates"]!=24576:
        raise AssertionError("Incomplete training")
    dump(output/"all_training_completed.json",barrier)
    for seed in SEEDS:
        for panel in ("test","challenge"):
            caches[seed][panel],audit=source_cache(output,panel,panels[panel],seed)
            source_audits.append(audit)
    for model in models:
        arm,seed=model["arm"],model["seed"]
        folder=output/arm/f"seed{seed}"
        state=load_checkpoint(ROOT/model["final_checkpoint_path"])
        for panel in ("train","test","challenge"):
            label="final_train" if panel=="train" else panel
            model[label]=save_prediction(folder/(label+"_predictions.npz"),state["params"],mux,
                caches[seed][panel]["words"],panels[panel],arm,seed,model["gradient_updates"],label)
        model["status"]="completed"
        dump(folder/"summary.json",model)
        print(json.dumps({"evaluated":arm,"seed":seed,"test":model["test"]["complete_accuracy"],
            "challenge":model["challenge"]["complete_accuracy"]}),flush=True)
    capacity=exhaustive_components(output,models,mux)
    if verify_lock(lock_path)!=lock_hashes or any(sha(ROOT[m["final_checkpoint_path"]])!=m["final_checkpoint_sha256"] for m in models):
        raise AssertionError("Inference mutated locked files or final checkpoint")
    source_rows=sum(a["source_forward_rows"] for a in source_audits)
    evaluation_rows=sum(m["validation_inference_rows"]+sum(len(panels[p]) for p in ("train","test","challenge")) for m in models)
    metadata.update(status="completed",finished_utc=utc(),training_finished_utc=training_finished,
        elapsed_seconds=time.perf_counter()-begun,trained_models=6,zero_update_controls=3,
        actual_gradient_updates=sum(m["gradient_updates"] for m in models),
        actual_training_presentations=sum(m["training_presentations"] for m in models),
        actual_selector_training_forward_mac=sum(m["selector_training_forward_mac"] for m in models),
        actual_source_forward_rows=source_rows,actual_source_forward_mac=source_rows*1248,
        actual_hybrid_evaluation_rows=evaluation_rows,actual_hybrid_evaluation_forward_mac=evaluation_rows*56,
        component_endpoint_forward_rows=capacity["endpoint_forward_rows"],component_endpoint_forward_mac=capacity["endpoint_forward_mac"],
        component_mux_only_rows=capacity["mux_only_cases"],component_mux_only_mac=capacity["mux_only_sparse_mac"],
        source_cache_files=len(source_audits),source_cache_bytes=sum(p.stat().st_size for p in (output/"source_cache").glob("seed*/*.npz")),
        checkpoint_files=sum(1 for _ in output.glob("*/seed*/checkpoints/*.npz")),
        source_weights_unchanged=True,copy_weights_unchanged=True)
    dump(output/"summary.json",{"schema":"handfill-selector-results-v1","models":models,"source_audits":source_audits,
        "component_summary":"component_capacity/summary.json","scope":protocol["task"]})
    dump(output/"run_metadata.json",metadata)
    print(json.dumps(metadata),flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,default=ROOT/"results")
    parser.add_argument("--lock",type=Path,default=ROOT/"source_lock.json")
    args=parser.parse_args()
    run(args.output,args.lock)
