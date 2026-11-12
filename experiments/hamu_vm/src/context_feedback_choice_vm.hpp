#pragma once
#include "context_choice_vm.hpp"
#include "direct_mask_update_vm.hpp"

// One guest window: apply the preceding consistency bit, then choose again.
// Context and tested hypothesis remain human-assigned entry parameters.
inline std::vector<int> context_feedback_choice_program(int base,int candidate) {
    if((base!=0&&base!=2)||(candidate!=0&&candidate!=1))
        throw std::invalid_argument("feedback context or candidate");
    auto code=direct_mask_update_program(base+candidate);
    code.resize(code.size()-2); // fall through instead of STOP
    auto choice=context_choice_program(base);
    code.insert(code.end(),choice.begin(),choice.end());
    return code;
}
