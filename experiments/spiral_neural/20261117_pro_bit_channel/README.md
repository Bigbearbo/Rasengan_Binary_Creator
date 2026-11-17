# Independent neural heads over a real discrete frame

This isolated study tests whether separately supervised small neural senders and receivers can cooperate using a packed discrete frame as the receiver's only case-varying input. Unlike previous externally supplied ID routing, the sender actually predicts every frame bit and the receiver learns the operation and operand fields from the received bytes.

## Preregistration and scope

Initial protocol commit: `5cf7ba17e33ba39570f3bce858262387c6e84c80`, before any new learner forward. Wire-prefix cost was clarified before training in `9517010cc73ee101f0a794705848402883879f35`. Exact learner, corpus, channel and frozen-core hashes were publicly locked in `a3de6c6c896c9813c85cec85751d0f75e11e0754`, before the single main run.

The frame is an existing Fable W **experimental candidate**, fixed m4/n5 with two operands and four existing operations: ADD, XOR, AND, OR. It is not normative SLE-AE1 or the canonical151 task profile. The first input is a synthetic 12-bit operation/operand request. This is supervised learning of a specified interface, not spontaneous language invention or natural-language understanding.

The 28-bit frame carries unary width declarations, a 4-bit operation code and two 5-bit operand words with tail zeros. It is hardened, packed into 32 payload bits and transmitted with an 8-bit record-length prefix: **40 actual wire bits per nonempty message**. A fixed syntax guard returns only a boolean. Valid raw bits enter the learned receiver; its predicted operation/operands alone are passed to the unchanged Fable W arithmetic core. Python supplies framing and dispatch; arithmetic is not learned here.

## Design

The 528 ordered pairs a,b in0..31 with a+b<32 each have all four operations, totaling2,112 tasks. Split by whole pair:384train/72validation/72test, or1,536/288/288tasks. All63 axis pairs are in training, so all32values are seen in each role. Test pairs are excluded under every operation; this is held-out combination transfer, not unseen-value or variable-width extrapolation.

Three speakers (12→16→28,684parameters) and three receivers (28→16→14,702parameters) use seeds101/202/303, distinct initializations and minibatch streams, no shared parameters or joint gradients. Receivers train only on canonical teacher frames. All six models run exactly1,024Adam updates,batch128,lr0.01,float64. Validation at0/32/128/512/1024;95% whole-frame/tuple is a progress marker, never a test-driven stopping or extension rule.

## Executed results

Each cell below is exact `(operation,a,b)` correctness on288untaught-pair test tasks. Rows are speaker seeds; columns are receiver seeds. These nine pairings reuse six components and are not nine independent training repetitions.

| Speaker / receiver |101|202|303|
|---|---:|---:|---:|
|101|282/288|282/288|282/288|
|202|288/288|288/288|288/288|
|303|288/288|288/288|288/288|

All receiver swaps work without fine-tuning. Teacher-frame→receiver is288/288for eachreceiver. All864actualspeakerframes are syntactically valid. Speaker101 has six legal but wrong messages; the receivers faithfully decode them. The answer score is284/288because two wrong commands happen to yield the correct answer. Example: AND(11,20) is transmitted asAND(11,4), both0; XOR(20,11) is transmitted asOR(20,11), both31. A correct tail, correct decoding and correct arithmetic do not ensure the intended meaning was transmitted.

| Intervention,2,592records each | Exact received-message tuple | Correct new answer on answer-changing subset |
|---|---:|---:|
|Replace operation with next legal code|2,592/2,592|2,058/2,058|
|Flip lowest bit of operand a|2,592/2,592|1,935/1,935|
|Rotate frames to next operand pair|2,592/2,592|2,358/2,358|
|Corrupt a tail zero|all2,592 rejected|not applicable|
|Cut payload|all2,592 rejected|not applicable|

The legal interventions show received content controls behavior. Shuffling reduces original-task answer accuracy to234/2,592=9.03%, while the model correctly follows the substituted message. Guard rejection is supplied by code, not a learned invalid-frame skill. There is no security-sandbox or adversarial-robustness claim.

## Cost and verification

One automated main run:6,144updates,786,432examplepresentations,30checkpoints. Training including saving took2.6815s; channel evaluation/saving6.2327s in this small local setup. These are not hardware benchmark or broader model-training speed claims. Training-forward dense MAC is515,899,392, excluding backward, optimizer, nonlinearities, evaluation and I/O.

One deployed pair has1,386trainablevalues,11,088float64weightbytes plus22,176Adam-bufferbytes if continuing training. Original W retains330stored table values,90nonzero,2,640bytes, plus code and provided prior knowledge. The actual16,416channelrecords occupy71,712wirebytes. P0+P1+channel executed14,208W calls, with all wrong semantic selections preserved.

Independent finite differences:all1,386coordinates pass,maxerror4.62e-10. A separate verifier imports none of the original model/codec/runner/W and reconstructs the full dataset,6,144Adamrecurrences,786,432batchindices,30checkpoints,30validation+6testpredictionfiles,2,112P0records,864P1records,16,416channelrecords,57metricgroups and3rawwire/stdoutpairs. PASS; maximum checkpoint parameter difference9.77e-15. From final saved weights and wire bytes, actual speaker/receiver logits reproduce exactly. Numerical recurrence replay is an audit, not another experimental training condition. Recorded W outputs are checked against an independent integer oracle without executing W again.

## Authorized artifact and replay

Full private Fable source, raw rows, initial/final checkpoints, Adam states, batches, losses, all messages/failures, verifier and detailed report remain in the authorized archive. Public Git does not contain those private originals.

| Artifact | Value |
|---|---|
| Filename |`sle_bit_channel_20261117_v2.zip`|
| Bytes |8,116,778|
| SHA256 |`909fe1730f16a2a5c30f5beedce7fb6087a0d56ad74ca5ef5f3d2a656f3953cd`|
| ZIP CRC |PASS|
| Members |124 files,123hashedpayloadfiles|
| Packaging revision |2; report wording clarification only, no model/data/result changes|

Obtain the exact authorized artifact from its owner, then run:

```sh
python replay_archive.py /absolute/path/sle_bit_channel_20261117_v2.zip
```

The hash-pinned entry validates archive size/SHA/CRC, every member hash and portable path, extracts into a fresh temporary directory, then runs the independent audit. It performs no new experimental training, original W execution or network call. Python3.10+ and NumPy are required; tested withPython3.12.14/NumPy2.3.5. The packaged public entry itself was executed successfully.

## Interpretation and next question

The result supports interchangeable **supervised discrete interfaces at one fixed profile**. It does not establish SLE superiority over equally structured binary fields or finite-precision vectors, variable word width/count, autonomous topology growth or learned arithmetic. Internal hidden states remain continuous vectors even though the inter-region channel is discrete.

The next proposed single-axis study is data-word width5→7 with fixed arithmetic and explicit old-interface retention, before a broad encoding comparison. This proposal is not part of the executed result.

U:user's internal-SLE and handfilled good-student growth direction. F:existing Fable W candidate/core and prior plan. A:this fixed interface/split/intervention design. T:executed results above. Dot:transport only. Related primary literature: [Discrete-Valued Neural Communication,NeurIPS2021](https://proceedings.neurips.cc/paper/2021/hash/10907813b97e249163587e6246612e21-Abstract.html) uses learned shared codebooks, not this fixed semantic code; no result is transferred from that paper by analogy.

NVIDIA status:skipped_unavailable,0actualcalls; no callable worker or configured credential in this environment. No Windows Codex or Gemini calls. Draft research only; no main queue changes or automatic merge. Windows transfer requires Dot's separate receipt.
