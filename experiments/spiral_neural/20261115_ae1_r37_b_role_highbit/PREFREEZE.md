# R37 pre-inference freeze — role-b single-bit high-value transfer

Work ID: SLE-AE1-R37-B-ROLE-HIGHBIT-20261115. Independent small neural-network research; separate from Codex P030–P035, Pro UR1 #12, VM/parser.
Parent: draft PR #86, exact head `f208308d6b9d816191e749ee51acb2dfa853fbd7`. Independent branch `research/sle-ae1-r37-b-role-highbit-20261115`. **No R37 neural forwards or optimizer updates ran before this freeze.**

## One intervention and prior result
R36's known r=2 second values `b=18,19` were copied 192/192 across four codec arms. R37 tests whether that success transfers to previously **untrained second-role** values `b=26,27`, paired `18→26`, `19→27`. Exactly ONE input data bit toggles, with corresponding ONE target bit toggle. a, c, d, task r, checkpoints, codec, model architecture and all output generation parameters remain fixed. This is **not** a globally blind new-value claim: numbers 26/27 appeared in other roles and earlier probes.

## Raw 01 / sources / immutable registration
SLE profile: `SLE-AE1-n5-v1`; numeric operands 0…29; numeric SLE word `format(n,'05b')+'0'`. Binary6 (`format(n,'06b')`) is a six-bit **control only**, not an SLE profile. SLE-frame question bits are `01 + 010 + format(r,'03b')+'0' + word(a)+word(b)+word(c)+word(d) + 111100`, always 39 literal 01 bits. Output is word(a)+word(b)+external S stop class for r=2 (12 wire data bits, S is not transmitted wire bit). Input and answer numeric codecs per arm: SS S/S; SB S/B; BS B/S; BB B/B.

The **16 fixed semantic cases** are the Cartesian product `a∈{14,15,28,29}`, paired `(b_old,b_new)∈{(18,26),(19,27)}`, `c∈{1,3}`, `d=5`, `r=2`. Build all literal raw Q/expected by the above deterministic word codec per arm. They were materialized and fixed **before any R37 NN execution**:
- Exact `r37_manifest.jsonl` SHA256: `5c7ec52d3d59ef01875f4e033495de6ac77a066bb1193c060251950608b19dff`
- Complete `r37_prereg.json` SHA256: `ce3bacfa036390eb0ad06224b07a226d3964d00f13779ad84175856f97f16223`
- Runner `r37_b_role_highbit.py` SHA256: `f2846f5bc012377b6f2aad791124fa615b51e9eca08377895e728b17c98a37e2`
- Source archive: immutable R36 companion ZIP `sle_ae1_r36_arity_transfer_20261115.zip`; SHA256 `e329545a7a2f1df131d530d71cacd585e6a85886737a4291b390151d312a6f9b`.
- Prior frozen control rows: R36 `r36_outputs/raw_results.jsonl`, only `r=2`. No re-running controls.

**Static preflight only** completed before freeze: original 12 checkpoint hashes matched archived controls; 136 historical ordered training events, b26/27 absent from second-role training; 16 unique semantics and 64 arm/Q combinations, no exact Q in existing 192-control set; 10,457 parameters each, no network forward.

## Fixed experimental budget, splits, gate
Historical training only: 136 ordered examples / 122 distinct questions, 1,408 teacher targets per epoch, 150 epochs and 3,300 Adam updates per seed per arm (101,202,303); none are retrained this round. Historical validation from prior arms remains untouched; no model selection. New `test_heldout_b` = 16 semantics ×3 seeds×4 arms = 192 autoregressive 01 generations. Existing `control_b` = 192 recorded R36 responses. Inference dense MAC estimate is 10,920 per forward, count actual forwards; new training MAC = 0.

**Primary prospective gate:** PASS only when BOTH matching-codec arms SS and BB each satisfy all four: heldout secondword correct ≥36/48, existing known-b secondword correct ≥44/48, correct paired single-bit response ≥36/48, and firstword unchanged under b flip ≥36/48. Otherwise FAIL. Mixed arms descriptive only; always report true-prefix STOP and free-run exact separately. Do not adjust test or gate after observing results, do not retrain following failure.

## Provenance/permissions
U: user's 01 NN education/generalization focus. F: P030–P035 and Pro #12 UR1, real R31–R36 checkpoints/outputs; last R36 result failed r1/r2 transfer and achieved known-b secondword 192/192. T at freeze: static preflight only, no fresh inference. A: known-b copying might be specialized; higher b may alias to 18/19. NVIDIA live calls 0 (no authorized callable endpoint in this runtime); local Codex 0, Gemini 0. No teacher LLM oracle. No merge, rewrite, private conversations or API keys.

Next owner: independent SLE small-NN researcher; after sealed run preserve both success/failure, raw outputs and checksum receipts. Full companion ZIP must accompany Git receipts for stand-alone replays.
