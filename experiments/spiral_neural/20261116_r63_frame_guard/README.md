# R63 — frozen R62 frame guard attached to frozen R52 math NN (completed)

2026-11-16. Owner: independent SLE small-NN research (not Pro/Codex/VM/lexicon). **Results of actual inference and NumPy replay; diagnostic PASS 8/8, NOT a successful math-learning experiment.**

Preregistration was committed **before any R63 neural forward** at [commit `1e1c4946`](https://github.com/Bigbearbo/Rasengan_Binary_Creator/commit/1e1c49463cac3634cd1cda5781d3e3ad9a6d23c9). The prereg SHA-anchors the precise source runner and 96-Q question manifest. No thresholds, lessons, checkpoints or source bytes were changed after freeze. This result is not a Pro UR1 or Codex P030–P035 run.

## Exact experiment

The R52 math network (3 frozen checkpoints, 10,465 params each) generates a full mathematical answer, including STOP, for legal 39-bit `SLE-AE1-n5-v1` questions. A separate frozen R62 neural classifier (3 raw-frame checkpoints, 1,313 params each) either permits its answer or outputs **REJECT_OUT_OF_BAND**, with no unapproved SLE error token. The only intervention is whether this pretrained raw-frame verifier is placed before math inference; comparisons are unguarded math and R62 frame-blind frozen control. Seeds 101/202/303, **zero new training updates**.

96 already-exposed source questions: 32 retention (validation) + 32 legacy and 32 fresh (test), each with `01` legal plus `00`, `11`, `10` illegal **diagnostic** root variants. Original mathematical answers come from frozen R52 and were compared to archived R52 original outputs. There is no full-bitstream overlap with the R62 training/validation/test manifest, but the numerical domain is not new. The 96-Q SLE word profile and split are frozen and hashed in the prereg.

| Three seeds combined | Learned raw-frame gate | Framing-blind control |
| --- | ---: | ---: |
| Valid `01` correctly accepted | **288/288** | 206/288 |
| Malformed `00`,`11`,`10` correctly rejected | **864/864** | 246/864 |
| Paired same-body logits | Differ with root | Identical, max difference 0.0 |

The fixed two-bit deterministic rule `Q[:2] == '01'` agreed with the raw-frame neural classifier on **1,152/1,152** in this experiment, without the extra 1,313 NN parameters / 1,280 dense MAC per input. The classifier has **no demonstrated efficiency advantage** over this fixed rule; the diagnostic dataset intentionally has 75% malformed frames.

**Math did not improve.** Exactly the same lawful full-answer outputs as archived R52 **288/288**; mathematically correct on validation **89/96**, on test **22/192**, total **111/288**. The unguarded math student generated an identical complete answer across all four different headers for each of the 288 seed×body pairs, consistent with its previously identified framing blind spot. No root rejection or full-answer learning capability was added to the mathematical weights. Sample retained failure: seed101, lawful raw `010100100001000111000001000001110111100`, gold `001000111000S`, math answer `000000100000S`, raw guard logit +8.0725 (accept).

## Measured work, reproducibility, negative evidence

Actual inference: **1,152** full mathematical free generations, **13,900** per-output-bit math forward passes (~**151,788,000** theoretical dense MAC); **2,304** small frame-classifier forward passes (~**2,949,120** dense MAC). No new optimizer updates / training MAC. Separate independent NumPy replay: **1,152/1,152 math**, **2,304/2,304 classifier**; max frame logit discrepancy `1.9073486328125e-06`. All **8/8 prespecified gates passed**. No false accept/reject examples in raw-arm test; many *math errors* remain and are retained unfiltered. Full raw pairs, model checkpoint sources, failure examples, independent replay code and reference manifests are stored in the artifact identified by its SHA below.

Full portable bundle (nested immutable source+weight R61 and R62 ZIPs, local exact runner, JSONL bits/answers, prereg, all metrics, independent `verify_bundle.py`, package hashes): `sle_ae1_r63_frozen_frame_guard_20261116.zip`, SHA256 `447ed20ee7290a63fbf05559823f63d22fdea06974979ad87990a6ae57dfa4f2`. Size 4,299,985 bytes; 10 ZIP members; CRC check passed. In the conversation artifact it is available as a downloadable sandbox file; this Git README preserves the identity but **does not claim binary ZIP bytes were uploaded to Git**. Clean unzip and source/weights/hash/replay check on the packaged bundle passed.

R63 original runner SHA256 `07960521a047d5d24e55f3184dd666aea485d91393e7f6131cbeb58a1c6dad52`. Q manifest SHA256 `d7d0839ea0a804a880354865564158fa2de30f29122bf2f70cb90bf8367a41af`. Full source prereg JSON SHA256 `9057400e09769f879563edf63f21a068fe71d10174bdbbdf5f7f9c6224f63ad3`. Full 1,152 record JSONL SHA256 `425d786ae45e8af9d07039fe0afab76466ae198be893eaa1929906b51449d974`. Source R61 ZIP `ac09f30323dd078bd0445935ebd0aa58eecf94dd5f0049cbe8c6805e5c431526`; R62 ZIP `8d9e0c637112922b766607ab07add1c40498d158af5df970814de9c2c09e6d81`.

## Research interpretation and next owner

[更新] A previously trained neural frame-validity head can veto syntactically malformed fixed-root questions before a frozen SLE math NN without changing valid math answers. [取代] Treating the R62 auxiliary frame-recognition result as evidence that one mathematical NN now understands SLE or improves mathematics. [原因] The separate math network retains its 177 wrong lawful answers out of 288; a simple deterministic two-bit check is a strictly cheaper comparator for the fixed prefix. [狀態] High confidence for this frozen diagnostic; low for dynamic width/version/multilayer or end-to-end mathematical SLE acquisition.

**Next owner: independent NN research.** New preregistration should compare a truly shared frame+answer network and a deterministic exact framing rule, with newly frozen variable versions/word-widths and mathematical holdout. Do not retune these already exposed cases. Pro UR1 and Codex P030–P035 unchanged. NVIDIA, local Codex, Gemini calls this run = 0; no authorized NVIDIA endpoint was exposed. No merge was performed.

U: user's independent genuine raw01 learning/math research direction. F: original Git AGENTS/handoff, Pro/Codex evidence and R52/R60/R61/R62 exact checkpoints, code, hashes. A: frozen guard pipeline and negative controls. T: R63 new math generations, paired frame logits, independent NumPy replay and source checks.
