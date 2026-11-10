#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
out="${1:-$root/build/guest-contract}"
mkdir -p "$out"
out="$(cd "$out" && pwd)"
cd "$root"
"${CXX:-g++}" --version | head -n 1
for name in tree_guest_revision_bypass tree_guest_transaction_envelope tree_guest_full_state_transaction guest_trial_contract tree_reject_mask work_insert_capacity vm vm_stop_reason vm_unary_skip vm_decode_snapshot; do
    "${CXX:-g++}" -std=c++17 -O0 -g0 -fsanitize=address,undefined -fno-omit-frame-pointer \
        "tests/test_${name}.cpp" -o "$out/test_${name}" >"$out/${name}.build.log" 2>&1
    ASAN_OPTIONS=detect_leaks=0 "$out/test_${name}" >"$out/${name}.run.log" 2>&1
    cat "$out/${name}.run.log"
done
