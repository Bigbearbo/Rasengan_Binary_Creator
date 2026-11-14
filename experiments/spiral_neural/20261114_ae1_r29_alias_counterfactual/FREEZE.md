# R29 — frozen before neural inference (2026-11-14)
Work ID: `SLE-AE1-R29-PREFIX-BIT-ALIAS-20261114`.
Scope: independent small neural learner; SLE-AE1-n5-v1; 39 native 01 input bits; 6-bit word(a) plus external STOP output. Not UR1/VM/parser. Parent R28 draft PR #78 at head `cd6d0fbb09b6948ac4be59e059f36854affa1788`.

Single intervention: within each pair, **only** change data word `a=20→28` or `a=21→29`: input bit index 10 (0-based), with r=1, b,c,d fixed. Compare **frozen** R27 and R28 checkpoints with three seeds 101/202/303; no further training. Both models use the same 10,457-parameter dual-routed network with 10,920 theoretical dense forward MAC per model call. Historical training was 136 lessons, 1,408 target positions per epoch, 150 epochs, 3,300 Adam updates/student; **new updates=0**.

Static 64 native 01 questions: 32 matched pairs (8 validation pairs at c1d4; 24 test pairs at c1d5/c3d4/c3d5); each has b∈{18,19,22,23}. R27/R28 training questions and their prior evaluation Q are excluded. **The a-values themselves are researcher-seen**, not novel value blind tests.

Precommitted primary gate, seed202 test split only (24 pairs; ALL required): R28 low/high output six-bit firstwords identical in ≥18 pairs; R28 high bit1 correct in ≤6 pairs; R28 low six-bit firstword correct in ≥18 pairs; R27 high bit1 correct in ≥18 pairs. FAIL if any component fails. This is a *replication/diagnostic* of the R28 alias, not proof of general neural rule learning. Secondary: firstword/exact answers, bit1-flip rate, output logit margin (1 minus 0) at true one-bit prefix, r1 STOP at prefix6, other-bit changes. Validation is descriptive only; no threshold tuning.

Freeze SHA256 of full local **original executable** `r29_runner.py`: `89445ca09c2a3b9020b15d3cd879c1af8325ba151d5903140c5fa31ebcb05dad`. Manifest SHA256: `d1d31d0a5efa97aed738413d72fe16a70928b18a330916a8cf798294623d7312`. Original `prereg.json` SHA256: `8028a72772792b4e48d47336ab4e15b709c13090796773f3f7c2379be2a02076`. `r28_runner.py` SHA256 `606b7e3446c02fc00169e379988b99cd181e048a57877ef763f999aed38ed8a2`. R28 whole ZIP SHA256 `bdb5d47ec9dcdef851247136c85acbf7923f4d9c9631b9b5357ccbe699d562dc`. The R28 original ZIP and full six weights are **not stored in Git**; separately supplied conversation archive is required to execute the full experiment. No reliance on unfrozen Pro/Codex branches.

Source checkpoint SHA256s (JSON weights):
```text
         R27                                                             R28
seed101  e8f2410ea8443ec4bcbb77e3375928d38a483d8fe91f2341730f8f78d184a83f 8558e0c71f6e0a964f1eb5974903f63cb863c8ea0c57e0fd89867193b3122b0c
seed202  8a7f0dc273658b5af9a6249c47227d92841e8104ff7cba40fec3b9e042545e7f 7f2d011cdf5bed155523823ea575ed0be640db8b0fdd2e6b062a65938443e44c
seed303  ddb5d382a5653229f7ece305c76fb20a91b71417868dacd57d76099577ea2845 b395b800b2497c963c5ed1dcd58f8090b333fcb5b6780c1ec56311b7ccb1e5b6
```
U: user priority is native01 curriculum/generalization, real student evidence, not VM. F: R27/R28 immutable failed experiments + checkpoints; P030-P035 and UR1 distinct research. T at this commit: only static manifest/shape/hash gate passed; **zero model forwards, zero new updates**. A: seed202 R28 may have turned the high bit into a value alias; persistence and soft-margin mechanism **unknown** until inference.
NVIDIA: not called, no approved live model/API entry point. Local Codex/Gemini not invoked. No secrets or private conversations published.
