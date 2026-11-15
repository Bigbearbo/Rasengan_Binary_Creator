# R54 independent read-only verification erratum

The training and frozen inference script, legal 96-question manifest, checksum-fixed R52/R53 weights, and all 576 resulting raw 01/STOP generations were **not changed**.

**What failed:** The original R54 runner's first post-experiment `verify` call rejected the existing manifest because its `source_seen()` discovery glob accidentally included the newly generated `r54_outputs/raw_results.jsonl`, falsely classifying R54's own Qs as previously seen sources. The true pre-run preflight **passed** against 1,548 previously archived questions and 60 historical JSONL files; this bug appears only after the results directory is written.

**How corrected:** A new *separate wrapper* `r54_verify_erratum.py` filters paths beginning with `r54_` out of **historical-source discovery only** and calls the original frozen runner's preflight / torch verify / independent NumPy verify. It does not modify the frozen script or regenerate any predictions. Corrected read-only replay: **576/576** PyTorch and **576/576** independent NumPy. Float32 NumPy maximum initial-logit discrepancy = **5.7220458984375e-06** (predeclared tolerance 1e-5). Final portable archive SHA256 check **325/325 PASS**.

Frozen runner SHA256: `17463cbe947454592317ef26dc2d920da4e8353fffde9f2fcd87905d46fc7a03`. Result raw SHA256: `25b833007f58ef59da32abbedce6684f403c8703b2dc4c7d96745f8bc3817f2b`. These hashes match the precommit and actual measurement. The erratum is a verifier bug, **not** a reason to exclude any model failure or mark a failed experiment as passed. All six original prereg gates remained unchanged. Run the wrapper (included in complete archived evidence) after extraction for neural replays; do not use the original runner's post-run `verify` directly.
