# R50 — frozen before any R50 neural forward / update

**Work ID:** SLE-AE1-R50-SCAFFOLD-RELEASE-20261115
**Owner:** independent SLE native 01 neural learning lane. **Baseline:** PR #100 (R49) head `b33cf25bba0274f32606e507c6d513198a8b28b8`; causal historical control R45 / PR #96, with R44 / PR #95 fixed-route positive control.
**U/F/T/A:** U = independent bitwise SLE neural growth, teaching, generalization and math education, not Hamster VM or syntax dictionary. F = R44/R45/R49 original archive and fixed Git PRs. T at freeze = local **static** legal-codec/material validation only; NO R50 network forward or optimizer update. A = initial b-only scaffold may reduce interference during subsequent full-source training (low confidence).

## Exactly one changed factor
R45 has unmasked `a+b+c+d` source access during **all** second-word training and final generation. R50 uses **b-only** hard source restriction for the first **90 training epochs (epoch 0–89)**, releases to **a+b+c+d** for epochs 90–149, and is **fully unmasked** at final independent generation. Same 10,457-parameter model; all trainable weight shapes, initialization, data, labels, optimizers, seed sequence, number/order of training events, minibatches, updates, inference gate are unchanged. This is an externally specified schedule, **not** a learned selector, and does not imply an algorithm discovered source routing.

## Profile, corpus and fixed splits
Legal `SLE-AE1-n5-v1`, integer values 0–29. Native question raw bits: `01 + 010 + 3-bit r + 0 + four × (5-bit numeric + 0) + 111100`, exactly **39 raw 0/1**. Answers: `r × (5-bit value + 0)`, with *external action* STOP `S`; STOP is not an on-wire punctuation character and is not Codex's separate whole-answer/句號 experimental interface.

**Train:** exactly R44/R45 136 ordered synthetic examples; 1,408 teacher-paired prefix targets per epoch; no large-model teacher for the student. **Historical validation:** 80 previously exposed exact-Q retention cases; reported honestly, not a blind validation set. **Legacy test:** 96 previously seen R44/R45 exact-Q contexts across b 18–29, no gate tuning. **New exact-Q test:** 96 contexts, 4 choices a={4,5,8,9}, 2 choices (c,d)={(4,7),(5,8)}, 12 choices b={18,…,29}; verified absent from all existing local `*manifest*.jsonl`, teacher train Q, and legacy+retention exact-Q. The **values** themselves were previously exposed; this is **context novelty only**, not truly unseen value generalization. 272 total per seed.

## Freeze and budgets
3 seeds 101/202/303, `torch.manual_seed(seed+12000)`, Adam lr 0.003, gradient clip 1.0, deterministic RNG minibatch permutations `default_rng(seed+201000+epoch)`, minibatch 64, 150 epochs × 22 updates = **3,300 updates/student**, **9,900 total**, **633,600 teacher target presentations**. Model **10,457 trainable parameters/student**. Per-target theoretical *forward dense* MAC 10,920, train-forward budget **6,918,912,000 dense MAC** (not hardware FLOPs; backward, validation and wall-clock costs separate). No continuation, budget extension, new seed or post-test selection.

## Pre-registered eight-component **joint** gate
All must be true for PASS: second-word legacy b18/19 ≥32/48; b24/25 ≥32/48; b26/27 ≥32/48; b28/29 ≥24/48; b20–23 ≥48/96; old 80×3 retention **fully autonomous exact with STOP** ≥216/240; new contexts b28/29 second word ≥24/48; and any new-context **full autonomous answer including STOP** ≥1 across 288 generations. Also report firstword, secondword, full exact and correct-prefix STOP separately. Historical control checkpoint and outputs are read-only. No outcome-guided revision.

## Cryptographic freeze receipts (local, prior to training)
- `r50_prereg.json` SHA256 `492a447a2629e9f358d4a9e87a3206ea861023dc182c20a9721a81372a13be8a`
- `r50_manifest.jsonl` SHA256 `ff2d3801b5e413bf977a9f9b2bfbf18b1a97e0a9f6b643f11e4d48c51af8478c`
- `r50_scaffold_release.py` SHA256 `6514f7a99ffb7ccf5958e9a4b5cde8847685d4d489f38ac7b1b4a4fc81683dde`
These three files and the immutable local R44/R45 inputs are sealed before training. A subsequent artifact ZIP will contain their original bytes, full executable runner, manifests, state, exact raw answers, failures and replay tools. Git stores this public freeze and public verifier/report; the ZIP is the full executable archive.

Static check already executed locally: **PASS** (136 curriculum events, 272 legal 39bit Q, no exact-Q collision, three seed configuration, 10,457 params). New neural forward/update at this commit: **0**.

## Restrictions and next owner
Do not run Pro UR1 / #12 or change its manifest or its ownership (Codex's target-shuffle follow-up); do not modify Codex's whole-region/句號 work, P030–P035 or Hamster VM; do not merge this stacked PR. No NVIDIA/OpenRouter endpoint configured or authorized in this environment: `nvidia_status=skipped`, `actual_calls=0`; Codex/Gemini actual calls 0. All public sources are synthetic and de-identified.
