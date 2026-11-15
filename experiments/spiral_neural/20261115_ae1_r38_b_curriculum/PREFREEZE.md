# R38 pre-training frozen registration — 2026-11-15

Owner: independent small NN SLE 01 researcher. Parent: Draft PR #87 / `research/sle-ae1-r37-b-role-highbit-20261115`. Independent SS arm (SLE input → SLE output); no Codex/Pro/VM/parser modifications. **No R38 NN forward or gradient update before this Git freeze.**

## One factor

Source is R31 native-01 course: 136 ordered events, 122 semantic questions, 1408 targets/epoch. The **only change** is the 8 r=2 second-role teacher appearances at indices **68,70: b20→26; 73,75: b21→27; 76,78: b22→26; 81,83: b23→27**. All r, a, c, d, event order, optimizer, seeds, loss, masks, network and target budget remain as before. New 26/27 each have four r=2 teacher appearances; old b18/19 stay taught; old b20–23 are displaced (retention diagnostic).

## Legal format and budget

SLE-AE1-n5-v1, domain integer 0..29, numeric value word `bin5(n)+0`; original Q `01 + 010 + bin3(r)+0 + word(a)+word(b)+word(c)+word(d) + 111100`, exactly 39 raw 01 bits, r=2 answer two 6-bit words + external STOP class S. No 30/31 or unapproved UR1 profile. Fixed no-firstword-mask student with secondword b-only engineered mask, **10,457 parameters**. Seeds 101/202/303, init `seed+12000`, Adam 0.003, batch 64, shuffle `default_rng(seed+201000+epoch)`, 150 epochs, **3300 updates/seed** (9900 total), **633600 train target presentations** and **6,918,912,000 training forward theoretical dense MAC**, excluding backward.

No training/validation reassignment. Historical R31 validation and original SS checkpoint controls stay frozen. Test splits: heldout b26/27 (16 R37 contexts ×3 seeds), known b18/19 (16 R36 contexts ×3), displaced b20..23 (16 new contexts ×3), historical r1 retention (80 R31 contexts ×3). R36/R37 old SS responses are reused; old SS displaced and r1 retention will be computed once to establish matched baselines. Tests are historically exposed to the researcher, **not blind new-number claims**. Exact raw tuples and targets are locally frozen.

## Prospective combined gate

PASS if **all four**: heldout high-b secondword ≥24/48; previously taught b18/19 secondword ≥44/48; displaced b20..23 secondword ≥36/48; historical r1 exact retention declines ≤12/240 versus R31. Any failure means overall FAIL. Also report seed-level, autonomous exact and correct-prefix STOP separately. Never add training/seed after observing test.

## Integrity receipts (created before model training)

- `r38_b_curriculum.py` local SHA256: `8704b05a8b1ec152fa9e3184e0248c6529ce975660277ba75c7375602d0a122e`
- Frozen native 01 `r38_manifest.jsonl`: `781e351ead001a74a30f75be3f92347bbe70530149a4fec126b23b35c90c35b9`
- `r38_prereg.json`: `8dfb4d25f96c6df2e908efc27383cbea5b0e784c20d778b28aa54de3defa04c6`
- Static gate **PASS** (no forward): 8 and only 8 changed b-role lessons, legal 39-bit raw Q, 128 unique test questions, X=(1408,160), 10,457 parameters, no test Q in new training course; source/checkpoint SHA bundled into frozen prereg.

## Provenance / permissions

U: user-authored requirement for small SLE neural network binary education, causal testing, no competing VM/parser work. F: Codex P031–P035; Pro UR1 PR #12 (separate, actual neural test already completed); R31–R37 original checkpoints and raw outputs. T: pre-training static gate only at this commit; **no new NN training or inference yet**. A: role-specific exposure may recover b26/27 but harm displaced or old skills; not an established mechanism. NVIDIA: skipped, no authorized callable OpenRouter endpoint, actual calls 0. Local Codex: absent, 0 calls; Gemini: 0 calls. No LLM teacher oracle, no auto merge, secrets, or private conversation uploaded.

Next owner: current independent NN worker after freeze: run once, preserve failures, exact original raw 01 outputs and SHA artifacts; independent PyTorch and NumPy checks. If code is later uploaded to Git, verify its SHA matches this preregistered source.
