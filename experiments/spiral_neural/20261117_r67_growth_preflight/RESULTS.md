# R67 H86→H110 source-missing preflight — real diagnostics, not Fable reproduction

**T actual test after remote frozen specification:** `d68a3efaaf90530bca82089c4305337225760119` (preregistration was remotely read back **before** first new forward).
Source SHA256: `905cf9fd565f957c7db3aa32f907f07752b1ab2b08f025e1743fcf99c4ee1a75`.
Independent verification source SHA256: `43d9deecf109c6437715d95bda6077ab1fca8020e0de8ca3220da92e00849d99`.
96-case raw manifest SHA256: `2199c4f41a7f0fe35c808f4192405501abd6d366c4995a220e795cf84b85b6e3`.

### Strict boundary
No access to the H-drive Fable handfilled 151→86→41 original, trained baseline B, legitimate Fable 151-input codec, left-rotation checkpoint, or hashes. No A/B/C comparison, no old-skill retention and **zero actual student learning updates**. SLE-AE1-n5-v1 legal 39-bit `01` questions were extended by 112 fixed zeros solely to exercise the H86/H110 shapes; 41-bit debug gradient targets are NOT Fable answer semantics. This is independent engineering reconstruction, NOT Fable reproduction.

### Results from executing this frozen source
```
python r67_growth_preflight.py --require-source-sha 905cf9fd565f957c7db3aa32f907f07752b1ab2b08f025e1743fcf99c4ee1a75 --out outputs
python verify_r67.py outputs
```
Three predefined seeds 101/202/303; 96 distinct legal raw bit questions (train 64 operands 0..23; validation16 operands24..26; test16 operands27..29). All 6 preregistered engineering gates PASS. 151→86→41 random old weights held frozen, 24 new tanh hidden units with random new incoming weights and zero new outgoing weights. On **all 96 inputs for each seed**, H110 logits were bit-for-bit identical to H86 at step0; max absolute change 0.

| Seed | new outgoing gradient norm at step0 | new incoming gradient norm at step0 | new incoming gradient norm after one debug outgoing-only update |
|---|---:|---:|---:|
| 101 | 0.2586502215 | 0 | 0.0015539546 |
| 202 | 0.2825361236 | 0 | 0.0018604300 |
| 303 | 0.2530583031 | 0 | 0.0017067793 |

This verifies capacity *can* receive training signal after a safe zero-step expansion. It does NOT show improved generalization or ease of learning left rotation.

Params 16,639→21,271 (+4,632). Dense forward MAC 16,512→21,120 (+4,608). Training updates = 0; there were only 3 synthetic first-step gradient probes on the new outgoing weights. NumPy read-only independent replay of three zero-step preservation checks PASS.

**Evidence archive**: `sle_nn_r67_h110_growth_preflight_20261117.zip`, SHA256 `4803fec88ef3c4cb77e9d74298933e27e52d18f6ad3a1817bcd199dbe3e9688f`, uploaded to authorized ChatGPT Library exchange `/SLE_NN_Exchange/archives/` for validated Codex transport; Git holds results, preregistration, provenance and SHA but not full unpublished H-drive sources. Archive includes full runner and verifier, raw 96 Q, results and 3 synthetic engineering checkpoints.

**Next owner: Dot coordinator / authorized local Codex mover**, only to inventory/transport Fable code, codec, original H86 handfilled weights, old-skill lesson and checkpoint, and SHA. No Windows access has been requested or granted by this report. When exact files are available and authorized, preregister the true A handfilled H86 vs B trained H86, both H110 grow with paired seeds and the *same* legal bit profile, same new-neuron initialization, same old-skill starting gate, left-rotate heldouts, train budget and retention. C random H110 as size reference. Stop if A/B old skill is not comparable.

U=user hybrid priority; F=Git #5, #10, #12, #115–117 and frozen R67 script (no H-drive files); T=present synthetic forward and gradient diagnostics; A=real A/B/C plan. NVIDIA calls=0, no authorized worker endpoint; Windows Codex calls=0; no auto-merge or other branch changes.