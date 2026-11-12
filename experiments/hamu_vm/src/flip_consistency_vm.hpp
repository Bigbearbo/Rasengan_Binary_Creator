#pragma once
#include "copy_consistency_vm.hpp"
// FLIP is consistent when answer XOR data is 111 iff teacher grades correct.
inline std::vector<int> flip_consistency_program() {
    return bitwise_consistency_program(true);
}
