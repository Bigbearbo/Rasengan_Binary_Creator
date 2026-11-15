# R54 — legal SLE c-token substitution (2026-11-16)

**Owner:** independent native-01 small-network researcher; not Pro/Codex/NVIDIA.
**Parent:** [Draft PR #104](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/104), head `1165204c1425ce084e049725781468c7b10df66d`. **Before any new R54 neural forward**, public prereg freeze commit `db5471fd13c3d702967d2e878cfc8256ea2c2e03` established the single factor, six thresholds, manifest, runner, and SHA256 digests. No source checkpoint retraining, no merge, no change to Pro/Codex/VM.

## Exact scope

**Only c changes** between paired legal 39-bit SLE questions, from encoded numeric zero to another valid encoded number in 1–29. Fixed r,a,b,d=0 and unchanged Echo truth. Correct output is r copies of 5-bit value+0 (first a, second b if r=2), then **external** STOP classifier S; S is *not* a grammar punctuation token. Profile `SLE-AE1-n5-v1`: `01 + 010 + bin3(r) + 0 + 4*(bin5(v)+0) + 111100`; all operand values 0–29.

Two arms share frozen R50 backbone and learned R52 eight gate logits: **R52 as trained**, and **R53 firstword hard c/d mask** as negative control. Neither arm receives a teacher answer during free generation. These are not independent trained model families; the 3 seeds (101/202/303) have correlated tasks.

Manifest: 48 matched pairs / 96 questions, 16 validation pairs (r1=8,r2=8) and 32 test pairs (r1=16,r2=16), each evaluated with three seeds in both arms. 96 exact Q are absent from 1,548 39-bit historical Q in the provided archive; **the values and Echo rules have appeared in older research**, so this does not establish new numeric-domain generalization. Original teaching course 136 events; this study adds **0 training updates**, checkpoint size **10,465 params per seed**. PRNG `54161116`.

| Measured across three seeds | R52 learned gates | R53 hard firstword c/d mask |
|---|---:|---:|
| 39-bit input → native complete generated outputs | 288 | 288 |
| Complete answer including free STOP correct | **192/288** | 126/288 |
| First numeric answer word correct | 207/288 | 136/288 |
| Second word correct on r=2 (144 rows per arm) | 116/144 | 116/144 |
| **Initial firstword logits change** upon legal c alteration | **144/144 pairs** | **0/144 pairs** |
| **Greedy firstword changes** upon legal c alteration | **50/144 pairs** | **0/144 pairs** |
| Complete correctness discordant between matched c variants | **40/144 pairs** | 2/144 pairs |
| Val full exact | 67/96 | 45/96 |
| Test full exact | 125/192 | 81/192 |

Of R52's **40** paired correctness discordances, **37** previously correct c=0 responses become wrong when c changes, and **3** previously wrong responses become correct. The paired effects cannot be explained by model weight changes, changes in a/b, or a non-SLE zero input; all inputs are legally encoded with the same profile. They do **not** prove any particular internal circuit, only observable dependence. R53 firstword invariance is established, but 2 full responses still change correctness because its later secondword/STOP computation can see c.

**Concrete failure:** seed101 pair `test-r1-03`, a25,b22,d0. c0 Q `010100010110010101100000000000000111100` expects and produces `110010S`. Legal c19 variant Q `010100010110010101100100110000000111100` expects the *same* `110010S` but produces `110110S`. The full 39-bit raw inputs, exact responses, and both model arms are saved in the R54 portable evidence archive.

## Joint gate and executed verification

**Diagnostic joint gate PASS 6/6**: 96 valid distinct questions and no prior exact overlap; R52 initial logits change 144/144; R53 do not 144/144; R52 greedy firstword changes 50/144 ≥10; R53 firstwords unchanged 144/144; independent float32 NumPy greedily reproduces 576/576 complete PyTorch outputs.

**Actual execution:** `verify_r53_package.py` 315/315 historic SHA256 PASS; new preflight 96/96; **576** free native responses; 6,336 new neural forward calls, proxy **69,189,120 forward dense MAC** (excluding replay and other work); **576/576 PyTorch replay PASS**, **576/576 independently computed NumPy replay PASS**; max NumPy initial-logit absolute discrepancy **5.7220458984375e-06**, below 1e-5; portable R54 SHA256 audit **325/325 PASS**. The original verifier had a *post-run self-contamination glob bug*: it scanned newly written R54 outputs as historical source. We fixed only the **separate read-only verification wrapper**; the frozen runner, raw outputs, manifest, pretrained model, and gate values were untouched. Preserve that negative audit and correction, do not silently erase it.

Full portable ZIP SHA256: `9aec51c9f7b2e4e48d33ea02af37fd26c5a2438a220bd00aa650058be110fc72`.
Exact frozen runner SHA256: `17463cbe947454592317ef26dc2d920da4e8353fffde9f2fcd87905d46fc7a03`.
Exact frozen manifest SHA256: `88ddd8ac2e390e735be907f0f797b23620ac5800b2df753b613638e3a30c809c`.
Prereg JSON SHA256: `36a229d85da023306cfa0dbd83e1896be6968690c12595d2eaf73d82faea98ad`.
Raw 576 outcomes SHA256: `25b833007f58ef59da32abbedce6684f403c8703b2dc4c7d96745f8bc3817f2b`.

The full evidence ZIP has 325 checked source/supporting files plus its own checksum manifest, including previous immutable checkpoint states, R54 prereg, exact matched-Q corpus, raw responses, student runner and read-only NumPy reproduction. These larger weights are **not in Git**, so this page alone is not a neural replay. For clean extraction: `python verify_r54_package.py`, then `python r54_verify_erratum.py verify` and `python r54_verify_erratum.py numpy`.

## Evidence interpretation and handoff

**[更新]** A semantically irrelevant but *valid SLE* third operand changes the learned model's firstword prediction (50/144 paired greedy changes), even with its output truth fixed. **[取代]** The R53 failure might merely be the artifact of suppressing the nonzero one-hot encoding of zero. **[原因]** This paired intervention changes a valid token to another valid token without deleting any features. **[狀態]** Reproduced observed effect high confidence; internal representation mechanism medium-low; unseen numeric skills and learned autonomous source choice unproven.

U = author's desired small NN study boundary; F = fixed R50/R52/R53 checkpoint archive, public Git handoff (including P030–P035 and UR1); T = this run's real 576 free responses and independent replay; A = possible learned nuisance/context dependency. NVIDIA calls 0 (no authorized callable live OpenRouter worker here), local Codex 0, Gemini 0.

**Next owner:** independent NN worker. To meaningfully advance *learning*, preregister matched-compute **input-dependent source gating vs static R52 learned gates**, separately held-out legal numeric/role domain, retention and full answer+STOP joint criteria. R54 paired corpus is now exposed and **must not be reused as a newly blind evaluation set**. Keep math teaching as a distinct forthcoming curriculum; R54 does not teach arithmetic.
