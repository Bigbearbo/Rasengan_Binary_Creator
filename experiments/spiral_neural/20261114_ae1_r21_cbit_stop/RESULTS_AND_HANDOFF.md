# AE1-R21 — c2→c0 一位元介入與 r1 STOP：真實診斷 PASS（2/3）

2026-11-14，owner: independent SLE01 scheduled neural researcher. **Read `FROZEN_BEFORE_FORWARD.md` first; it was pushed BEFORE any R21 neural forward (commit `c586fcbf10463c5652f618fcd0972e698781e8ff`, immutable).** Then the exact raw manifest and runner were pushed on this separate branch. This PR depends on R20 #69; no merges or changes to Pro/Codex/VM/parser.

## Result and interpretation

The same 6 frozen R19/R20 checkpoints were evaluated at r=1 STOP cursor=6 with the same a,b,d and network, changing only c=2→0 (a *single native 01 input bit*). No neural training, labels used solely for offline STOP scoring and six true preceding answer bits to select cursor. The student does not use previous output *bit values*, only cursor occupancy. R19 is a deliberately hard-masked negative control.

| Set / 3 seeds | R19 c2→c0 (S correctly predicted) | R20 c2→c0 (S correctly predicted) |
| --- | ---: | ---: |
| validation diagnostic, 10 pairs/seed | 30/30 → 30/30 | **14/30 → 29/30** |
| test diagnostic, 10 pairs/seed | 30/30 → 30/30 | **13/30 → 28/30** |
| pooled, 20 pairs/seed | 60/60 → 60/60 | **27/60 → 57/60** |

R20 TEST per-seed: seed101 **4→10/10**, recovered6, regressed0; seed202 **0→8/10**, recovered8, regressed0; seed303 **9→10/10**, recovered1, regressed0. TEST R19 per-seed **10→10/10** and max absolute S-margin delta **0.0** each. Thus the **predeclared PASS gate is met by seeds101 and202**, while seed303 does not reach +3. All validation and test cases and all failures remain in the raw archive.

TEST mean `logit(S)-max(logit(0),logit(1))` change in R20 (seed101/202/303): **+6.5043 / +7.1846 / +2.6405** logits; R19: all **0.0**. E.g. seed202 test a=2,b=24,c2→c0, same r1 native prefix: Q `010100010000100110000000100000110111100` to `010100010000100110000000000000110111100`; S margin **−4.674 → +3.783** and correct STOP flips false→true. This is an observable output sensitivity, not learned general copy.

**Main finding:** r1 STOP access to c exposes an out-of-training-domain c=2 context (r1 teaching c only 0 or 1; 54/60 parent c0 and 6/60 c1; r1 teaching d=0). In these frozen R20 students, c2 at this input slot materially causes many STOP errors; switching only that bit to a taught c0 restores 30/33 previously wrong predictions across both halves. This explains a substantial part of the observed R19→R20 r1 STOP decline on the *exact selected diagnostic panel* without adding a route patch. The same fixed c bit has no effect on R19, as its frozen r1 STOP hard mask predicts. R20 c0 still has 3/60 failures; other unseen contextual factors can remain. This does **not** establish a general causal training mechanism, full-answer correctness, why the optimizer learned this representation, or SLE superiority over ordinary binary. All data are researcher-seen; not independent blind heldout.

## One-variable experiment, prereg, budget

Profile: SLE-AE1-n5-v1. 40 legal native raw01 Q (39 bits), all supplied as `manifest.jsonl`; 20 matched pairs a=0..3, b=24..28, r=1, c=2 vs0, d=3. Validation a0/1, test a2/3, same distribution, not a new blind split. Same 136 previously taught examples/112 unique, original 3 seeds 101/202/303 and 150 epochs/3300 Adam updates *per previously trained model*; R21 made **0 new optimizer updates**.

Exactly **240 new PyTorch student forward calls**, 6 pretrained models ×40 Q, 10,457 parameters per model, 10,920 forward dense MAC each = **2,620,800 inference dense MAC** (no backprop); note 240 batch rows, model executed in six batch-call invocations. NumPy independent forward audit over the same 240 cases, **240/240 argmax and logits agree**, maximum absolute logit difference `5.7220458984375e−6` (tolerance 5e−5), no new Torch passes or gradient updates. All source/checkpoint bytes checked against the prereg SHA256; frozen R20 ZIP SHA256 `9c698971dfd6fe1f89701be99fc2fa592edce006f017efd5c4e89dbdf5671866`.

Original source R19 PR #68, R20 PR #69. R19 STOP mask failure found post hoc in #68 and corrected in #69, neither was modified here. P030–P035 actual experimental branches and Pro #12 UR1 (its real NN training was completed) checked; do not conflate these with the AE1 thread or with P031 shared synthetic question-bank semantics.

## Replay

Git has `FROZEN_BEFORE_FORWARD.md`, `prereg.json`, `manifest.jsonl`, and full **byte-identical** `run_r21.py`. Full R19/R20 model weights, sources and all 240 raw R21 outputs are in companion ZIP; Git alone **cannot** replay from checkpoints. Extract companion ZIP so it contains sibling `r14_source/`, `experiment_r19/`, `experiment_r20/`, `outputs_r19/`, `outputs_r20/`, and this `r21_experiment/` (or copy these four Git files to that experiment folder). With Python 3 + NumPy + PyTorch:

```sh
cd r21_experiment
python run_r21.py gate --source-root ..
python run_r21.py numpy_verify --source-root ..
```

The validation command is read-only (except Python bytecode caching under root). To rerun the 240 student forwards, use a fresh extracted directory without `raw_logits.jsonl` and `results.json`, then run `python run_r21.py diagnose --source-root ..`. It refuses to overwrite the archived raw output. Compare JSON results and SHA rather than assuming exact backend floating-point bytes across hardware.

**Artifact SHA256:** raw 240 student logits `40c3a71e799afc8ac86c7961a1a4cbb05c6c45d11d8e582e4984ea0cefab974f`; results summary `90cef1f2e3ab107e3194f1bd21dab3034cec9dfa936cc71e27dac0a55358f971`; runner `270e248789c4de608e1c612a788fa82525b488b14a8f43a24b239652e820bb70`; manifest `d78c00bc7bf783c3a431a9dad76cee3a666393b634c05f742367e3540dba21b5`. Companion ZIP filename and SHA reported in this run's final Git handoff and conversation after clean verification.

## U/F/T/A and next owner

U: author's independent small neural research goal, retaining SLE native01 and avoiding VM/syntax work. F: historical R19/R20 source, frozen trained weights, R20 diagnostic panel, P030–P035 separately. T: THIS RUN's 240 actual student PyTorch forwards, independently rebuilt NumPy logits, immutable prereg and all source/manifest/checkpoint hashes; prior training unchanged. A: R20 STOP failure has a strong **specific** out-of-exposure c-word effect; exact internal mechanism and transfer to unseen contexts remain low-confidence. NVIDIA **skipped**; no authorized callable external-reviewer endpoint in this runtime, actual calls 0. Local Codex 0, Gemini 0.

**Next owner:** independent NN research worker. Before a new course, check if the 33 original R20 r1 STOP misses can be stratified by c/d exposure and whether distinct new heldout contexts support the same effect. A new genuine training comparison should equalize c-word STOP exposure without hard-coded masks; only after preregistering a new unexamined split and an equal-structure ordinary binary baseline. Do not train on the current researcher-seen panel and later call it blind.
