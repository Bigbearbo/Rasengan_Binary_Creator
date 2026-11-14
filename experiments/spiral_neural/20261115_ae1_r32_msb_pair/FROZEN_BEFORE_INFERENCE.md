# R32 PRE-FORWARD FREEZE — 2026-11-15
work_id: SLE-AE1-R32-A-MSB-PAIR-20261115
owner: independent scheduled small-NN researcher; parent PR #81 (head 0fdbf0c79b4a91d2d492426c3854d3d188b07773)
stage: FROZEN; zero new NN inference or optimizer updates at this commit
Legal profile: SLE-AE1-n5-v1. Input is exactly 39 raw 0/1 bits (01 + 010 + 0010 + four 6-bit data words + 111100); r1 echo output is 6 data bits then external S.
Factor: within each pair change ONLY first data word a: 12→28 or 13→29; zero-based raw Q bit 9 (the first significant bit of a) flips 0→1. b,c,d,r, labels' other five answer bits and checkpoint remain fixed. No hard firstword mask.
Frozen arms: pretrained R30 unmasked (PR #80), R31 c2 nuisance course (PR #81), same 10,457-param architecture, 3 seeds 101/202/303; no retraining or teacher oracle to generate student answers.
Train: historical same 136 teaching appearances / 1408 teacher-forced targets / 3300 optimizer updates per seed per arm; a=12/13/28/29 absent from all input-word positions in training; fresh updates 0.
Calibration: 8 matched pairs = 16 raw Q; b16/17, c0/2, d0. Test: 16 matched pairs = 32 raw Q; b16/17/20/21, c0/2, d1. Thus 24 pairs, 48 raw Q, 288 free generations across 6 immutable checkpoints.
Predeclared success gate (ALL required, only on TEST):
1. R31 minus R30 on a12/13 low-side firstword correct ≥ 6/48;
2. R31 minus R30 on a28/29 high-side firstword correct ≥ −4/48;
3. R31 both-side fully correct first answer word ≥12/48 paired seed-context cases;
4. Each seed low-side firstword degradation no worse than −4/16.
Always report bit flip on 1st output bit, full answer, true-position STOP, exact errors and failures. Never adjust gate after seeing outputs. Calibration cannot be used to revise gate.
Important provenance limitation: two numerically distinct a-pair types are repeated across contexts, NOT 48 independent high-bit generalizations. a28/29 were seen in previous *evaluations*, but never in these training courses; test d1 combinations are absent from R31 prior manifest. a12/13 are absent even from prior training vocabulary roles.
Costs: 0 training MAC this round; 10,920 theoretical dense MAC per new forward call, full calls reported after execution. No VM/parser/UR1/P030-P035 reruns.
Canonical raw manifest SHA256: bfdc7e5d52a03940c43fb8d75decc8c0dbfd4d9aded8f680984c06a033e9cac9
Frozen full prereg JSON SHA256 (available in companion): 6912998cce56f8a875eb24b02b49250191613da514e85ed3d5d9b56d6b3c3989
Frozen complete experiment runner SHA256: 7a9169a6ddf34a4a9c87d1d331c343e23626873741994636620de3365bd99d82
R31 immutable source companion ZIP SHA256: 961bad8563c23363c71812aab1c22b961c7f1f022b1896d3f107c3f19059776f
T before freeze: ONLY local static codec/profile/48-row generation/source-and-checkpoint hashes; no new NN forward. A: check whether prior c2 lesson transfers to novel lower a-values and 1-bit MSB pair. U: user's independent NN generalization goal. F: PR #80/#81 checkpoints and source. No NVIDIA/Codex/Gemini authorized runtime calls (0).
Write scope: experiments/spiral_neural/20261115_ae1_r32_msb_pair/ on own branch. No automatic merge and no change to other worker branches.
