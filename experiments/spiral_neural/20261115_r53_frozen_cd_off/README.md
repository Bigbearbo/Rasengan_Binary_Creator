# R53 frozen firstword c/d ablation — actual result, FAIL

2026-11-15. Owner: independent native-01 small NN research. Parent: R52 Draft PR #103 head `bb5863d110f9238d941d4f2ecdb31f2957c4e936`. This branch does not alter Pro UR1 / Codex / VM / parser work. **Pre-inference public freeze** commit `9596e489961c72c11d685ba1cbc12afb2be717f5`, before any R53 neural generation. This is an exposed-data causal diagnostic, **not** a newly held-out value test.

Single intervention: frozen R52 model, preserve trained firstword a,b source gates, zero firstword c,d contributions for cursor 0–5; preserve learned secondword gates and STOP. No training; no backbone changes, no gate-logit updates. SLE-AE1-n5-v1, r∈{1,2}, a,b,c,d∈[0,29], native 39-bit `Q=01+010+bin3(r)+0+4*(bin5(v)+0)+111100`, answer `r*(bin5(v)+0)` plus external STOP class S. Seeds 101/202/303; each student 10,465 params, trained in this round 0, inference 15,148 forward calls, theoretical 165,416,160 dense MAC (10,920 per call); backward MAC 0.

| Paired exposed panel, all three seeds | R52 firstword | R53 firstword | R52 full exact + STOP | R53 full exact + STOP | Newly right / newly wrong |
|---|---:|---:|---:|---:|---:|
| Historic retention (240) | 240 | 167 | 220 | **150** | 0 / 70 |
| Legacy previously seen (288) | 0 | 54 | 0 | **35** | 35 / 0 |
| R50/R51 known fresh-context (288) | 78 | 96 | 66 | **76** | 40 / 30 |
| TOTAL (816) | 318 | 317 | 286 | **261** | 75 / 100 |

Secondword correctness did not change: total 544/816 for its role-specific metric (including a retention group largely of r=1, for which secondword is not applicable). Controlled gold-prefix secondword and STOP logits: **1,632/1,632 bit-exact unchanged**. Firstword outputs changed in 359/816, and firstword initial logit vectors in 816/816. New result independent replay: PyTorch 816/816 and separately implemented NumPy float32 816/816 PASS. Public compact PyTorch replay 816/816 PASS. Clean ZIP 315/315 member SHA256 verification PASS, plus clean public replay PASS.

**Preregistered six-way conjunction FAIL 5/6:** legacy firstword ≥1 PASS; legacy full ≥1 PASS; known fresh full ≥66 PASS; historic retention full ≥220 **FAIL (150)**; nonintervened logits 1632/1632 PASS; firstword changed ≥1 PASS.

By-seed legacy full 17/96,0/96,18/96; fresh full 21/96,21/96,34/96; retention full 45/80,50/80,55/80. Do not hide seed202 legacy zero or any originally correct examples now broken.

A concrete newly recovered legacy example: seed101 Q `010100100001110110110011000011100111100`, gold `001110110110S`, R52 `000010110110S`, R53 `001110110110S`. A newly wrong retention example with **c=d=0**: seed101 Q `010100010000010100100000000000000111100`, gold and R52 `000010S`, R53 `000000S`. The learner receives bit one-hot features: even the SLE encoding of numeric zero has positive features for the zero bits. Removing c,d input features is not equivalent to leaving numeric zero. The exact internal representation explanation remains a hypothesis, not proven.

Artifacts: entire **316-file, full-weight ZIP is a conversation attachment rather than stored in Git**, SHA256 `15171a95cd33aab632eb494ec83d08a280a5c7e44b92043532f36f83efb9f731`. Git contains immutable prereg, this report and [public replay code](r53_public_replay.py); ZIP has `r53_prereg.json`, `r53_frozen_firstword_cd_off.py`, `r53_outputs/raw_results.jsonl` (816 raw bitstreams), `r53_outputs/results.json`, old R52 checkpoint evidence, `verify_r53_package.py`, `R53_PACKAGE_SHA256.json` and detailed `R53_RESULTS_AND_HANDOFF.md`. The Git replay **requires** extracting the ZIP; Git alone does not carry weights. Runner SHA256 `94a91f480a3b1cea49bd86232b1a8af95b5bc9aa0801d78f75dc3df73a29e6e0`, public replay SHA256 `8f07b1d7ce940275d336a42825f03b49331329c513019aabdd3a60ed2536f5c4`, raw records SHA256 `61769f2862ca22f0d59974edd2455aa7a09d4b2debafae7db93f56ebe394453b`.

Run (after extracting package): `python verify_r53_package.py`; `python r53_public_replay.py`; `python r53_frozen_firstword_cd_off.py replay`; `python r53_frozen_firstword_cd_off.py numpy`. All executed this run, exact PASS.

[更新] Fixed-weight c/d removal can recover 35 exposed legacy complete replies, but destroys 70 retention successes and reduces total exact success 286→261. [取代] Learned high c/d firstword gates are safely removable as irrelevant. [原因] Learned representations encode even zero-valued c/d, so the ablation is distribution-changing. [狀態] Results high confidence; internal causal mechanism moderate/low.

U: user instruction to study true 01 learner, separate NN from VM and parser. F: Git R50/R52 original checkpoints, frozen sources and P030–P035, Pro #12 UR1 evidence. T: new R53 816 generations, checksum/replay tests, controlled logit parity, all failures preserved. A: learned nuisance-zero-feature dependency as candidate mechanism. NVIDIA actual calls=0, skipped because this runtime has no authorized live OpenRouter worker; local Codex=0, Gemini=0. No teacher model used to produce student answers; all expected bits from deterministic codec.

Next owner: independent NN researcher. **Do not fit another mask on the same 816 exposed contexts.** Predeclare a new legal genuinely held-out value split or larger legal profile, matched fair flat-binary control, and independently check retention, full autonomous outputs and STOP; if learning source selection, compare context-dependent gates with static cursor gates at matched budgets. This result does **not** establish generalization or SLE superiority.
