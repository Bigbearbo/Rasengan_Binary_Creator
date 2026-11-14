# R33 six-bit numeric word-layout control: actual equal-resource neural training

Date: 2026-11-15 Asia/Taipei. Owner: independent scheduled SLE 01 small-NN researcher; not Hamster VM, dictionary/parser, Pro UR1 or a P030–P035 rerun.

**Formal frozen gate: INCONCLUSIVE.** Three actual binary6 neural students trained, and three existing R31 SLE students used as fixed baseline. Before *any R33 NN forward*, immutable source/manifest/prereg SHA were committed in [freeze commit 38ada798](https://github.com/Bigbearbo/Rasengan_Binary_Creator/commit/38ada798eabfaf7f6741ee7f8d2cd548218a6417). The original freeze document remains unchanged. This result file was created only after the actual experiment and independent verification.

## Single controlled representation factor (limits important)

Valid SLE `SLE-AE1-n5-v1` numeric word: five numeric bits followed by one delimiter 0, `f'{n:05b}0'`. Comparator **BINARY6-IN-AE1-FRAME** numeric word: ordinary six-bit binary `f'{n:06b}'`. Both use identical 39 raw01-question bits including shared header, four six-bit slots and footer, identical output slots, external STOP `S`, same 10,457-param NN with prior role routing. **The comparator is NOT itself a legal SLE profile or a standalone plain-binary language.** The single codec intervention changes number words both in questions *and* answers; this is a narrow layout comparison, not a proof of language superiority or an isolated input-only factor.

Same 136 ordered semantic teaching events (122 distinct), 1408 teacher targets/epoch, 150 epochs, seeds 101/202/303, same student initial tensor values, same Adam/clip/batch and 3300 updates per student. R31 three SLE checkpoints and course were **reused with 0 new SLE updates**; R33 three new binary6 students had **9900 new Adam updates / 633600 target presentations**, **6,918,912,000 theoretical training-forward dense MAC** (backprop excluded). No LLM/teacher oracle for student output: truth computed from a deterministic numeric codec, output is true PyTorch autoregression.

Frozen corpus 144 semantic questions per arm and 3 students/arm: validation a6/7 (8), unseen-low a12..15 (32), unseen-high a28/29 (16), near a20..23 (32), exact course-retention (first 40 distinct, **r1=19/r2=21**), test-stop a8..11 (16). New compared a-values are absent from the first-number role during training but some already appeared in historical probes, so **not globally blind**. All questions and targets are literal 0/1 plus external stop.

## Pooled three-seed scores

Each cell is `first six answer bits correct / whole autonomous answer correct / STOP correct given gold prefix`. The last field is *not* autonomous STOP correctness.

| Split / scored questions | SLE | Binary6 |
|---|---:|---:|
| Validation /24 | 6 / 5 / 13 | 4 / 4 / 24 |
| Heldout-low /96 | **8 / 4 / 50** | **15 / 15 / 87** |
| Heldout-high /48 | **25 / 11 / 31** | **17 / 17 / 48** |
| Near /96 | 64 / 30 / 56 | 73 / 73 / 96 |
| Exact retention /120 | 120 / 120 / 120 | 120 / 120 / 120 |
| Test-stop /48 | 44 / 39 / 43 | 23 / 23 / 48 |

Pooled heldout-low + high: **SLE first 33/144, binary6 first 32/144**; **SLE full autonomous 15/144, binary6 32/144**. Frozen SLE−binary6 gate required >=+16 first, >=+12 full, retention no worse than −15/120, true-prefix STOP no worse than −12/48, and firstword seed parity >=2/3. Actual deltas **+1 first, −17 full, 0 retention, −5 STOP**, seed firstword deltas **+2/+16/−17**. Symmetric binary6 advantage gate also FAIL, therefore **INCONCLUSIVE**, without modifying the preset. High-range firstword favored SLE, near and low more often favored binary6, and whole-answer STOP differed dramatically.

Concrete stored 01 failure seed202 a28,b16,c0,d3: valid SLE target `111000S`, true model output `11100010010011111111111111111111` (firstword correct but fails to STOP); binary6 target `011100S`, model output `010000S` (stops but numeric copy wrong). Original Q and all logits stored in companion.

## Reproducibility and original evidence

Immutable source SHA `6ed0248820e5b7f603714365644e41fe44391dc2086574a2053ec85f4027a17e`, prereg SHA `e9a794f92e02b03b674358e125a42a42a8f08b02308df2f1649a4006927bad5d`, paired 144-row raw01 manifest SHA `0f301ffe93bb151917d2fbe45dcde496e4a75e4e1f86995e0b20a32bc9ad16aa`. Original R31 source/control companion whole ZIP SHA `961bad8563c23363c71812aab1c22b961c7f1f022b1896d3f107c3f19059776f`. R32 PR [#82](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/82) initial head `711a853403049b7fae4fbbbbcdbb81bb5e62e1b4`.

Executed `python r33_binary6_control.py freeze` & `gate` before training, then `train`, `replay`, separate NumPy `r33_audit_numpy.py`. All PASS. **864 real autonomous full generations**, **10,659 forward calls, 116,396,280 inference dense MAC**; saved-weight PyTorch replay 864/864 exact; independently implemented NumPy NN inference 864/864 exact, max logits difference 2.86102294921875e-6. Clean companion ZIP extraction verified **91/91 SHA files and complete two replay paths PASS**. Three novel checkpoint weight JSON files plus all three old model weights, raw bits, 144 cases, true outputs, scripts, full R31 dependencies, inventory and independent audit are in conversation companion ZIP, **not in Git**. Hence Git-only checkout cannot itself regenerate this experiment: use downloadable companion and `verify_r33_companion.py` below.

Companion file `sle_ae1_r33_binary6_word_control_20261115.zip` **SHA256 `2668ecb623c4ea91b36f7e194e0b5f4c561af6a3cb2e240e14c8d815c31b4e13`** (1,729,957 bytes). For full verification `python verify_package.py --full` inside extracted companion; requires compatible Python/PyTorch/NumPy, and performs no retraining.

[更新] In this equal-resource *word-layout* comparison neither encoding won the preregistered joint gate. [取代] A conjecture that SLE bit layout should show general high-bit firstword benefits. [原因] Pooled unseen firstword differed by only +1/144 and SLE exact was −17/144 with seed spread. [狀態] Actual numeric observations and repeatability confidence high; whole-system advantage or internal causal mechanism confidence low.

U: user-directed raw01 small NN mathematical teaching/generalization. F: PR #5 shared corpus, P032–P035, Pro #12 neural failure, and immutable R31/32 checkpoints/source; #5 semantic bank has *not* proved student learning. T: this R33 training/inference/independent audit, replay and clean extracted ZIP. A: codec bit placement may shift output boundaries/STOP, but inputs+targets jointly changed. Next owner = independent NN researcher; next meaningful single-factor experiment could decompose **input-only vs output-only** under strict matched budgets and newly reserved numeric values; do not rerun R33 or infer general SLE defeat/win.

NVIDIA actual calls=0 (no available authorized callable endpoint); local Codex=0 (not available in this runtime); Gemini=0. No external or user-private content/API keys, no auto-merge, no existing Pro/Codex work branch changed.
