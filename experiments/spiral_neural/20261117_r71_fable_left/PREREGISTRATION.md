# R71 preregistration — paired H110 LEFT acquisition (2026-11-17)

Work ID: R71_FABLE_H110_LEFT_AB_C. Owner: independently scheduled SLE 01 neural researcher.
Source: R70 PR #123 (stacked on R69 PR #120), not main. The public branch carries only sanitized program and experimental results; private source/checkpoints live in ChatGPT Library.

## Frozen evidence (F)
- Fable original source ZIP /SLE_NN_Exchange/fable_handfilled_h86_bf6e9e84_20261117.zip SHA256 fffa456a365d2e429ccec16b56f896fb7338cd654528513b247a5e872b285cfe
- R69 /SLE_NN_Exchange/archives/sle_nn_r69_fable_b_old_h86_20261117.zip SHA256 22179e2b944c616d3559195361901dc36c941b788b0340ab58ea9fcb0be94890
- R70 /SLE_NN_Exchange/archives/sle_nn_r70_fable_b_h86_continuation_20261117.zip SHA256 0e4059980160a4776acd760c1728134533d2107614da51b20b765f143c623290
- hand.py SHA256 166ef00fce69386f89a1f832785a77e2fb465b3831c5d78854ac85083deceed8; compiler.py SHA256 bf6e9e84d6b2ddc2462b586fd25c5cb8a2f4fc913bc7803655ccf39591d085ab; original A H86 NPZ SHA256 97d671b42f735bea818878652a4d209e4dcfec3037049327dcb6014095e4e523.
- Original fixed-layout Fable151 raw binary input and 41-bit binary output, 7 information bits + 0 word terminator; candidate experimental profile, NOT normative SLE-AE1 or a claim of arbitrary position handling. Original compiler op=1 LEFT, op=0 ECHO, op=3 REV; 3/4 words only.

## Unique factor and groups
Initialization/source of old H86 knowledge:
A = exact Fable handfilled H86, zero pretraining updates, expanded with 24 units.
B = R70 trained H86 at 8192 old-skill updates from seeds 101/202/303, expanded with identical 24 units as paired A.
C = random H110 baseline, separately initialized per paired seed, no pretraining. C is NOT old-skill eligible; report as reference not matched A/B.
A/B new 24 incoming W1 = same Gaussian per seed, zero new b1 and zero outgoing Wo. C starts random H110. A/B old logits must be exactly preserved at zero update; A/B initial 9-old-family val >=95% each or AB training not reported as qualified. All groups reset Adam m/v/step to zero for the new phase; all weights are trainable (no freeze). Same lr=.003, b1=.9, b2=.999, eps=1e-8, global gradient norm cap 1. Same paired batches and validation per seed. A/B/C same model width 151→110→41 = 21,271 params, 21,120 forward dense MAC per row.

## Fable codec and splits
Fable hand.sets(2603) fixed value split TR96, VA16, TE16, disjoint. Training new LEFT (op1)3/4 with 16 of each, plus 32 old lessons = batch64. Old lessons: REV4 12, REV3 4, REV2 4, COPY4 4, COPY3 2, COPY2 2, DIRTY-COPY1 2, CLEAN-COPY1 1, PUNCT 1. Each LEFT sample has distinct values within phrase. Train left word order n=3: [1,2,0], n=4: [1,2,3,0]. Use Fable locked compiler.qa for gold and hand.build as independent input-frame check; neither runs in inference.
Frozen paired validation panel: RNG 7113, 48 unique unordered-payload groups for each n=3/4 from VA pool; paired ECHO/REV/LEFT per group (288 rows). Frozen final test panel: RNG 7114, same design from TE pool (288 rows); no test inference or tuning until completion. Full 7 information bits per word position must exhibit both 0 and 1 or report failure. Freeze split/records before training; same pool means val/test vocab unseen in TR but Fable A never had a training corpus; B historical exposure proven TR-based by R69/R70 source.
B historical R70 old-knowledge cost: 8192×64=524,288 presentations per seed, separate from new LEFT. A human handfill/design time unknown; no claim time-free comparison.

## Budget, checks, gates
Paired seeds 101/202/303. 4096 new optimizer steps per group/seed = 64×4096 presentations; LEFT = 32×4096 presentations per student. Zero and fixed 128,256,512,1024,2048,4096 validation checkpoints. No early termination or adaptive change. Record cumulative training presentations, LEFT presentations, unique ordered LEFT payloads, updates, first observed gate crossing and previous non-crossing (not exact crossing question count). LEFT 95% on overall validation means >=92/96, with per 3/4 count reported; stronger secondary per-n threshold >=46/48. Old-skill retention: all 9 legacy families >=95% each AND drop <=5 percentage points from own zero-step baseline, report even if failed. Report full raw 41-bit correct, decode/frame failure including submit, 3/3 paired group correctness, ECHO/REV alias/confusion and failures. No invalid prediction exclusion.
First two steps independently inspect new W1/b1/Wo gradients, Adam updates and trainability; first-step zero incoming expected because Wo new=0, second-step incoming gradient must become nonzero. If not, fail diagnostic before drawing handfill conclusions.
Frozen test evaluated ONCE at completion, not used for checkpoint selection. Keep failures, no cherry-picking. Independent checkpoint replay only after training. No external LLM teacher for student labels beyond deterministic frozen Fable codec; NVIDIA no invocation unless authorized accessible endpoint.

## Ownership and delivery
Do not touch Fable's original sources, Pro or Codex branches; public Git isolated, no auto merge. Keep private original bytes/checkpoints in Library exchange with SHA manifest and request Dot only when genuinely READY_FOR_PULL.
