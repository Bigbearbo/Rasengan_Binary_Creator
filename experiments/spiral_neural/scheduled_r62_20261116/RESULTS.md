# R62 actual training results — auxiliary raw-01 frame recognition

**Status: 7/7 preregistered quantitative gates PASS; narrow structural task only.** This is a new genuinely trained, 3-seed, two-arm tiny NN experiment, not P030–P035, UR1, VM, or a changed SLE dictionary. Pretraining Git prereg commit: `7efc2916d5163b9d8a3f4a7e4405c367a1b1fd5e` on this isolated branch. No merge.

## Experimental configuration and trace
Source profile `SLE-AE1-n5-v1`: legal 39 raw bits `01+010+bin3(r)+0+4*(bin5(v)+0)+111100`, with `r∈{1,2}`, `a,b,c,d∈[0,29]`. The legal source Q strings agreed byte-for-byte with **272/272** already archived R61 reference Q. Separate auxiliary binary validity target: `01→valid`, `00/11→invalid` in training, `10→invalid` held out; malformed headers are **illegal test controls**, never passed off as legal SLE questions.

Unique canonical base Q: 120 train with all values 0..19, 32 validation with all values 20..24, 64 test with all values 25..29. Exact raw manifest 744 JSONL rows; train effective pool is 480 records after duplicating 120 legal rows to balance valid/invalid. Same *initial* 1,313-parameter `39→32 tanh→1` network, same Adam/minibatches and labels for two arms: only raw framing bit availability differs. Masked control zeros bits 0 and 1 before input, while the unmasked arm ingests all 39 raw 0/1 values. Seeds 101/202/303, 400 Adam updates/arm/seed, batch64, lr=.01, no early stopping. Real **2,400 updates / 153,600 target presentations**, theoretical forward **196,608,000 dense MAC**, backward not estimated. This is NOT a math-answer output head.

## Observed independent heldout results

| metric, all 3 seeds | raw bits visible | framing-blind control |
| --- | ---: | ---: |
| test valid `01` accepted | **192/192** | 82/192 |
| test illegal `00`, `11` rejected | **384/384** | 220/384 |
| test entirely untrained `10` rejected | **192/192** | 110/192 |
| valid higher logit than invalid, paired test each seed/corruption | **64/64 (all 9 contrasts)** | 0 meaningful discrimination |
| maximum logit difference across four header variants on same body | varies correctly | **0.0** |

Raw side also scored validation valid 96/96, seen invalid 192/192, unseen `10` 96/96. The blind arm got 412/768 test judgments; caution that 3/4 of test cases are invalid, so unbalanced aggregate accuracy is misleading. Its decisive property is **exactly identical logits across all four header choices with same 37-bit body**; it cannot infer the label from that body alone.

Example seed101/test-000: legal `010100010111000110100110010111000111100` was accepted with probability ~0.999647; the same body prefixed `00` or `11` was rejected (~0.000616, ~0.000491), and the withheld `10` was rejected (~0.00000076). These are separate validity probabilities, not mathematical 01 answer strings.

All six checkpoint files are original newly trained NPZ weights. Stored raw predictions: **2,304** entries (validation+test × 3 seeds × 2 arms). Independent NumPy-only code computes `tanh(X @ W1.T + b1) @ W2.T + b2`; max absolute logit discrepancy to stored PyTorch outputs **1.9073486328125e-6**. Original trainer's own PyTorch and NumPy replay also 2,304/2,304. ZIP has 15 files, 14 content hashes independently checked, testzip succeeded; ZIP SHA256 `8d9e0c637112922b766607ab07add1c40498d158af5df970814de9c2c09e6d81`. Full runner, prereg JSON, 744 source rows, six models, raw predictions, failures/gates, independent standalone verifier and SHA list are in that separate conversation attachment (ZIP **is not hosted in this Git PR**).

## Preregistered gates
Seven conjunctive gates all PASS: valid accepts ≥180/192; seen invalid rejects ≥330/384; unseen double-flip rejects ≥160/192; per seed/invalid kind valid-logit rank ≥55/64; blind pair logit gap ≤1e-6; role-wise heldout-value split and exact AE1 profile checked; NumPy replay all 2,304 heldout logits (<5e-5). Rejected examples among raw heldout: **0**; blind arm's systematic indistinguishability is the informative negative result.

## Important pretraining receipt erratum (preserved, not overwritten)
The Git prereg text mistakenly printed **earlier runner SHA** `684bf38b4ed5ef6a10bdb0f0085e91126ce1d13bf30311e59a41e4e8b18b2ac2`. Before any NN training or forward, a bookkeeping bug in the replay-count label `1536` versus the correct `2304` was fixed in the local runner, producing SHA `65f705fcea7872650cf40eb14b724a225cf2c2ef25bfde13dac9b5f619a52207`. The updated hash was stored in local prereg JSON and explicitly checked immediately before the first training call. **The correct runner byte hash was NOT publicly Git-frozen before training**, so exact-runner prereg audit strength is weaker than the numerical design freeze; retain this limitation. Split, sample count, target, NN architecture, training logic, parameter/MAC budget and numerical gates were not changed post-test. The full correct runner/manifest bytes, local receipt and raw outputs are archived.

## Limitations and next owner
A separate supervised syntax-validity classifier succeeds on a **two-bit fixed opening**, which is a narrow easy task. It does not demonstrate math-answer generalization, STOP, arbitrary unknown grammar, extension to variable width, or that the old R50–R61 math network gained framing awareness. The value split is new *within R62*, not global research-blind. The only conclusion from this positive diagnostic is: the header can be learned and distinguished if the network actually receives those bits and is explicitly taught positive and negative examples; an architecture that masks them cannot.

**U**: author direction to advance native-01 neural teaching/transfer independently; **F**: original R60/R61, repository guidance, P030–P035/UR1 refs; **A**: matched framed/hidden diagnostic idea; **T**: this run's six actual trained small NN, complete 2,304 predictions, independent replay and null control. NVIDIA reviewer 0 calls (no authorized accessible endpoint); Codex 0; Gemini 0. No sensitive user content, keys, or external oracles.

Next owner: independent NN researcher. Next causal experiment should include a frame-aware *mathematical-output* model and old-math retention with prereg frozen legal/illegal curriculum, rather than declaring this auxiliary head a solved SLE mathematics system.
