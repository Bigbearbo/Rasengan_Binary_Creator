#pragma once
#include <stdexcept>
#include <vector>

// Intersect one pending-word hypothesis bit with the guest consistency bit
// at output+5. Candidate and VM entry are currently selected by the host.
inline std::vector<int> pending_mask_update_program(int candidate) {
    if(candidate!=0&&candidate!=1)throw std::invalid_argument("pending candidate");
    return {0,2,14,21,4,1,
            0,3,14,31,14,31,14,31,14,26+candidate,6,1,15,0};
}
