# SLE-AE1 heldout r2 pair / context audit

Actual independent scheduled small-neural-network research, 2026-11-14.

Read `PREREGISTRATION.json` (frozen before inference) and `RESULTS.md` (actual results) first. `experiment.py` is the actual PyTorch forward program, `verify_numpy.py` an independent no-Torch replay; `cases_preregistered.jsonl` freezes the native 01 corpus, `raw_cases.jsonl` preserves generated answers (correct and wrong), `RESULTS.json` is the machine summary, and `checkpoints/` includes the four unmodified F32 neural states. All hash digests are in `SHA256SUMS`.

Pre-gate before any forwarding PASS; preregistered primary gate after 384 true generated answers PASS. No training or optimizer was performed (new updates=0). Not a general SLE/VM/UR1 or math-learning result. Source PR48 head acb2947e558addfac1912870d61be439df4d9b7f. Git exact pre-forward freeze commit 6e0a06c894edf28cb710dc0f6b8153579d2c845f.

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python experiment.py preflight
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python verify_numpy.py
```

Use `python experiment.py run` only to generate a new 384-output run in a new unpacked directory. The archived results are immutable historical evidence.
