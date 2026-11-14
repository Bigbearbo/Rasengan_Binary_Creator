# R27 frozen preregistration — first-word curriculum
Status: PRE-TRAIN FREEZE (no optimizer result in this commit). Owner: independent scheduled SLE 01 NN. Date: 2026-11-14.
Scope: separate from P030-P035 / UR1 / VM / syntax-tree engineering. Origin: archival R26 ZIP sha256 `2c945803a5336820a5f17c72daaaa7cd1a9a46f9b9299c0fc0af87d1cbe115e3`. Immutable control R20 has 3 original neural checkpoints.

Single manipulated factor: among 136 R20 original teaching events, replace only 24 early r=1 first-data-word `a` values, indexed 0,2,...,46, with 24/25/26/27 repeated six times. Do NOT modify r, b, c, d, examples count, target count, initial seed, input/answer grammar, 10,457-parameter R20 DualRoutedStudent architecture, Adam (lr .003/clip 1), batch64 or RNG/permutation policy. This deliberately changes firstword supervised labels; it is a *curriculum intervention* and not an architecture/codec advantage experiment.

Legal native raw SLE profile `SLE-AE1-n5-v1`: Q=01+010+three-bit r+0+four*(five-bit ID+0)+111100, length 39; r=1 answer=6-bit a + external STOP, not an SLE word. The student only sees native 01; deterministic generator makes offline labels, not inference oracle.

Total 136 appearances, 1408 answer targets per epoch, 150 epochs, 3300 Adam updates / seed, seeds [101,202,303]; 3 freshly initialized true neural students from seed+12000; control R20 original weights NOT retrained. Total 9900 updates, 633600 target presentations, 6,918,912,000 theoretical training-forward dense MAC (backward excluded; wall-clock and inference separately).

Frozen splits: 8 validation native Q r1 a26/27 × b18/19/22/23 c0 d1; 16 formal test unseen a28/29 × same 4 b × (c0,d0)/(c2,d1), where a28/29 never occurs in R27 training; 16 near-high diagnostics a20..23 × b18/19/22/23 c0 d0; retention 48 seen_baseline plus 32 taught_high inherited unchanged from R20. Total 120 raw Q. These are not globally researcher-blind because some high-bit concepts were previously studied. New train/test raw Q disjoint.

Predefined gate: PASS requires >=2/3 seeds individually attaining (i) test 6-bit firstword correct increase >=4/16 against frozen R20, (ii) seen_baseline exact loss <=4/48, (iii) taught_high exact loss <=4/32, (iv) test correct-prefix STOP loss <=2/16. Report full generation/exact and STOP even on failure; no rescoring after looking.

Frozen artifact content hashes:
- runnable source `run_r27.py` sha256 `7ed975a5236f49d97f606aed6ae13b33bd010ae80591c503e19106c666c01399`
- full 120-case raw01 `manifest.jsonl` sha256 `5856ea02e4aff0d8386091b804f7fed886c5f3d7654b20aa024522945599b962`
- `prereg.json` sha256 `9fe6a3052de9e0830a331c95e2a1861deb3e827037963d93fdd4ac0c5793e421`
- 136-tuple course canonical JSON sha256 `7bd864cd07deb7cd724cad32450fc8a5eab5b86b88426d758ec55dda3f8d020e`
- source R20 weights SHA256 seed101 `4231d63398493d683b94ab572f846a9267d5a20ad6a39edcec0baf976801b464`; 202 `0b241799b07458b144a3d2b9a6cf42f61f082d9b1b8377359878e5075bab5a62`; 303 `58137a8d4dacd33c1597bbdaa901a32640eb79060c9a16ebba0af8b2227d435a`.

Examples of actual frozen raw bits Q -> offline answer: validation `010100010110100100100000000000010111100` -> `110100S`; test `010100010111000100100000000000000111100` -> `111000S`; near-high `010100010101000100100000000000000111100` -> `101000S`. Full 120-case manifest and runnable SHA-verified source packaged in final evidence; exact sha commitments above predate new student training.

U: user's request for SLE01 NN education, growth and generalization. F: R20/R23/R26 checkpoints, Git P030–P035 plus UR1. T at freeze: static preflight gate only (136 events, 120 legal 01 Q, hash checks). A: possible improvement on heldout a28/29; uncertain. No Codex/NVIDIA/Gemini inference calls. The next Git result commit must retain this freeze, all seeds and negative examples. Do not merge automatically.
