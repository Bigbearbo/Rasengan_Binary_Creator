# R60 framing-bit diagnostic — results and next owner

**Prerequisite:** see `PREREG_FROZEN.md`, committed as `d24aafcd1f026db675f38011486e60da3ebe014a` and fetched/verbatim verified **before any R60 neural forward**. R59 parent PR #110 exact head `df7d6d7b13ae2df8d4bf1cbc3c6484fb70a44d55`. No changes to other NN lanes, P030–P035, Pro UR1, VM or parser.

## One variable and controlled data
- Original *legal* profile: `SLE-AE1-n5-v1` 39-bit raw-01 question, value domain 0..29. **Intervention** flips only bit index 0 `01...` → `11...` which is deliberately **INVALID SLE**; it is a protocol negative control, **not** a new valid SLE problem, numeric blind set, or training target for rejection.
- Reuse 96 R59 legal original questions (validation32/test64) and their previously frozen 864 actual answers, one matching mutant per Q. R52/R55/R56 × seeds 101/202/303 = nine frozen 10,465-param checkpoints. Historical course 136 lessons; **zero new training updates** and training dense MAC zero.
- Freeze hashes: runner `a15c842d9673dc3f517aac0dbe54227604ff8dc8718bed799dc743173d587970`, prereg JSON `5bdbbb6e09fd96c966a8a030545b7cc0fb3fefdf8844d08a09ccc1935c6529e3`, 96-item manifest `ad5e76980f2ebcb156a4006cdeb77c6bdbdd134574ade8538b73f667b445285c`. These were generated and recorded in Git before test; all fixed-source hashes checked at runtime.

## Real neural inference and independent replay (T)
| Preregistered diagnostic | R52 | R55 | R56 | All |
|---|---:|---:|---:|---:|
| New invalid-bit free 01 answers **exactly identical** to frozen legal answers, including STOP/cause | 288/288 | 288/288 | 288/288 | **864/864** |
| Independent NumPy frozen-weight replay on new invalid probes | 288/288 | 288/288 | 288/288 | **864/864** |

Gold-prefix logits on valid/invalid matched probes max absolute difference **0.0**. **8,715 fresh autoregressive forward calls ×10,920=95,167,800 theoretical forward dense MAC**, 864 new *student-generated* raw-01 answers, no LLM teacher oracle, 0 training updates. All six prereg diagnostic gates **PASS 6/6**; this is an architectural diagnostic pass, NOT a success at SLE understanding. Of the 864 reused valid controls, **537 were already incorrect**; the exact same response on invalid input has no well-defined mathematical correctness.

Concrete preserved negative case (R52, seed101): legal `010100010001010110010001010111000111100` → student `000010S`, legal expected `001010S`. Mutant **invalid** `110100010001010110010001010111000111100` → student **same** `000010S` rather than recognizing malformed framing (rejection was not in student curriculum, so cannot grade as taught skill).

## Explanation and boundary

Actual R52/R55/R56 forward paths encode only data `z[:,9:33,:]`, role `z[:,5:9,:]`, and generated position; framing positions `0..4` and `33..38` are omitted. This explains the **bitwise identical** matched logits/answers without appealing to a mysterious inability to learn SLE. The full Q is presented as bits, but its header is never fed into the learned feature pipeline. This was already true in the earlier R50→R52 path, and R55 value-gate did not correct it.

[更新] The nine present frozen students are insensitive to SLE bit0 framing, proven with real outputs. [取代] Inferring recognition of the entire 39-bit SLE protocol from a raw-01 interface. [原因] The forward source slices ignore framing and all 864 new matched predictions remain identical with max logit delta 0.0. [狀態] High confidence for these checkpoints and this intervention; no general verdict on frame-aware architectures.

## Raw evidence, provenance, command

The complete portable package `sle_ae1_r60_framing_ablation_20261116.zip` **SHA256 `0456137f1beecdad134377eb968255d0634189d2f025f69f9bb0bf8c5fc55915`** has 406 members, 405 verified file SHA256 entries, **all 398 original R59 archive member bytes preserved**, full original checkpoints and student runner, 96 matched legal+invalid Q, 864 new answers, prereg and all failure examples. New answers: `r60_outputs/raw_results.jsonl` SHA256 `059ef2faa3a01f7bc3da0d33c4806cb723dfc71a95500c9c8ecca013e9fca8fd`. The new `verify_r60_public.py` on this PR is stdlib-only; Git **does not contain** entire weights/answers and cannot independently execute the NN until paired with the archive.

After extracting ZIP, `cd r56_workspace`:
```sh
python r60_framing_ablation.py static
python r60_framing_ablation.py numpy
python verify_r60_public.py
```
These 3 were actually run PASS locally, plus one fresh `eval` run **after** remote freeze. `eval` deliberately refuses to overwrite existing results. The originally archived R59 metadata is not attributed as new T.

Provenance: U author's independent raw-01 and falsifiable teaching goal; F committed Git guidance and original R52–R59 checkpoint/traces; T this turn's remote prereg, 864 real model calls, independent NumPy and stdlib replays; A hypothesis that frame bits were feature-sliced away, supported by direct source. NVIDIA 0 actual calls (no authorized accessible worker), local Codex 0, Gemini 0. No merge.

**Next owner** independent SLE NN researcher. Pre-register a **legal framing-aware** input representation and matched-parameter / equal-update control, or design a **separate invalid-protocol rejection curriculum with a legal reject output** if robustness is desired. Keep full exact-Q, numeric-domain, generalization, STOP and old-skill gates; don't retrofit this already exposed corpus into a blind test.