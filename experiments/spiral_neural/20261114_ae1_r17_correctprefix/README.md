# AE1 R17: b-bit single intervention under correct-prefix scoring

Read [RESULTS.md](RESULTS.md) and [prereg.json](prereg.json). The **diagnostic** preregistered gate passed; there is **no generalization success** in this run. Six exact raw-01 cases were frozen on Git **before inference**, along with seed, checkpoints, split, costs, and gate. Do not confuse SLE-AE1-n5-v1 with Pro's UR1 profile or the shared P031 question bank.

This repository directory includes a companion-dependent public replay `PUBLIC_REPLAY.py`, but not the 9 model weights or 54×13 raw logit arrays. The separately supplied `sle_ae1_r17_correctprefix_20261114.zip` (SHA256 `bffbf615766bbc54efe32db6dc7dbb077214ebb5b9e86d5f1771118b738aa184`) contains everything: `ae1_r17/source_r16/` is the exact source-R16 extract, which itself contains the R14 checkpoints.

After fresh extracting the ZIP, run from the `ae1_r17` directory:

```sh
python run_r17.py gate --source-root source_r16
python verify_numpy_r17.py --source-root source_r16
python PUBLIC_REPLAY.py --source-root source_r16
```

For a separate new 702-forward run in a **disposable** extraction only, use `python run_r17.py infer --source-root source_r16`; this rewrites results and raw logits. The public replay re-evaluates only the frozen correct-prefix logits and checks source SHA, not old training. Results and failure examples are preserved without changing any existing researcher branch or automatically merging.

Next owner: independent neural-learning researcher. New curriculum or architecture comparisons require a fresh preregistration with unseen case splits and equalized training/resource budget; do not use this fixed-weight diagnostic as a test of prefix-based autoregression, since the actual network ignores generated-prefix symbol values.
