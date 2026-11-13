# SLE-AE1 frozen role-swap diagnostic — BEFORE neural execution (2026-11-14)

Status: **PREREGISTERED ONLY**. New optimizer steps=0. New inference not run at this commit. Owner independent neural scheduled worker; no changes to Pro/Codex/VM/parser.

Work ID `SLE-AE1-ROLE-SWAP-20261114-R11`; source PR #55 companion ZIP SHA256 `53f6e312f30570ef7d458f35b25c17b49eb7b161415bb5d3b165645aeb8f10a0`, original `run.py` SHA256 `79ac66bd8f2c2fd82b559310bc44e0eae05e3cb23949d1dd9af14e80048acf9a`, source `results.json` SHA256 `78353a7db90a981eba4a9700361a00fafaf77124ef3ec230b98c5bd90d6152bd`.

Frozen local `probe.py` SHA256 `03c928492259b11886681f51ad93e8959e3d41fae7378255dbba3ffc78511ea7`; exact 28-question native `cases.jsonl` SHA256 `44dc28558b33b41dc646d696aec11c77057ecdc494ce8f95a109cfce785a90b7`; local `prereg.json` SHA256 `33dca8cb41336eb87f9d2d64d3f6438bafbaccb32ccc372f5fbef406be6eb5c1`. Source checkpoints and all raw are in the separately supplied ZIP (Git alone is not checkpoint complete).

**One intervention:** The position of a never-trained data ID `j` in an otherwise unchanged pair `{j,h}`, versus its second-word position when the pair is swapped. `j∈{6,7,10,11,12,13,14}`; `h∈{18,19}` (high anchors trained in both answer positions), `r=2,c=0,d=1`. Source first-new responses are **reused** from prior #55 archive (84 rows), not regenerated; genuinely new second-new results (84 rows) and 168 full teacher-forced traces of 13 bits will be evaluated. All six frozen authentic seed101/202/303 × tied/untied models; no weight edits.

Legal `SLE-AE1-n5-v1`: 39 raw 01 bits, `01+010+0100+4*(5-bit ID+0)+111100`; correct answer two six-bit words followed by student-generated external `S`. Training historically 136 presentations / 112 distinct, 150 epochs, 3300 Adam optimizer steps/student (this run **zero**); model parameters tied 10457/untied11081, dense MAC 10920 per neural forward. No LLM/teacher oracle used to choose student answers.

Diagnostic validation `j=6,7`; diagnostic test `j=10,11,12,13,14` (previously inspected: **NOT** a new researcher-blind test). For each seed/test 10 matched pairs.

**Primary pre-fixed gate:** on at least 2/3 tied seeds, first-new ≤1/10 exact, second-new ≥3/10 exact, and second-new leads untied by ≥2/10. Report gate FAIL if unmet. Secondary observational outcomes: complete raw bit answers/STOP, first free error position, correct-prefix target prediction and logit margins for first/second output word, NumPy independent replay. Never retune or select seeds after result.

**Pre-forward gate:** check ZIP SHA, six checkpoint hashes/metadata, original raw results; verify distinct 28 Q/profile and raw expected string; no j in source course; archived first-role Q equals source `test_new_first` and expected. If any fail, stop without neural inference. Original source encoder/decoder is not refit or changed. New evaluation modifies Q only (and uses true-prefix supervision *only to score*, never optimize).

U author asks genuine raw-bit NN educational generalization, F PR55 bytes/source, T pending, A role-specific output routing hypothesis. Reviewer: NVIDIA skipped (no separately authorized OpenRouter endpoint), local Codex unavailable, call count zero unless actually invoked. This is distinct from Pro UR1 and E3; no automatic merge. Next owner independent NN experiment reviewer.

**Next files**: `cases.jsonl` manifest; experiment script fixed by hash before inference; post-run `RESULTS.md`, public raw/failures and independent verification.