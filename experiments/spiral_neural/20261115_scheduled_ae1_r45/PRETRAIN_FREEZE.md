# R45 PRE-TRAIN FROZEN: balanced lessons without secondword hard b-route

Date: 2026-11-15 (Asia/Taipei). Owner: independent SLE raw01 small NN worker. This branch extends **PR #95** head `456c0127b62f32bcb896596be529e6c79fb803f9`; do not merge automatically.

**State at this commit: no R45 neural training, no new R45 neural forward pass.** Local reproducible R45 program, JSON prereg, and fixed test manifest have passed static checks; hashes below bind them. Record Git commit SHA before running the real experiment.

## Single experimental change
Control: **R44** trained `NoFirstMask`, whose second answer word has an engineered hard mask selecting only b. Intervention: **R45** trained original `WordStudent(True)`, reading a,b,c,d also for that second answer word. **Every other condition is the R44 curriculum and optimizer**, with identical initialized state tensors, same 136 ordered examples and the same 1408 target positions per epoch. A static architectural check verified that with identical weights, firstword and STOP operations are unchanged; only the secondword route differs. The original R44 three checkpoints/results are not retrained. This is a matched architecture ablation, not a new learner without all structural priors.

## Fixed materials
Legal profile `SLE-AE1-n5-v1`, integer values 0..29. Native question = `01+010+bin3(r)+0+4*(bin5(value)+0)+111100` = **39 raw 0/1 bits**. Answer = r six-bit numerical words + generated external STOP action S; S is not an on-wire SLE bit. Student receives only native Q and its own answer prefix at generation, not the offline teacher oracle.

Train: R44 frozen 136 events; 1408 supervised targets per epoch, batch64; 150 epochs, 3300 Adam updates per seed, seeds **101,202,303** (initialization seed+12000; shuffle default_rng(seed+201000+epoch)); Adam lr .003 and global gradient clip1; 10,457 parameters per model; total 9,900 updates, 633,600 presented targets, **6,918,912,000 theoretical training forward dense MAC** (backward, decoding and wall time excluded). No additional training, no cherry-picked checkpoints.

Validation/retention: R44 already observed 80 old Q (both r1/r2), 240 outputs. Test: 96 exact R44 Q, 288 outputs, a=6,7,10,11; b=18..29; (c,d)=(12,14)/(13,15). These question strings are outside the training set but were **already inspected in R44**; NOT a new blind test. b28/29 were not taught as the secondword role in R44, but have appeared in prior research. Full answer must include exact firstword, secondword AND autonomous STOP.

Prospective ALL-gate before neural run: secondword correct b24/25 >=40/48; b26/27 >=40/48; b18/19 >=40/48; b28/29 >=40/48; b20..23 >=72/96; old 80 Q exact >=216/240; **96 new Q exact >=1/288** (R44 0/288). Report each seed and failed cases even if FAIL. Separate teacher-correct-prefix STOP from spontaneous stopping.

## Frozen local artifact SHA256
- `r45_unmasked_balanced.py`: `9bcb929bea438ea39b3f18e4292f8147a06b4ecb77d1cf661f6bd7e3bedb05c8`
- `r45_prereg.json`: `d2fb8240d7619f791aaad8ed5207514b57cbccdf2c62d3cb3bba913cbbe0beba`
- `r45_manifest.jsonl`: `d8900796e8e50c116d9b780f42377e5ef40332623a3dd39a448903dec57e8416` (same test panel bytes as R44)
- Parent ZIP: `sle_ae1_r44_b2_balanced_curriculum_20261115.zip` SHA256 `a6dfa017ac4fc080ed723a530fe50471733c40e16d282cdc0bd35212ae01ec9f`.

Static validation actually executed (CPU, Python/PyTorch): `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python r45_unmasked_balanced.py freeze`; `... python r45_unmasked_balanced.py static` => **PASS** 136 lessons,96 test,80 retention,3 seeds,10457 params. A ZIP containing program, prereg JSON, manifest, source and checkpoints will accompany the eventual final report; this Git page alone is not executable.

Sources U=user's independent SLE NN education/generalization direction; F=PR #95 R44 frozen checkpoints & curriculum, PR #89 R39 unmask implementation, P030-35 reports, Pro UR1 #12, public Git AGENTS/handoff; T=static checks, **not** post-freeze training yet; A=balanced curriculum may or may not offset context interference. NVIDIA: 0 calls (no authorized endpoint/credential), Codex 0, Gemini 0. No private chat, API secrets, VM changes or grammar changes. Next owner: same independent neural researcher, execute fixed trial then publish actual negative and positive outcomes, independent replay, full raw 01, checkpoint SHA and next evidence owner.
