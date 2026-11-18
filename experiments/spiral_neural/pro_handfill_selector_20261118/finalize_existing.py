"""Recover final metadata only after a preserved end-of-run Path-join exception.

This module does not import the model/trainer, perform network inference, or
update any weights. Every scientific output already exists. It preserves the
original running metadata and recorded failure, verifies fixed inputs and
completed output inventory, and reconstructs only missing summary/accounting.
"""
from __future__ import annotations
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parent
RESULTS=ROOT/"results"
SEEDS=(101,202,303)
ARMS=("handfilled_frozen","random_train","handfilled_train")
STEPS=(0,16,64,128,256,512,1024,2048,4096)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def dump(path,obj):
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf-8")


def main():
    receipts=ROOT/"receipts"
    original_copy=receipts/"run_metadata_before_recovery.json"
    receipt_path=receipts/"metadata_recovery.json"
    if original_copy.exists() or receipt_path.exists() or (RESULTS/"summary.json").exists():
        raise FileExistsError("Recovery already attempted or completed")
    original_bytes=(RESULTS/"run_metadata.json").read_bytes()
    original=json.loads(original_bytes)
    if original["status"]!="running":
        raise ValueError("Only preserved running metadata can be finalized")
    lock=read_json(ROOT/"source_lock.json")
    expected=lock["source_sha256"]
    if len(expected)!=20 or expected!=original["source_sha256"]:
        raise ValueError("Unexpected source lock")
    for name,digest in expected.items():
        rel=Path(name)
        if rel.is_absolute() or ".." in rel.parts or sha(ROOT/rel)!=digest:
            raise ValueError("Locked file changed: "+name)
    if sha(ROOT/"source_lock.json")!=original["source_lock_sha256"]:
        raise ValueError("Lock bytes changed")
    stderr=ROOT/"training_stderr.log"
    error=stderr.read_text(encoding="utf-8")
    if "TypeError: 'PosixPath' object is not subscriptable" not in error or 'final_checkpoint_path' not in error:
        raise ValueError("Unexpected failure; refusing metadata-only recovery")
    barrier=read_json(RESULTS/"all_training_completed.json")
    if (barrier["actual_gradient_updates"]!=24576 or barrier["trained_models"]!=6
            or barrier["zero_update_controls"]!=3 or len(barrier["checkpoint_sha256"])!=9):
        raise ValueError("Training barrier incomplete")
    for name,digest in barrier["checkpoint_sha256"].items():
        if sha(ROOT/name)!=digest:
            raise ValueError("Final checkpoint changed")
    data=read_json(ROOT/"data.json")
    panels=data["panels"]
    expected_counts={"train":8240,"val":2096,"test":3120,"challenge":936}
    if {p:len(rows) for p,rows in panels.items()}!=expected_counts:
        raise ValueError("Unexpected dataset counts")
    before={str(p.relative_to(ROOT)):sha(p) for p in RESULTS.rglob("*") if p.is_file()}
    models=[]
    source_audits=[]
    expected_checkpoints=[]
    expected_predictions=[]
    for seed in SEEDS:
        for panel in expected_counts:
            path=RESULTS/"source_cache"/f"seed{seed}"/(panel+".npz")
            with np.load(path,allow_pickle=False) as z:
                meta=json.loads(str(z["metadata_json"]))
                if (z["words"].shape!=(expected_counts[panel],14) or z["logits"].shape!=(expected_counts[panel],18)
                        or z["hidden"].shape!=(expected_counts[panel],24)
                        or z["case_ids"].tolist()!=[r["case_id"] for r in panels[panel]]
                        or meta["seed"]!=seed or meta["panel"]!=panel or meta["cases"]!=expected_counts[panel]):
                    raise ValueError("Incomplete source cache")
            if panel in ("test","challenge") and datetime.fromisoformat(meta["created_utc"])<datetime.fromisoformat(barrier["training_finished_utc"]):
                raise ValueError("Heldout cache predates training barrier")
            source_audits.append(meta)
        for arm in ARMS:
            folder=RESULTS/arm/f"seed{seed}"
            model=read_json(folder/"summary.json")
            steps=(0,) if arm=="handfilled_frozen" else STEPS
            final=steps[-1]
            if (model["arm"]!=arm or model["seed"]!=seed or model["gradient_updates"]!=final
                    or model["status"]!="completed" or model["final_checkpoint_sha256"]!=barrier["checkpoint_sha256"][model["final_checkpoint_path"]]):
                raise ValueError("Incomplete per-model summary")
            trace=read_json(folder/"training_trace.json")
            if len(trace)!=final or any(item["step"]!=i or item["optimizer_step"]!=i for i,item in enumerate(trace,1)):
                raise ValueError("Incomplete training trace")
            for step in steps:
                path=folder/"checkpoints"/f"step_{step:04d}.npz"
                expected_checkpoints.append(path)
                with np.load(path,allow_pickle=False) as z:
                    meta=json.loads(str(z["metadata_json"]))
                    if meta["step"]!=step or meta["arm"]!=arm or meta["seed"]!=seed or z["param_w"].shape!=(14,) or z["param_b"].shape!=(1,):
                        raise ValueError("Bad checkpoint")
                expected_predictions.append((folder/"validation"/f"val_{step:04d}.npz","val",step,arm,seed))
            for panel in ("train","test","challenge"):
                label="final_train" if panel=="train" else panel
                expected_predictions.append((folder/(label+"_predictions.npz"),panel,final,arm,seed))
            models.append(model)
    for path,panel,step,arm,seed in expected_predictions:
        with np.load(path,allow_pickle=False) as z:
            meta=json.loads(str(z["metadata_json"]))
            if (z["output_bits"].shape!=(expected_counts[panel],7) or z["selector_logits"].shape!=(expected_counts[panel],)
                    or z["case_ids"].tolist()!=[r["case_id"] for r in panels[panel]]
                    or meta["arm"]!=arm or meta["seed"]!=seed or meta["step"]!=step
                    or meta["metrics"]["complete_correct"]!=int(z["complete_correct"].sum())):
                raise ValueError("Incomplete pipeline prediction")
    capacity=read_json(RESULTS/"component_capacity/summary.json")
    if (capacity["endpoint_files"]!=15 or capacity["cases_per_endpoint"]!=16384 or len(capacity["endpoints"])!=15
            or capacity["mux_only_cases"]!=32768 or capacity["mux_only_correct"]!=32768):
        raise ValueError("Incomplete component summary")
    for endpoint in capacity["endpoints"]:
        path=RESULTS/"component_capacity"/endpoint["arm"]/f"seed{endpoint['seed']}"/f"step_{endpoint['step']:04d}.npz"
        with np.load(path,allow_pickle=False) as z:
            meta=json.loads(str(z["metadata_json"]))
            if z["output_bits"].shape!=(16384,7) or meta["metrics"]!=endpoint["metrics"]:
                raise ValueError("Incomplete component endpoint")
    with np.load(RESULTS/"component_capacity/mux_truth_table.npz",allow_pickle=False) as z:
        if z["output_bits"].shape!=(32768,7) or int(z["complete_correct"].sum())!=32768:
            raise ValueError("Incomplete mux control")
    if len(expected_checkpoints)!=57 or len(expected_predictions)!=84 or len(source_audits)!=12:
        raise ValueError("Wrong output inventory")
    observed_counts={"checkpoints":len(list(RESULTS.glob("*/seed*/checkpoints/*.npz"))),
        "validation_predictions":len(list(RESULTS.glob("*/seed*/validation/*.npz"))),
        "final_train_predictions":len(list(RESULTS.glob("*/seed*/final_train_predictions.npz"))),
        "test_predictions":len(list(RESULTS.glob("*/seed*/test_predictions.npz"))),
        "challenge_predictions":len(list(RESULTS.glob("*/seed*/challenge_predictions.npz"))),
        "source_caches":len(list(RESULTS.glob("source_cache/seed*/*.npz"))),
        "component_endpoints":len(list(RESULTS.glob("component_capacity/*/seed*/*.npz")))}
    if observed_counts!={"checkpoints":57,"validation_predictions":57,"final_train_predictions":9,"test_predictions":9,
                         "challenge_predictions":9,"source_caches":12,"component_endpoints":15}:
        raise ValueError("Unexpected extra/missing outputs")
    source_rows=sum(a["source_forward_rows"] for a in source_audits)
    evaluation_rows=sum(m["validation_inference_rows"]+sum(expected_counts[p] for p in ("train","test","challenge")) for m in models)
    now=datetime.now(timezone.utc).isoformat()
    span=(datetime.fromisoformat(capacity["created_utc"])-datetime.fromisoformat(original["started_utc"])).total_seconds()
    if span<0:
        raise ValueError("Invalid time ordering")
    metadata=dict(original)
    metadata.update(status="completed_after_metadata_recovery",finished_utc=capacity["created_utc"],
        metadata_recovered_utc=now,training_finished_utc=barrier["training_finished_utc"],
        elapsed_seconds=span,elapsed_seconds_method="UTC timestamp span from run start to saved component summary; original perf_counter value lost at metadata exception",
        original_perf_counter_elapsed_seconds=None,trained_models=6,zero_update_controls=3,
        actual_gradient_updates=sum(m["gradient_updates"] for m in models),
        actual_training_presentations=sum(m["training_presentations"] for m in models),
        actual_selector_training_forward_mac=sum(m["selector_training_forward_mac"] for m in models),
        actual_source_forward_rows=source_rows,actual_source_forward_mac=source_rows*1248,
        actual_hybrid_evaluation_rows=evaluation_rows,actual_hybrid_evaluation_forward_mac=evaluation_rows*56,
        component_endpoint_forward_rows=capacity["endpoint_forward_rows"],component_endpoint_forward_mac=capacity["endpoint_forward_mac"],
        component_mux_only_rows=capacity["mux_only_cases"],component_mux_only_mac=capacity["mux_only_sparse_mac"],
        source_cache_files=12,source_cache_bytes=sum(p.stat().st_size for p in (RESULTS/"source_cache").glob("seed*/*.npz")),
        checkpoint_files=57,source_weights_unchanged=True,copy_weights_unchanged=True,
        recovery_new_training_updates=0,recovery_new_model_inference_rows=0,
        recovery_note="All training and saved pipeline/component inference completed; final locked trainer failed only at Path joining in its final checkpoint hash check. Separate saved-output-only finalizer validated hashes and reconstructed missing metadata. Locked trainer, barrier, checkpoints and predictions remain unchanged.")
    receipts.mkdir(exist_ok=True)
    original_copy.write_bytes(original_bytes)
    dump(RESULTS/"summary.json",{"schema":"handfill-selector-results-v1","models":models,"source_audits":source_audits,
        "component_summary":"component_capacity/summary.json","scope":read_json(ROOT/"protocol.json")["task"],
        "finalization_status":"reconstructed_from_complete_saved_outputs_after_metadata_exception"})
    dump(RESULTS/"run_metadata.json",metadata)
    unchanged={name:digest for name,digest in before.items() if name!="results/run_metadata.json"}
    if any(sha(ROOT/name)!=digest for name,digest in unchanged.items()) or any(sha(ROOT/name)!=digest for name,digest in expected.items()):
        raise AssertionError("Recovery changed scientific files")
    receipt={"schema":"handfill-selector-metadata-recovery-v1","status":"PASS_METADATA_ONLY_RECOVERY",
        "created_utc":now,"known_exception":"TypeError from ROOT[final_checkpoint_path] in final hash check; no training/inference code repaired or re-executed",
        "finalizer_sha256":sha(Path(__file__)),"locked_files_verified":len(expected),
        "source_lock_sha256":sha(ROOT/"source_lock.json"),"final_checkpoint_hashes_verified":9,
        "output_inventory":observed_counts,"preserved_scientific_file_count":len(unchanged),
        "preserved_scientific_sha256":unchanged,"training_stderr_sha256":sha(stderr),
        "original_run_metadata_sha256":sha(original_copy),"new_run_metadata_sha256":sha(RESULTS/"run_metadata.json"),
        "reconstructed_summary_sha256":sha(RESULTS/"summary.json"),"new_training_updates":0,"new_model_inference_rows":0,
        "new_weight_updates":0,"elapsed_timestamp_span_seconds":span,"lost_perf_counter_elapsed_seconds":None,
        "timing_limit":"8-place timestamp arithmetic is a wall timestamp span, not a retained perf_counter benchmark; recovery and subsequent verification time are excluded."}
    dump(receipt_path,receipt)
    print(json.dumps({"status":receipt["status"],"output_inventory":observed_counts,"updates":metadata["actual_gradient_updates"],
        "recovery_new_updates":0,"recovery_new_inference":0,"elapsed_timestamp_span_seconds":span,
        "receipt":str(receipt_path)}))


if __name__=="__main__":
    main()
