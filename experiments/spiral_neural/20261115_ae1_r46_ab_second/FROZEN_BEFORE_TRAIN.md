# R46 — frozen **before** any new neural forward or optimizer update

Status: preregistration. Researcher: independent SLE native-01 small-network worker. Parent: R45 PR #96 head `0f673c9743b6a2e72129cc284a908b8296cbe498` (no Pro/Codex/VM writes).

## One intervention and causal question

Hold **R44** identical except at response-arity `r=2` output indices `6..11`, unmask **operand a** in addition to existing b; continue to block c,d. At all other output positions use all inputs as previously. R44 b-only and R45 a,b,c,d are immutable read-only controls, not retrained. This isolates the cost of letting a irrelevant source reach the second word, *not* a learned selector; any downstream hypothesis about learned routing remains unproved. Hypothesis: some R45 damage could come from specific distractors and may not appear with only a released.

## Fixed data and representation

Legal `SLE-AE1-n5-v1`, value range **0..29**. Input exactly 39 native bits: `01 + 010 + bin3(r) + 0 + (bin5(a)+0) + (bin5(b)+0) + (bin5(c)+0) + (bin5(d)+0) + 111100`. Expected output is `r` 6-bit SLE numeric words; output `S` is a *separate external stop action*, not a wire token. Offline reference builds the teacher labels; free-generation student receives raw Q and only its **own** generated prefix, not the correct answer or a teacher oracle.

Training: unchanged **R44 136 ordered events**, exactly 1408 teacher-forced targets/epoch, seed 101/202/303, `torch.manual_seed(seed+12000)`, 150 epochs, minibatch 64, deterministic epoch shuffle `default_rng(seed+201000+epoch).permutation(1408)`; 3300 Adam updates/seed, 9900 total, 633600 target presentations, Adam learning rate .003, cross entropy for 0/1/S, gradient clip 1. **10457 parameters** each; dense forward MAC 10920/target, **6918912000** theoretical training-forward MAC, excluding backward/optimizer. Stop at 150 epochs, never pick intermediate checkpoint after test.

Validation/retention: **historical R38 80 full Q** ×3; existing and inspected, no model selection. Test: **96 R44 Q** ×3, already checked in R44/R45, not newly blind. Among these per seed: b18/19 16Q, b20..23 32Q, b24/25 16Q, b26/27 16Q, b28/29 16Q; b28/29 are untrained **in second-word role** but globally previously exposed.

## Gates fixed before run

Joint pass requires: b24/25 secondword >=40/48, b26/27 >=40/48, b18/19 >=40/48, b28/29 >=32/48, displaced b20..23 >=72/96, 80Q historical full-exact >=216/240, and **>=1** complete new two-word exact including autonomous STOP across 288. Report each independently; any one failure => FAIL. Also report firstword and gold-prefix STOP, distinct from free-generation success, with raw 01 cases and per-seed failures.

## Frozen local companion artifact fingerprints

`r46_ab_second_route.py` SHA256 `b10356f0161eebe12037b07c3bb7dc9ddce9b252b428641309bd8e77a2fba0b9`

`r46_manifest.jsonl` SHA256 `d8900796e8e50c116d9b780f42377e5ef40332623a3dd39a448903dec57e8416`

`r46_prereg.json` SHA256 `de3f7f63300aa6ad3d550f43ed191abee1c0d526c13b0d1ad8438be40038f3d1`

`R44 train course` SHA256 `a8c28b69fe15b8b8181dd701b3da4abb723e47acc866c8b920e854fac758f8fe`

Source immutable companion: `sle_ae1_r45_balanced_unmask_20261115.zip` SHA256 `7dfe1c5683fe117ae46e4c8e4569f5b62285eeda2fb2265c0f6f99da5a73eeea`. Complete R46 script and manifest are in the **local companion**, not this Git prereg; their hashes are recorded here to prevent retrospective code substitutions.

U: user specifies independent raw-01 small neural research with matched cost/retention. F: R44/R45 public PRs and local immutable signed-hash companion. T: only corpus/hash/syntax and source checks **so far**; no R46 neural claim at freeze. A: a's causal effect is unknown until training. NVIDIA actual calls 0 (no authorized callable OpenRouter endpoint); no Codex/Gemini execution. Next owner: independent NN researcher; publish negative and positive cases without cherry-picking. Do not merge automatically.
