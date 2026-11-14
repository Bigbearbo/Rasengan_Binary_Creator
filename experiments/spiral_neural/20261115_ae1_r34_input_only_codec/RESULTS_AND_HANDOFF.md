# R34 Results and handoff — INPUT-ONLY numeric-bit layout, native SLE output

**Decision: preregistered joint gate FAIL.** Research owner independent small-NN. Source R33 #83, R31 #81. Formal *before training* Git commitment `f5456568beff9e74ba2ea59d2b3cd0696741bdd7`; see PRETRAIN_FREEZE.md. Pro #12 has actual negative NN ACK training. Codex P031–P035 are already executed and not repeated. No Hamster VM or parser edit.

One changed factor from R31 S/S: numeric **input** slots use padded binary6 `{n:06b}`; **answers** remain legal SLE-AE1-n5-v1 `{n:05b}0`, both with identical 39-bit SLE-AE1 framing and external STOP S. The input binary6 arm is **not a legal SLE profile**. R31 S/S and R33 B/B arms reuse the original immutable checkpoints, and R33 is descriptive only. Same ordered 136-event course / 122 unique tuples, three seeds, 10,457 parameters/student, equal initial tensors, 150 epochs, batch64, Adam .003, clipping1, **3×3300=9900 real new optimizer steps**, **633600 training targets**, **6,918,912,000 theoretical forward-only train MAC** (excludes backward). Same 144 semantic fixed eval questions, same train/validation/heldout/retention split, same rule for full greedy binary outputs. Values appeared in prior analyses; **not a globally blind test**.

| Panel, 3 seeds pooled | R31 SLE input/output | R34 binary input, SLE output | R33 binary input/output, historical |
|---|---:|---:|---:|
| Unseen-a-role low first word /96 | 8 | **1** | 15 |
| Unseen-a-role high first word /48 | 25 | **7** | 17 |
| Combined heldout first 6 bits /144 | **33** | **8** | 32 |
| Combined heldout autonomous exact+STOP /144 | **15** | **4** | 32 |
| Near high first 6 bits /96 | 64 | **77** | 73 |
| Exact training-course retention /120 | 120 | 120 | 120 |
| Separate true-prefix test_stop /48 | 43 | 47 | 48 |

Prespecified gate needed both heldout firstword gain >=12/144 and heldout exact gain >=12/144 (plus retention loss <=15/120, separate STOP loss <=12/48, and 2/3 seeds nondecline). Actual differences **-25, -11, 0, +4**, per-seed heldout firstword deltas **0, -19, -6**. Thus FAIL, not a win for either whole language. R34 firstword on near-high *improved* 13/96: a counterexample to claiming the new input is universally worse.

One actual failure (seed202, r1,a28,b16,c0,d3): input raw bits `010100010011100010000000000000011111100`, legal SLE target `111000S`, autonomous model returned `11101010110011111111111111111111`, capped without STOP and with wrong first numeric word.

**Actual T evidence:** Python static gate PASS; three actual CPU-trained students, 432 new complete raw01 neural generations, **6,549 inference forwards / 71,515,080 forward dense MAC**. `python r34_input_only_codec.py replay`: PyTorch saved-state replay **432/432 exact PASS**. `python r34_numpy_audit.py`: independently coded NumPy model **432/432 exact PASS**, max absolute true-prefix logits error **1.9073486328125e-6**. Clean extraction, **105/105 file SHA**, PyTorch and independent NumPy replay all PASS. No retraining of 864 earlier R33 generations.

New checkpoints SHA256: seed101 `533c7bbdff707fedb0f30b55e659b6f07360b69cb3302be313c3ef6ad9d2fb9b`; seed202 `eb36e032c86bb665cb111897de452e54eacd5c086bdc07bae780ce75dbcc9e9a`; seed303 `011a2d2a98601ec5440394fe806633290ec76628b6036070df9b13a2d098d7fa`.

Raw output JSONL SHA256 `87e60d1945c654d684012d89c7395746dc1e4030d5d65e99f687f42825e7148d`. Local full-source `r34_input_only_codec.py` SHA `25dd27cd82ca5ab122c2eb7a7ea140dfd627ebfc3a35bf9d3b02b2bedb01abaf`. Frozen prereg SHA `000378d3388a41fb9d8a218318a4dc2dd105583eb26a5d4502bcc410a77b8d2e`; raw train/test hashes are in PRETRAIN_FREEZE.md.

Full **105-file companion ZIP** (source, immutable R31/R33 reference sources and weights, new real weights, raw test, independent NumPy verifier, hash inventory, failure examples, complete local R34_RESULTS_AND_HANDOFF.md), SHA256 `b82ff5ed42016e6f96afa419e83707905a699990bb4b34d52fcdfaca7785f1af`, stored in this conversation, **NOT Git**. Git-only checkout is NOT a runnable full reconstruction. To verify the companion after extraction: `python verify_r34_package.py && python r34_input_only_codec.py replay && python r34_numpy_audit.py` from the extracted root; the Git verifier can check the same inventory. No hidden extra optimizer runs.

**U:** author direction: 01 small NN education and fair causal comparisons. **F:** R31/R33 weights, Pro PR12, Codex P030–P035, shared bank PR5; static checked. **T:** this run's freeze-before-train, 9900 updates and 432 independent NumPy validated answers. **A:** numeric input bit position is an important but not single sufficient source of joint R33 differences; inner mechanism unknown. **Next owner:** isolated small-NN researcher to preregister the *fourth* cell, SLE input + binary6 output, same budget. Avoid describing three-cell cross-arm differences as a proven output-only causal effect. No SLE advantage established.

NVIDIA actual calls **0** (no authorized callable worker here); local Codex **0**, Gemini **0**. No keys, private messages or automatic merge.
