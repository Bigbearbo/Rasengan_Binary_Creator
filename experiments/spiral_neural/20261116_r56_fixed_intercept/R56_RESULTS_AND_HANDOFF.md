# R56 — same 500-update budget, static-source intercept control

## Actual independent neural run (2026-11-16)
**Preregistered five-gate joint result: FAIL (4/5 PASS).** Pre-run public freeze commit: `1c6e03b5cd1c790a4e9278bd54a071669574f45a`; this preceded **all** new R56 forward passes and optimizer updates. Based on [R55 Draft PR #106](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/106), exact parent SHA `3d031b1481bc3006329e0aee66029cddb704d068`.

Only experimental factor: R55 trained eight per-source **value-conditioned slopes**, starting at zero with frozen R52 intercepts. R56 trains the eight original **static cursor×source intercepts**, starting from the same R52 checkpoints. All 10,457 R50 backbone parameters frozen, no neural model oracle answers during free generation. Each seed (101/202/303): 500 Adam updates, lr .04, batch64; identical 1,272 nonSTOP teacher-prefix targets from the same 136-event course and same `default_rng(seed+55001)` sample sequence. 10,465 total model parameters, eight trainable. 1,500 combined updates / 96,000 target presentations / 1,048,320,000 theoretical train forward dense MAC, excludes backward and extra gate arithmetic.

Profile `SLE-AE1-n5-v1`; 39-bit raw 01 Q, operands 0–29, r1/r2; full output must include external STOP. Exactly R55's frozen manifest: 32 validation and 64 test legal contexts ×3 seeds, plus 80 archived historical retention ×3 seeds. These evaluation contexts were previously seen in R55 research. **This is a diagnostic matched-budget comparison, not novel numerical-domain blind generalization.** Historical R52/R55 models were not retrained.

| Full autonomous answer incl STOP | R52 unchanged | R55 value slopes | R56 static intercepts |
| --- | ---: | ---: | ---: |
| Validation | 30/96 | 32/96 | **32/96** |
| Test | 45/192 | 44/192 | **44/192** |
| Historical retention | 220/240 | 219/240 | **220/240** |
| All | 295/528 | 295/528 | **296/528** |

Test per seed R55→R56: 101 16→16/64; 202 10→12/64; 303 18→16/64. **Two newly correct and two newly incorrect** on same 192 tests. Test first-word R56 62/192, second-word r2 49/96. Validation R55/R56 full exactly 32/96 each; retention gains 1.

**Fixed gates:** R56 test ≥R55 44/192 PASS; R56 test ≥original R52 45/192 **FAIL**; retention ≥R55−12 PASS; each seed drop ≤4 PASS; independent Torch+NumPy replay all 528 PASS. The aggregate outcome does not demonstrate any benefit from the additional optimization, whether static or value-conditioned. Do not infer universal architecture equivalence.

**Executed:** 1,500 Adam updates; new free 01 answers 528; 5,763 free-inference forwards (62,931,960 theoretical dense MAC). PyTorch replay 528/528, independent NumPy replay 528/528; maximum sampled initial logit difference 2.8610e-6. Separate standard-library raw audit 528/528. Extracted ZIP independently checked 350 file SHA256 entries. Full runner, three trained gate checkpoints, exact Q/answers, earlier source checkpoints and reusable replay code in ZIP:

`sle_ae1_r56_fixed_intercept_control_20261116.zip` (provided as an accompanying conversation artifact; not committed to Git). Archive SHA256 `15e5c81168f2e8c6139e549e405250ce672bf1398b5c0290ee41cc2a3260fbfa`. Frozen runner SHA256 `2197adbb9df85c5dd34269f6f1653240364daba2394e28d76bfe2be86f23c28c`, prereg JSON `e26173159cc52fb89e09e69a4e6a7aea5345c8fa4b570e8943ffca651a89bd4c`, raw-result JSONL `d53674ede8ecd1e78eb164a24bd5689bd083763afdfa1f643ff7651593bcc67f`.

**Failure examples:** seed303 legal Q (r1,a25,b28,c28,d10), expected `110010S`: R55 correct `110010S`, R56 wrong `110110S`; seed202 (r1,a26,b25,c15,d15) expected `110100S`: R55 wrong `000100S`, R56 correct. All test gains and losses, including bitstrings, are preserved in the ZIP evidence.

**[更新]** On identical examples, adding 500 equal-budget updates to static gates yields the same total test accuracy as value-conditioned gates, but different individual successes. **[取代]** A small numeric-conditioned gate seemed the natural fix for R52's nuisance-variable response. **[原因]** R55 and R56 both 44/192 full test against baseline R52 45/192. **[狀態]** These observed counts high confidence, internal causal generality low confidence.

U=user's native-01 learning/reproducibility goals; F=parent Git PR #106 and immutable R55 ZIP; T=this actual local R56 execution, replay and raw audit; A=interpretation that new gate type alone did not resolve interference in these seen contexts. NVIDIA calls 0 (no authorized locally callable OpenRouter worker/key); local Codex calls 0, Gemini calls 0. No changes to Pro UR1, Codex P030–P035, parser or Hamster VM, and **do not auto-merge**.

**Next owner:** independent NN researcher. Next independent high-value test is a truly separate operand role / numeric-domain holdout under matched budgets, with preregistered STOP, historical retention and plain-binary comparator where appropriate. Do not tune on the reused R55 test manifest.
