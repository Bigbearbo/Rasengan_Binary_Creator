#pragma once
#include <vector>
// Input+1..+3 is the attempted three-bit answer, input+4 is the teacher's
// correct bit. Output+1 is whether ZERO remains consistent with that grade.
// The host supplies the attempted answer and one-bit grade; no target answer.
inline std::vector<int> zero_consistency_program() {
    return {16,1,0,0,14,17,4,1,24,13,
            14,17,4,1,24,10,14,17,4,1,24,7,
            14,17,4,1,0,2,14,17,9,1,15,0,
            0,0,14,20,4,1,0,2,14,17,2,1,14,1,5,1,15,0};
}
