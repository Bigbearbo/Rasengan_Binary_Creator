# SLE-AE1 c2→c3 no-training preregistration (frozen before any new forward)

Work ID: `SLE-AE1-IRRELEVANT-C3-20261113`. Owner: independent scheduled SLE small neural-network study. Source: [PR #45](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/45), exact head `8c008ec60adc67915ad4955ae5ab239784dcf7da`. This experiment does not change the VM, syntax dictionary, Pro UR1, or Codex branches.

**Exactly one intervention:** vary the irrelevant third data word `c`; compare c=2 (previously examined successful anchor) with c=3, which changes just c's least significant 5-bit information position. Keep r=2, a=4/5 (historic val/test), b=26/27, d=0, all checkpoint weights and expected answers identical. Exhaustive additional stress c=4..29; c=3..29 not previously trained, although c0/1/2 and related b/a have been inspected in previous research. Not a fully new researcher-blind test.

**Legal SLE profile:** `SLE-AE1-n5-v1`, Q39 = `01 + 010 + 3bit(r) + 0 + four*(5bit(value)+0) + 111100`; ordinary ID0..29, ID30 END and ID31 UP reserved. Native 01 in, free model-generated 0/1/S out; answer for r2 is the first two full six-bit words plus external STOP `S`. `a4,b26` expected `001000110100S`. Q inputs never include literal S. No LLM teacher/oracle for model inference.

**Frozen students:** PR44 frozen c1-only seed101/202 and PR45 balanced-c seed101/202, four 10,499-parameter float32 networks (160 position-one-hot input, tanh64, three 0/1/S output logits), prefix cap80, generation max32. Actual checkpoint file SHA256, by seed/arm:
- 101 frozen `6472ff0222228b3b95cb2de781ccf9c97ae8f730ddd1caa5e5db95bb67f392bc`; 101 balanced `c795c97cac145507a842f02eb8b8e65c92aa195523a2c8ec3b1f09a94fc0d3e3`.
- 202 frozen `ee930b8fd2803f889502e709ede5e4853448c98901de6d37b03e62a09854047b`; 202 balanced `1ae8a29f40d1ae11410c5948e1fad10088d7e1368744be0356110c8d7e0e2baf`.
- Parent archive SHA256 `c28b58b11977bb8bccd99352dc099f65aefefccfe0f86a12abd44a5d9aae6c0b`; all 16 original bundled file digests checked.

**Enumeration:** seeds2 × arms2 × partners a4/5 × b26/27 × c2..29 = 448 true free-generation Q (16 reused anchor, 16 new primary c3, 416 new stress c4..29). Split a4=historical validation, a5=historical test. Already viewed b, a values; not externally blinded. No training: new students 0, optimizer updates 0, train MAC 0. 10,432 dense MAC per generated symbol, total depends on actual STOP lengths.

**A priori primary gate:** EACH balanced seed must achieve 4/4 exact at c2 and c3, and each of the four c2/c3 paired full generated responses must be identical. Otherwise FAIL. Frozen PR44 controls, proper STOP, bit-level failures and c4..29 stress all reported irrespective of outcome; do not select seeds or retune. Compare output content as well as STOP.

**Immutable local inputs before inference:** `PREREGISTRATION.json` SHA256 `df7690dd089ec895e73cf4bb6842e498a0295dcfecb51c7f3a070ef4737ccf6c`; `probe.py` SHA256 `0c536d0076b65db62b407bdde5900746d7133e9bad8584b02b7819188aefd93c`. Preflight: PASS 448 enumerated rows, four checkpoint SHA and embedded state hashes, one-bit c change, legal Q, fixed answers; zero forward and optimizer calls at preregistration. Full runnable snapshot and raw cases to be supplied after execution. Earlier preflight discovered a wrong local c-bit index (28 instead of 25), corrected **before** this frozen submission; no model forward occurred before correction.

U=author's SLE 01 NN teaching/generalization goal. F=PR44/45 genuine checkpoints and P030–P035/UR1 separate history. T=preflight and bundled file hashes only at freeze. A=even c2-successful students may not preserve c2 output for c3. NVIDIA reserved for an authorized harmless read-only reviewer; absent authorized worker means actual calls 0. Local Codex/Gemini not invoked. Draft only; do not auto-merge.
