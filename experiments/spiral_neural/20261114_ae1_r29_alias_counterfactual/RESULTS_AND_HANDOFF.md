# R29 — matched single input bit alias audit (2026-11-14)

**Numerical preregistered gate PASS; scientific independent-context replication NOT ESTABLISHED.** This distinction is essential, not a posthoc change to the gate.

## Exact scope / real execution
Independent small native-01 SLE-AE1-n5-v1 neural students, not Hamster VM/UR1/parser or a repeat of P030–P035. The pre-inference Git freeze is commit `5c494aee649ef0ace18e97f44ca81ca10e817503`, following pre-published 64-question `manifest.jsonl` commit `254b00bc721e217401140c6d1b8e7e9935cbc0cb`; original FREEZE remains intact. Matched input pairs change only **bit10 (0-based)** in first data word: a20 (`101000`) → a28 (`111000`) or a21 (`101010`) → a29 (`111010`). All other tokens remain fixed.

Validation 8 pairs c1d4, test 24 pairs from c1d5/c3d4/c3d5; each pair varies b∈{18,19,22,23}. All 64 raw 39-bit inputs are disjoint from R27/R28 questions but **the numeric values themselves have been seen by the researcher**. Six *previously trained* saved checkpoints (R27/R28 × seed101/202/303) are immutable controls. **0 new Adam updates; 384 real fully autoregressive native-01 generations; 7,574 actual dense forward calls = 82,708,080 theoretical forward dense MAC**, 10,457 parameters/student. Historical R27/R28 exposure 136 lessons, 150 epochs, 3,300 updates/student; no weights repaired.

## Primary outcome: seed202 test group, 24 nominal pairs

| Frozen arm | low a20/21 firstword correct | high a28/29 firstword correct | identical low/high six-bit firstword | high bit1 correct | high bit1 logit margin 1–0 | margin change high-minus-low |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| R27 | 12/24 | **24/24** | 12/24 | 24/24 | +5.6207 | +5.8813 |
| R28 | **24/24** | **0/24** | **24/24** | **0/24** | −0.2613 | **+6.3907** |

Preregistered numerical gate required R28 identical≥18/24, R28 high bit1 correct≤6/24, R28 low correct≥18/24, and R27 high bit1 correct≥18/24; **all four pass**. However both arms have 0/24 *correct true r1 STOP* in the high-value seed202 test group; firstword success is not a complete response success. R28 seed101/303 high firstword are 24/24, so the alias failure is seed-specific.

**Critical identification failure identified after inference:** Firstword output positions 0–5 in both networks are architecturally masked to **data word a only**. Consequently changes in b,c,d CANNOT change firstword logits; confirmed by independent NumPy checks. The 24 nominal new-context pairs collapse to **two functionally distinct a-bit interventions per seed/arm**. So do NOT claim 24 independent confirmations, unseen context transfer, improved general copy, or SLE advantage. Original prereg remains unaltered. This was a badly chosen contextual replication criterion, not a new scientific PASS.

**New diagnostic refinement:** R28 seed202 does *not* ignore the high input bit: its positive +6.3907 high-minus-low logit shift is bigger than R27's +5.8813, but the R28 prediction margin remains below zero at −0.2613. This is consistent with a shifted learned decision boundary/bias, **not verified internal neuron-level causality**. The observed firstword alias a28→a20 and a29→a21 should no longer be described as bit-insensitivity.

## Sources, full evidence / replay limits

- Base Git main SHA `d032a825c2b419f365bf34a531baee3b53b91750`. Parent R28 [draft PR #78](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/78) head `cd6d0fbb09b6948ac4be59e059f36854affa1788`; R27 [#77](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/77). Distinct Pro UR1 [#12](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/12) includes actual failed neural ACK training and does not authorize this experiment's profile.
- Frozen executable `r29_runner.py` SHA256 `89445ca09c2a3b9020b15d3cd879c1af8325ba151d5903140c5fa31ebcb05dad`; frozen `prereg.json` `8028a72772792b4e48d47336ab4e15b709c13090796773f3f7c2379be2a02076`; `manifest.jsonl` `d1d31d0a5efa97aed738413d72fe16a70928b18a330916a8cf798294623d7312`.
- New 384 `raw_results.jsonl` SHA256 `b160df22aca25db1c8b6c1e57a6bf949bab0e0218210fe3ddbf46eab73538f61`; numeric `results.json` SHA256 `d1c670ec76ad9c6f77356eb857520cdbdc24ef2dfe019df9fcf871155aa2f53d`. R28 source ZIP SHA256 `bdb5d47ec9dcdef851247136c85acbf7923f4d9c9631b9b5357ccbe699d562dc`.
- Complete R29 ZIP SHA256 **`b84383617aad6a6099655eb1f9de358524c99e2aaafddd216afbbd12b796ee35`**; full runnable PyTorch runner, 6 JSON checkpoints and raw outputs are in *conversation attachment*, NOT uploaded into Git. Git contains public freeze/manifest, companion audit source, this result; **Git alone cannot rerun checkpoint inference**.
- Actual verified in a *clean extraction*: `sha256sum -c SHA256SUMS` all files PASS; `OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 python r29_runner.py gate --source base` PASS; same prefix `python r29_runner.py replay --source base --out r29_outputs` 384/384 PASS; same prefix `python r29_numpy_audit.py --source base --out r29_outputs` 384/384 PASS, max logits |Δ|=**2.8610e−6**, verified exact firstword context collapse. This is replay integrity not semantic learning.
- Provenance: **U** user's separate native 01 neural curriculum/generalization research; **F** Git P030–P035/Pro UR1 and saved R27/R28 checkpoints; **T** this actual model inference, integrity and independent NumPy tests; **A** learned threshold shift mechanism is candidate interpretation. **NVIDIA skipped**, no approved live OpenRouter path; actual calls NVIDIA 0, local Codex 0, Gemini 0.

## Next owner / experiment
Do NOT re-run near-high b/c/d context sweeps for firstword in this hard-routed architecture. Study distinct heldout firstword bit configurations or compare **a matched model without a-only firstword routing** under frozen equal parameters/MAC and new heldout, requiring both exact firstword and STOP. To establish SLE benefit, separately implement a genuinely equivalent ordinary-binary control with same output conventions and accounting. Retain this numerical PASS **and** the scientific experimental-design failure, without retroactive gate editing, hidden extra seeds, or auto-merge.
