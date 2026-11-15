# R43 — One-scalar cursor-9 output calibration: actual neural inference, primary gate FAIL

Date 2026-11-15. Independent SLE native 01 small NN workstream; **NOT** a VM, parser, Pro UR1, or Codex P030–P035 rerun. Branch base R42 PR #93 head `e32a5cbcd6354379348ec8cc9961dfb93b0c6410`. Pre-inference freeze commit **`2c8bfe3d93801f293c94e1e7e37c51c9ce1a1084`** was written before the 480 new paired NN questions were evaluated.

## One predeclared factor and split

R38 hard-b-routing / R41 paired-batch original **six frozen 10,457-parameter checkpoint** files, seeds **101, 202, 303**. NO new model training / NO extra Adam updates. One **externally fitted teacher-supervised calibration scalar** `tau` per checkpoint, from **previous R42 teacher-forced 16 one-bit edges** per checkpoint: `tau=(max-low-margin+min-high-margin)/2`. At only answer-prefix position 9, change `logit[1] -= tau`. No other logits, weights, masks, or original SLE source change. This is *host-side label-informed calibration*, **not** something the neural student learned.

Legal **SLE-AE1-n5-v1**, integers **0–29**, 39 raw question bits `01+010+bin3(2)+0+4*(bin5(v)+0)+111100`, two six-bit SLE answer words + **external STOP**. Same historical R38/R41 course: 136 events ×150 epochs, 3,300 original Adam steps / seed; R43 new training=**0**, training MAC=**0**. Test: `a={8,9,14,15}`, `(c,d)={(12,14),(13,15)}`, `b=18..27`, `r=2`; **80 input raw Q**, verified absent from earlier stored manifest/train Q, ×3 seeds×2 original architectures = **480 newly tested checkpoint–question pairs**. The Q contexts were untouched before R43; the numbers themselves were historically exposed, **NOT globally blind new values**.

Immutable freeze SHA256:
- prereg `886def47028cbcb4873ddd49cfe0081034d07ededbd4c74afca28b7eb3aa7bdf`
- manifest `75f569d68edce870b4c1c8d9a9d8afa07425f88a10431222b9763fb465a0d568`
- executed source `61e68745c133626ac145b0ae9c6db7693b681ce9dbaba46105db5ce1c15e9940`

## Actual results (each arm ×3 seeds)

| Original vs scalar-corrected | R41 original→corrected | R38 original→corrected |
|---|---:|---:|
| b24/25 gold-prefix bit 2¹ correct /48 | **0→48** | **0→48** |
| b24/25 second word, true-firstword seeded /48 | 0→24 | 0→24 |
| b24/25 second word, fully autonomous /48 | 0→24 | 0→24 |
| Known b18/19/26/27 gold-prefix bit /96 | **96→64** | **96→64** |
| Known b18/19/26/27 seeded second word /96 | **96→64** | **96→64** |
| Displaced b20–23 seeded second word /96 | 80→48 | 80→48 |
| Entire spontaneous correct two-word answer /240 | **0→0** | **0→0** |

**Primary preregistered R41 composite FAIL: 3/5 individual conditions PASS**, specifically rescued low b bit (48/48) / rescued low b seeded second word (24/48) / low b free secondword gain (+24) pass; two taught b-retention gates fail (each lose **32/96**). The R38 replicate separately yields identical counts. R41 per-seed corrected b24/25 second-word with true firstword: seed101 **0/16**, seed202 **16/16**, seed303 **8/16**. Thus the average gain conceals unequal behavior and old-value regressions. No fully correct two-word response at all.

**Failure example, raw 01, R41 seed101**: common `a=8,c=12,d=14`. For b24, Q `010100100010000110000011000011100111100`, gold `010000110000S`; teacher-forced bit margin shifts **+4.00546→−4.00118** (right sign), but full generated output changes `00000010010000000000000000000000`→`00000010000000000000000000000000`, both wrong/no STOP. For b18, Q `010100100010000100100011000011100111100`, gold `010000100100S`, previously correct bit margin **+5.73142** becomes **−2.27522** (wrong); taught copy is corrupted. All 480 paired records, source checkpoints and omitted failures are in the companion archive.

## Executed resource and verification

**480** real checkpoint–Q pairs, **960** full autoregressive generations, **960** seeded secondword generations, **960** teacher-forced bit probes, **54,208** genuine NN forward calls; theoretical forward dense **591,951,360 MAC** (10,920/call), not total system FLOPs. PyTorch rerun **480/480 paired contexts** reproduced tokens/margins exactly; **independent NumPy 480/480** reproduced tokens and margin maximum absolute error **1.90735e−6**. Clean ZIP extracted, static/legal/source gate PASS, **198/198 per-file SHA256** PASS, PyTorch and independent NumPy replay PASS. New training 0; no Pro UR1 retraining. NVIDIA/Codex/Gemini live calls all **0** (no authorized callable local NVIDIA endpoint or local Codex in this runtime).

**Full runnable companion ZIP**: `sle_ae1_r43_cursor9_calibration_20261115.zip`, SHA256 **`e2fecd9eaade65b454bb06ea8242fd3411b6b9dc505fee4612ad900578d64026`**, 2,473,415 bytes, **not uploaded to Git**. It remains attached to this ChatGPT run, contains script + six original checkpoints + 80 raw manifest/test cases + complete output + independently implemented replay and SHA verifier. A Git-only checkout cannot recompute inference without this companion ZIP.

Reproduce *in a freshly extracted ZIP*: `python verify_r43_bundle.py` (includes all hashes / source gate / PyTorch + NumPy replay). Explicit mode commands: `python r43_bias_calibration.py gate`, `python r43_bias_calibration.py replay`, `python r43_bias_calibration.py numpy`. Running `run` again is unnecessary for verification.

**[更新]** Correcting a locally miscalibrated output decision bit can rescue partial new-context copying but severely damages taught values; all full answers still fail.
**[取代]** A single threshold shift suffices to turn correct direction-of-logit into robust retained second-word ability.
**[原因]** Two matched arm replications show rescue **and** 32/96 taught regressions and total full-exact 0.
**[狀態]** High-confidence inference/replay on these six checkpoints; low-confidence neural-causation and transfer to other models, unseen numbers or math lessons.

U=user requested single-factor, real native 01 NN curriculum/growth research; F=historic PRs P030–P035, shared bank #5, Pro UR1 #12, R38/R41 weights and R42 logits; T=this run real inference and independent replay; A=external-threshold causal test/interpretation. None of this is proof an NN itself learned to calibrate. No auto merge; no other branch rewritten.

**Next owner:** independent NN research; preregister a **student-learned** conditional role/context calibration or a truly new legal test domain with real baseline/equal budget and separate fully autonomous exact/STOP gates. Avoid treating b24/25 as globally unseen values; Pro UR1/Codex 321-dim three-round program remains a different workstream.
