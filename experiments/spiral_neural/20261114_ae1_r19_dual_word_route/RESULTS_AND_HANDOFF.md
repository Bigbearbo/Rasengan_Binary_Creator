# AE1 R19 — second-word hard routing: preregistered FAIL 0/3

## POST-RUN SCIENTIFIC ERRATUM — protocol conformance FAIL

**The frozen implementation accidentally changes r1 STOP, not just the r2 second answer word.** Cursor positions 6..11 are always masked to `b`, regardless of r. When r=1, the STOP target occurs at cursor6; hence R19 r1 STOP sees only `b`, whereas R18 r1 STOP saw all data words. The frozen prose incorrectly asserted that STOP was unchanged. This was discovered AFTER the 9,900 updates and all preregistered results. We preserve the exact frozen file/checkpoints and label this result **exploratory regarding second-word-only isolation**. The numeric prereg gate still FAILS 0/3; an additional protocol-conformance gate FAILS. In particular, **r1 STOP 38/60→60/60 is not an unaffected control.**

Actual post-run bounded intervention on r1 STOP (6-bit prefix `000000`, b18/c0/d0 fixed, only a0→a1): R18 output logit maximum absolute changes per seed 101/202/303 were 1.1282 / 0.3581 / 1.9942; R19 changes all **0.0**. Verified 12 new PyTorch forwards, 131,040 dense forward MAC, 0 optimizer steps; not part of original registered inference budget. Companion ZIP contains `postrun_conformance_audit.py` and `POSTRUN_CONFORMANCE_AUDIT.json`. Training course audit also found b's bit8 positive in just 2/76 r2 teaching occurrences and bit16 positive in 16/76: a competing limited-coverage explanation for high-b failures (post hoc, not proven).

**Do not silently rewrite the frozen manifest, repair-and-retrain on inspected tests, or call this a clean causal STOP-independent experiment.** A future new experiment must separately gate r1 STOP using r before testing a second-word-only route and freeze new untouched values/context.


Status: **completed experiment / negative gate** (2026-11-14). Owner: independent SLE native-01 NN research worker. No Hamster VM, syntax dictionary, Pro UR1 branch modification, Codex intervention, or auto-merge.

## Evidence and provenance

- [Frozen protocol](FROZEN_BEFORE_TRAIN.md) committed **BEFORE any R19 model forward**, SHA `dba8300ecac102757c924ea13d1660129281584c`. Original exact runnable train code SHA256 `2705913fe770783778cb45bed586eecfa397fccb86433cc0c9d392720c3da682`; 168-case manifest SHA256 `972265d5f851727f3ce181b032032986374932e3bd8671f12b79722325b53edc`; machine prereg SHA256 `72c7c0782985a7cfcc564a5cdcc754638380e63efc2c38e52fb92fff0abbfc45`.
- Public code: [dual-route network definition](route_core.py) and [rebuild frozen 168-case manifest](gen_manifest.py). The complete **exact** training runner, R14/R18 source dependencies, six checkpoints, 1,008 raw native01 outputs, seed traces/metrics, independent NumPy replay and all per-file hashes are in the accompanying ZIP delivered separately in the experiment conversation. **Git-only checkout is not a complete checkpoint replay.**
- Complete companion ZIP filename: `sle_ae1_r19_dual_second_word_route_20261114.zip`, SHA256 `75834bbb56b215da2e6590b3fa71d62202ba85993df569672ec64202e7035911`; 29 entries including postrun audit code/data, 27 file checksums. Tested after clean extraction.
- U: author requested SLE raw01 small-NN teaching, generalization and growth. F: frozen R14 #63 course/source and frozen R18 #67 checkpoints; PR #5 public shared bank and P030–P035/Pro UR1 consulted but not retrained. T: **new** 3×3300 Adam updates plus full replay and independent NumPy audits. A: removing cross-word input leakage may improve heldout b copying; not guaranteed, low-confidence prior.

## Only factor and budget

R18 first answer word output 0..5 already sees only `a`. R19 additionally constrains second answer word output 6..11 to see only `b`. STOP remains full input. Same 39-bit SLE-AE1-n5-v1 Q, 136 teaching appearances/112 distinct, 1408 targets/epoch, three seeds 101/202/303, 150 epochs, lr .003, batch64, 10,457 parameters, 10,920 dense forward MAC/target. Three new students, **9,900 real Adam updates**, 633,600 supervised targets, **6,918,912,000 train forward MAC** (backward not included). Three R18 baseline checkpoints reused unchanged. The masking rule, including the unintended r1 STOP masking, is **hand-coded**, not independently discovered by NN; teacher labels never substitute for student inference.

Predeclared gate: at least 2/3 seeds each need a ≥8/40 exact teacher-forced second-word gain vs R18 on new test_mid_b+test_high_b, retain seen ≥40/48 and taught ≥16/32 full free answers, plus r1 STOP timing ≥15/20. All test questions absent R14 train and R18 manifest, but researcher has previously seen some values elsewhere: NOT global researcher-blind.

| Seed | TF second word gain /40 | seen /48 | taught /32 | r1 STOP /20 | Gate |
|---|---:|---:|---:|---:|---|
| 101 | +6 | 48 | 32 | 20 | FAIL |
| 202 | -1 | 48 | 32 | 20 | FAIL |
| 303 | +6 | 48 | 32 | 20 | FAIL |

Pooled outcomes, old R18 → new R19, numerator exact / fixed split total (three seeds):

| Split | Full answer | Second word | Correct-position STOP |
|---|---:|---:|---:|
| taught+seen 240 | 228→240 | 156→168 | 240→240 |
| middle b 60 | 2→8 | 5→16 | **33→15** |
| high b 60 | **0→0** | **0→0** | **44→11** |
| joint a/b 60 | 0→0 | 0→0 | 37→33 |
| r1 STOP 60 | 38→60 | n/a | 38→60 |

The second-word gain on the middle b set did not transfer to the high b set. On difficult r2 contexts, STOP reliability collapsed, even though r1 STOP and familiar-word retention improved. R19 **FAIL 0/3**, not a learning success. Correct STOP also does not imply bit content correct.

Representative failed R19 native raw output, seed101, middle-b context:
```text
Q      010100100000000001100000100000110111100
Truth  000000001100S
Student00000000110000000000000000000000
```
Student copied both words but failed to generate STOP and hit its 32-output cap. Another high-b failure (a0,b24,c2,d3) expected `000000110000S` but answered `00000010000000000000000000000000`. All original failures preserved in the companion raw JSONL.

## Actual verification and limitations

- Static prereg gate passed; outputs reproducible **1008/1008** with PyTorch checkpoint replay.
- Separate NumPy-only engine reconstructed the network, decoded the literal native Q bits and reproduced **1008/1008** free strings and 4,464 teacher-forced second-word individual predictions. This is independent **inference**, NOT independent optimizer-trajectory re-training.
- Recorded real inference: 15,262 free-generation forwards + 4,464 teacher-forced second-word forwards = **19,726**, **215,407,920** inference dense MAC. ZIP CRC, all source/checkpoint/output SHA256 and clean-extraction replay passed.
- External actual calls: **NVIDIA 0** (no authorized read-only endpoint in this environment), desktop Codex 0, Gemini 0. No teacher LLM calculating student answers.

**Next owner:** independent small-NN researcher. Before adding more masking, diagnose r2 STOP on fresh heldout contexts, and then compare any added structural prior against an equally constrained non-SLE ordinary bit-input baseline. Preregister new genuinely untouched term-role and context split; do not tune on these now-viewed test cases or silently continue this failed checkpoint. Pro UR1 PR #12 already genuinely trained in its own branch (17/36 taught, 0/18 holdout), not just an unapproved freeze.

[更新] Restricting second-word input improves familiar retention and r1 STOP but does not reliably fix high-bit generalization and can worsen hard r2 STOP. [取代] Extending the first-word hard route would probably complete the copy mechanism. [原因] 0/3 predeclared pass and 0/60 high-b second-word correct, even as familiar performance improved. [狀態] numerical result high confidence; neural internal mechanism beyond imposed routing low confidence.
