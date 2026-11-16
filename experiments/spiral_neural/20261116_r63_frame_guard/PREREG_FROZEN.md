# R63 — frozen frame-aware inference pipeline: preregistration

Date: 2026-11-16 (Asia/Taipei). Owner: independent scheduled SLE small-network research (not VM/parser/Codex/Pro).

## Question and single factor
Does the previously trained R62 39-bit raw-01 frame-validity **auxiliary neural network**, placed before the **unchanged R52 free math-answer NN**, prevent malformed-frame input being sent as an answer without changing the lawful answers? Compare with the existing R62 framing-blind control and an unguarded math network. All weights are frozen; this is modular orchestration, **not a jointly trained student**. Rejection is out-of-band; **no new SLE error word is invented**.

## Exact sources
Parent R62 PR #113 head `30ec8f7b337d3f244d072d475017715e77c78bc5`, stacked on R61 PR #112. R61 archive SHA256 `ac09f30323dd078bd0445935ebd0aa58eecf94dd5f0049cbe8c6805e5c431526`. R62 archive SHA256 `8d9e0c637112922b766607ab07add1c40498d158af5df970814de9c2c09e6d81`. Freeze actual local runner SHA256 `07960521a047d5d24e55f3184dd666aea485d91393e7f6131cbeb58a1c6dad52`, full generated 96-Q manifest SHA256 `d7d0839ea0a804a880354865564158fa2de30f29122bf2f70cb90bf8367a41af`, complete local prereg JSON SHA256 `9057400e09769f879563edf63f21a068fe71d10174bdbbdf5f7f9c6224f63ad3`. The runner/manifest/pre-reg bytes are retained in the local artifact for later publication; this Git freeze anchors their SHA before new NN inference.

## Profile, data, and split
Only `SLE-AE1-n5-v1`: 39-bit Q = `01+010+bin3(r)+0+4*(bin5(v)+0)+111100`, r=1/2, four values a,b,c,d=0..29. Old R52 Q are exact bitstrings; each Q yields four **paired** header variants `01` valid, `00`, `11`, `10` deliberately **invalid diagnostic**. 96 distinct old R52 questions, selected with SHA256 order of `R63-frame-guard|Q`: 32 old retention (16 r1/16 r2), 32 legacy, 32 fresh; four variants = 384 unique questions. Check **zero exact-Q overlap** against the complete R62 744-row manifest.

No training in this run, no fitting, and no hyperparameter tuning. Validation/regression: 32 old retention Q, test: 32 legacy+32 fresh Q; all 96 are globally previously exposed R52 cases, **not new blind mathematics**. Three paired seeds 101/202/303. There are 288 lawful and 864 malformed root variants over seeds.

## Fixed models and budget
Frozen R52 math NN 10,465 parameters/seed (including 8 trained source-gate parameters), ~10,920 dense MAC per predicted output bit. R62 raw-framing head 1,313 parameters/seed and framing-blind head 1,313, each 1,280 dense MAC per query. Only the raw-framing head is active in the guarded pipeline. Classifier accept threshold: logit >= 0, unchanged. Planned primary inference: 1,152 full baseline math generations + 2,304 frame-classifier logits. Optimizer updates = 0, new training MAC = 0. Independently reproduce **all** 1,152 math answers and 2,304 frame logits with NumPy (separately counted); no LLM/teacher answers are passed to the free student.

## Preregistered gates (all required)
1. Sources have unchanged SHA; no updates.
2. Test valid-frame acceptance by raw head >= 175/192.
3. Test malformed-frame rejection by raw head >= 520/576.
4. Test raw-head decisions agree with trivial deterministic two-bit header rule >= 700/768.
5. Blind-control logit invariant across the same body/four headers, max difference <= 1e-6.
6. Valid math outputs unchanged from archived R52 outputs, all 288/288 (regression, **not** 288 correct math answers).
7. Full math-generated answer unchanged across each body's four header variants, 1,152/1,152.
8. Independent NumPy replay: all 1,152 math answers and 2,304 classifier logits.

Failures/false accepts/false rejects must be saved, no epoch or threshold extension. Deterministic header check is a stronger zero-neural-MAC baseline for this **fixed** prefix; PASS does not establish efficiency gains or grammar learning. Next owner should evaluate nontrivial variable framing or end-to-end multi-task learning, not repeatedly teach a two-bit constant.

## Provenance
U: independent raw01 small-NN mathematics, language, growth, and generalization. F: immutable R52/R60/R61/R62 checkpoints/results; branch-specific P030–P035 and Pro UR1 verified separately. A: add frozen auxiliary gate, compare blind/deterministic controls. T: only static manifest/source validation before this Git freeze. NVIDIA/Codex/Gemini actual calls: 0; no authorized remote NVIDIA endpoint made available. No merge permitted.
