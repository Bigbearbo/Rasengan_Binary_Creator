#pragma once
#include <stdexcept>
#include <vector>

// One fixed candidate slot: read the preceding VM check at output+5 and
// intersect it with the persistent hypothesis bit at work+40+slot.
inline std::vector<int> direct_mask_update_program(int slot) {
    if(slot<0||slot>3)throw std::invalid_argument("mask slot");
    return {0,2,14,21,4,1,
            0,3,14,31,14,31,14,26+slot,6,1,15,0};
}
