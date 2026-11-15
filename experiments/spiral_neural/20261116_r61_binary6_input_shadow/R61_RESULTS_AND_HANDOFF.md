# R61: SLE-n5 fixed numeric tokens ↔ binary6 input isomorphism (actual NN training)

**Owner**: independent scheduled small-neural researcher. **Base**: R60 Draft #111 head `f22721d54f751beee33ba7e0a8145e3b5437590c`. **Freeze before any R61 NN computation**: commit `651a64b879123aa8cf2dfcd42d4cacaa00242a72`, see [frozen prereg](R61_FROZEN_PRETRAINING.md). Date: November 16, 2026, Taiwan.

**Single factor**: each SLE numeric token (legal `SLE-AE1-n5-v1`) is `bin5(v)+0` (6 bits), compared with ordinary binary6 `0+bin5(v)`, v=0..29. The latter is a NON-SLE shadow, not an invented legal profile. Permute pretrained, frozen source encoder input columns by the matching six-bit rotation. Same 39-bit framing, roles, 01 input alphabet, canonical SLE output bits and host STOP. Only eight gate logits trainable on both sides; **this is a coupled-initialization input-only control, not an independent cold-start or all-system codec comparison**.

136 authentic R52 course events, 1,272 nonSTOP training targets; NumPy sampling `default_rng(seed+52001)`, batch 64, Adam lr 0.07, 500 updates each × seeds 101, 202, 303 = **1,500 actual updates, 96,000 target presentations**. Each model 10,465 params (10,457 frozen backbone + eight trained). Train forward dense MAC **1,048,320,000** excluding backward; inference+diagnostics **13,516 forward calls / 147,594,720 dense MAC**. No model/LLM oracle computes predictions.

272 paired Q: 80 historical retention, 96 legacy, 96 previously-exposed novel combinations ×3=**816 newly generated binary6 NN answers**. None are truly unknown Q/domain, hence **NOT a new blind generalization test**.

| Fixed prereg gate | R61 actual |
| --- | ---: |
| Legal source SLE + paired numeric shadow | 272/272 PASS |
| Coordinate-rotated training input onehot | 1,272/1,272 PASS |
| All three trained gate-logit max abs vs R52 <0.01 | **0.00000190735 PASS** |
| Same R52 vs binary6 autonomous answer incl STOP ≥810/816 | **816/816 PASS** |
| Correct-prefix first/STOP max logit abs <0.005 | **0.00000381470 PASS** |
| Independent NumPy generation replay | **816/816 PASS** |

**Joint six-gate result: PASS.** Complete answer exact both representations **286/816** (history 220/240, legacy 0/288, exposed-new 66/288); no difference in any of 816 free answers. Three real training students, and independent NumPy replay; this is not just testing a parser.

**Falsification boundary:** for fixed width, changing a trailing zero into a leading zero and relabeling the encoder cannot by itself yield SLE learning advantage; this does *not* refute variable-width SLE or natural language grammar, nor show any mathematics/STOP/framing acquisition. R60 previously found fixed framing bits ignored by the architecture; this test does not fix that.

Immutable local source artifact:
- prereg SHA256 `813f91a308c2d3da26601ccac761ff5e4d064293d5e7e98064b021397dfcb500`
- paired raw-bit manifest SHA256 `9e82173c8223da698da1b5198a6afb57345592a6d87e89e38ef4576b99f9c012`
- actual training/replay runner SHA256 `845dd2507c7702053ea270d8d2fee5a4e57fb37245d8f52be3cb18f072a3b76b`
- raw 816 outputs SHA256 `824d6396094db87d8d689568eb763be673d666aad3530e9843fd6052f7649715`
- packaged complete R61 source / old checkpoints / answers / gates ZIP SHA256 `ac09f30323dd078bd0445935ebd0aa58eecf94dd5f0049cbe8c6805e5c431526` (395 files)
- complete Markdown result SHA256 `bdf9aab7606541e5ff72523c4480565499a2c10291aeb04b80c0dfc5dce3b41c`

**Public verifier**: [R61_PUBLIC_VERIFY.py](R61_PUBLIC_VERIFY.py) works against clean extracted ZIP, requires Python stdlib only. `python R61_PUBLIC_VERIFY.py .` checks SHA, manifest, output evidence, gates. Full NN replay: `python r61_binary6_input_isomorphism.py numpy` with PyTorch/NumPy imports. Clean extracted ZIP 395/395 SHA, public receipt verification and 816 NumPy replay all PASS. Git holds public prereg/report/verifier; **full training runner and checkpoint binaries/text are in complete ZIP, not claimed to be hosted in this PR**. Initial wrong manifest filename was repaired before freezing and before neural work.

**U/F/T/A**: U author specified independent native01 small NN learning and ordinary binary comparison; F historic R52 model/course, R60 #111 and P030–P035 source; T three newly trained seed models, 816 free generations and independent replay; A the parameter-isomorphism hypothesis confirmed in this controlled configuration. NVIDIA/Codex/Gemini actual calls each **0** (no authorized accessible local NVIDIA worker); no changes to Pro UR1 #12, Codex P030–P035, Hamster VM, syntax trees, main. No auto-merge.

**Next owner**: independent small-NN researcher. More useful next factor than repeating bit rotations: give the student a trainable legal framing input with a controlled curriculum and legal error/decline output, measure genuine learned structure; or test variable width / version profiles against a *properly matched, from-scratch* ordinary binary baseline across new heldout domains. Do not reuse exposed 816 Q as fresh evidence.
