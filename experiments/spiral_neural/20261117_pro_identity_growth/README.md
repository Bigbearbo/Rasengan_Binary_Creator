# Needs-based local growth and reversible consolidation

This bounded study asks when corrected identities should receive separate capacity and when repeated corrections can form a shared rule. The protocol was published before main training in commit `ab59ec71b21f82211b54709ac7f5e790a6895db3`.

## Design and measured result

A handfilled base already knows4 meanings,6 aliases per meaning and2 contexts:48 context/word pairs. Four worlds share a fixed9-event teaching stream: no changes, a genuine group change,2 isolated changes, or3 isolated changes. Two aliases remain permanently held out. Six allocation policies are compared across10 namespace seeds. The seeds permute identities and operations; they are not independent random neural initializations.

The base stays frozen. Each added unit has a hard identity/group gate and4 trainable residual output values. External code decides allocation, promotion and rollback. This is a semantic-component study with supplied meaning groups, not autonomous topology invention or canonical151bit language learning.

| Policy | Genuine shared change: final added cells | Held aliases correct | Two isolated exceptions: minimum unchanged-case retention | Three isolated exceptions: minimum retention |
|---|---:|---:|---:|---:|
| Preallocated exact |48|0%|100%|100%|
| Allocate every new observed identity |7|0%|100%|100%|
| Allocate only on observed mismatch |4|0%|100%|100%|
| Consolidate after2 distinct agreeing identities |1|100%|91.30%|93.33%|
| Consolidate after3 distinct agreeing identities |1|100%|100%|93.33%|

Rollback restores final correctness in both isolated-exception worlds. Frozen base weights alone did not prevent temporary behavioral damage through changed routing. Wrong held-alias predictions can carry a98.73% softmax score; that score does not establish a rule's applicability to unseen identities. Exact-only repair scores95.83% overall in the shared world while held-alias transfer remains0%.

The consolidation policy retains7 unique evidence records. Active-cell reductions are not identical to total-memory savings. Costs include base, fixed gates, trainable values, routing keys, Adam state and policy evidence; exact-over-shared masking is explicit external control.

## Actual execution and verification

One automated main run completed240 trajectories,2400 snapshots and2160 feedback events with54000 Adam updates in4.257409seconds including evaluation/serialization; observe calls took1.430067seconds. These times exclude design, coding, review and delivery. No seed selection or manual intervention during the run.

An independent verifier imports neither model nor runner. It reconstructs dense gates, full scalar Adam arithmetic, allocation/consolidation/rollback policy,900 identical-visible-prefix states and all metrics/cost summaries. All240 trajectories and54000 updates replayed; maximum numeric discrepancy8.88e-16. Finite-difference, Adam and exact-priority fixtures also pass.

A separate27-case diagnostic reconstructs the trained snapshots and makes54 actual calls to the unchanged candidate W core. It correctly executes27/27 selected plans. Eight semantic selections are wrong for their world's target and remain recorded as errors. Old arithmetic-cache results are inherited evidence, not new execution.

Known groups, supplied IDs, noiseless fixed labels and trivial4-logit corrections sharply limit generality. A symbolic implementation could realize the same allocation policies. This does not demonstrate SLE encoding superiority, learned growth policy, unrestricted depth selection, natural-language learning or hardware speedup.

## Authorized archive replay

Original private core source and full snapshots are not published in this repository. Obtain the authorized artifact from the owner and run:

```sh
python replay_archive.py /path/to/sle_identity_growth_20261117_v1.zip
```

| Artifact | Value |
|---|---|
| Filename | `sle_identity_growth_20261117_v1.zip` |
| Bytes |1519183|
| SHA256 |`6f72122c769e83e5e3643a75fd97149fe610151e7ffe690f5b00a505395758f4`|
| ZIP members |283|
| Member hashes |282; the manifest is pinned by the outer ZIP hash|
| Protocol SHA256 |`5ca10a1c508f2437807325ccb6918396b58a20596d4d87d5fa7b3600ea343e6b`|

The entry checks hash, CRC, paths and every member, then runs the independent verifier in a temporary directory. It does not retrain, call an external model, execute new W cases or access the network. This exact packaged replay passed in the authoring environment.

The archive includes the complete Traditional Chinese report, fixed data, models, all states, negative results, source and optimizer hashes, controller logs, numerical checks and integration traces. An optional preflight wrapper had read the numeric-check receipt's wrong key; the actual checks had passed. The main runner recorded its own source hashes before any observation; no source/data/policy changes or training restart occurred. The later implementation receipt states its actual timing.

No main queue changes or automatic merge. Dot's Windows retrieval and hash ACK remain separate from author-side validation.

## Primary design precedents

[Dynamically Expandable Networks](https://arxiv.org/abs/1708.01547), [Progressive Neural Networks](https://arxiv.org/abs/1606.04671), and [Progress & Compress](https://proceedings.mlr.press/v80/schwarz18a.html) inform growth, frozen-path reuse and consolidation. This study is not a reproduction of those papers.
