# R21 PRE-FORWARD FREEZE — one c-bit perturbation of r1 STOP (2026-11-14)

**Immutable preregistration, committed before new R21 student inference.** Owner: independent SLE01 small-NN research scheduler. Parent source PR #69 head `468f2a4d55a1d5d4b75499887dee12c5725568bc`; comparison R19 PR #68 head `b7aada524b85f2771f6b98e7cb03402804037968`. No UR1 authorization claimed, no modifications to Pro/Codex/VM or parser.

**Only varied experimental input:** in each matched pair change *third data word* `c=2 → c=0` (one raw payload bit). Keep native SLE-AE1-n5-v1 profile, header `01`, advanced echo op `010`, r=1, first data word `a`, second word `b`, fourth word d=3, position=6 (STOP), **six correct first-word answer bits as supplied prefix**, all network weights and routes fixed. The model ignores prefix bit *values*, but prefix determines cursor6. Both arms are *already trained* R19 dual-route and R20 conditional dual-route models, seeds 101/202/303. No teacher/oracle answering during inference; predetermined answer used only to fix prefix and score STOP against offline label. This is a research-seen diagnostic, NOT blind generalization, natural learned rule, SLE-vs-ordinary-binary proof, or new training.

**Exact paired panel/split:** a=[0,1] validation diagnostic, a=[2,3] test diagnostic; b=[24,25,26,27,28]; c in [2,0], d=3. Thus 10 matched validation pairs and 10 matched test pairs; 40 39-bit legal raw input Q, 6 checkpoints, 240 true neural forwards. Raw Q constructed as `01 + 010 + r(3b) + 0 + [a,b,c,d](each 5b + 0) + 111100`; offline expected `a(5b)+0+S`. One data bit difference per pair. Sources R20 original `test_r1_stop` 20 c2 cases; c0 are counterfactual questions. No training cases change or enter evaluation.

**Resources:** each checkpoint has 10,457 trainable parameters, one inference 10,920 dense MAC, total budget 240 forwards = 2,620,800 dense MAC. New optimizer updates: 0. Historical teaching fixed: 136 appearances/112 distinct, R14 base 120 plus 16 balanced highbit, r1 STOP target 60 and r2 STOP target 76 per epoch, 150 epochs/3300 updates per original trained seed. No replay optimizer, no budget extension or additional seed.

**Predeclared gate:** per seed on TEST 10 matched pairs, moving c2→c0 must recover at least **3** former wrong STOP argmax predictions **and** improve net STOP correctness by at least **+3/10**. Require at least 2/3 R20 seeds achieve this AND R19 frozen negative-control STOP class invariant and maximum absolute STOP margin change <1e-5 for all test pairs. Otherwise FAIL. Always report both validation/test and margins `logit(S) - max(logit(0),logit(1))`; save every prediction, including failures. R19 should be invariant by architectural masking; R20 change is enabled by its corrected r1 STOP route. No result-contingent retuning; test is researcher-seen.

**Source/version integrity** (SHA256, compare byte-for-byte before run):
- Original complete R20 ZIP: `9c698971dfd6fe1f89701be99fc2fa592edce006f017efd5c4e89dbdf5671866`.
- R21 exact `manifest.jsonl`: `d78c00bc7bf783c3a431a9dad76cee3a666393b634c05f742367e3540dba21b5`.
- R21 complete runnable `run_r21.py`: `270e248789c4de608e1c612a788fa82525b488b14a8f43a24b239652e820bb70`. Source file will be included with companion runnable evidence.
- `r14_source/run.py` `79ac66bd8f2c2fd82b559310bc44e0eae05e3cb23949d1dd9af14e80048acf9a`.
- `r14_source/parent_course.json` `e63d60db2b4f3fe316c76712e20d010eeb1a43d1afa8e15aa3faec9619e72f6a`.
- R19 `experiment_r19/run_r19.py` `2705913fe770783778cb45bed586eecfa397fccb86433cc0c9d392720c3da682`.
- R20 `experiment_r20/run_r19.py` `dbfad19c66ae2dd3f20113e8eb7e965fd576f9984462fd6a82c029897a28f15e`.
- R19 checkpoint seeds 101,202,303 SHA256: `19d6d58ae3c407619d4855ec9cbc5d7bee4df147398c163dedee82173483604b`, `0c4e470f840dc1065d804240320b0a220819c455419584d1454c0e306fdcf2f2`, `ec15c55f219dc2e95e89dd6c7ae631c47bf456be3169f777dca9f9da4e9adb5f`.
- R20 checkpoint seeds 101,202,303 SHA256: `4231d63398493d683b94ab572f846a9267d5a20ad6a39edcec0baf976801b464`, `0b241799b07458b144a3d2b9a6cf42f61f082d9b1b8377359878e5075bab5a62`, `58137a8d4dacd33c1597bbdaa901a32640eb79060c9a16ebba0af8b2227d435a`.

**Pre-forward engineering preflight:** local run `python run_r21.py gate --source-root ..` PASS (40 legal Q, 20 pairs, all hashes); 0 Torch NN forwards or training updates. A static gate coding typo was corrected before this freeze and before neural execution; this freeze covers the final SHA above. This file and the manifest must be published remotely before `diagnose` starts.

**Provenance:** U=author's independent NN/SLE teaching research mandate; F=R19/R20 original code and immutable checkpoints; T=only static gate pre-forward, numeric result pending; A=third-word c2 context might cause r1 STOP failure after unmasking (low-confidence hypothesis, not a finding). NVIDIA delegated: 0 (no configured authorized reviewer available); local Codex/Gemini: 0. Public synthetic bits only. Next owner: independent NN investigator; post-run failure analysis and structure-matched ordinary binary controls only after this preregistered diagnostic.
