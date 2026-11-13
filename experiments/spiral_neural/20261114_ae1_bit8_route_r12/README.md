# AE1 bit8 route / R12

Independent scheduled SLE 01 neural study, 2026-11-14; **preregistered gate FAIL 0/3**. See [pre-forward protocol](PREREGISTRATION.md), [source/seed/data freeze](prereg.json), [all 32 legal native-bit cases](cases.jsonl), [exact Python diagnostic](probe.py), [independent NumPy verifier](verify_numpy.py), [raw/result hashes](results.json) and [actual outcomes](RESULTS.md).

No new training. 6 frozen PR55 checkpoints, 192 true next-bit logits, 96 paired one-bit interventions, 2,096,640 theoretical dense forward MAC. All 192/192 logits and 96/96 paired margins independently verified PASS; this is not autonomous full-answer accuracy. Full six source checkpoint states, 192 output vectors, 96 pair records, raw 01, failure cases, independent verifier and SHA256SUMS are supplied only in companion `sle_ae1_bit8_output_route_20261114_r12.zip` (SHA256 `a40a83c28ebb6fbfe2e05b8d11cf1897a0ba56416d53fdf7256aefa12e01e7ee`). Git repository by itself cannot reconstruct source weights.

Preregistration was published at commit `4a24fd9022e94c5f80f338ac87e48cc842dd3f9f` **before** neural inference. To replay after extracting companion ZIP and entering experiment folder:

```sh
python probe.py gate
python probe.py run
python verify_numpy.py
sha256sum -c SHA256SUMS.txt
```

Runtime used Python3 / PyTorch2.10.0+cpu / NumPy2.3.5. New training updates = 0. Validation/test low-bit sets were already inspected historically; they are `diagnostic_val`/`diagnostic_test`, **not blind**. No personal keys, private dialogues or local runtime coordination state in Git. No local Codex/NVIDIA/Gemini calls (each 0). The NVIDIA read-only endpoint was not authorized/available here.

Next owner: independent NN reviewer; next experiment a genuinely new vocabulary split and equal-budget answer-position coverage, not post hoc tuning of this fixed test.
