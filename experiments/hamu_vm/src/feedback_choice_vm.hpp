#pragma once
#include "hypothesis_mask_vm.hpp"
#include "mask_choice_vm.hpp"
#include <stdexcept>
// Input+5 says whether to apply input+1..+4 keep bits before choosing.
// Both phases run in one VM program window and one program entry.
inline std::vector<int> feedback_choice_program() {
    std::vector<int> code={16,1,0,0,14,21,4,1,24,2,26,0};
    auto update=hypothesis_mask_program();
    update.resize(update.size()-2); // omit its STOP, fall through to choice
    code.insert(code.end(),update.begin(),update.end());
    const int choice=int(code.size()/2);
    if(choice-5>31)throw std::logic_error("choice jump range");
    code[11]=choice-5; // unconditional pair 5
    auto choose=mask_choice_program();
    code.insert(code.end(),choose.begin(),choose.end());
    return code;
}
