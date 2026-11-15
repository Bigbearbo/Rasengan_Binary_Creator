# R55 preregistration — BEFORE model training or new evaluation

owner: independent SLE native-01 small-neural research worker
parent: PR #105 head `fcdd81c85a644f6a28aeb28253cf5afd9c6e0ef3`
status: FROZEN; this is **not** a result, not a model run, and not a merging request.

## Single intervention

Use R52 learned static cursor-by-source gates and its frozen R50 backbone as control. Keep **10,457 backbone weights and all 8 R52 gate intercept logits frozen**. Add only eight trainable source-value slopes (two output-word cursor regions × four source words); each gate logit is R52 intercept + slope × (legal input numeric value − 14.5)/14.5. Slopes initialize to zero, so the first model forward is algebraically R52. No external correct-source selection at inference. This is **value-conditioned gating**, not general semantic routing.

Legal data: `SLE-AE1-n5-v1`, numeric operands 0..29; raw Q is `01+010+bin3(r)+0+4*(bin5(v)+0)+111100` (39 actual 0/1 bits). Raw answer is r encoded 6-bit native SLE word(s) plus **external** STOP class S, not a wire SLE terminator. r=1 or 2. Do not use LLM/teacher oracle for student generation.

Source local archive: R54 ZIP SHA256 `9aec51c9f7b2e4e48d33ea02af37fd26c5a2438a220bd00aa650058be110fc72`; verified source archive 325/325 items. Sources: R50, R52 and R54 archived checkpoint, frozen runner and original 136-event course. Train 1,272 first/second-word non-STOP prefix targets, no heldout Q.

Splits fixed **before training**: 32 novel exact-Q validation, 64 novel exact-Q test (each half r1/r2); seeded generator `55161116` uniform legal operands 0..29 rejecting Q already present in archived JSONL. Separately 80 exposed historical retention Q. Exact Q are new; operand values and semantic operation **are not globally unseen**. Three seeds 101,202,303. All splits descriptive; no selection or extended training after reading metrics.

Optimizer: Adam lr0.04; 500 updates × batch64 per seed, deterministic samples with replacement `default_rng(seed+55001)`; 1,500 total updates, 96,000 supervised target presentations. Base dense forward theoretical MAC 1,048,320,000; gate operations and backward MAC separate/unestimated. Parameters per student: 10,457 frozen backbone +8 frozen intercepts +8 new slopes =10,473 total (8 trainable). No early stopping, no extra epochs.

## Prespecified ALL-gate

Against frozen R52 predictions on the same 64 fresh exact-Q test examples ×3 seed (192 cases):
1. R55 complete answer incl autonomous STOP >= R52 + 8 cases
2. Firstword correct R55 >= R52 − 6 cases
3. r2 secondword correct R55 >= R52 − 6 out of 96
4. Historical 80×3 full retention R55 >= R52 − 12
5. Absolute value of at least one learned slope exceeds 0.1 for every seed
6. Independent NumPy full generation replay all 528 R55 Q×seed and PyTorch replay match

All six gates must pass; negative results preserved. Record gains **and** regressions, per-seed, split, exact raw 01 answers, stop cause, actual forward calls, and no test tuning.

## SHA freeze (local original artifacts)

`r55_prereg.json` SHA256: `ac8a59b04a6cf1a579e7ee56a98f2c2984c1c64dee8902ed7e641d71797c148e`
`r55_manifest.jsonl` SHA256: `fd480fd1f8d1e88309fa7476b2be7721de7aca61f4c96b8ce6ac0870ae0f7fd8`
`r55_value_conditioned_gate.py` SHA256: `abb5b92bf840653d5da8ca01fba9e66c91efe86e6596018dd74915784fb9403a`

U: user experimental priorities and constraints. F: prior Git/ZIP checkpoints. T before freeze: archive 325/325 SHA check, static legal manifest and train-array check only; **no new neural evaluation or optimizer update**. A: slopes may suppress nuisance input without destroying retention; low confidence.

NVIDIA calls 0, no callable authorized worker/credentials; Codex/Gemini calls 0. Do not touch Pro UR1, Codex P030–P035, parser, Hamster VM, or existing worker branches. No auto-merge.
