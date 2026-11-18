"""Describe saved predictions without new inference, training, or checkpoint edits."""
from __future__ import annotations
from collections import Counter
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_prediction(path):
    with np.load(path,allow_pickle=False) as z:
        return {k:z[k].copy() for k in z.files if k!="metadata_json"},json.loads(str(z["metadata_json"]))


def main():
    output=ROOT/"posthoc_analysis.json"
    failure_path=ROOT/"posthoc_final_pipeline_failures.jsonl"
    if output.exists() or failure_path.exists():
        raise FileExistsError("Posthoc analysis already exists")
    summary=json.loads((ROOT/"results/summary.json").read_text(encoding="utf-8"))
    run=json.loads((ROOT/"results/run_metadata.json").read_text(encoding="utf-8"))
    if run["status"] not in ("completed","completed_after_metadata_recovery"):
        raise ValueError("Experimental run is incomplete")
    panels=json.loads((ROOT/"data.json").read_text(encoding="utf-8"))["panels"]
    component=json.loads((ROOT/"results/component_capacity/summary.json").read_text(encoding="utf-8"))
    component_map={(x["arm"],x["seed"],x["step"]):x["metrics"] for x in component["endpoints"]}
    models=[]
    failure_counts=Counter()
    with failure_path.open("x",encoding="utf-8") as fh:
        for model in summary["models"]:
            arm,seed,step=model["arm"],model["seed"],model["gradient_updates"]
            folder=ROOT/"results"/arm/f"seed{seed}"
            record={"arm":arm,"seed":seed,"updates":step,"first_validation95":model["first_validation_95"],
                "first_two_consecutive_validation95":model["first_two_consecutive_validation_95_ending_at"],
                "final_train_accuracy":model["final_train"]["complete_accuracy"],
                "final_validation_accuracy":model["validation"][str(step)]["complete_accuracy"],
                "reused_test_accuracy":model["test"]["complete_accuracy"],
                "fresh_challenge_accuracy":model["challenge"]["complete_accuracy"],
                "validation_regressed_from_initial":model["validation_degraded_from_initial_at_recorded_checkpoint"],
                "minimum_recorded_validation_accuracy":model["minimum_recorded_validation_accuracy"],
                "validation_auc":model["validation_accuracy_auc_by_update"],
                "final_pipeline_failure_counts":{},"error_distance_counts":{}}
            for panel,path in (("train",folder/"final_train_predictions.npz"),
                               ("val",folder/"validation"/f"val_{step:04d}.npz"),
                               ("test",folder/"test_predictions.npz"),
                               ("challenge",folder/"challenge_predictions.npz")):
                predicted,_=read_prediction(path)
                rows=panels[panel]
                if predicted["case_ids"].tolist()!=[r["case_id"] for r in rows]:
                    raise AssertionError("Prediction rows differ")
                failed=np.flatnonzero(~predicted["complete_correct"])
                record["final_pipeline_failure_counts"][panel]=len(failed)
                distance_counts=Counter()
                for i in failed:
                    row=rows[int(i)]
                    delta=abs(row["a"]-row["b"])
                    bucket=next((label for ceiling,label in ((0,"tie"),(1,"gap1"),(2,"gap2"),(4,"gap3to4"),(8,"gap5to8"),(16,"gap9to16"),(127,"gap17plus")) if delta<=ceiling))
                    distance_counts[bucket]+=1
                    source_ok=(int(predicted["decoded_a"][i])==row["a"] and int(predicted["decoded_b"][i])==row["b"])
                    failure={"arm":arm,"seed":seed,"step":step,"panel":panel,"case_id":row["case_id"],
                        "raw_frame_bits":row["frame_bits"],"source_op_index":row["op"],"a":row["a"],"b":row["b"],
                        "target_max":row["max_answer"],"target_bits":row["target_bits"],
                        "decoded_a":int(predicted["decoded_a"][i]),"decoded_b":int(predicted["decoded_b"][i]),
                        "selector_logit":float(predicted["selector_logits"][i]),"selection":int(predicted["selection"][i]),
                        "target_selection_left_on_tie":int(row["a"]>=row["b"]),
                        "predicted_answer":int(predicted["predicted_answer"][i]),
                        "predicted_bits":"".join(map(str,predicted["output_bits"][i].tolist())),
                        "source_operands_correct":source_ok,
                        "stage_annotation":"comparator/copy output wrong despite correct decoded operands" if source_ok else "source operand error exposed; no oracle correction"}
                    fh.write(json.dumps(failure,ensure_ascii=False,sort_keys=True)+"\n")
                    failure_counts[f"{arm}/{panel}"]+=1
                record["error_distance_counts"][panel]=dict(distance_counts)
            initial,_=read_prediction(ROOT/"results/component_capacity"/arm/f"seed{seed}"/"step_0000.npz")
            final,_=read_prediction(ROOT/"results/component_capacity"/arm/f"seed{seed}"/f"step_{step:04d}.npz")
            record["component_initial_accuracy"]=component_map[(arm,seed,0)]["complete_accuracy"]
            record["component_final_accuracy"]=component_map[(arm,seed,step)]["complete_accuracy"]
            record["component_changed_selection_count"]=int(np.count_nonzero(initial["selection"]!=final["selection"]))
            record["component_changed_answer_count"]=int(np.count_nonzero(initial["predicted_answer"]!=final["predicted_answer"]))
            record["component_initial_correct_final_wrong_count"]=int(np.count_nonzero(initial["complete_correct"]&~final["complete_correct"]))
            record["component_initial_wrong_final_correct_count"]=int(np.count_nonzero(~initial["complete_correct"]&final["complete_correct"]))
            record["component_final_strata"]=component_map[(arm,seed,step)]["strata"]
            with np.load(folder/"checkpoints/step_0000.npz",allow_pickle=False) as z:
                initial_values=np.concatenate([z["param_w"],z["param_b"]])
            with np.load(folder/"checkpoints"/f"step_{step:04d}.npz",allow_pickle=False) as z:
                final_values=np.concatenate([z["param_w"],z["param_b"]])
            record["initial_selector_values"]=initial_values.tolist()
            record["final_selector_values"]=final_values.tolist()
            record["selector_parameter_l2_change"]=float(np.linalg.norm(final_values-initial_values))
            record["selector_weight_cosine_to_initial"]=float(np.dot(initial_values[:14],final_values[:14])/(np.linalg.norm(initial_values[:14])*np.linalg.norm(final_values[:14])))
            models.append(record)
    result={"schema":"handfill-selector-posthoc-v1","created_utc":datetime.now(timezone.utc).isoformat(),
        "status":"POSTHOC_DESCRIPTIVE_NO_FEEDBACK","new_model_inference_rows":0,"new_training_updates":0,
        "source_results_sha256":sha(ROOT/"results/summary.json"),"models":models,
        "failure_file":failure_path.name,"failure_file_sha256":sha(failure_path),
        "failure_records":sum(failure_counts.values()),"failure_counts":dict(failure_counts),
        "failure_scope":"Every incorrect final pipeline output on train, val, reused test, and fresh challenge; all checkpoint successes/failures remain in complete NPZ predictions.",
        "interpretation_limits":["Same-task warmstart continuation cannot establish preservation under learning a second conflicting task.",
            "Component oracle bits isolate comparator/copy function; they are not actual source decoding success.",
            "No new parameters, updates, batches or hyperparameters were chosen from these summaries."]}
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"saved":str(output),"failure_records":result["failure_records"],
        "rows":[{k:r[k] for k in ("arm","seed","final_train_accuracy","final_validation_accuracy","reused_test_accuracy","fresh_challenge_accuracy","component_final_accuracy")} for r in models]}))


if __name__=="__main__":
    main()
