# AE1 R13 — PRE-TRAINING FROZEN EXPERIMENT (2026-11-14)
Status: pre-registered before any R13 optimizer steps or neural evaluation. Owner: independent scheduled SLE small-NN worker. Git main base d032a825c2b419f365bf34a531baee3b53b91750. Do not merge automatically.

Work ID: AE1-R13-BIT8-CURRICULUM-20261114. Exact profile: SLE-AE1-n5-v1; native input `01+010+r3+0+4×(5bit ID+0)+111100`; teacher output `word(a)+word(b) for r=2`, followed by STOP S (not an input bit). 39-bit Q. F32 shared-word encoder, 10,457 parameters, 10,920 forward dense MAC per target. No LLM oracle.

**One curricular factor**: replace the 16 injected r2 first-answer a=16,17,18,19 examples (4 low b values 0..3; c=0,d=1) with identical 16 templates using a=8,9,10,11. Keep all 120 parent lessons, 136 presentations, 112 unique lessons, 1408 teacher targets per epoch, model and initial seed. Original control: immutable tied checkpoints of PR #55, reused without re-training. New treatment: three from-scratch tied models at seeds 101/202/303, Adam lr0.003, clip_norm1, 150 epochs, batch64, exact 3300 updates/student (9900 total), total new forward-only training MAC=6,919,488,000 (excludes backward). The first answer bit8 has 0 positive examples under control vs 16 in treatment; 16 bit16-positive cases in control vs 0 in treatment. Thus replacing one bit-position exposure, not claiming a completely isolated neural mechanism.

Validation: a12 x b[0,1,2,3,18,19,22,23] r2 c0 d1 (8). Primary fixed test: a13,14 x same b (16); a12..14 never occur in any training input word in either arm. Seen retention: r1/r2 a0..5 x b18,19,22,23 c0 d0 (48). Taught injections each arm: 16×2 sets. Total 104 unique valid Q/student. Validity check: legitimate word range ID0..29, never infer a grammar version. Holdouts are student-unseen compositions, NOT independent researcher-blind.

**Pre-declared gate**: >=2/3 paired seeds have treatment primary exact >=4/16, advantage over frozen control >=4/16, treatment seen retention >=40/48, treatment taught injection >=12/16. No extra epochs/seeds, no best-checkpoint cherry-pick, no swapping val/test based on result. Report failures and all raw outputs.

Provenance: U=author's long-run NN/SLE learning goals; F=PR #55's six F32 trained models and source, PR #59 prior bit8 outputs, historical P030–P035, Pro UR1 #12 separate; A=first-bit8 positive target coverage may matter; T BEFORE THIS COMMIT=static local source/profile/count gate PASS, zero new NN forward and zero optimizer. Current R13 work is independent of Pro UR1, Codex E4/F3 and Hamster VM.

Source immutable byte digests frozen *before training*:
- Original PR55 companion ZIP SHA256 53f6e312f30570ef7d458f35b25c17b49eb7b161415bb5d3b165645aeb8f10a0
- Original run.py SHA256 79ac66bd8f2c2fd82b559310bc44e0eae05e3cb23949d1dd9af14e80048acf9a
- Parent course SHA256 e63d60db2b4f3fe316c76712e20d010eeb1a43d1afa8e15aa3faec9619e72f6a
- New train_bit8.py SHA256 8d2fa0224c86a189859e5046e52d10815a33da5989364e11580b9c201cc21c99
- New native 104-question cases.jsonl SHA256 8e9ab96501706fbb6d508955e559ccf8b20c50e41f7a0aaf1175d268bb484ed4
- prereg.json SHA256 df0dd16aab55da09177810f33e935b9546b2e5b31280b222585366c7a73aa82b
All complete code, JSON, actual checkpoints and raw outputs will be supplied as companion ZIP; Git freeze records their exact hashes before any NN execution. These are sanitized synthetic technical artifacts only, no private chat or API key.

NVIDIA: skipped_unavailable (no authorized reachable endpoint), actual calls 0. Codex and Gemini not invoked. No automatic merge. Next owner: independent NN verifier, then separate fresh testing of output bit-position compositional transfer.
