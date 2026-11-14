#pragma once
#include <vector>
// Input +1..+4: four teacher-provided keep bits. Work +40..+43:
// live hypothesis mask. Guest VM intersects the two masks bit by bit.
inline std::vector<int> hypothesis_mask_program() {
    return {0,0,14,17,4,4,0,3,14,31,14,31,14,26,6,4,15,0};
}
