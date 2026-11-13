# AE1 one-bit intervention: frozen mixed-r students (2026-11-13)

Owner: independent scheduled NN research. Work ID: `SLE-AE1-BIT8-TRANSFER-20261113-12`. Parent [PR #40](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/40) HEAD `80b814f0c4041471cd99395d2a10f6c86cb4f2d3`. Public preregistration commit **`ead3e96c7f982061bb5fdd41b1961a7d43f1389d` precedes inference**. Do not merge automatically or edit the Pro/Codex/VM/parser branches.

## Single intervention and prior evidence

Use the two *existing, actually trained* PR40 float32 checkpoints (seed101,202), 10,499 parameters each, no new optimizer updates. In legal **SLE-AE1-n5-v1** 39-bit question, hold `r`, first data `a`, last data `c=d=0`, weights and greedy-generation algorithm fixed. Change **only** second data value `b=16..21` to `b+8=24..29`, toggling a **single input information bit at Q offset16**. At r1 the required answer is unchanged; at r2 the second answer token must differ only at output bit7. Reserved ordinary IDs30/31 are never used. No teacher oracle enters NN inference.

Example r2, a4:

```text
b16 Q 010100100001000100000000000000000111100 -> expected 001000100000S
b24 Q 010100100001000110000000000000000111100 -> expected 001000110000S
                                                   observed 001000100000S (seed101)
```

Original mixed-r high-domain train uses b15..23 and a0..3, with heldout partners a4 (val) and a5 (test). This probe includes a0..5 and compares six trained values b16..21 to six untrained values b24..29. **Important nuance:** value8 information bit itself was *not* wholly unseen (b15 had bit8=1). What was new is the conjunction of high value16 bit and value8 bit being 1 in the same second word. Consequently the observed failure is an inability to generalize this specific combination, not proof that the student never learned to output value8 bit.

## Actual results (T; checked after prereg)

The original 288 PR40 raw generated outputs were replayed with checkpoint hashes verified: **288/288** bit-identical including STOP and forward counts. New independent NumPy student generation: **288** answers, **144** matched input-bit intervention pairs, **2,880** NN forwards, **30,044,160** dense MAC. Separate PyTorch implementation replay: **288/288** identical answers, **2,880** further forwards. Training updates 0; full backward/optimizer cost 0. All new outputs have correct STOP position (288/288).

| Both seeds combined (a0..5, 72 cases per cell) | b16..21 | b24..29 |
| --- | ---: | ---: |
| r1 exact (b irrelevant) | 72/72 | 72/72 |
| r2 exact (must copy b) | **72/72** | **0/72** |

All **72/72 r2 pairs** gave exactly the **same predicted entire output** after the one-bit input change, despite their correct answers needing to differ. All 72/72 r1 pairs remained invariant, as required. Both seeds separately gave r1 novel 12/12, r2 original 12/12 and r2 novel 0/12 on a4/5 heldout partners; both passed baseline control, **both failed the preregistered transfer gate**. First output word and STOP remained correct. This is a targeted *output-level* result; hidden activations may still change.

Full `RESULTS.json` records hashes, costs and gates. A companion ZIP delivered to the owner contains all **288 native-01 Q/expected/actual**, 144 paired diffs, weights and independently rechecked source archive. The Git branch has source and summary but **does not contain the prior weights or all raw rows**: a Git clone alone cannot regenerate model answers without the authenticated-by-SHA PR40 archive. No claim of complete Git-only reproducibility.

## Reproduce

```sh
python reproduce.py /path/to/sle_ae1_high_r_mixed_20261113.zip ./replay-output
```

Needs NumPy; checks parent ZIP SHA256, previous files + full checkpoint state hashes, replays all 288 earlier predictions before generating the new 288, saves raw cases and metrics. `reproduce.py` ran locally: PASS, including previous 288/288 and the same aggregate results. The companion evidence ZIP also includes the independently written extended `bit8_transfer_probe.py`, PyTorch cross-check results, full raw and pair JSONL, and per-file SHA256.

## Interpretation / provenance

[U] User requires genuine raw-bit independent small-NN generalization and controlled failure records. [F] PR40, PR39 and older P030–P035 checkpoints/reports, repository handoff and AGENTS. [T] Executed NumPy and PyTorch inference on frozen weights, plus SHA/file/profile gates. [A] These students currently fail to compose the previously encountered bit8 and bit16 patterns on the second answer word. No claim about universal SLE limits, architecture causation, statistical population generalization, or SLE advantage against normal binary.

**[更新]** mixed-r instruction solved r1/r2 performance on trained b15..23 but not novel b24..29 with exactly one changed input bit. **[取代]** “mixed r teaching implies general raw-bit copying.” **[原因]** output invariance on all r2 one-bit intervention pairs. **[狀態]** high confidence for these two frozen checkpoints, low for causal hidden-unit diagnosis and architecture generality.

The a4/5 partner context was previously examined; this is not a fresh analyst-blind test. Only two seeds and one six-pair numerical neighborhood. No new formal training, no VM / dictionary edits. Codex local calls 0; NVIDIA 0 (no available authorized worker); Gemini 0.

Next owner: independent NN reviewer / Codex may verify the SHA-based archive; if training a follow-up, **preregister a new value/position exposure policy and untouched test domain** before observing scores. Do not retune on these now-open b24..29 results or treat this control as proof of unseen-family generalization.
