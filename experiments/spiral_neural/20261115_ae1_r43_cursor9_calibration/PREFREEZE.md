# R43 pre-inference freeze — raw 01 output-bit threshold calibration

**Status:** PRE-INFERENCE / STATIC GATE ONLY. Do not interpret this commit as completed student inference or training. Branch base: PR #93 head `e32a5cbcd6354379348ec8cc9961dfb93b0c6410`. Owner: independent scheduled small-NN researcher. Scope distinct from Codex PR #90 (whole-answer 321-dim design), P030–P035 and Pro UR1 #12.

## One and only intervention
Apply ONE *external*, per-checkpoint scalar decision-margin translation at answer cursor 9 (the second word's information bit `2^1`), namely `logit[1] -= tau`; all trained neural weights, routing masks, all other token logits, architecture, data and 01 wire grammar unchanged. No Adam updates, no new student parameters. Calibration **does read teacher-provided labels on old R42 contexts**; it is an externally supervised diagnostic, **not evidence the NN itself learned**. Source checkpoints are unchanged R38 and R41 seeds 101/202/303, 10,457 parameters each. Profile `SLE-AE1-n5-v1` numerical 0–29, NOT 30/31; 39 raw bits `01+010+bin3(2)+0+4*(bin5(v)+0)+111100`, answer two 6-bit value words plus external STOP S. S is not part of SLE wire.

## Splits & immutable schedule
- Historical student training: R38/R41 136 events, 150 epochs, 3300 Adam steps/student. R43: **0 training updates; 0 training-forward MAC**.
- Calibration/validation: existing R42 `raw_edges.jsonl` b24/25→b26/27 bit-2^1 edges on 8 *previously viewed* contexts, separately for each of 6 checkpoints. `tau=(maximum low-end logit1−logit0 + minimum high-end logit1−logit0)/2`. No examination of R43 test to choose tau.
- Test: a∈{8,9,14,15}; (c,d)∈{(12,14),(13,15)}; b∈{18,19,20,21,22,23,24,25,26,27}; r=2; total **80 legal previously untested raw Q** per checkpoint, 3 seeds ×2 arms = 480 paired baseline-vs-calibrated question comparisons. Previously studied *numeric values*: never call globally blind new values. The script asserts no identical Q in previous manifest(s) or R38 lesson questions.
- Model resource: 10,457 fixed weights/checkpoint + one separate calibration scalar/checkpoint. 10,920 theoretical forward dense MAC/call. Full autonomous generation max32 actions; second-word generation additionally tested after **true firstword prefix** as a separate diagnostic, as well as the teacher-forced single bit. Both original and corrected full outputs recorded. Real inference calls and MAC counted after run.
- No epoch/seed selection, test-driven tuning, follow-up training or new profile approval. **NVIDIA calls 0**: no authorized local live OpenRouter worker; local Codex calls 0. Pro UR1 manifest SHA not approved and not used.

## Precommitted R41 joint gate (all five required)
1. b24/25 true-prefix cursor-9 classification correct ≥42/48.
2. b24/25 second word correct when only the first answer word is provided ≥24/48.
3. Previously taught b18/19/26/27 cursor-9 true-prefix correctness decline ≤0 (from fresh matched baseline).
4. Previously taught b18/19/26/27 seeded-secondword retention decline ≤0.
5. b24/25 fully autonomous secondword accuracy gain ≥6/48, without providing the firstword prefix. Report separate full-answer exact and R38 replication even if gate fails.

## Local source/manifest lock (computed BEFORE new R43 NN forward)
- `r43_bias_calibration.py` SHA256 `61e68745c133626ac145b0ae9c6db7693b681ce9dbaba46105db5ce1c15e9940`.
- `r43_prereg.json` SHA256 `886def47028cbcb4873ddd49cfe0081034d07ededbd4c74afca28b7eb3aa7bdf`.
- `r43_manifest.jsonl` SHA256 `75f569d68edce870b4c1c8d9a9d8afa07425f88a10431222b9763fb465a0d568`.
- Exact frozen 6 source-checkpoint SHA256 values, existing R42 raw-edges SHA, full code, source audit paths and all 80 raw Q+truth pairs are inside the immutable local prereg/manifest. A companion ZIP containing these will be retained if the experiment completes; this Git freeze is a public lock receipt, **not a self-contained executable**.

Provenance: U=author asks real, single-factor 01 NN research; F=R38/R41 checkpoint and R42 probes, Git P030–P035, Pro UR1; T=static checking only at freeze; A=boundary-shift hypothesis. Next owner: independent SLE NN researcher, then Codex/Pro optionally audit, no automatic merge.
