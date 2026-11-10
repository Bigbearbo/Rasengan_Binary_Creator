# Hamster World / Spiral Language VM (research snapshot)

## Subsequent research changes

The original import described below is preserved as provenance. Later work is
tracked in [DECISIONS.md](DECISIONS.md), [GUEST_TRIAL_CONTRACT.md](GUEST_TRIAL_CONTRACT.md),
and dated reports under `results/`.

The second iteration adds typed VM stop diagnostics and uses them in the
host-only trial reference to reject invalid jumps/windows. It does not make
transactions mandatory for callers of the raw interpreter. Legacy skip and
deferred-window semantics remain explicit compatibility choices (D-007).

Run the related regression set with `bash scripts/verify_guest_trial_contract.sh`.

## Original import

This directory is a text-file checkout of the ChatGPT Library archive
`/倉鼠世界/程式版本/hamu_vm_tree_guest_full_state_transaction_20261110.zip`,
archived 2026-11-10 (Asia/Taipei). The archive contains 395 UTF-8 files;
this checkout adds this README.

Original archive SHA-256: `9a78c642655d88c556541b7b8f3b3b8e1491e1a3cfc66144fdf463841f08bb16`

## Layout

`src/` — C++ core and research implementations.
`tests/` — regression tests and controlled experiments.
`fixtures/` — deterministic question fixtures.
`prototypes/` — experimental implementations.
`results/` — historical experimental reports and logs (not all re-run in this sync).
`Makefile` — historical build/test targets.

## Verified for this import

The archive passed ZIP integrity verification. The targeted host-only full-state
transaction regression compiled and passed in the import environment:

```sh
cd experiments/hamu_vm
g++ -std=c++17 -O0 -g0 -fsanitize=address,undefined -fno-omit-frame-pointer \
  tests/test_tree_guest_full_state_transaction.cpp -o /tmp/hamu_full_state
ASAN_OPTIONS=detect_leaks=0 /tmp/hamu_full_state
```

Expected: `PASS: full-state host checkpoint rolls back work, generation, HP, exception and revision overflow`.
A known inherited `prior_generation_main()` missing-return compiler warning remains.

**Scope:** This latest experiment uses a host-only `FullStateEnvelope`. It is
not a production VM-wide mandatory transaction boundary, disk crash-atomicity,
or autonomous Zero-world learning. See `results/tree_guest_full_state_transaction_20261110.md`.

These files are an imported research snapshot, not a claim that all historical
logs have been independently reproduced.
