# R53 事前凍結（首次神經推論前）— frozen firstword c/d-off

Work ID: SLE-AE1-R53-FROZEN-FIRSTWORD-CD-20261115
Owner: independent scheduled native01 small neural network research
Parent: Draft PR #103 head `bb5863d110f9238d941d4f2ecdb31f2957c4e936`
Status: pre-inference; no new R53 NN forward or training at publication.

**One controlled factor:** on the **first answer word only** (decoder cursor positions 0–5), forcibly zero the *c,d* source contributions, leaving the learned *a,b* gate scalars unchanged. On the second word (6–11) keep the frozen R52 learned gates; on external STOP leave all inputs unchanged. R50 backbone and all eight R52 learned gate logits remain immutable. This is researcher-enforced test-time ablation, **not self-routed learning**. No new training (updates=0; 10,465 parameters, trainable=0 in this study).

Hypothesis: R52 nearly-saturated first-word c/d gates may create nuisance dependence explaining the exposed-legacy firstword 0/288. This may help legacy firstword but cause fresh-context/retention regressions. Do not posthoc adjust the mask, seeds, checkpoints or thresholds.

**Legal profile:** SLE-AE1-n5-v1. `r ∈ {1,2}`; each `a,b,c,d ∈ [0,29]`; 39 raw 0/1 question bits `Q=01+010+bin3(r)+0+4*(bin5(v)+0)+111100`; expected answer `r*(bin5(v)+0)` followed by an **external** stop class `S` (not a SLE punctuation token). Full autonomous answer includes STOP and is the primary outcome. No teacher oracle computes the student's free output.

**Frozen split:** training=136 historical R52 events, used only to define source; this run trains none. Validation=80 exposed historical retention Q, legacy test=96 exposed R44/R45 Q, fresh-context test=96 exposed R50/R51 Q, × three seeds 101/202/303 = 816 total. None is a new blind numeric test. Baseline is original R52 raw record per (seed,Q); paired predictions. Banned: further training or retuning from test.

**Predeclared conjunction, all required:** legacy firstword ≥1/288 (R52=0), legacy full ≥1/288 (R52=0), fresh full ≥66/288 (R52=66), retention full ≥220/240 (R52=220), exactly 1,632 identical gold-prefix non-intervened secondword/STOP logit comparisons, and ≥1 changed first-word generation. Record every new wrong as well as every new correct, per seed, full STOP and counterfactual metrics. A failed conjunction means **FAIL**. Log actual forward calls and theoretical dense MAC proxy at 10,920 MAC/forward; backward cost 0.

**Immutable sources:** R52 conversation ZIP SHA256 `c749c56d71a1bc5d41363e8bc6d207cd99a5296f80f0bcc77dab0bacc57c1db1`; R52 raw `b32ff44d8281b8276b685eda107f28b24026a4f45bc14a62d4577db0fd635ebc`; R52 summary `7631ff18411302244ffb1cb490bd9e8836ac18d7f0844bd580816bbd4bc99b3e`. Three backbone SHA256: 101 `8a30848c1084627fb8fb20bacbd8f844e8b9fb22a27879d6bf8202bdb6499417`, 202 `490da5ea65b1ddf4119c573c3b048c84824905434a7241ba717bd036c5a0fc7e`, 303 `c5c6a56b795ca114eb4cd42104f4d9aab056be77d61dfad11cbd1a1bb3993d6f`.

Gate JSON SHA256: 101 `69a242ed2448f0ae724e27ee8b238e63d65f1018d865b5acfc98b72e946e8e7a`; 202 `34e88abd3324a9df8c4ce93ef833b74ac73c533fcd6d36d9060ea5315d284477`; 303 `a26e127779d5028aee1e57f0267ab61667b3299a8e7f9bb5bbd4cc63184b6218`. Local prereg JSON SHA256 `3738332e0caffa159e522f43e539372ce36b685129b0ed8ea09f41767103f0a3`. Runner SHA256 (pre-script, prior to test) `94a91f480a3b1cea49bd86232b1a8af95b5bc9aa0801d78f75dc3df73a29e6e0`. This frozen document + hash identifies the code and test, and the code/outputs will be linked after execution.

Provenance: U = independent NN/SLE role/constraints; F = immutable R52/R50 sources, PR #103 and branch evidence; T at freeze = only SHA, Python syntax, static inspection (no R53 neural inference); A = c/d nuisance mechanism hypothesis (unconfirmed). NVIDIA calls 0 (no connected authorized callable OpenRouter worker), Codex 0, Gemini 0. No Pro/Codex/VM/grammar branch modifications or merge.