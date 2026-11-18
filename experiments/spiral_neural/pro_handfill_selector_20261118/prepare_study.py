"""Prepare immutable inputs and handfilled gates; perform no model inference.

Run once beside feature_transfer_20261118. All subsequent execution/replay is
self-contained. Labels are teachers, never runtime feature replacements.
"""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import numpy as np

ROOT = Path(__file__).resolve().parent
PR132 = ROOT.parent/"feature_transfer_20261118"
SEEDS = (101, 202, 303)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False)+"\n", encoding="utf-8")


def main():
    if any((ROOT/name).exists() for name in ("data.json", "protocol.json", "handfilled_mux.npz", "source_manifest.json")):
        raise FileExistsError("Prepared study already exists; refusing overwrite")
    copied = []
    names = {"data.json": "sources/pr132_data.json", "protocol.json": "sources/pr132_protocol.json",
             "source_lock.json": "sources/pr132_source_lock.json", "sources/codec.py": "sources/codec.py",
             "sources/pr130_data.json": "sources/pr130_data.json", "sources/pr129_data.json": "sources/pr129_data.json"}
    for seed in SEEDS:
        names[f"sources/receiver_seed{seed}.npz"] = f"sources/receiver_seed{seed}.npz"
        names[f"batches/seed{seed}.npz"] = f"batches/seed{seed}.npz"
    for old, new in names.items():
        target = ROOT/new
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(PR132/old, target)
        copied.append({"path": new, "sha256": sha(target), "size_bytes": target.stat().st_size,
                       "source_study": "pro_feature_transfer_20261118_v1", "source_path": old})
    old_data = json.loads((ROOT/"sources/pr132_data.json").read_text(encoding="utf-8"))
    data = json.loads(json.dumps(old_data))
    from sources.codec import make_row
    groups = data["group_splits"]["unused"]
    if len(groups) != 117 or any(a >= b for a, b in groups):
        raise AssertionError("Expected all 117 untouched unequal source groups")
    challenge = []
    for lo, hi in groups:
        for a, b in ((lo, hi), (hi, lo)):
            for op in range(4):
                row = make_row(op, a, b, 7)
                row["source_operation_answer"] = row.pop("answer")
                row["max_answer"] = max(a, b)
                row["target_bits"] = format(max(a, b), "07b")
                row["unordered_pair"] = [lo, hi]
                challenge.append(row)
    data["panels"]["challenge"] = challenge
    data["group_splits"]["challenge"] = groups
    del data["group_splits"]["unused"]
    data["panel_counts"]["challenge"] = len(challenge)
    data["schema"] = "handfill-selector-dataset-v1"
    data["continuation_note"] = "Train/val/test exactly reuse PR132. PR132 test outcomes informed this design; reused test is a continuation benchmark, not pristine independent confirmation. Challenge uses all 117 previously unused unordered groups, fixed before new model inference."
    data["selector_teacher"] = "a>=b (left on ties), explicit additional supervised decision label; inference sees actual source predictions only."
    if len(challenge) != 936:
        raise AssertionError("Wrong challenge frame count")
    for split in ("train", "val", "test"):
        if data["panels"][split] != old_data["panels"][split]:
            raise AssertionError("Prior panel changed")
    if set(map(tuple, groups)) & set(tuple(p) for split in ("train", "val", "test") for p in data["group_splits"][split]):
        raise AssertionError("Challenge group contamination")
    dump(ROOT/"data.json", data)

    l1_indices = np.asarray([[j, 14] for j in range(7)]+[[7+j, 14] for j in range(7)], dtype=np.int16)
    l1_weights = np.asarray([[1., 1.]]*7+[[1., -1.]]*7)
    l1_bias = np.asarray([-1.5]*7+[-.5]*7)
    l2_indices = np.asarray([[j, j+7] for j in range(7)], dtype=np.int16)
    l2_weights = np.ones((7, 2), dtype=np.float64)
    l2_bias = np.full(7, -.5, dtype=np.float64)
    np.savez_compressed(ROOT/"handfilled_mux.npz", layer1_indices=l1_indices, layer1_weights=l1_weights,
        layer1_bias=l1_bias, layer2_indices=l2_indices, layer2_weights=l2_weights, layer2_bias=l2_bias,
        source_word_output_indices=np.asarray([14,15,4,5,6,7,8,16,17,9,10,11,12,13], dtype=np.int16),
        metadata_json=np.array(json.dumps({"schema": "handfilled-sparse-copy-network-v1",
            "threshold": "score>=0", "layer_units": [14, 7], "edge_weights": 42,
            "biases": 21, "numeric_parameters": 63, "gate_connectivity_indices": 42,
            "source_word_reordering_indices": 14, "input_order": "a7MSB,b7MSB,selector(left=1)"}, sort_keys=True)))
    protocol = {
        "schema": "handfill-selector-preregistration-v1", "run": "pro_handfill_selector_20261118_v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "question": "Can a handfilled neural comparator/copy skeleton reuse actual learned word decoding, and does learning a small explicit decision improve on re-learning seven answer bits? Can a correct handfilled decision remain correct when training resumes?",
        "provenance": {"U": "User proposed mature-network growth, SLE word communication between brain regions, permitted temporary disturbance/recovery, and explicitly requests combining training with handfill.",
            "F": "PR130 demand receiver checkpoints inherited via PR132; Fable W candidate raw-bit profile; original Fable handfill work motivates a modular skeleton but its arithmetic weights are not copied here.",
            "A": "Assistant-defined threshold comparator, sparse neural multiplexer, explicit selection supervision, three arms and fixed-budget continuation/fresh challenge protocol.",
            "T": "Preparation performs zero training updates and zero model inference. Execution receipts record later actual work."},
        "source": {"source_study": "PR130", "source_head_commit": "c35ff7d13ae427fc2ed6c5959665d121edd6bf50",
            "source_archive_sha256": "a908a726571d5337cefe71dd193256e656bde8f729a181cf57109d2c93e5b579",
            "delivery_pr132_commit": "c9b8ead87ada2334a10c385639a23793d1561e20",
            "delivery_pr132_archive_sha256": "88afb3c9072a29b90382ab25281757c9e682ae68c37e5d71eb181c9c0a01a855",
            "seeds": list(SEEDS), "arm": "demand", "role": "receiver", "shape": [34,24,18],
            "full_model_values": 1290, "inherited_updates_per_lineage": 5120,
            "inherited_presentations_per_lineage": 655360, "new_source_updates": 0,
            "freezing_scope": "Controlled reuse/initialization study only. Does not impose freezing or zero regression on the user's general growing-network hypothesis."},
        "task": {"name": "fixed_MAX_readout", "raw_input": "34-bit legal n7 Fable W candidate profile",
            "frame": "11110 | 11111110 | op4 0 | a7 0 | b7 0",
            "source_opcodes": {"ADD":12,"XOR":9,"AND":7,"OR":8},
            "opcode_scope": "Existing opcode meanings unchanged; nuisance variation for externally selected MAX readout. No learned task routing or formal MAX opcode is claimed.",
            "output": "Seven answer bits; not a full serialized SLE response",
            "teacher": "True a,b generate selector label a>=b and offline max-answer scoring only. They never replace source-decoded input words.",
            "input_to_new_module": "Actual source logits thresholded and fixed-coordinate reordered into a7MSB,b7MSB. No raw-input bypass, truth correction, parsed true operand input, normalizer, or oracle routing."},
        "data": {"panels": data["panel_counts"], "group_counts": {k: len(v) for k,v in data["group_splits"].items()},
            "reused_test_status": "Continuation benchmark known from PR132, not a fresh independent test",
            "challenge": "All117 previously unused unequal unordered groups, both orders and all4opcodes=936frames; none used by PR129/PR130 sources or PR132 train/val/test. Fixed before model inference; no ties.",
            "split_unit": "Unordered semantic pair, not opcode/order variants", "source_domain": "n7 bounded source support, a+b<128; no unseen numeric vocabulary or unbounded length claim",
            "test_barrier": "No new receiver/model inference on reused test or fresh challenge until all6 trained models finish4096updates. No extension, tuning or reseeding from test/challenge.",
            "truth_usage": "Labels and audits only. Explicit selector supervision is extra task decomposition relative to PR132 answer-bit training."},
        "model": {"arms": ["handfilled_frozen","random_train","handfilled_train"],
            "handfilled_frozen": "Exact comparator+copy, zero updates, actual learned source decoder",
            "random_train": "Random15-value linear comparator trained on explicit selector labels; same fixed copy network and actual learned source decoder",
            "handfilled_train": "Same exact comparator initialization then train its15values with identical batches/optimizer on the SAME MAX selection task; fixed source/copy. This is continuation on one task, not a second conflicting new skill or a continual multi-task preservation test.",
            "comparator": {"weights": [64,32,16,8,4,2,1,-64,-32,-16,-8,-4,-2,-1], "bias": .5,
                "activation": "selector=1[linear_score>=0]", "values": 15, "train_loss": "Binary cross entropy on unthresholded selector logits",
                "random_initialization": "RNG2100000+seed, weights normalstdsqrt(2/15), bias0; no arithmetic weight prior",
                "prior_and_scale": "Exact handfilled weights encode binary significance, comparison and a tie convention; larger initial norm/logit scale than random is part of this engineered initialization, not controlled away."},
            "copy_network": {"architecture": "For each bit, threshold(a_j+s-1.5), threshold(b_j-s-0.5), then threshold(left_j+right_j-0.5)",
                "units": 21, "edge_weights": 42, "biases": 21, "nonzero_numeric_values":63, "connectivity_indices":42,
                "source_reordering_indices":14, "no_python_selection_shortcut": True},
            "per_candidate_account": {"source_values":1290,"new_numeric_values":78,"retained_inference_values":1368,
                "trainable_values_trained_arms":15,"fixed_new_values_trained_arms":63,"new_threshold_units":22,
                "source_dense_mac_per_query":1248,"selector_mac_per_query":14,"copy_sparse_mac_per_query":42,
                "total_forward_mac_per_query":1304,"source_tanh_units":24,"word_bit_thresholds":14,
                "new_optimizer_values_trained_arms":30,"source_optimizer_values_provenance_only":2580,
                "cost_scope": "Actual full18-output source forward includes unused opcode logits. Bias addition, thresholds, tanh, Adam/backward, IO and connectivity storage are reported separately; MAC is not end-to-end runtime cost."}},
        "training": {"trained_models":6,"zero_update_controls":3,"seeds":list(SEEDS),"trained_arms":["random_train","handfilled_train"],
            "updates_per_model":4096,"batch_size":128,"batch_streams":"Exact PR132 saved streams, paired per seed across trained arms",
            "optimizer":"Adam","lr":.01,"beta1":.9,"beta2":.999,"eps":1e-8,"clip_global_norm":5.0,
            "checkpoints":[0,16,64,128,256,512,1024,2048,4096],"early_stop":False,"reseed":False,"test_tuned_continuations":0,
            "normalization":"None; source thresholded bits retained exactly","source_cache":"Shared per-seed decoding for all arms; cache costs counted once and deployment forward cost also reported"},
        "evaluation": {"primary":"Whole seven-bit MAX accuracy; per-seed results, no seed cherry-picking",
            "secondary":["Explicit selector accuracy (ties can differ while MAX remains correct)","first validation95 and first two consecutive checkpoints95", "validation accuracy AUC by update", "final train fit", "source operand/tuple accuracy and signed bit margins", "answer accuracy conditional on source correctness", "failure records and answers neither decoded input", "warmstart regression at recorded checkpoints"],
            "threshold":"95% is a reported progress marker, not a condition to proceed or extend training",
            "component_control":"After all training, exhaustively evaluate every arm/seed initial state and all6 trained final states on all128x128=16384 oracle bit-pairs (15 endpoint files), with a+b<128/outside/tie strata; source decoder is not run. Also evaluate fixed mux on all32768(word-pair,selection)inputs. These diagnose comparator/copy correctness and rule distortion, not actual learned-source generalization. Never tune or extend training from these outcomes.",
            "comparison_limits":"PR132 differs in input interface, supervision, parameter count, arithmetic/copy priors and source-readout use. Improvement cannot isolate SLE encoding superiority or pure information reuse."},
        "execution":{"one_automated_fixed_batch":True,"external_model_calls":0,"W_calls":0,
            "manual_training_interventions":0,"no_formal_queue_change":True,"no_autonomous_growth_claim":True,
            "nvidia_status":"skipped_unavailable", "nvidia_reason":"Root checked: no callable worker or configured OpenRouter/NVIDIA key; actual calls0"},
        "claims_allowed":"Does the tested handfilled/learned hybrid work on specified panels, how efficiently its small comparator learns, and how exact initialization behaves during this training?",
        "claims_forbidden":["SLE beats other encodings without encoding controls","arbitrary-length or arbitrary-task generalization","randomly initialized small models cannot learn","source must always be frozen","zero-old-dip requirement","handfilled function was learned from examples","new test/challenge independence beyond declared split/history"]
    }
    dump(ROOT/"protocol.json", protocol)
    dump(ROOT/"source_manifest.json", {"schema":"handfill-selector-sources-v1","copied":copied,
        "preparation_model_inference_rows":0,"preparation_training_updates":0})
    print(json.dumps({"prepared":str(ROOT),"panel_counts":data["panel_counts"],"source_files":len(copied),
        "training_updates":0,"model_inference_rows":0,"protocol_sha256":sha(ROOT/"protocol.json")}))


if __name__ == "__main__":
    main()
