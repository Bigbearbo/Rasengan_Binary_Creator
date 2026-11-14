# R25 FROZEN before any new NN inference (2026-11-14)
work_id: SLE-AE1-R25-D4-D5-OUT-OF-DOMAIN-20261114
owner: independent scheduled SLE NN (not Codex/Pro/VM/parser)
source: PR #74 R24 fixed source, six genuine R20/R23 checkpoint states
profile: SLE-AE1-n5-v1; 39 raw input bits, r=1, expected=first 6-bit word+STOP
unique intervention: change ONLY d=4 versus d=5 (one raw input bit); c=0 versus c=2 is a paired nuisance stratum, not a training change; R20 vs R23 arms are historical fixed weights.
calibration (not used to retune gate): a=0,1; b=8..11; c=0,2; d=4,5; 32 questions.
formal test: a=2..5; b=13..16; c=0,2; d=4,5; 64 questions.
seeds: 101,202,303; student count 0; training updates 0; reused checkpoints 6; parameters per network 10457.
dense forward MAC per position 10920; inference count observed, not predetermined exact, cap 32 greedy positions +1 STOP logit per Q per net; maximum 6*96*33*10920=207567360 MAC, excluding independent replays.
model output labels: 0,1,S; teacher answer computed offline only for scoring and teacher-position STOP margin. No teacher oracle at inference. STOP margin = logit(S)-max(logit(0),logit(1)).
predeclared JOINT gate per seed for EACH d=4 and d=5 (test has 16 per c and d):
(1) c2 mean teacher-forced STOP margin R23-R20 >= +0.75;
(2) c2 greedy first word correct R23-R20 >= -1 of 16;
(3) c0 STOP correct R23-R20 >= -2 of 16;
(4) c0-versus-c2 first-6-output invariance count R23-R20 >= -1 of 16.
Pass requires both d and at least 2 of 3 seeds. ALL metrics including exact full answer and failures published even if gate FAIL.
novelty preflight: all 96 questions disjoint from historical R20/R21/R22/R23 and R20/R23 training, and d4/d5 OOD vs prior R24 d3.
manifest SHA256 (local frozen exact JSONL): 0465f40a29cd9a9c9069cad739e2dbb2018d8fce29fedc72328b290d7ffbbefb
r25_probe.py SHA256 (local frozen code): e2c02b935c45b3a8f5b7fd1c73ad611e663d61d630ae8dfa9f06352aaa4f43f1
r14_source/run.py SHA256: 79ac66bd8f2c2fd82b559310bc44e0eae05e3cb23949d1dd9af14e80048acf9a
experiment_r20/run_r19.py SHA256: dbfad19c66ae2dd3f20113e8eb7e965fd576f9984462fd6a82c029897a28f15e
r23_experiment/verify_numpy.py SHA256: 5fe9ad091593963c4a3cd8dbc97923b5609c0a79c7ff3e84027a6f139c866e32
weights are frozen and verified by 6 SHA256 entries in companion prereg.json (complete ZIP).
Limit: fixed-weight transfer, no general SLE acquisition claim. Stop margins do not imply full copy. U=user small-NN direction, F=historic actual source/checkpoints, T=preflight only until evaluation, A=possible context interference; confidence low until measured.
NVIDIA status: skipped_unavailable; no authorized worker endpoint exposed to this runtime, actual calls=0. Codex/Gemini actual calls=0.
Git branch is isolated, PR remains draft, never auto merge.
