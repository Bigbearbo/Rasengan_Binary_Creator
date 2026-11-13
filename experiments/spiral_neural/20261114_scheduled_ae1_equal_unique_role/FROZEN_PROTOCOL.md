# SLE-AE1 equal-distinct-sample role exposure — frozen before optimizer (2026-11-14)

## Scope, parent and single factor
Independent native-01 small NN, not VM, parser or Pro/Codex UR1. Base exact PR #53 commit `61cf62856bbc20bacc779cc7c4b7953ae733cee3`; source learner frozen PR #40 seed 101/202 checkpoint, 10,499-parameter tanh MLP (L80,H64) and 120 immutable parent lessons (96 distinct). Two arms with exactly the same high values 16..19 and low values 0..3, in 16 additional r2 lessons: high value as first answer word (`first_high`) versus second (`second_high`). Both arms set irrelevant suffix c=0,d=1 (old parent ALL d=0), preventing the unequal-parent-overlap flaw in PR #53. Both have 136 presentations, **112 distinct cases** and 1,408 correct-prefix targets per epoch, and the same target token histogram.

The only between-arm policy factor is the high/low answer-slot swap. Setting d=1 in both arms also means a cross-study comparison with PR #53 is confounded by suffix context; the within-run arm comparison is controlled for it. This is not a new SLE grammar or a mathematical problem bank.

## Exact reproducible immutable local artifacts prior to NN work
- Code `run.py` SHA256 `edae40874fd937616e4f7a93e642dddf75d010e7cc02f1dea757e0bd24a55f1f` (10,780 bytes).
- Per-arm evaluation manifest `cases.jsonl` SHA256 `2eaf6ff3293a398322fbf4668407a9164b818886a6daf7c386f0b49fb9a0121f` (33,600 bytes, 256 rows).
- Parent `parent_course.json` SHA256 `e63d60db2b4f3fe316c76712e20d010eeb1a43d1afa8e15aa3faec9619e72f6a` (1,478 bytes).
- Parent seed101 F32 checkpoint file SHA256 `ac022fdcac1c6e9de5b78e1667519a6443e05c7f8e48fe4b84514432a1576009`; seed202 `048c719e8c2afbbcac579b80a2f820989eb68ba030a1f2ce7c2747474897a157`.
- Local full `prereg.json` SHA256 `3a1d1356829a895b81d39cb632b417a544777f0a645658ae612bbc7b57380306`; the local complete ZIP, including source weights, will be supplied as a companion artifact, not secret upload.
- Encoding SLE-AE1-n5-v1: Q39=`01`+`010`+r(3 information bits + terminal0)+4×(five data bits +terminal0)+END `111100`; r=1/2, IDs0..29 only. Answer is first r full data words then **self-generated** external STOP; no teacher LLM, padding-as-zero, forced truncation, hidden word/role embedding or answer-length oracle.
- Python/PyTorch CPU, deterministic algorithms enabled, two paired seeds101/202, each starts same immutable parent weights with **fresh** Adam moments in both arms (optimizer history unavailable), lr0.003, batch64, 100 epochs, 22 mini-batches per epoch, 2,200 optimizer updates/student; 4 students total 8,800. Training 563,200 target presentations and 5,875,302,400 training forward dense MAC, excluding backward and optimizer; 10,432 MAC per forward.

## Evaluation gate fixed before train
Each student evaluates exactly 128 valid native Q39 strings, with arm-specific exact taught controls (not wrongly called 'taught' when only an untaught pairing):
- 48 known baseline: a0..5 × b18/19/22/23 at r1 and r2 with c0,d0.
- 16 **exact injected** r2 questions for its own arm (actual taught Q, c0,d1).
- 16 val first-role transfer: a20..23 × b18/19/22/23 (numeric values seen as former second outputs; not new numbers) r2,c0,d1.
- 24 student-unseen values: a24..29 × same b choices r2,c0,d1 (these never appear in either input or output during current training).
- 24 paired suffix diagnostics: same student-unseen a,b but d=0; **not** an independent test set.

Per-seed strict PASS iff first_high val+test at least **8/40**, its lead vs second_high at least **6/40**, and EACH arm retains **40/48** baseline. Otherwise FAIL regardless of exploratory figures. The student-heldout 24..29 set is not investigator-global-blind: earlier studies probed overlapping values and bits. Report outcomes of both seeds; no added seed, retest epoch or revised manifest after seeing results.

## Preflight, provenance, limits and next owner
Before training, verify all SHA256, exact 136/112 course counts and 1,408 target positions, source F32 model hashes, teacher-label histogram, legal manifest of 256 unique-per-arm Q, value/split absence, exact Adam/MAC budget. Keep all raw Q/expected/actual errors and terminal decisions. After inference, load weights with independent NumPy implementation and require per-reply equality; preserve negative results.

U=raw-01 independent student education. F=PR #40 immutable checkpoint and PR #53 repetition confound. A=the possibility that high-first lessons help transfer independently of distinct-sample coverage. T=only commands truly executed after this freeze, to be recorded later. NVIDIA read-only review only with authorized callable worker; no known live OpenRouter credential, initial actual calls0. Codex desktop0; Gemini0; teacher LLM oracle0. No auto merge or mutations to other work branches. Next owner: independent small-NN reviewer, and later a genuinely withheld distribution/split if this limited gate improves.
