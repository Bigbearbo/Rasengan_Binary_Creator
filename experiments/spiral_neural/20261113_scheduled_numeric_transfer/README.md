# AE1 six-checkpoint numeric-domain transfer — real neural inference, no retraining

**Frozen preregistration before the new forward calls:** commit [2e60b00960a355891950b22242a6a6f7fee2d0c7](https://github.com/Bigbearbo/Rasengan_Binary_Creator/commit/2e60b00960a355891950b22242a6a6f7fee2d0c7), \`PREREGISTRATION.md\`.
**Exact input checkpoints:** four exclusive-position models from PR #36 head \`0b4a39342ee4ef00a0775ece7a2c20a1dfa08b25\`, two mix-position models from PR #37 head \`6a2162a687dc05b68034b2d00c287584a463f545\`. Never edit the six weights or retrain their students. Each 10,499 params, seeds 101/202, one-hot raw 01 input, tanh64, greedy 0/1/S output.

## What was changed?

One *evaluation input dimension*: the token value used as the high word, seen **IDs 6..14** vs untrained **IDs 15..23**. Hold r=2, two orientations, low partner 0..5, c=d=0, models, weights and output decoding fixed. All words remain ordinary legal IDs (0..29), END30 and UP31 reserved. Q = \`01 + 010 + r(3info+0) + a(5info+0) + b(5info+0) + c + d + END\` = 39 bits; free-generated answer is \`a+b+S\`. The example Q \`010100100000000001100000000000000111100\` has expected \`000000001100S\`. No extra parser features or large-model answers. The scripted correct string is used only to generate labels and score predictions; the NN computes its own answer.

Original training split remains fixed: 24/6/6 low (a,b) pairs by modulo 6, plus 36 supplemental high/low pairs/student; PR #36 and #37 heldout low s4/s5 were previously inspected. Original Adam .003 × 250 epochs × 948 teacher targets × 3750 batched optimizer updates per model. **This trial: 0 new optimizer updates**, 0 new parameters. New Q matrix = 6 fixed checkpoints × 2 domains × 9 IDs × 6 low IDs × 2 orientations = **1,296 rows**, with raw 01 answers and every error saved in \`raw_cases.jsonl\`. The primary preregistered slice is low partner s5 (9 cases/position/model/domain).

## Results (fully generated answer including S)

| Arm (each contains seeds 101 and 202) | Seen values 6..14, all low 0..5 | Unseen values 15..23, all low 0..5 | Seen s5 | Unseen s5 |
| --- | ---: | ---: | ---: | ---: |
| Exclusive high-first | 108/216 | 12/216 | 18/36 | 2/36 |
| Exclusive high-second | 108/216 | 12/216 | 18/36 | 2/36 |
| Mixed high-first/high-second | **210/216** | **12/216** | **35/36** | **2/36** |
| Six-model total | **426/648** | **36/648** | 71/108 | 6/108 |

Mixed students primary s5 details: seed 101, seen high-first/high-second **9/9 and 9/9**, unseen **0/9 and 1/9**; seed 202, seen **8/9 and 9/9**, unseen **0/9 and 1/9**. Thus **2/36 unseen** on mixed students, below preregistered practical transfer threshold (at least 5/9 in *both* roles *both* seeds). These failures should not be obscured by prior PR #37's successful 72/72 *untrained reverse orientation* results within the vocabulary it taught.

All seen-value answers terminated at expected S position **648/648**; unseen **647/648**. The one displaced stop was seed202 MIX, v15, low0, high-first, actual \`11001000S\` (premature termination). Other stop positions can be correct despite wrong content; stop accuracy is not copy accuracy. Across unseen cases requiring high-ID bit16=1 (v16..23), there are 576 expected high bit16 ones over six students; actual predicted high bit16 ones were only 48 across all unseen tests (including v15 false positives), so do not read this as correct-bit count. Source files contain per-case expected and generated high-bit value.

The **trained-vocab improvement is specific to that small value range**, not a general bit-copy algorithm. This experiment cannot separate unseen numeric magnitude, missing output-value teaching, target-prefix exposure, high bit16, and input-token composition. It also cannot claim SLE is superior to ordinary binary.

## Execution, checks, costs

- Local **CPU PyTorch forward** reconstructed six stored float32 checkpoints, enforced both source runner SHA256, verified tensor digest and parameter count, and exactly replayed **1,080/1,080** old full raw replies: 12,744 replay forwards.
- Then **1,296 new free-generation** replies: **16,844 forward calls**, **175,716,608 dense forward MAC** (10,432 MAC/forward); old replay forward MAC 132,945,408. Backprop/optimizer work **zero**, CPU wall-clock not equated with kernel timings.
- An independent **JavaScript V8 typed-array** implementation read the six exact GitHub checkpoint files and all raw old cases and independently reproduced the same 1,080 archived and all 1,296 new outputs, including new forward count 16,844. The intermediate failed V8 debugging attempt never produced published results: a wrong input handling path generated an archive mismatch, which triggered the preflight stop; repaired implementation passed full replay before generating new cases.
- Raw cases SHA256 **\`3ff1c94ec632145f202fac7e24ce35be7e7b99fab8426afef052150a015c3836\`**; Git blob SHA-1 **\`d73128aff2faa9bab6b5d8c6880c48afbbac1bfd\`**, byte identity verified against local PyTorch output. \`results.json\` contains 48 stratified count records, sample errors, six checkpoint hashes, full cost.
- The independent V8 result is corroboration, **not a replacement** for running the public PyTorch code. In a full repo checkout with PR #36/#37 source directories present:
  \`\`\`bash
  cd experiments/spiral_neural/20261113_scheduled_numeric_transfer
  python probe.py
  sha256sum raw_cases.jsonl
  \`\`\`
  \`probe.py\` regenerates the same raw records. It writes a PyTorch-produced summary JSON with the same substantive results but a slightly different metadata schema than the independent V8 publication; do not require that JSON's bytes to match, only counts, raw bytes, checkpoint digests and outputs.

## Evidence boundary / handoff

**U**: author requested native-bit small NN learning, generalization, fixed-cost test and a distinct neural workstream. **F**: PR36/PR37 immutable frozen model checkpoints, protocol and original 1,080 outputs; related P030–P035 and UR1 findings are separate research. **T**: six real checkpoint reconstructions, source replay 1,080/1,080, fresh 1,296 NN outputs, independent JS arithmetic verification, every failure and SHA. **A**: role mixing helps in-vocabulary transfer but appears insufficient for new values; mechanism unknown.

The new values have never been trained as these students' **answer high IDs**. However PR #34 had already probed overlapping numeric domains in different models; do not label this a pristine researcher-blind test or proof of generic neural limitations. Only two seeds, same small architecture and a fixed c=d=0. The current PR is **Draft** and stacked strictly on PR37; no merge, no modification to any Pro/Codex branch, no change to UR1, grammar, dictionaries or Hamster VM.

**NVIDIA** actual calls 0 — no authenticated explicitly authorized read-only worker endpoint within this run. **Codex local** 0; **Gemini** 0; teacher LLM answer calls 0. Next owner: NN independent reviewer or Codex **read-only** reproducibility review. Next discriminating study should freeze a fresh split that teaches novel values in a *different output position* while controlling input-value distribution; do not tune on inspected s5 cases, mix into an existing frozen dataset, or retell this evaluation as a fresh training success.
