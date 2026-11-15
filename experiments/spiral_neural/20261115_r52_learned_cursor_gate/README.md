# R52 — learned eight-parameter cursor-conditioned source gate (2026-11-15)

**Real PyTorch training + autonomous raw-01 neural generation. Preregistered joint diagnostic gate PASS 6/6; robust generalization NOT achieved.** This is an independently scoped small neural-network study, not the Pro UR1/VM/Codex/parser track.

## Provenance / causal control
- Parent: [R51 PR #102](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/102), head `03a03709477d459379287c0149e6c2779cab8178`; inherited **immutable R50 backbones** (seed 101/202/303), 10,457 params each.
- **Pre-training Git freeze commit `7ce617cbc65517697c2fea22f0d94dbaba17bc8a`**, made *before* all R52 neural computation; prereg JSON sha256 `026e3adb5b38114572ec27cd3eb06fb23d17d59180e69eb42601fc08af8c815e`; runner sha256 `4fdbada2112eb6741cee7b08435c5d2df0c89354d6586b9e4fcc6b7d8a3e5c46`.
- **Unique changed variable:** introduce **8 trainable sigmoid weights** = 2 pre-engineered output cursor regions × 4 input sources (a,b,c,d), all initial logits 4.0. Every original model parameter frozen. STOP sees original full input. The model learns gate weights from existing training prefix/targets, rather than a researcher selecting b-only at test time as R51 did. **The cursor-region division is supplied in advance**, not inferred by the model.
- Legal `SLE-AE1-n5-v1`: r=1/2, numbers 0–29; exactly 39 raw question bits `01+010+bin3(r)+0+4*(bin5(v)+0)+111100`. Answer is `r*(bin5(v)+0)`, followed by an **external STOP action S**, not on-wire sentence punctuation.
- Fixed original 136 training lessons → 1,272 non-STOP supervised target positions; seed-specific RNG `seed+52001`; Adam lr=.07; **500 updates per seed, batch64**, 1,500 optimizer steps/96,000 target presentations total. 10,465 total params/student, 8 trained (10,457 frozen). Training-forward dense MAC proxy **1,048,320,000**; excludes backward/gates.
- Test 80 historical-retention +96 previously inspected legacy +96 previously R50/R51-tested fresh-*exact-context* questions, ×3 seeds=816. **Neither 'fresh' nor b18..29 is truly uninspected numeric-domain blind testing**. No heldout tuning or additional seeds.

## Actual results (three seeds aggregated)

| Measured item | R50 full sources | R51 externally forced b | R52 learned gates |
| --- | ---: | ---: | ---: |
| Previously examined fresh-context secondword | 86/288 | 240/288 | **212/288** |
| Previously examined fresh-context firstword | 54/288 | 54/288 | **78/288** |
| Previously examined fresh-context **complete incl self STOP** | 28/288 | 47/288 | **66/288** |
| Legacy firstword | 10/288 | 10/288 | **0/288** |
| Legacy secondword | 98/288 | 240/288 | **184/288** |
| Legacy **complete incl self STOP** | 2/288 | 8/288 | **0/288** |
| Historical retention complete incl self STOP | 210/240 | 222/240 | **220/240** |

Per-seed R52 fresh complete: **22/96, 4/96, 40/96**. Despite passing all the *registered* numeric criteria, the serious legacy regression (2→0/288 complete), Seed 202 weakness, and many paired losses mean this is NOT a stable broadly generalized copy model. R52 vs R50 fresh complete: 45 newly correct, **7 previously correct lost**. R52 vs R51 fresh: 31 gained and 12 lost. Retention vs R50: 11 gained, one lost. Legacy: no gains and two losses.

## Learned gate values (first/second cursor, source order a,b,c,d)

| Seed | First word | Second word |
| --- | --- | --- |
| 101 | [.99978, .45702, .98155, .99307] | [.28004, .99976, .48478, .39446] |
| 202 | [.99980, .35127, .99973, .99978] | [.49869, .99976, .91633, .45944] |
| 303 | [.99978, .40542, .87350, .99198] | [.14752, .99974, .40664, .29196] |

All three firstword rows have a highest, all three secondword rows have b highest, as preregistered. **Firstword c/d weights often remain nearly as high as a**: this is NOT exclusive source isolation, nor learned algorithmic role assignment beyond the engineered two-cursor prior.

Pre-registered six *joint required* tests: fresh secondword ≥R50+48; fresh firstword ≥R50−12; fresh full ≥R50 28; retention full ≥R50 210; each seed a highest firstword; each seed b highest secondword. **PASS 6/6 as a limited diagnostic, not a global success claim**.

## Raw failed/successful cases (not hidden)
- Fresh seed101 `010100100001000101010001010010000111100`: expected `001000101010S`; R50 `000000000010S`; R51 `000000101010S`; R52 **`001000101010S`** (rescued).
- Fresh seed101 `010100100001010101110001010010000111100`: expected and R50/R51 `001010101110S`; R52 **`001010111110S`** (new regression).
- Legacy seed101 `010100100001110110110011000011100111100`: expected and R50/R51 `001110110110S`; R52 **`000010110110S`** (lost correct first word).

## Evidence, reproducibility, costs
Three real seed-specific trained gate JSON states and 816 raw native-01 free outputs in companion ZIP `sle_ae1_r52_learned_cursor_gate_20261115.zip`, **SHA256 `c749c56d71a1bc5d41363e8bc6d207cd99a5296f80f0bcc77dab0bacc57c1db1`**, **307 members**, including all prior R50/R51 checkpoints and code. **This ZIP is a conversation attachment, NOT stored in Git.** Git alone does not reproduce neural outputs.

From newly extracted ZIP:
```bash
python verify_r52_package.py
python r52_learned_cursor_gate.py replay
python r52_learned_cursor_gate.py numpy
```
Performed after clean extraction: original R51 **296 inherited SHA256 checks** and **9 added SHA256 checks** PASS; real neural PyTorch free-generation replay **816/816 identical**, independent NumPy reimplementation **816/816 identical**. STOP logit is unchanged for **816/816**, as its input was not masked. R52 new test forward calls **11,884**, inference theoretical dense MAC **129,773,280**, separate from training MAC; gate/backprop compute not accounted. Original R51 strict verifier refuses extra future R52 files by design; use the R52 verifier (which checks all 296 original member hashes) instead. The inherited R51 verifier is not modified.

## Judgment / next owner
**[更新]** A supervised 8-parameter conditional gate can, in this *exposed task*, preferentially weight firstword=a and secondword=b and improve some complete answers. **[取代]** R51's researcher-supplied b-only mask was the only available way of restoring secondword behavior. **[原因]** Only 8 new weights trained; R52 full answer 28→66/288 in previously inspected fresh contexts. **[狀態]** Actual numerical replay high confidence; general source selection and novel-value transfer low confidence, especially legacy complete 0/288.

Next independent NN worker: design a **new genuinely never-inspected legal train/val/test numeric-role partition**, matched native ordinary-binary control and equal total budget. Separate firstword/secondword/STOP, repeat r1/r2/r3 only after legal independent profile preregistration. Do not retune this exposed R52 test or merge stacked PRs. P031 shared math bank has 1,342 synthetic cases but verification of bank consistency is **not** student math learning.

**Ownership:** U=user research direction; F=Git parent, R50/R51 immutable model/checkpoint/codec; T=R52 actual PyTorch Adam training/816 native free outputs/two independent replay paths/ZIP integrity; A=learned conditional source gating hypothesis. NVIDIA status skipped: no authorized direct model endpoint; Codex/Gemini/NVIDIA actual calls **0**. No Pro UR1, Codex, parser or Hamster VM writes. No automatic merge.
