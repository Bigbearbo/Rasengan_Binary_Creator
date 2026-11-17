# Raw-bit interface growth: five-bit to seven-bit words

Completed study `pro_growth_channel_20261117_v1`, 2026-11-17. This continues the actual six [PR129](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/129) sender/receiver checkpoints. The scope is the existing Fable W candidate, not canonical151 or normative SLE-AE1.

## Outcome

All three validation-driven pairs grew to **sender H32 / receiver H24**. Their final full message pipeline solved **3,072/3,072** new-range tasks, **864/864** original-format tasks, and **862/864** old-value/new-format tasks. Two receiver101 errors in the new layout misread 7 as 3 for XOR(7,3) and OR(7,3); both are preserved.

Growth does not yet provide uninterrupted retention. Function-preserving additions changed logits by at most 4.44e-15, but subsequent learning temporarily lowered old-task validation to **53.47%** before recovery. The final result supports learning and final compatibility after growth, not immunity to forgetting throughout training.

## Four paired controls

Every model has a fixed 4,096-update budget, batch128 (64 old/64 new), three seeds101/202/303. All four arms share the same batch stream within role/seed. Adam moments reset in all arms at0,512,1024. Growth decisions use validation only; no test-tuned continuation.

| Arm | Final sender/receiver hidden units | Parameters per pair | First checkpoint where both heads pass all three validation panels, seeds101/202/303 | Full new-range pipeline, per seed out of1024 |
|---|---|---:|---|---|
| Reuse H16, expand I/O only |16/16|1732|none/none/none|819/766/722|
| Validation-driven growth |32/24|2988|2048/2048/2048|1024/1024/1024|
| Reuse, H32 from start |32/32|3412|1024/1024/1024|1024/1024/1024|
| Random H32 |32/32|3412|1024/2048/1024|1024/1024/1024|

The growth policy adds8 units at update512 or1024 when any old/new/old-wide validation panel is below95%, capped at32. It is an external heuristic, not a learned architecture policy or proof of minimum capacity. Demand growth uses12.43% fewer final parameters and18.84% fewer forward-training dense MAC than immediate H32 under the fixed budget; it reaches the joint progress marker later. The random H32 control also ultimately succeeds.

## Actual raw interface

Four existing operations ADD12/XOR9/AND7/OR8, two operands. Frame is unary m4 opening, unary n5 or n7 opening, then op and two words, each with tail0. Raw frame28→34bits; packed payload4→5bytes; one-byte-length-prefixed wire40→48bits.

The receiver gets only actual packed bytes in a separate subprocess. The grown numerical input is the left-aligned raw frame padded only at its end; no semantic parsing or field-position adapter feeds the network. The fixed syntax guard returns validity; original frozen W executes only the receiver's predicted command. Arithmetic, packing, guard, requested-width sender flag and growth policy remain supplied structure.

Sender input17 retains the old12 request slots and appends high bits plus width flag; output34 uses first28 for old frames. Receiver input34/output18 retains old coordinates and appends four predicted high bits. Old-frame high-bit mistakes count as errors, never silently truncate. All old and new trainable weights can change after morphing.

Old-to-grown and grown-to-old communication is checked. All grown senders to old receivers pass3456/3456 tasks. An old sender's six inherited legal errors remain visible when a new receiver faithfully decodes them. Old receivers reject384 n7 messages by their fixed version guard, even24 with numerically small operands; this is a format contract behavior, not learned error detection.

Cross-seed interchange uses the first128 new held-out tasks per pair; matched pairs use all1024. All9 pairings in demand/reused-H32/random-H32 pass128/128. Pairs share components and are not independent training replicates. Demand legal operator/operand interventions follow the actual message768/768, including624/624 cases changing the answer. Tail/cut rejection is external syntax checking.

## Data and cost

Pair splits keep all four operations for a pair together. Parent384/72/72 pairs are unchanged. New domain excludes all528 old pairs;192 new axis anchors plus1856 fixed-shuffled pairs form2048 train pairs, followed by256 validation and256 test pairs;5168 unused. Every number occurs individually in training, so this is held-out combination testing, not entirely unseen-number learning. Old test pairs were historically inspected in PR129. Old values encoded n7 are a separate held-out format-transfer panel, not additional training examples.

Actual new work:24 models,98,304 gradient updates,12,582,912 presentations,17,167,810,560 forward-training dense MAC,216 checkpoints. The automated training loop took79.589s including evaluation/saving; channel inference19.300s. These are tiny-setup observations, not general speed benchmarks. Parent training6144updates/786432presentations is inherited, not repeated or free. Forward MAC excludes backward/Adam/nonlinearities/core/IO.

A validation-only posthoc diagnostic zeros added-unit readout contributions in memory, without changing saved models or retraining. New-range accuracy collapses, confirming the added units are used; this does not establish theoretical necessity or minimum size. Its19,200 rows and22,348,800 MAC are separately recorded.

## Reproducibility and audit

Preregistration commit `ae8d6fee5179dc10897574049f27e658ba632b22` precedes main training; source lock commit `182b2aa4ed162aeefbc485600eb7687e582bb509` pins19 files before training. No locked source or experimental model was changed afterward.

Independent data/optimizer reconstruction passes98,304 updates,216 checkpoints,720 prediction files,384,000 rows,78 preservation records and all9 growth events. Final checkpoint parameters/Adam/logits/losses match exactly. An initial verifier attempt used mathematically equivalent softmax with a different floating-point order and stopped at2.08e-9 gradient-norm drift. The single verifier change aligned operation order, with unchanged tolerances; both receipts/revisions are retained. No failed experimental seed was retrained.

Separate channel reconstruction and cross-review pass31,104 records,30 checkpoints,15 streams,99 groups and174,336 wire bytes. All29,939 recorded W calls match an independent integer oracle; the audit invokes W zero times.64 deterministic preflight calls bring actual new W executions to30,003. Channel implementation and channel verifier share an author, with a separately authored numerical helper and method/root cross-review; no false independent-authorship claim.

Public Git contains this screened report, protocol, source hashes and archive replay entry. Original private Fable source, checkpoints, all raw successes/failures and numerical audit history remain in the owner's authorized immutable archive.

## Replay an authorized archive

```bash
python replay_archive.py /path/to/sle_growth_channel_20261117_v1.zip
```

Default mode checks archive SHA256/size/CRC/all member hashes, independently reconstructs data and finite-difference fixtures, and recomputes the entire final channel. It checks the pinned prior full-training PASS receipt, without repeating all optimizer recurrences. To repeat those too:

```bash
python replay_archive.py /path/to/sle_growth_channel_20261117_v1.zip --full-training
```

Python3.10+ and NumPy required. Extraction is temporary; no released model is mutated, no new experimental training occurs, and no arithmetic-core execution or network request is made by either replay mode.

## Next question

Study growth while a frozen old serving version remains available, promoting the candidate only after joint old/new/interface validation. Count extra model storage and switching cost, and distinguish service-level protection from the candidate never forgetting. No next-stage experiment is claimed here.

Function-preserving growth references: [Net2Net](https://arxiv.org/abs/1511.05641), [Network Morphism](https://proceedings.mlr.press/v48/wei16.html). Frozen-column retention reference: [Progressive Neural Networks](https://arxiv.org/abs/1606.04671).

User: growth/internal-SLE concepts. Prior authors: original W and parent evidence. Research assistant: protocol, implementation and actual tests. Dot: archive transport and separate Windows acceptance. Draft research only; no main queue change or automatic merge.

## Released immutable artifact

Filename: `sle_growth_channel_20261117_v1.zip`  
Bytes: 153908649  
SHA256: `a908a726571d5337cefe71dd193256e656bde8f729a181cf57109d2c93e5b579`  
Members: 1254 (1253 individually hashed payload files).

The release entry was executed in default mode after packaging: archive hash/CRC/all-member hashes, independent data/gradient preflight, and all31,104 final-channel records PASS; current optimizer recurrences0. The prior full98,304-update audit is preserved in the pinned archive. Windows transport acceptance is separate from these checks.
