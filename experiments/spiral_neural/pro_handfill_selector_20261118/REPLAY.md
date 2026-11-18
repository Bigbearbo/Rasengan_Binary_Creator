# Replaying this immutable experiment

Run: `pro_handfill_selector_20261118_v1`; public Draft PR133.

The archive contains all source checkpoints, raw frames, splits, batch indices, sparse neural gates, trained checkpoints, successes/failures, and an independent NumPy verifier. Verification needs Python3 and NumPy; the recorded run used Python3.12.14 and NumPy2.3.5. `verify_results.py` imports no model or trainer. It recomputes all saved predictions and only the first16updates of each trained model (96verificationrecurrences); it does not add experimental learning or rerun all4,096updates.

The public `replay_archive.py` entry pins this ZIP's byte count and SHA256, checks CRC and every payload hash, extracts to a temporary directory, restores original nanosecond modification times from `payload_manifest.json`, preserves the archived audit receipt, and invokes the independent verifier. It never modifies the ZIP or original experiment directory.

```bash
python replay_archive.py /absolute/path/sle_handfill_selector_20261118_v1.zip --receipt /absolute/path/new_replay_receipt.json
```

For offline inspection, all verifier source and inputs are in the archive. Use a NEW disposable extraction: validate payload hashes, restore each file's `mtime_ns` from `payload_manifest.json`, rename the extracted `receipts/result_audit.json` to `result_audit_recorded.json`, then run `python verify_results.py` from that extracted root. The verifier refuses to overwrite an existing audit receipt. ZIP timestamps alone have insufficient precision for its test-barrier file-order checks.

## Recorded end-of-run exception

The original locked `run_train.py` is retained exactly as executed. All24,576updates and all raw-frame/component predictions completed; a Path subscription typo in the final checkpoint-hash check then raised TypeError before the global summary was written. `training_stderr.log`, the original running metadata and all model outputs are preserved. `finalize_existing.py` validated saved inputs/outputs and recovered metadata with zero additional inference or updates. Status is explicitly `completed_after_metadata_recovery`.

Replaying saved results does not run the original trainer or finalizer. The original trainer is forensic evidence, not an error-free training entry to run casually over the delivered directory. A future training study should start in a new directory with a separately reviewed correction and new source lock. Neither the verifier nor the finalizer silently extends the existing experiment.

`prepare_study.py` originally copied source materials from the sibling PR132 directory. Its required copied outputs are already included, so verification has no sibling-repository dependency and preparation must not be rerun over these inputs.

## Scope

PR132 train/validation/test are reused; the test is a continuation benchmark. The936-frame challenge is117 previously unused unordered pairs. Ideal-word exhaustive diagnostics bypass the source only to test the comparator/copy component; they are separately identified and are not raw-frame source generalization. The fixed MAX readout is selected externally, using the declared Fable W candidate profile. Original operation codes are not redefined.

The payload manifest excludes its own hash. The complete ZIP hash/size are pinned outside the ZIP in the public entry and handoff. Reports and old source artifacts are not modified during replay.
