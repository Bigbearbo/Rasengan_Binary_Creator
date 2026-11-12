#pragma once
#include "context_choice_vm.hpp"

// One guest entry checks stable work+45 before selecting context from work+44.
// The two candidate masks and the meaning of that bit are preassigned.
inline std::vector<int> routed_context_choice_program() {
    std::vector<int> code;
    auto e=[&](int op,int param){int i=int(code.size()/2);code.push_back(op);code.push_back(param);return i;};
    e(16,1);e(0,3);e(14,31);e(14,31);e(14,31);e(4,1);
    e(24,2);e(15,0); // unknown operator: do not select a candidate
    e(0,3);e(14,31);e(14,31);e(14,30);e(4,1);
    const int branch=e(24,0);
    const auto copy=context_choice_program(0);
    const auto flip=context_choice_program(2);
    code.insert(code.end(),copy.begin(),copy.end());
    const int flip_start=int(code.size()/2);
    code.insert(code.end(),flip.begin(),flip.end());
    if(flip_start-branch>31)
        throw std::logic_error("routed context choice jump range");
    code[2*branch+1]=flip_start-branch;
    return code;
}
