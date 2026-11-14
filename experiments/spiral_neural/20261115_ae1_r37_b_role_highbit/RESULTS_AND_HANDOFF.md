# R37 — b-role high-bit transfer, actual neural negative result (2026-11-15)

Independent SLE 01 small-NN work. **Pre-inference Git freeze commit `473802d840153795473f09783c8d4ff5db3dad03`** was created before the first new forward pass. R36 #86 parent head `f208308d6b9d816191e749ee51acb2dfa853fbd7`. Separate branch, no merge, no Pro/Codex/VM/parser code changes.

## One-variable causal probe
R36 correctly produced the *second* numeric answer word b18/19 on all **192/192** r2 outputs (4 codec arms × 3 seeds). R37 fixes all 12 existing 10,457-parameter checkpoints and the r=2 task, a∈{14,15,28,29}, c∈{1,3}, d=5; **only changes b18→26 or b19→27**, toggling exactly one question bit and one desired answer bit. The 192 original R36 r2 responses are the existing no-rerun control; **192 new** model-owned autoregressive responses were generated. SLE arms use legal `SLE-AE1-n5-v1` 5-bit-value+0 numeric words (0..29) with 39 literal input bits; binary6 arms are controlled same-frame **non-SLE** word codings, not complete new languages.

Values 26/27 were **not used in the b-role training curriculum**, but did occur in other training roles or historical diagnostics: this is a role-heldout, **not a globally blind new-numeric-value** test. The neural architecture has an explicitly engineered secondword b-only mask. Any claim is conditional on that architecture and the narrow measured values.

## Frozen primary gate: FAIL

The predeclared criterion required BOTH matching-codec arms SS and BB to meet heldout b correct ≥36/48, old b correct ≥44/48, correct single-bit output response ≥36/48, and firstword stable ≥36/48. No gate edits and no additional optimization.

| input→output | old b18/19 second correct | new b26/27 second correct | correctly flipped 1 bit | firstword stable | new correct-prefix STOP | new full exact |
|---|---:|---:|---:|---:|---:|---:|
| SS SLE→SLE | 48/48 | **0/48** | 0/48 | 37/48 | 16/48 | 0/48 |
| SB SLE→binary6 | 48/48 | **0/48** | 0/48 | 23/48 | 24/48 | 0/48 |
| BS binary6→SLE | 48/48 | **0/48** | 0/48 | 39/48 | 19/48 | 0/48 |
| BB binary6→binary6 | 48/48 | **0/48** | 0/48 | 30/48 | 23/48 | 0/48 |
| Total | 192/192 | **0/192** | 0/192 | 129/192 | 82/192 | 0/192 |

In **160/192** new responses the secondword is literally unchanged from the old b18/19 response, despite new desired b26/27. For SS seed101 `(r,a,b,c,d)=(2,14,26,1,5)`: expected `011100110100S` but student produces `110110100100S`, the same full output as old b18 case; firstword was also wrong. This does **not** prove a universal mechanism, but disproves interpreting the old secondword 192/192 score as a general high-bit copying ability.

## Actual compute / exact reproducibility
- R37 **new** true NN generations **192**, total **4,778 forward evaluations**, 10,920 theoretical dense MAC each = **52,175,760 inference dense MAC**; **zero new optimizer updates / training MAC**.
- Original R36 baseline **192** model outputs **not** rerun or counted as new.
- PyTorch full output replay **192/192 PASS**; independent NumPy forward + greedy output **192/192 PASS**, maximum inspected logit delta **2.86102294921875e-6**.
- Clean extraction ZIP verification **148/148 SHA files PASS**, portable Python integrity/count verifier PASS, independent PyTorch and NumPy replay PASS again.
- Pre-inference manifest SHA256 `5c7ec52d3d59ef01875f4e033495de6ac77a066bb1193c060251950608b19dff`, prereg SHA `ce3bacfa036390eb0ad06224b07a226d3964d00f13779ad84175856f97f16223`, runner SHA `f2846f5bc012377b6f2aad791124fa615b51e9eca08377895e728b17c98a37e2`.
- **Full companion** `sle_ae1_r37_b_role_highbit_20261115.zip`, **SHA256 `899c078f391bb4e85c6ca26dfde73dd4a14d291c6a4f5c3cb20bbb5d253d2cba`**, 2,264,192 bytes, 149 files, includes all 12 original checkpoint JSONs, source, manifest literal 01, new 192 raw responses, old baseline, SHA inventory, failed examples and replay scripts. Distributed as a conversation attachment, **not on Git**; Git alone is NOT standalone for neural replay. See public `verify_r37_companion.py` for independent integrity/count verification only.

**Portable replay** after obtaining the companion ZIP:
```sh
unzip sle_ae1_r37_b_role_highbit_20261115.zip -d R37
cd R37
python verify_r37_companion.py .
python r37_b_role_highbit.py gate
python r37_b_role_highbit.py replay
python r37_b_role_highbit.py numpy
```

## Source/owner
U user small NN raw-bit education and generalization. F historical P030–P035, Pro #12 actual UR1 failed ACK and R31–R36 evidence. T R37 exactly 192 new NN outputs, source/integrity checks, negative result and NumPy replay. A high-b role value alias is a hypothesis about learned representation, not a demonstrated internal weight mechanism. Actual calls: **NVIDIA 0** (no authorized live worker in this runtime), **local Codex 0**, **Gemini 0**; no external teacher for student answers.

Next owner: independent NN researcher. To examine actual **learning**, predefine a matched b26/27 curriculum and retained old b18/19 control under fixed budgets and new student initialization. Alternatively freeze a legally approved genuinely novel task/profile for prospective OOD comparison. Do not rerun this diagnostic or silently change the SLE profile.
