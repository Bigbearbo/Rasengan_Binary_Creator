# R52 PRE-TRAIN FREEZE — learned cursor-conditioned source gating
Date 2026-11-15; independent SLE native 01 small-NN lane. Source R51 PR #102 head `03a03709477d459379287c0149e6c2779cab8178`.

This document was committed BEFORE any R52 neural training or new test generation. Full prereg JSON SHA256 `026e3adb5b38114572ec27cd3eb06fb23d17d59180e69eb42601fc08af8c815e`; frozen Python runner SHA256 `4fdbada2112eb6741cee7b08435c5d2df0c89354d6586b9e4fcc6b7d8a3e5c46`. These complete files remain in a separate sanitized companion archive; the Git receipt is not sufficient by itself for neural replay.

## Single causal intervention
Three **immutable R50 frozen 10,457-weight** backbone students (seeds 101/202/303). Add **eight learnable sigmoid source gates**, arranged as 2 cursor-role rows (first answer word positions 0..5, second word 6..11) × four input word sources (a,b,c,d). Both rows are initially unbiased (all logits 4.0). Fixed R50 neurons, decoder and STOP logits remain unchanged; at STOP mask is disabled. **Only these eight gate parameters receive Adam updates**, with teacher-labelled raw-01 answer prefixes; no gold answers during autonomous free output. Unlike R51, do NOT explicitly set b-only for the second-word learner. Positional region is engineered and is a limitation, not a learned general grammar.

Legal SLE-AE1-n5-v1 (n5, values 0..29, r1/r2). Exact 39-bit raw question `01+010+bin3(r)+0+4*(bin5(v)+0)+111100`; raw answer `r*(bin5(v)+0)` with external stop class S, NOT wire sentence punctuation.

Train: original R50 136 course events, **1272 non-STOP targets** at first/second answer cursors (no new lesson). Deterministic sampling with replacement, RNG seed+52001, **500 updates per seed**, batch 64, Adam lr=.07, no early stopping, 1,500 total updates, 96,000 target presentations, backbone forward dense MAC proxy 1,048,320,000 (10,920 each; gate ops/backprop excluded). Parameter count 10,465 / trainable 8. Test: 80 previously used historical retention, 96 previously inspected legacy and 96 already inspected R50/R51 new-exact contexts, ×3 seeds=816 free answers. **There is NO blind new numeric-value test**. Baselines are stored frozen R50 unrestricted and R51 externally b-only replies. No equality claim about training or extra parameters vs those baselines.

## Predeclared ALL-required gate (else FAIL)
1. Fresh context secondword at least R50 +48/288.
2. Fresh context firstword at least R50 −12/288.
3. Fresh context complete answer incl autonomous STOP at least R50 28/288.
4. Historical retention complete answer at least R50 210/240.
5. For **each seed**, learned firstword gate weight on a > every other source.
6. For **each seed**, learned secondword gate weight on b > every other source.

Keep per-seed raw bitstrings, error cases, learned gate values, PyTorch and independent NumPy replays; never retune based on test. A pass would show only learnable cursor-conditioned preference on this exposed r1/r2 task, NOT autonomous generic selection or universal copying.

Source and checkpoint SHA256 are frozen in accompanying r52_prereg.json; parent R50 ZIP SHA256 `0f41050c5b09ca46465995e8779fc1530c37c2ff7a6d5ad5a3b4df415a6981e1`; R51 ZIP SHA256 `77b3352c42e6e51dbc0dd1c70d087783f238b3671dee2c465bbc479ac6cdac1f`. Static prereg check PASS (no neural forward).

Provenance: U user mandates independent native-01 NN research. F referenced Git P030–P035/R50/R51 sources and immutable checkpoints. T no new R52 neural evaluation or update at freeze. A model hypothesis: eight supervised gates can learn source specialization; outcome unknown.

NVIDIA actual calls 0: no live authorized callable NVIDIA endpoint here. Codex/Gemini calls 0. Do not modify Pro UR1, Codex, parser, VM branches, or merge automatically.
