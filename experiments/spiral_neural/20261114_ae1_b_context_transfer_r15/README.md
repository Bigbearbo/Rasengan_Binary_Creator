# AE1 R15 native-01 NN inference: b context transfer

Read [frozen preregistration](prereg.json), [51 legal raw-bit inputs](manifest.jsonl), [before-run receipt](FROZEN_BEFORE_RUN.md), and [actual results](RESULTS.md).

Result: **FAIL, 0/3 predeclared seed gates**, but mixed bit8+bit16 students still get 14/45 full replies correct for different b contexts; standalone high-bit controls 0/45. All 459 real NN replies and nine immutable checkpoint SHA verified by a separate NumPy engine, 459/459 identical; optimizer updates zero. See RESULTS for caveats.

Git includes the exact pinned Torch [runner](run_r15.py), independent [NumPy verifier](verify_numpy_r15.py), the pre-registered inputs and report. The complete accompanying ZIP `sle_ae1_b_context_transfer_20261114_r15.zip` (SHA256 `ac361c7a439133df46ed90ae42a38f4f77ab1861089b0b53aec0ea015eefbe0d`) includes 9 checkpoint files, frozen parent curriculum and source, 459 original Q/output rows, inference logs, source hashes, and the two programs. **Git checkout alone is not a full replay.**

From the extracted companion's `sle_ae1_b_context_transfer_r15/` folder:

```sh
sha256sum -c SHA256SUMS.txt
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python run_r15.py gate
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python verify_numpy_r15.py
```

Tested all three commands in a clean extracted copy: 26 file SHA PASS; static legality PASS; NumPy 459/459 full replies PASS. Use a fresh extracted copy for `python run_r15.py infer`, which creates/replaces local result files. No auto-merge, no Pro/Codex branches changed.
