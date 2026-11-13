# AE1 R12: frozen bit8 → target-bit readout sensitivity

**FROZEN BEFORE NEURAL FORWARD — 2026-11-14, Asia/Taipei.**
Owner: independent scheduled NN experiment; not Codex, Pro, UR1, VM or syntax owner.

Work ID: `AE1-BIT8-ROUTE-R12-20261114`.
Source: [PR #55](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/55) six authentic AE1 F32 checkpoints, companion ZIP SHA256 `53f6e312f30570ef7d458f35b25c17b49eb7b161415bb5d3b165645aeb8f10a0`; [PR #57](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/57) contains source copy/role probe and is NOT rerun. Original architecture/source `run.py` SHA256 `79ac66bd8f2c2fd82b559310bc44e0eae05e3cb23949d1dd9af14e80048acf9a`; source `results.json` `78353a7db90a981eba4a9700361a00fafaf77124ef3ec230b98c5bd90d6152bd`.

**Locally fixed before run, byte hashes**: `probe.py` SHA256 `7ffac184f73a275ef78f2f4c303413ffec65a93b3c89d477fdc57e91727a0e63`; `verify_numpy.py` SHA256 `8d177b3d43dd92f917fd4fbc9437313940d48fba0023259770b00fd79be24654`; `cases.jsonl` SHA256 `45d8dcbd7c39515d1b57b04476bbd2c3edd59cdffbfe04873f3a272f45a1a71d`; `prereg.json` SHA256 `b1cdb920f0c2777f4dd9092a9fb031db813fa6765f0e087d3668a130ac7f4454`. The separately packaged byte-matching files will be appended after execution; this commit freezes their identities and success criterion.

**Single intervention**: change one DATA ID information bit corresponding to decimal +8 in the target word (`low∈{0,1,2,3}` to `low+8`), keeping other data words, header, `r=2`, `c=0`, `d=1`, and all preceding **correct answer bits** fixed when querying the target output bit. Compare two answer positions separately: first at output index 1, second at output index 7. Both have preceding target bit 0. Fixed seen anchor `h∈{18,19}` in opposite word. For first position `a=low(+8),b=h`; second `a=h,b=low(+8)`. No answer fed as an inference target; exact preceding prefix is diagnostic only. Each difference has one input data bit flip and the same output prefix.

SLE profile: `SLE-AE1-n5-v1`, 39 raw 01 question bits `01+010+0100+four*(5-bit ID+0)+111100`; expected teacher label `word(a)+word(b)+external S`. Legal `0≤ID≤29`. This test examines **one next-bit logit**, not complete student response and not generalized SLE grammar.

**Design split (already known to researchers; NOT blind)**: `low=0,1` diagnostic validation; `low=2,3` frozen diagnostic test. Six immutable models: seeds 101/202/303 × tied/untied. Total 32 distinct Q, 16 paired contrasts, 192 genuine forward passes over 6 models, 96 pair records. Tied model 10457 params, untied 11081; per forward 10920 theoretical dense MAC. New training updates=0. Historical training: 136 presentations, 112 unique, 150 epochs/3300 updates per student. Run preflight before models are loaded; no further model training.

**Predetermined primary gate**: at least 2 of 3 tied seeds on 4 frozen test pairs for NEW FIRST-word target output: ≥3/4 positive change in `(logit1-logit0)` after +8, while ≥3/4 newly flipped target bits still classified incorrectly. This probes the weak aligned signal hypothesis; PASS would not mean full word copying or causal proof of output-only bottleneck. Report all role/arm/seed baseline and new margins, sign counts, exact target bit, embedding distances; keep FAIL.

Independent verifier: pure NumPy F32 reconstructs every checkpoint's 3 logits and embedding (not Torch forward), must match tolerance 1.5e−4 logits / 1.5e−5 embedding; preserve raw 01, negative cases, source/file SHA. No optimizer, LLM oracle, or NVIDIA secrets. NVIDIA not called unless a separately authorized read-only endpoint exists; no local Codex claimed. No auto-merge.

U author asks genuine bounded SLE neural work; F source weights/code/lesson exposure; T only after execution; A candidate that the readout sees an insufficiently strong or misaligned bit8 signal. Next owner independent NN reviewer; avoid after-the-fact blind-test labels.
