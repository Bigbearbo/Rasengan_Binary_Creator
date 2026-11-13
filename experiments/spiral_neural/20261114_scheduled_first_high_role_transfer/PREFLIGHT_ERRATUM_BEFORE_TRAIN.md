# Pre-training preflight erratum — no neural updates have occurred

The first local `python run.py gate` failed **before any optimizer update** because the test mistakenly required *both* curriculum arms to contain 112 unique lesson tuples. Source parent has 96 distinct lessons among 120 presentations. The 16 first_high injections give 112 unique lessons; the 16 second_high injections overlap 8 existing baseline lessons, giving 104 distinct lessons. Each arm still has 136 presentations / 1408 target-prefix examples, equal high and low value multisets, and identical target-bit marginals.

We fixed only the **invalid uniqueness assertion**; did not change either curriculum, heldout values, seeds, model, acceptance gates, or training budget. The original prereg is preserved. This uniqueness imbalance is an important interpretive limitation: distinct combinations, as well as first/second output role exposure, are not equally represented; any result can only be attributed to the entire frozen role-swapping curriculum policy, not purely role exposure divorced from repetition.

Original runner SHA256: `9c912192f94c432c01d625219a4170bab05af047045df5fe2d1587ba06ce98d4`.
Corrected runner SHA256: `3b7deb04c4f2e9050a2d67d29a0a4ed8d4ca196016a0cf0ee995326f3021be8a`.
The corrected `prereg.json` records this erratum; the original pinned parent_course and checkpoint SHA256 are unchanged.
Planned 4×100×1408×10,432 = **5,875,?** training forward dense MAC (the exact integer must be recomputed in the actual results, not treated as verified here). Adam updates 0 as of this erratum. No heldout neural inference performed.

U: native SLE 01 learning scope. F: immutable PR40 true checkpoint and course. T: pretraining static gate failure. A: revised repetition caveat. NVIDIA and desktop Codex actual calls 0.
