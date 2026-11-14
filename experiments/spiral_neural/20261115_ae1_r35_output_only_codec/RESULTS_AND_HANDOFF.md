# R35 — completed fourth numeric-codec cell (SLE input / binary6 output)

Status: **INCONCLUSIVE** by the pre-published symmetric gate. Public freeze was committed as `1d70449210b9a574932e6484d4bb6faa7ec7273d` **before** the new PyTorch training. Workstream: independent scheduled small-NN SLE 01 research, not Pro UR1 or Codex P035. Dates: 2026-11-15. Parent [R34 PR #84](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/84), head `a3de2320428683b11328ffd8f9f457de0d2dbaba`.

**One new factor:** six output numeric bits switch from SLE n5 word + terminating 0 to padded ordinary binary6; **39 input raw bits remain SLE-AE1-n5-v1**. Only the input is a legal SLE profile; hybrid binary6 output and analogous previous cross-code arm are not entire valid SLE messages. External `S` is a STOP class, not a raw input bit. The trainer is unchanged 10,457-parameter `NoFirstMask`, and the same ordered 136 semantic course records are rendered into the chosen target codec. P031 math-bank semantic tests do not prove NN learning.

| Input → output | Unseen-low first /96 | Unseen-high first /48 | Unseen first /144 | Unseen exact /144 | Taught exact /120 | `test_stop` true-prefix STOP /48 |
|---|---:|---:|---:|---:|---:|---:|
| R31 SS: SLE → SLE (preserved) | 8 | 25 | **33** | 15 | 120 | 43 |
| R35 SB: SLE → binary6 (**new**) | 2 | 17 | 19 | **19** | 120 | 48 |
| R34 BS: binary6 → SLE (preserved) | 1 | 7 | 8 | 4 | 120 | 47 |
| R33 BB: binary6 → binary6 (preserved) | 15 | 17 | 32 | **32** | 120 | 48 |

Pre-registered **SB minus SS**: unseen first **−14/144**; autonomous exact **+4/144**; retention **0/120**; correct-prefix STOP **+5/48**. Unseen-first per-seed deltas: 101 **0**, 202 **−17**, 303 **+3**. Neither direction satisfies both first-word and autonomous-exact thresholds; gate **INCONCLUSIVE**, not PASS and not “SLE won/lost”. Descriptive heldout interaction `(BB−BS)−(SB−SS)`: first **+38/144**, exact **+24/144**, STOP **+11/144**, without p-value or population-generalization claim.

Both matched policies SS+BB combine for 65/288 unseen-first successes versus cross-code SB+BS 27/288. This is a hypothesis-generating observation **not evidence of an intrinsic SLE advantage**: cross-code arms require actual numeric re-encoding while matching arms may use direct copying. Input/output codec choice also affects target-label frequencies.

One preserved fail example, R35 seed101: input `010100010011000100000000000000110111100`, expected `001100S`, generated `000000S` (value a12). Other seeds and failures, 432 full outputs, stored in full companion artifact.

## Training/verification, facts not extrapolations

The exact frozen `r35_prereg.json` SHA256 is `7174a5e646dee2f37666dae5415604322fa09bbad05e09b3f942f1e9d77a1535`; runner source `3f617c46cf67bd641bb0919b01199689cb13954c15b2403da76d115b5440a0a6`; raw train manifest `ae94e8d7f4c730ce6b26451d57edd228a2ab3c93b664e84356b0905bb0897d72`; test manifest `02f04ba556c4c70e49122371d5ee61e0cc2f82dce171602b3e02a394b5782825`. Frozen splits in unique semantic items: validation_low 8; test_unseen_low 32; test_unseen_high 16; test_near 32; retention 40; test_stop 16; three seeds yield 432 new complete outputs. Withheld first-role numeric values were already used in prior historical probes: not globally blind.

Three new PyTorch students seeds **101/202/303**, 150 epochs each, Adam 0.003, batch64, 3,300 updates/student ⇒ **9,900** updates and **633,600** teacher-target presentations. Training **6,918,912,000 dense forward MAC only**, backprop excluded; new 432 NN 01 autoregressive replies, **3,852** inference forward calls and **42,063,840** inference MAC. No seed picking or post-test training.

- `python r35_output_only_codec.py gate` → PASS; `train` once; `replay` → **432/432** original saved whole replies and checkpoint SHA.
- `python r35_numpy_audit.py` → **432/432** independent NumPy neural-forward/autoregressive replay; max true-prefix logit difference **1.9073486328125e−6**. Same frozen tensor weights and xvec representation, independent forward/greedy code; auditor made 0 optimizer updates.
- Raw 432 outputs SHA256 `51689353796bfc05052766458ccde4b0adc6f51a5c3b3a604ae74a5800e8c814`.
- New checkpoint SHA256: seed101 `153aa8807929f3886b95a4ea2daa78644146f1c1cc102c6a6fd74d590580c8a9`, seed202 `4de0d51fe5551046ef03dcd7852352bd80758232f85316fd2fd2032d311be9e9`, seed303 `310bfcdc999275b94db922c3c9bb63ab2ea7e5a5ed339d695c8148455ca1e389`.

**Provenance:** U = user independent native-01 neural education and scientific controls; F = frozen R31/R33/R34 source/checkpoints, Git roles, Codex P031–P035 and Pro UR1 [PR #12](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/12) existing records; T = only this newly executed R35 PyTorch training/greedy and independent NumPy; A = relative copying versus translation difficulty, not established internal NN cause.

**Reproducibility boundary:** complete source, prior and new weights, manifests, raw output traces and verification are in the *conversation companion ZIP*, **not all in Git**. This Git branch contains the immutable freeze, public checker and reproducible aggregate figures, but a Git-only checkout cannot rerun the full NN without the companion archive. No private conversations, personal data or secrets copied to Git.

**Next owner:** independent SLE NN education researcher: preserve these negative/inconclusive results; distinguish cross-code recoding load from rule-generalization; preregister a truly new holdout (confirm legality/exposure of a30/31) or a matched-language baseline and evaluate first-word, autonomous exact, retention and STOP jointly. No Pro/Codex branch overwrite and no automatic merge.

NVIDIA actual **0** (no callable authorized endpoint available), local Codex **0**, Gemini **0**. No new math teaching claimed; P031 shared semantic bank is a separate validation layer.
