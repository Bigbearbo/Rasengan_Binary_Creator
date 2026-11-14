# Host-only generation persistence prototype — 2026-11-03

U: user prioritizes scalable, correct tree memory and inheritance; F: prior generation-handle-host-trial ZIP; T: this run; A: remaining design.

New: `tests/test_tree_generation_persistence.cpp`. Text snapshot `HAMU-GEN-1` stores lineage ID, capacity, segment_used, all per-slot 64-bit generations and 32-bit canonical rows. Restore parses all fields before writing rows, then invalidates/rebuilds derived indexes. New child lineage invalidates parent handles. Core VM unchanged.

Reproduction: `g++ -std=c++17 -O0 -g0 -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_tree_generation_persistence.cpp -o gen_persist_test && ASAN_OPTIONS=detect_leaks=0 ./gen_persist_test`.

T: PASS reload preserving stale-handle rejection, same-ID reuse, failed stale delete, corrupted/truncated input preserving state, offspring lineage isolation. First attempt failed because restore omitted `segment_used`, making restored canonical rows invisible; fixed by including segment_used in snapshot header. A first compile also failed because nested test included a second `main`; fixed test harness. Compiler warns from inherited test helper's renamed main, not this test's main.

Limitations: host-only experiment, no guest-accessible handles, no real VM snapshot API integration, no durable file crash-atomicity, no checksum or structural validation, no rollback of mutations after a successful restore, no proof of unique lineage allocation, no cross-version migration, and no HP/storage accounting. Rewinding an old snapshot while retaining references created in a later timeline can recreate an ABA alias; a monotonic incarnation/epoch or a policy invalidating all external handles on restore is required. Reuse at uint64 generation overflow is rejected in erase. Current parser can accept structurally inconsistent but syntactically valid rows; do not load untrusted snapshots.

Next: design restore epoch and atomic commit of canonical rows + generation metadata, then test rollback, cross-lineage handles, large capacity, and guest-facing reference representation.
