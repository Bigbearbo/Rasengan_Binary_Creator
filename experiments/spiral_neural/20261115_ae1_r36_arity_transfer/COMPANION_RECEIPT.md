# R36 companion evidence receipt

Standalone companion ZIP (distributed as the conversation attachment rather than uploaded to Git):
`sle_ae1_r36_arity_transfer_20261115.zip`

**ZIP SHA256:** `e329545a7a2f1df131d530d71cacd585e6a85886737a4291b390151d312a6f9b`

Archive has **130 entries**, size **2,109,160 bytes**, including 12 historical unchanged checkpoint JSONs from R31/R33/R34/R35, frozen input/expected raw 01 manifest, pre-inference spec, original teacher/training provenance, code, all 384 new raw NN generations, outputs, NumPy audit, immutable R36 results, 128-item `R36_SHA256SUMS`, and inventory.

Read-only verification after separately obtaining and cleanly extracting the ZIP:

```sh
python verify_public_companion.py <extracted-R36-root>
cd <extracted-R36-root>
python r36_arity_transfer.py gate
python r36_arity_transfer.py replay
python r36_arity_transfer.py numpy
```

**Already executed on the actual original archive:** clean extraction + 128/128 per-file SHA PASS; source/checkpoint gate PASS; independent PyTorch 384/384 and NumPy 384/384 full-output replays PASS. `verify_public_companion.py` is a public, standard-library-only helper that checks this receipt and recomputes summary counts; it is **not** a neural inference test and **not** a replacement for the other replay commands. A Git-only checkout lacks the ZIP/weights and cannot run those original neural replays.

R36 freeze Git commit `ff0ff4d4ddc790fab5489577457a09ae2b5973df` predates all new neural inference. Inference compute 7,764 forwards / 84,782,880 theoretical dense MAC; training updates=0. Primary transfer gate FAIL. No Codex/Pro/NVIDIA fresh work or rerun claimed; zero live NVIDIA calls due no authorized worker endpoint in this runtime. No automatic merge, no private information.
