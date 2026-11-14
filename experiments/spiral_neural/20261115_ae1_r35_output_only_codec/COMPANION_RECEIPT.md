# R35 immutable companion receipt — 2026-11-15

This Git branch **does not contain** the neural checkpoint files; the complete downloadable companion was produced in the separate research conversation and has been independently verified.

- Artifact filename: `sle_ae1_r35_output_only_codec_20261115.zip`
- SHA256: `0d423fa03e7b12937b1999e1dfbc0a2f7d12c7896fea4608b1dca7b523cff22f`
- Compressed bytes: `2082977`
- Archive members: `120`; full `R35_INVENTORY.json` covers `119` other files, all `119/119` successfully SHA verified from **freshly extracted** copy.
- Clean extraction audit: `python verify_r35_companion.py` → PASS; `python r35_output_only_codec.py replay` → 432/432 full NN greedy outputs and saved checkpoints match; `python r35_numpy_audit.py` → 432/432 independent NumPy replay, maximum true-prefix logits difference `1.9073486328125e-06`.
- Frozen original trainer/preregister/raw manifests and three new checkpoints have eight pinned hashes in `verify_companion.py`, published in this branch. Git-side verifier can run against an extracted ZIP with `python verify_companion.py /path/to/extracted`.
- First public Git commit before training: `1d70449210b9a574932e6484d4bb6faa7ec7273d`. Results commit: `4284b79c89db068b14151a2725d3c1733b781443`. Public verifier commit: `403068144755d9e88b25a1d0134d9eea38dd21a9`.

Exact scope: R35 added three PyTorch models with total 9900 Adam updates; all prior SS/BS/BB models were **reused**, not retrained. The scientific gate remains **INCONCLUSIVE**. No external oracle computing student answers, no Codex or NVIDIA calls, no private material, no auto merge.

The external companion archive is **not recoverable by simply cloning this Git PR**; repository-side code only verifies a companion downloaded separately and its published evidence summaries. Research owner should preserve raw source and archive custody.
