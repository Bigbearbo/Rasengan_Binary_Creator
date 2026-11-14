# R30 immutable pretraining erratum 01 — static source audit, before any new model training/forward

Original FREEZE.md commit: `3579a225916de557786de91b159597e030c3ea63`.

**Static preflight FAIL before training** on course uniqueness: `len(course)==136 and len(set(course))==112` failed. R28's actual course includes 136 lesson events and **118 distinct (r,a,b,c,d) tuples**, not 112. This is a bookkeeping error in the researcher's prereg, not an alteration of the curriculum. The user-specified single causal factor and R28 fixed source course remain unchanged. The mismatch was found using `r28.curricula(ref,m,r27)` without any newly trained model or inference.

Corrected assertion: `len(course)==136 and len(set(course))==118`. Corrected R30 runner SHA256: `e69dda36723ce435887715539728bfe8eff70f522dbbeef45acc9aeb1e353630`. Corrected R30 prereg SHA256: `021684c38ff7a30fac9aece307571b3c5460dc9f7550e7b999e6944c5851f760`. Exact 168-record native raw01 manifest SHA256 **unchanged**: `b8a7aa71b1921e28b8fc85f61e2ae16c5856dbd13d59d612bd506bbb7d2eac64`.

All other frozen conditions, source checkpoints, seed budget, split and PASS gate **unchanged**. The initial erroneous freeze and this correction are both retained; do not present it as originally correct. This correction is committed before calling the new network or optimizer.

U: User prioritizes fidelity, exact freeze and negative receipts. F: Original R28 course generator. T: Locally observed initial static assertion fail and independent `len(set(course))=118` check; zero new learner updates. A: no inference about learning effects yet.
