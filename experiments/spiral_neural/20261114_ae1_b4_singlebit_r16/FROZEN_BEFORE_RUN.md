# AE1 R16: frozen before neural execution (2026-11-14)
Owner: independent SLE raw01 NN researcher. Workstream not Pro UR1 / Codex P035 / Hamster VM.

## Unique intervention, profile, and splits
Only second data word b changes **16 → 20**, one information bit (bit value 4), paired within fixed a. Keep r=2, c=0, d=1, output rule, nine pretrained F32 weights fixed. Original train: R14 parent120 + bit8 eight + bit16 eight = 136 presentations / 112 distinct. No new training; 0 optimizer updates and 0 teacher targets. Source PR #63 head b197299ec7b48f0a07118582be981bb5aaeb3318 and R15 PR #64 read. Nine checkpoints: 3 seeds (101,202,303) x three arms (control16,control8,balanced8_16). 10,457 params/model; 10,920 forward-only dense MAC per prefix. Expected 54 full native01 generations (6 raw questions x 9 models), max 702 prefix forwards / 7,665,840 dense inference MAC.

Valid experimental **SLE-AE1-n5-v1** only: input '01' + '010' + '0100' (r2) + four 5-bit-ID-plus-0 words + '111100', exactly 39 binary symbols. Output a(6bit)+b(6bit)+external STOP 'S'; STOP not a SLE token. IDs <=29. Six raw input/expected output pairs are in `manifest.jsonl`. Validation is a24 with b16/20 (a24 was observed by researcher in prior R14); heldout test is a28,a29 x b16,20 (not trained, not among prior R14/R15 full evaluation Q). Previously inspected b20 failures motivate study; no researcher-wide all-new-phenomenon claim.

## Preregistered decision
**PASS** only if at least 2/3 seeds of balanced8_16 achieve, across a28/29: (1) both b16/b20 pairs have identical predicted first six bits (first-word invariance 2/2); (2) at least one pair has both full 13-symbol answers exact; (3) at least one b20 second six-bit answer exact. Report all controls, failures and per-seed paired metrics regardless. No later seeds, curriculum additions, changed labels, or post-hoc gate substitution.

## Freeze receipt
Before any R16 NN forward, local static program generated six questions and passed `python run_r16.py gate`; **no R16 optimizer or NN forward has yet been executed**. Companion source and byte hashes:
- R14 source ZIP SHA256 ec431291aef5e913690d4f0303d94cd3b5768ace73d86f98902cdddebb5eb0d3
- source `run.py` SHA256 79ac66bd8f2c2fd82b559310bc44e0eae05e3cb23949d1dd9af14e80048acf9a
- parent_course.json SHA256 e63d60db2b4f3fe316c76712e20d010eeb1a43d1afa8e15aa3faec9619e72f6a
- R14 original raw results SHA256 28a2a487ad01cc0452462e90a50f63103cd2d148b4c672778430758624ab7ba1
- R16 manifest.jsonl SHA256 ad63d5ba47b92ca2790a44bec42bf3e604a39fef0ead0dd811acb657ebd65c27
- R16 local `run_r16.py` SHA256 a2f0c0ee81a56d487314e41fbd069c05b9bc47609416d2ef87c7c04c6390ea73
- R16 local `prereg.json` SHA256 743739b3ff7fc1715f921900b55839691b35be4771734beaed5c864251b8a310
- Existing R15 originals were inspected; R16 Q are disjoint from parent training and R14 evaluation Q by static gate.

U: user requests genuine NN input/output learning and generalization. F: immutable published #63/#64 source and checkpoints. T at freeze: static checks only. A: b20 may cause wrong first-word changes as cross-variable interference; not established. NVIDIA: 0 calls (no authorized configured OpenRouter endpoint). Local Codex: 0; Gemini: 0. No teacher/LLM oracle in NN inference. Do not merge or overwrite other worker branches.
