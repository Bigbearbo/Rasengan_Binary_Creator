# R31 pre-training freeze — 2026-11-15 / SLE-AE1-n5-v1

Workstream: independent small native-01 neural education; NOT Hamster VM, parser, UR1, P030–P035 rerun. Next owner: independent NN researcher. Parent: R30 Draft PR #80 branch `research/sle-ae1-r30-no-firstword-mask-20261115`; reuse its **true** trained checkpoints. Do not merge this branch automatically.

## Only scientific factor
Reuse the exact R30 10,457-parameter unmasked firstword network, initialization, Adam state policy, epochs, shuffles, architecture, secondword route, STOP, and lesson positions. In **16 of R28's 24 high-a r=1 appearances**, change ONLY ignored third data word `c=0` to `c=2`, such that each `a=20..27` has two `c=2` and one `c=0` appearances. All other training questions and targets are unchanged. Old R30 frozen checkpoint is control, not retrained.

Course: 136 appearances, 1,408 target prefixes per epoch, 150 epochs, 3,300 Adam updates/seed, 9,900 new Adam updates total; seeds 101/202/303; Adam lr=0.003, batch64, clip norm1; 633,600 target presentations total; 10,457 weights; 10,920 dense forward MAC/target; 6,918,912,000 theoretical train forward MAC excluding backward, validation, codec.

Profile: valid `SLE-AE1-n5-v1` raw **39-bit 01 input**, fixed header `01+010+r3+0` plus four `(5-bit dataID+0)` and terminator `111100`; IDs 0..29; first answer=6 raw bits, r2 second answer=6 raw bits, external STOP `S` (not SLE token). Deterministic original teacher codec supplies train targets/offline correctness only; no model/oracle supplies student answers.

Split: 168 *previously frozen* R30 questions (validation4, heldout-a28/29 24, near-a20..23 32, stop24, r2 4, exact retention 48+32) plus **56 new paired** c=0/2,d=0 cases: paired_val8 at a26/27, paired_unseen16 at a28/29, paired_near32 at a20..23. Total 224 unique native01 Q. Train a28/29 absent. A28/29 have appeared in prior researcher's panels; student-heldout but **NOT researcher-blind**. Old R30 168 responses reused without rerunning; only old checkpoint's new 56-case panel is fresh old inference.

## Gate fixed before any new neural forward
PASS iff ALL:
- R31 minus R30 aggregate on frozen `test_unseen_a` firstword: >=+8/72
- Complete answers there: >=+6/72
- `test_near_a` firstword change: >=-8/96
- historical 48+32 per-seed exact old retention: aggregate >=-12/240
- `test_stop` teacher-correct-prefix stop: >=-6/72
- every seed's unseen firstword change: >=-8/24

New 56 pairs are *descriptive causal diagnostics*, not gate tuning, do not treat repeated contexts as independent a values. Never alter gate after test. Stop after fixed 150 epochs; log all negative results and checkpoints.

## Immutable pretraining SHA256 commitments (local independent companion)
- R31 runner `r31_runner.py`: `d83a828df067e17d931477842b79bb51a303b61c2a39e7cecaf84b377ed7982b`
- R31 exact 224 raw01 `r31_manifest.jsonl`: `8dc4c608930d693aeaae29c2b5109cbc91cfc6ca3df50442861a9c308474f630`
- R31 pre-registered full `r31_prereg.json`: `f85442ce2f2bff364e9a340485b9364184bfeeb9a4bdd419ab7025590c96d06f`
- R31 exact 136-course JSON SHA256: `7926392fc6bc0147763fc5c5fd35e776449540a96cbb9ff59b49f618f730f8e4`
- R30 runner SHA256: `e69dda36723ce435887715539728bfe8eff70f522dbbeef45acc9aeb1e353630`
- R30 portable ZIP SHA256: `22747e62238b527bb6c1ce7fe1bb0f6352cf970495b90c74e37a86700809d714`

The local generated manifest and runner passed static protocol checks before this Git freeze. Preserve exact files in result companion; hashes bind bytes even though not all files are placed in Git in this freeze. Complete result evidence must be published separately and must be honest if Git alone cannot replay without the companion.

U: user requests SLE 01 neural curriculum and generalization. F: Git PR80 and local verified R30 archive. T before this freeze: source/hash/manifest static checks ONLY, **zero new neural forwards or updates**. A: variable irrelevant-word c2 exposure might improve unrestricted firstword invariance; uncertain. NVIDIA: not authorized/available runtime, 0 calls. Local Codex: not invoked, 0 calls. No private data or API keys.
