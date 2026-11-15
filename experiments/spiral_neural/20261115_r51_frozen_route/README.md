# R51 — frozen R50 projection: second-word b-only inference (2026-11-15)

**Actual inference diagnostic, joint preregistered gate PASS 5/5.** The freeze was published in Git commit `5987b77feb048a278074088db7b91168d856fd7e` **before** any R51 model forward. Parent R50 [PR #101](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/101), head `7bb9923a1399db474f4ea29b758ef8fce75f1382`. No training, merges or external worker claimed.

Only intervention: three immutable R50 seed101/202/303 checkpoints keep full input visibility for firstword and STOP, but at r=2 secondword positions 6–11 use **b-only** instead of a+b+c+d. No weight or curriculum updates, no supervised answers during free generation.

| Three students | R50 open | R51 b-only | Paired transition |
|---|---:|---:|---|
| Legacy secondword, 96Q×3 | 98/288 | **240/288** | +150 rescued / 8 newly wrong |
| R50-tested new-context secondword, 96Q×3 | 86/288 | **240/288** | +164 rescued / 10 newly wrong |
| Legacy full exact + self STOP | 2/288 | **8/288** | +6 / 0 lost |
| New-context full exact + self STOP | 28/288 | **47/288** | +21 / 2 lost |
| Historical retention full exact + self STOP | 210/240 | **222/240** | +13 / 1 lost |
| First 6 generated bits (literal parity) | | **816/816 identical** | |
| Nonintervened teacher-prefix logits | | **2232/2232 identical** | |

Fresh-context full exact by seed: 101 **7→11/96**, 202 **7→6/96**, 303 **14→30/96**. Thus projection improves aggregate results but is **not monotonic**: three previously complete-correct Q become wrong.

**All five predeclared gates passed**: fresh secondword ≥+48; legacy secondword ≥+48; firstword correctness invariant; fresh full exact nondecrease; ≤12 previously correct historical full answers lost (actually 1/240). It would be incorrect to claim the network has learned autonomous selection of b — an external researcher supplied this mask.

## Input / evidence

Legal `SLE-AE1-n5-v1`, values 0–29, exactly 39 literal 01 input bits; 136 original read-only lesson events; 80 historical retention, 96 old tested and 96 R50-tested new exact-Q contexts, all ×3 seeds. All b18–29 values were previously exposed. No new numeric-role blind set and no new independent generalization trial.

Three **10,457 parameter** students, **0** new Adam updates, **0** training MAC, **25,276** actual forward calls, theoretical inference forward dense MAC **276,013,920** (not backprop). 816 new native free generations incl external S stop action, plus gold-prefix secondbit and stop diagnostics kept distinct. PyTorch full replay **816/816**, independent NumPy free replay **816/816**, identical bitstrings, STOP causes and forward-step counts. Original R50 source/archive 288 SHA256 checks PASS before freezing, and after clean R51 ZIP extraction original 288 and R51 **296** files pass integrity checks.

The full public synthetic companion package contains 3 frozen checkpoints, 816 paired rows, raw failure cases, exact prereg JSON, runner `r51_frozen_r50_route.py` and `verify_r51_package.py`. Filename: `sle_ae1_r51_r50_frozen_b_projection_20261115.zip`, SHA256 **`77b3352c42e6e51dbc0dd1c70d087783f238b3671dee2c465bbc479ac6cdac1f`**. It is attached to the research conversation, **not uploaded to Git**, so Git documents/verification alone cannot reproduce neural generations.

Run from extracted ZIP:
```bash
python verify_r51_package.py
python r51_frozen_r50_route.py static
python r51_frozen_r50_route.py replay
python r51_frozen_r50_route.py numpy
```

The frozen runner SHA256 `dea69e7d3b39a5b9e677000b12ed09251cffa37f92663cb38eeaab93872ec159`; prereg JSON `9697e921d49ab91508094c1ff890389520e73817c7a52ed641c60a5dbc0368af`; output rows `db82f3cee4c40a51b18fa26372dcef68259567cc6e8f9330e7584df5190f90f6`; summary `951151cc8c5495b465cc585807d85ccd6f71bfc56e6bb3a9d644d8f3d858b486`.

### Demonstrative failure and counterexample

Seed101 new-context Q `010100100001000100100001000001110111100`: expected `001000100100S`; open `000000000000S`, projected `000000100100S`. Secondword rescued, firstword remains wrong.

Seed202 new-context Q `010100100001010101110001010010000111100`: expected and open `001010101110S`; projected **wrong** `001010111110S`. Two such new-context regressions and one old retention regression are in the raw rows.

[更新] Partial b-role knowledge from R50 survives in frozen weights despite degradation under full-source inference. [取代] Most of R50's earlier secondword skill may have been erased during late open-source training. [原因] Same R50 weights show fresh-context secondword 86→240/288 when only inference mask changes. [狀態] Causal paired output evidence high; true neural representation and novel-value generalization low.

**Next owner:** independent NN worker. Study a *learned conditional source selector* with controlled data and a never-inspected legal value domain against matched ordinary binary and full answer/STOP gates. Stop adding arbitrarily tuned mask schedules on exposed data. Pro UR1/Codex P030–P035/VM untouched. Provenance U = user independent research remit, F = fixed R50/Git/prior checks, T = R51 actual inference+replay, A = mechanism hypothesis. NVIDIA/Codex/Gemini actual calls 0; no authorized NVIDIA endpoint in this runtime.
