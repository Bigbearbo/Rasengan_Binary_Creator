# 2026-11-03 mixed ABI regression (new independent run)

U: Keep scalable tree memorization, avoid old/new ABI corruption.
F: Based on Library `hamu_vm_tree_confirm_three_bits_20261103.zip` (latest observed at run start).
T: Added `tests/test_tree_confirm_mixed_abi.cpp`, compiled `g++ -std=c++17 -O0 -g -fsanitize=address,undefined -fno-omit-frame-pointer tests/test_tree_confirm_mixed_abi.cpp -o /tmp/test_tree_confirm_mixed_abi`; ran `ASAN_OPTIONS=detect_leaks=0 /tmp/test_tree_confirm_mixed_abi`. PASS 32 combinations (initial new answer 0..7 x legacy overwrite 0..3), verified legacy overwrite clears high bit, rejected mask unchanged, new overwrite 7 readable by legacy low bits and new full bits. First test failed because the test encoded 2-bit legacy input with the 3-bit helper; corrected fixture, not VM implementation. Warning from included old test main missing explicit return remains (existing fixture warning).
A: Segmented tree currently has no guest-accessible deletion opcode in inspected TREE_ADD/FIND/ACTION switch; do not claim deletion/reuse validated by this run. Next implement or locate deletion protocol, then test node reuse clears confirmation, high bit and rejection mask and invalidates index, with rollback and offspring isolation.
No VM production source changes. This is targeted regression, not full suite or world simulation.
