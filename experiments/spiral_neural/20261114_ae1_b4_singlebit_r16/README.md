# R16 — SLE-AE1 b-bit4 paired neural diagnostic

Independent native-01 NN experiment, 2026-11-14. Read [frozen protocol](FROZEN_BEFORE_RUN.md), [six raw input cases](manifest.jsonl), [actual failed results](RESULTS.md), and [public NumPy replay](PUBLIC_REPLAY.py). No Hamster VM/UR1 training modifications.

Requires separately provided companion ZIP `sle_ae1_b4_singlebit_r16_20261114.zip` SHA256 `a7c941e60e8ae76cbbf362ac67bf75cf949811ae385b7dc8ac9fbb42df22ecc9` containing nine unchanged original F32 checkpoints and all 54 raw outputs. Git-only checkout does not reproduce NN output without these bytes.

After clean companion ZIP extraction, commands actually checked:
```bash
python run_r16.py gate
python run_r16.py infer
python verify_numpy_r16.py
python PUBLIC_REPLAY.py
```
Static gate PASS; 54 actual full NN outputs, 702 forward; independent NumPy PASS 54/54. No optimizer updates; original R14 training and PR #63 unchanged. Avoid rerunning inference in the authoritative evidence copy, as it regenerates output files; use a disposable extraction.

Owner: independent SLE small NN. Next owner: same workstream, independent correct-prefix sensitivity diagnostic. Source provenance U/F/T/A separated in RESULTS. Not automatically merged.