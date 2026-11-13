# AE1 R12 — bit8 target-position next-bit margin diagnostic

2026-11-14; **preregistered primary gate FAIL, 0/3 tied seeds**. Unlike existing [PR #57](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/57), this is a new single-bit margin + encoder-activation intervention using the six genuine, frozen [PR #55](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/55) checkpoints. No new training, no free-generation whole-answer accuracy claim, no Codex/UR1/VM/parser work.

**Before any new NN forward**, the immutable protocol, expected source and local executable/checkpoint hashes, 32 native 01 manifest entries, splits, three fixed seeds and outcome gate were committed to Git in `4a24fd9022e94c5f80f338ac87e48cc842dd3f9f` and validated. No rerun of prior trained models' learning. Source model ZIP SHA256 `53f6e312f30570ef7d458f35b25c17b49eb7b161415bb5d3b165645aeb8f10a0`; source program `run.py` SHA256 `79ac66bd8f2c2fd82b559310bc44e0eae05e3cb23949d1dd9af14e80048acf9a`. Main commit and other workers' active branches untouched.

## Single intervention, true raw 01

In the legal `SLE-AE1-n5-v1` profile, use Q39 `01+010+0100+four*(five-bit-ID+0)+111100`, answer two six-bit words plus an **external** STOP action `S`. For r=2, c=0, d=1, fixed opposite anchor h∈{18,19}, target low∈{0,1,2,3}: flip one information bit in the target word ID, low→low+8, without altering preceding **correct-answer prefix** supplied only for next-bit diagnosis. Compare answer output index 1 (first word) and 7 (second word) separately. 32 Q (16 paired contrasts), three seed 101/202/303 × tied/untied checkpoint = 192 genuine Torch next-bit forward and 96 comparisons. `diagnostic_val=low0/1`, `diagnostic_test=low2/3`, **previously explored word domain, not researcher-blind**.

Each tied model has 10,457 parameters, untied 11,081, fixed 10,920 theoretical dense MAC per forward; total **2,096,640** theoretical forward dense MAC, 0 optimizer updates. Input, exact prefix, student logits, target-bit predictions, target-word embedding and signed paired margin change are fully recorded in separate downloadable ZIP with all six checkpoints, raw records and independent verification. Git alone lacks the six checkpoint weights.

**Pre-fixed gate**: ≥2 of 3 tied seeds must have ≥3/4 positive delta in `logit(1)-logit(0)` for the *new FIRST word* diagnostic test pairs while ≥3/4 new target bits still classified incorrectly; this would only lend support to a weak-but-aligned bit8 signal, not demonstrate general copying.

| test; 12 pairs each | correct newly flipped target bit | positive margin shifts | postflip logit(1)-logit(0) median | embedding displacement L2 median |
| --- | ---: | ---: | ---: | ---: |
| tied first | **0/12** | 5/12 | -14.55 | 1.478 |
| tied second | **0/12** | 5/12 | -9.62 | 1.478 |
| untied first | **0/12** | 4/12 | -12.33 | 0.802 |
| untied second | **0/12** | 6/12 | -8.97 | 1.384 |

By seed, tied FIRST word test had 2/4, 2/4, 1/4 positive shifts (101/202/303), all new bit outputs were incorrect. **Gate FAIL 0/3**. All old/low-bit target predictions were correct; all new/bit8 target predictions (both roles/arms) were 0 when truth was 1, including the preassigned diagnostic validation subset. Each word's embedding does respond substantially to the bit8 input flip, but the downstream signed output margin often moves in the wrong direction and never suffices to flip output decision. This **does not identify a decoder-only bottleneck**, nor establish learned bit-level semantics; correct-prefix single-token inference is not autonomous free-generation.

## Actual execution and verification

`python probe.py gate` PASS (all frozen manifest, source checks, legitimate format, 6 checkpoints, no bit8 ID exposure); then `python probe.py run` executed exactly 192 Torch forwards/96 paired contrasts. `python verify_numpy.py` does not import the Torch probe and independently recomputes **192/192 three-logit vectors** and **96/96 paired deltas**, all PASS: largest abs logit error **1.90735e−6**, embedding error **1.19209e−7**. Companion ZIP contains source, logs, mistakes, Sha256SUMS with complete clean-extraction verification.

Public `probe.py` SHA256 `7ffac184f73a275ef78f2f4c303413ffec65a93b3c89d477fdc57e91727a0e63`; `cases.jsonl` SHA256 `45d8dcbd7c39515d1b57b04476bbd2c3edd59cdffbfe04873f3a272f45a1a71d`; `verify_numpy.py` SHA256 `8d177b3d43dd92f917fd4fbc9437313940d48fba0023259770b00fd79be24654`. Full raw logits SHA256 `1ae3b542c3323975452c57ad2d1ee26fe8216570dd6e7ae19e69179734ea8203`; paired result SHA256 `a9f036cd4a29867d67f05199464411e2c8a69410ff4e60712fc019e7402cfab0`.

Provenance U: author requests genuine NN raw-01 SLE experiments. F: immutable PR55 NN checkpoint and earlier PR57 diagnostic. T: actual R12 forward and independently verified numerical results. A: unconfirmed explanation of representation/readout; this gate fails, and higher-level causality remains unproven.

NVIDIA `skipped_unavailable` (no separately authorized, actually usable read-only endpoint), model calls 0. Local Codex calls 0; Gemini calls 0. No LLM/student answer oracle, no secrets or private conversation uploaded.

[更新] Bit8 input changes hidden word embeddings, but not output decisions; paired output-margin response is inconsistent. [取代] Prior speculation that bit8 was wholly invisible in input encoder or that second-word transfer is stable. [原因] Direct checkpoint-level paired bit-flip with a frozen success criterion and independent output verification. [狀態] Numerical findings HIGH confidence for these checkpoints; causal model/architecture claim LOW.

**Next owner:** independent NN reviewer. The next teaching intervention should freeze genuinely new vocabulary and balanced role/context exposure, then examine untrained word values. Do not tune on these already-observed diagnostics and call them new holdout.
