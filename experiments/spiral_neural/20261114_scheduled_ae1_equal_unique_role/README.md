# SLE-AE1 equal-unique high-word-role comparison

This **independent small-neural experiment** preregistered the teaching-policy contrast at [freeze commit 54c83e5](https://github.com/Bigbearbo/Rasengan_Binary_Creator/commit/54c83e5d202153c6fdbcf53cf8793252c2d3f228), trained four real PyTorch CPU students only after the freeze, and reported the **failed** primary gate in [RESULTS.md](RESULTS.md).

Each arm has 120 parent lesson presentations +16 new r2 lessons (both use c0,d1 so no injected question duplicates parent): **136 presentations /112 unique** in each arm, **1408 teacher targets per epoch** and equal token histogram. Only the first/second high-word output position changes across the two arms. The models share source F32 parent weights per seed101/202. This is not Pro UR1, P030–P035 rerunning, VM, parser, or mathematical learning.

## Reproducibility and missing remote artifacts

The companion evidence archive `sle_ae1_equal_unique_role_20261114.zip` SHA256:

`dee1121c7ca6ecd7d1f66bc0cb42e48f05f4f1603c14dc446634ff3e15a21093`

is distributed in the corresponding research conversation. It contains **all source and final F32 checkpoints**, full actual `run.py` (frozen SHA256 `edae40874fd937616e4f7a93e642dddf75d010e7cc02f1dea757e0bd24a55f1f`), `prereg.json`, 256 entry `cases.jsonl` (frozen SHA256 `2eaf6ff3293a398322fbf4668407a9164b818886a6daf7c386f0b49fb9a0121f`), `parent_course.json`, `results.json`, all 512 complete `raw_cases.jsonl` replies, `validate_design.py`, `verify_numpy.py` and per-file `SHA256SUMS.txt`. **Git alone is not weight-complete**. Do not construct a fabricated ZIP link from the filename; retrieve the provided companion artifact.

On a **clean extraction** of that archive with Python3/PyTorch/NumPy:

```sh
sha256sum -c SHA256SUMS.txt
python validate_design.py
OPENBLAS_NUM_THREADS=1 python verify_numpy.py
```

The three commands PASS in the execution environment. The exact independent NumPy verifier and static native-bit split checker are also in this Git directory; Git blobs equal their locally executed bytes. To retrain, use a second clean extraction and `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python run.py train`, which overwrites the final weights/outputs. Do **not** rerun this already-validated experiment unless replicating; the full source code is included in the archive rather than pasted into this Git PR.

## Result boundaries

Actual four students, total 8,800 Adam steps, 512 real free-run replies; independently 512/512 replay. First-high val known-values 15/32 vs control 0/32; fully student-unseen values **0/96** across all four. Seed101 fails frozen gate, seed202 passes: **whole run FAIL**. Output STOP being correct does not rescue incorrect content. Project investigators have already seen overlapping number ranges, thus do not label this investigator-blind. The historical PR #53 comparison is additionally confounded by suffix d differences.

NVIDIA 0 (no authorized callable reviewer here); Codex desktop 0; Gemini 0; LLM answer oracle 0. No cross-workstream mutations or merges. Next owner: design a stricter fresh value/context split and a genuinely new copy-inductive-bias contrast, not post-hoc retuning on this test.
