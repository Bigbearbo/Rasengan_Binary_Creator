# PR131: retaining a mature small network while adding capacity

This experiment separates two sources of old-skill interference: changing inherited parameters and adding a new contribution to shared outputs. PR130's early decline happened before its first hidden-unit expansion. Here we test a frozen inherited base, with either unrestricted or explicitly format-scoped new outputs, at two added widths.

## Interpretation update: rebound and reuse (2026-11-18)

The motivating user hypothesis allows transient early interference. The question is whether a modest added fraction makes mature learning easier to recover while the new part connects new learning, and whether excessive disturbance can restore old answers through a reorganized computation. Our prior response misread that as uninterrupted preservation. Frozen/gated conditions answer a different engineering question and do not refute the clarified hypothesis.

This update reads already archived results only: zero new training, neural forward passes or W calls. A post hoc recovery description is the first saved checkpoint after the observed trough where at least95% of originally correct old-validation cases are retained and every subsequent saved checkpoint stays at least95%. For joint+8 this is S101/202/303=512/512/1024 and R101/202/303=1024/512/1024; joint+16 gives512 for all six. Thus these two widths do not establish faster recovery for the smaller addition. They add50% and100% of the16-unit parent, not an exhaustive small-to-large sweep. This descriptive marker does not replace preregistered acceptance.

Archived component diagnostics also distinguish regained answers from unchanged division of work. For joint+8 Sender101 on test_old, the final complete head scores288/288; its current inherited16-unit component with current output weights/bias scores39/288 by itself, versus282/288 for the original parent. The new branch is now needed for those old answers. Ablating a coadapted branch does not prove erased knowledge: inherited features may remain while readout and compensation change.

Sources: archived analysis_results.json, model_results[].old_retention_by_checkpoint and component_diagnostics_final.test_old. No immutable source, checkpoint, raw prediction, preregistration or ZIP was modified.

Next priority is recovery plus structural reuse in existing joint checkpoints, using multiple diagnostics rather than raw parameter distance or one ablation. Hidden-unit permutation/sign symmetries and coadapted readouts must be considered. A later controlled added-size comparison should keep old learning plastic and track actual output/gradient disturbance as well as unit count. The present residual units read raw inputs and meet the old units at the output; directly reading mature hidden features is a separate proposed architecture, not something this experiment already demonstrated. The mixed-width teaching proposal below remains a distribution-control question, rather than the primary answer to this clarification.

## Executed finding

The smaller unrestricted branch disturbed old skills less in all six paired role/seed comparisons, but learned the new format poorly. Freezing the old base alone did not protect the complete network output. Freezing it **and** restricting the new branch to the longer format preserved all originally correct old cases; adding 16 units then gave 99.61%, 99.61%, 99.90% complete semantic accuracy through the actual binary channel on the new range.

This successful new branch is as large as its 16-unit parent. It is not evidence that arbitrarily tiny growth suffices. Nor did every validation replicate pass: the format-gated +16 condition passes the preregistered joint validation marker in **2/3 seeds**, even though its final reused test panels pass in 3/3. Sender303 scores 267/288 on old values encoded in the new format. No extra training or reseeding was used.

## Fixed comparison

Three mechanisms × two appended sizes (8/16) × two roles × three seeds (101/202/303) = 36 models, each with 4,096 updates. All inherit the unchanged PR129 parent checkpoints and reuse PR130's datasets and entire minibatch streams. New incoming weights share the same 16-column random block prefix; outgoing weights start at zero.

| Mechanism | Inherited parameters | New branch output |
|---|---|---|
| `joint` | Trainable | All inputs |
| `frozen_open` | Fixed | All inputs |
| `frozen_gate` | Fixed | Width7 only |

The head computes `base(x) + gate(x) * residual(x)`. In frozen conditions the complete first16-unit block and all output biases are fixed, including zero/-2 I/O extensions. No residual output bias is added. Sender gate uses existing requested-width coordinate16; receiver gate uses raw-header coordinate10. This is a handfilled syntactic scope rule, not a learned router. A trainable-base plus gate condition is omitted, so the full interaction is not identified.

Both roles still operate on the existing candidate raw bit profile: m4/n5→n7, two operands, ADD12/XOR9/AND7/OR8. The receiver gets only fixed weights and actual packed binary stdin. Arithmetic remains the original Fable W core. This is not canonical151/SLE-AE1 acceptance, learned arithmetic, autonomous growth policy, or encoding-superiority evidence.

## Actual binary channel

Entries are seed101 /202 /303, with all source and receiver mistakes retained. Tuple correctness requires the operator and both full operands; coincidentally correct arithmetic answers are separate.

| Condition | Old n5 /288 | New range n7 /1024 | Old values n7 /288 |
|---|---|---|---|
| joint +8 | 288/288/288 | 1022/1024/1023 | 288/288/287 |
| joint +16 | 288/288/288 | 1023/1024/1024 | 288/288/288 |
| frozen open +8 | 282/286/286 | 3/9/0 | 9/14/1 |
| frozen open +16 | 287/288/288 | 994/986/1008 | 257/249/275 |
| frozen gate +8 | 282/288/288 | 30/62/52 | 23/25/24 |
| frozen gate +16 | 282/288/288 | 1020/1020/1023 | 278/282/278 |

For frozen-open, the lowest observed old validation accuracies span 77.43–93.06% with +8 and 36.11–85.76% with +16. Smaller additions were locally less disruptive, not harmless. The fixed-gated old score retains all parent errors as well as its correct cases: sender101 still has six old test errors.

All three held-out panels were historically examined in PR130. They remain disjoint from training pairs but are reused benchmarks, not fresh blind tests. No test-driven continuation or model repair occurred. Full validation histories and the 2/3 versus3/3 distinction are archived.

## Diagnostic boundary and next question

Sender303's 21 oldwide validation errors are legal frames with 22 erroneous 0→1 value bits; 19 are in added high positions. Width7 training contains every operand value individually, but excludes the entire old pair region `a+b<32`. This is a post hoc distribution association, not proof of the cause.

The next proposed control is to replace a fixed fraction of width7 teaching examples with training-only old pairs written in width7, at unchanged total budget and active example count. Keep validation/test pairs excluded and report the cost of fewer new-range examples. It has **not** been run. A later per-word routing comparison could test more direct reuse of mature computations.

A separate post hoc ablation adds already saved old-validation base and branch logits without the gate. It uses no new model forward/update. Failure after this substitution demonstrates dependence on the gate for these weights; it does not predict what a separately trained ungated model would learn.

## Costs and verification

Actual experiment: 147,456 updates, 18,874,368 presentations, 27,216,838,656 forward-training dense MAC, 360 checkpoints; 132.681731 seconds including evaluation/serialization. Frozen parameters and zero frozen Adam moments were checked after 98,304 updates. +8 pairs store 2,572 parameters; +16 pairs store 3,412, including their frozen bases. Frozen trainable counts are840 and1,680. MAC excludes backward/Adam/nonlinear/gate/IO/core costs; no end-to-end speedup is claimed.

Actual channel: 28,800 records, 18 fresh receiver processes, 54 groups,167,616 bytes; 28,013 original W calls and787 fixed-guard rejections. All13,560 final model×case failures are indexed, along with complete successes and raw outputs.

Independent full audit executed once and passed all147,456 Adam recurrences,360 checkpoints,1,188 prediction files/633,600 rows,98,304 freeze checks and2 clipping events. Parameters, Adam, logits and losses match exactly. This computation is verification, not extra experimental training. Channel audit recomputed all records and integer-oracle answers with zero additional W calls; maximum sender/receiver logit error0. The channel author wrote a separate verifier using independently authored mathematical helpers, and another reviewer cross-reviewed it; authorship is not overstated.

Preflight reconstructed12,928 data rows and36 initializations on all2,112 old cases; finite differences checked410 parameters with maximum error7.88e-11. Two zero-update preflight receipts are preserved. Complete methods, figure, source, split, parents, checkpoints, traces, failures and provenance are in the authorized archive.

NVIDIA status: `skipped_unavailable`, actual calls0 (no callable endpoint/configured key in this environment). Windows Codex/Gemini calls0. Local independent review was used; no external teacher is claimed.

## Source and artifact

Parent: [PR129](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/129), head`00d089115461dd29f06044a6082363d48c058650`.

Prior growth: [PR130](https://github.com/Bigbearbo/Rasengan_Binary_Creator/pull/130), head`c35ff7d13ae427fc2ed6c5959665d121edd6bf50`.

Preregistration:`d751939ffbf7173b7488e8d33f0029b722449c79`; source lock:`50b8820140fe08fee574d0b12632de9819af1340`, both before training.

Archive:`sle_retention_growth_20261118_v1.zip`  
Size:407,083,289 bytes;1,828 members,1,827 hashed payload files.  
SHA256:`588c9d28b8e3e1ec61cec9a09ef31cb8b437f070678cf0d1ef5b55b7426acb14`.

Obtain the exact archive from its owner. [replay_archive.py](replay_archive.py) pins archive size/SHA and every member, checks CRC, extracts into a fresh temporary directory, reconstructs data and recomputes the final channel. The default performs zero new optimizer recurrences; `--full-training` additionally repeats the full independent recurrence audit. Released weights are never overwritten. Exact experiment environment: Python3.12.14/NumPy2.3.5 with one BLAS thread.

```bash
python replay_archive.py /path/to/sle_retention_growth_20261118_v1.zip
# Optional full recurrence audit, not necessary for ordinary transport:
python replay_archive.py /path/to/sle_retention_growth_20261118_v1.zip --full-training
```

User concepts, source evidence, assistant designs and executed results are separated in the archive provenance. Dot transports and checks byte integrity; transport is not experimental authorship or acceptance of scientific conclusions. Draft only; no main queue mutation, merge or deployment.

Primary context: [Net2Net](https://arxiv.org/abs/1511.05641), [Progressive Neural Networks](https://arxiv.org/html/1606.04671v4), [Learning without Forgetting](https://arxiv.org/abs/1606.09282). These establish related methods, not substitute evidence for this bounded experiment.

Default packaged replay was actually executed from the immutable ZIP and passed: all payload hashes/CRC, dataset reconstruction and28,800 final-channel records;0 current optimizer recurrences and0 new W calls. The optional full-training wrapper was not run again; the independently executed147,456-update full audit is pinned inside the archive.
