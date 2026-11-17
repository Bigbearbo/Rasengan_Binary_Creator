# R69 real B-old-skills H86 pretraining result (2026-11-17)

**3/3 B students FAIL the frozen equal-start eligibility gate. This is NOT a LEFT-learning comparison and is NOT evidence that handfilled A learns LEFT faster.**

Public pre-neural freeze commit: `56d5b3b7ff384226681fde4088208dfef2ae87aa` (remote read-back verified). Source artifacts are from ChatGPT Library `/SLE_NN_Exchange/fable_handfilled_h86_bf6e9e84_20261117.zip`. Original Fable sources and handfilled A weights are not republished here.

Frozen run: 151-bit experimental Fable fixed-layout raw input → 41-bit raw NN output including submit; 151→86→41, 16,639 parameters; 16,512 theoretical dense MAC/forward. This **is not a normative SLE-AE1 legal profile certification**. `hand.py` SHA256 `166ef00fce69386f89a1f832785a77e2fb465b3831c5d78854ac85083deceed8`, `compiler.py` SHA256 `bf6e9e84d6b2ddc2462b586fd25c5cb8a2f4fc913bc7803655ccf39591d085ab`, A NPZ SHA256 `97d671b42f735bea818878652a4d209e4dcfec3037049327dcb6014095e4e523`. Historical lost compiler SHA not asserted identical.

One intervention: B fresh random H86 trained on exactly the nine old Fable families with no LEFT, instead of A handfilled H86 at zero training. Seeds 101/202/303; each 4,096 Adam updates, batch64, lr .003, fresh optimizer state, frozen 9-family mixed curriculum. Three seeds: 12,288 actual updates, 786,432 target rows; 12,985,565,184 theoretical training forward dense MAC excluding backprop/inference. Actual original `hand.sets(2603)` gives train/val/test value pools of 96/16/16 (mutually disjoint); val 2,049 exact raw bit Q, test 4,097. Fixed checkpoints 0/256/512/1024/2048/4096; blind test used only at end. Gate is **each** old family full exact output including submit >=95% on validation, not just pooled accuracy.

| Starting H86 | Val total exact | COPY4 val exact | Test total exact | COPY4 test exact | all nine val families >=95% |
|---|---:|---:|---:|---:|---|
| A original handfilled, 0 updates | 2049/2049 | 100% | 4097/4097 | 100% | PASS |
| B seed101, 4096 updates | 2014/2049 | 239/256 = 93.36% | 3990/4097 | 461/512 = 90.04% | FAIL |
| B seed202, 4096 updates | 2003/2049 | 241/256 = 94.14% | 4019/4097 | 465/512 = 90.82% | FAIL |
| B seed303, 4096 updates | 2011/2049 | 243/256 = 94.92% | 4012/4097 | 486/512 = 94.92% | FAIL |

Additional seed202 REVERSE3 val 242/256 =94.53%, also below gate. All 3 B students converge substantially on most old skills but fail strict per-family starting equivalence. No extra seed, extension, LEFT training, H110 A/B/C, or test-driven adjustment is performed in this run.

Independent replay without importing original Fable code: `PASS 18 B saved checkpoints replayed on frozen 2049 raw validation inputs; 3 final test panels 4097 raw inputs; A original replayed both panels`. Full R69 ZIP includes own `run_r69.py`, `verify_r69.py`, raw Q+masked gold bits, first64 batches per B seed, training-stream SHA256 receipts, all 18 B optimizer+RNG checkpoints, and final failure examples. It is stored privately in Library `/SLE_NN_Exchange/archives/sle_nn_r69_fable_b_old_h86_20261117.zip`, ZIP SHA256 `22179e2b944c616d3559195361901dc36c941b788b0340ab58ea9fcb0be94890`, size 4,532,887 bytes. Full replay of A needs the original Fable NPZ in its Library source package; R69 does not republish original private Fable source or weights.

**Prereg erratum**: frozen pre-run text said 94 TR values. Frozen source program `hand.sets(2603)` actually returns 96 values because it adds 126/127 to TR; this was not changed after freeze, and actual split is included in the archive. Preserve the typo as an erratum; do not silently rewrite history.

U: user requested fair handfilled+learning comparison. F: Fable original code and A NPZ. T: three genuinely trained B students and independent replay in this isolated session. A: follow up with a **separately preregistered** B pretraining budget comparison or changed curriculum after establishing fair old-skill start. Neither proposal nor the earlier Fable LEFT single-seed report is mistaken for the full A/B/C result.

No local Windows Codex, NVIDIA, or Gemini call occurred; NVIDIA not enabled via an authorized worker entrypoint here. No merges or other agents' workstreams were changed. Next owner: independent NN research, then Dot for **hash-only** Windows archive transfer.