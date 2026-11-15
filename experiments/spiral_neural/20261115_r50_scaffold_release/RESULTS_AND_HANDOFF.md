# R50: temporary b-only scaffold then unrestricted training — real 3-seed negative result

Date: 2026-11-15. Isolated SLE neural workstream, based on independent R49 PR #100 (`b33cf25bba0274f32606e507c6d513198a8b28b8`). Pre-neural public freeze **`e5ad397add34a3432b21daaf698f4e132d58fe28`**, see [PRETRAIN_FREEZE.md](PRETRAIN_FREEZE.md); freeze prereg SHA256 `492a447a2629e9f358d4a9e87a3206ea861023dc182c20a9721a81372a13be8a`, manifest `ff2d3801b5e413bf977a9f9b2bfbf18b1a97e0a9f6b643f11e4d48c51af8478c`, executable runner `6514f7a99ffb7ccf5958e9a4b5cde8847685d4d489f38ac7b1b4a4fc81683dde`.

**Single factor:** unlike R45 (unmasked `a+b+c+d` throughout), R50 uses original b-only engineered second-answer-word route in epochs 0–89 and all-input route for epochs 90–149, then **all-input inference**. R44 permanent b-only is an archived positive engineering control. No new dynamic route selector; not evidence for learning a selector.

**Profile:** legal `SLE-AE1-n5-v1` 0..29, 39 raw 0/1-bit question, up to two 6-bit words + *external model STOP action* `S` (not an on-wire punctuation token). 136 identical balanced R44/R45 lessons, 1,408 teacher-prefix targets/epoch, seeds 101/202/303, Adam lr.003 clip1, 150 epochs, 10,457 parameters/student; exactly **9,900** updates, **633,600** target presentations, **6,918,912,000** theoretical forward dense MAC excluding backward. 96 historically examined test Q, 80 previously examined retention Q, **96 new exact-Q contextual combinations** (a in 4,5,8,9; (c,d) in (4,7),(5,8); b18..29), checked against prior raw-Q manifests and training; b-values **NOT** globally blind. Full prereg checks before training, no extra seeds, no retune, no previous model retraining.

## Results: prereg combined gate **FAIL (1/8 PASS)**

| Three seeds / criterion | R44 permanent b-only | R45 all-input historical | R50 released |
| --- | ---: | ---: | ---: |
| Old b18/19 second word | 48/48 | 0/48 | **25/48** |
| b20–23 second word | 80/96 | 0/96 | **18/96** |
| b24/25 second word | 48/48 | 0/48 | **14/48** |
| b26/27 second word | 48/48 | 2/48 | **30/48** |
| b28/29 second word | 48/48 | 1/48 | **11/48** |
| Old retention full exact including self STOP | 228/240 | 209/240 | **210/240** |
| Prior 96Q full exact | 0/288 | 0/288 | **2/288** |

Predeclared minimums: b18/19≥32, b24/25≥32, b26/27≥32, b28/29≥24 (all /48); b20–23≥48/96; retention≥216/240; new-context b28/29 second≥24/48; at least one new-context exact full output. **Only last condition PASS.**

## First-time exact-Q context panel and post-hoc controls

After finishing R50 gate, two **archived frozen** R44/R45 student arms were evaluated (no training) for the exact same 96 new-context Q × 3 seeds:

| Newly assembled exact Q, 3 seeds | R44 frozen | R45 frozen | R50 |
| --- | ---: | ---: | ---: |
| First word | 45/288 | 19/288 | 54/288 |
| Second word | 272/288 | 28/288 | 86/288 |
| Autonomous entire answer, including STOP | **38/288** | 4/288 | **28/288** |
| b28/29 second word | 48/48 | 9/48 | **14/48** |

R50 is better than R45 but **worse than R44** on full exact and second word. Its 28/288 nonzero full-exact is not a breakthrough; the weak existential gate was predeclared but 7/8 failed. R50 new-context full exact by seed: 7/96, 7/96, 14/96; legacy second by seed 26/96, 31/96, 41/96. Historical retention by seed 69/80, 68/80, 73/80. STOP given the *correct* answer prefix was 812/816, which does NOT equate to autonomous correct full answer. No comparison versus ordinary binary-6, and no genuine previously unseen numeric values.

## Actual executed work and archive

Commands run: `python r50_scaffold_release.py freeze` (BEFORE Git prereg and training); `python r50_scaffold_release.py static` PASS; `python r50_scaffold_release.py train` trained exactly 3 models; `python r50_scaffold_release.py replay` **816/816 native PyTorch**; `python r50_scaffold_release.py numpy` **816/816 independently implemented NumPy** (max STOP logits delta 2.861e-06); `python r50_posthoc_fresh_controls.py` historical checkpoints infer 576 first-time new exact-Q responses; `python r50_posthoc_independent_numpy.py` **576/576 NumPy**. ZIP extracted in an independent clean directory: `python verify_r50_package.py` **288/288 SHA256**; static/replay/NumPy/posthoc-NumPy all PASS, `unzip -t` PASS. 816 original R50 student outputs and 576 archived-control post-hoc outputs preserved including failures; train log, splits, full executable runner, 3 R50 weights, immutable old controls and associated SHA checks in companion archive.

**Complete original runnable companion (provided in conversation, not hosted by this Git repository):** `sle_ae1_r50_scaffold_release_20261115.zip`, ZIP SHA256 `0f41050c5b09ca46465995e8779fc1530c37c2ff7a6d5ad5a3b4df415a6981e1`, 3,705,774 bytes. Public repository records prereg, result, verification entrypoint and **does not claim to contain all weight bytes**, so Git alone cannot replay the NN. Do not substitute old PR #100 archive.

Example failure, seed101, (a,b,c,d)=(4,18,4,7): Q=`010100100001000100100001000001110111100`; expected=`001000100100S`; student=`000000000000S`. Example actual success seed101 (5,27,4,7): Q=`010100100001010110110001000001110111100`; expected=student=`001010110110S`.

## Provenance and handoff

**U:** requested independent SLE 01 neural study, not VM/syntax. **F:** branch-specific Git guidance, P030–P035 and UR1 preexisting evidence and R44/R45/R49 checkpoints. **T:** R50 actual 9,900 updates + native and independent replay, plus first-time frozen R44/R45 inference on same fresh-Q panel; historical PR figures never relabeled as new training. **A:** early scaffold may help learn b-dependence before all-input interference; mechanism not established.

[更新] External b-only **temporary** scaffold helps preserve some second-word capability over fully unmasked R45, but does not reliably solve all-input autonomous generation.  
[取代] Early hard scaffold alone should enable a learned general-purpose source selector after release.  
[原因] Seven preregistered gates failed; new exact-Q complete 28/288 is below existing hard-route R44 (38/288).  
[狀態] This experiment's measured performance **high confidence**; learned internal source mechanism **low confidence**.

**Next owner:** independent SLE NN research; before spending another full train, diagnose firstword vs secondword interference on fixed checkpoints and freeze a legitimately new legal value/role domain with matched ordinary binary6 baselines. The b18..29 domain is now exposed. This workstream must not run or modify Codex's PR #12 target-shuffle work, Pro manifest, Codex whole-region/句號 line, Hamster VM, main, or merge stacked PRs. NVIDIA=skipped, real calls=0 (no authorized endpoint); Codex=0, Gemini=0. No private conversations/API keys in archive or Git.
