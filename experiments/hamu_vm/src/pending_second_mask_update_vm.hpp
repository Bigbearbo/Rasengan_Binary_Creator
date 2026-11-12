#pragma once
#include <stdexcept>
#include <vector>

// Intersect the second word's selected hypothesis with the guest's
// consistency result at output+5. The host still selects the trial branch.
inline std::vector<int> pending_second_mask_update_program(int candidate) {
    if(candidate!=0&&candidate!=1)throw std::invalid_argument("second candidate");
    return {0,2,14,21,4,1,
            0,3,14,31,14,31,14,31,14,31,14,24+candidate,
            6,1,15,0}; // work+68,+69
}
