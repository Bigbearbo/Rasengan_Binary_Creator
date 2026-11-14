#pragma once
#include "tree_feedback_mask_vm.hpp"
#include "tree_context_grade_confirm_vm.hpp"

// Publish a separate completion bit only after both candidate intersections.
// A positive observation matching neither hypothesis must not confirm the
// temporary singleton that can exist between the two updates.
inline std::vector<int> tree_feedback_cycle_program(int slot){
    std::vector<int> w={0,3,14,31,14,31,14,31,14,31,14,31,14,31,14,20,3,1};
    auto guard=tree_grade_guard_program(slot);
    w.insert(w.end(),guard.begin(),guard.end());
    for(bool flip:{false,true}){
        auto code=tree_feedback_mask_body(slot,flip);
        code.resize(code.size()-2);
        w.insert(w.end(),code.begin(),code.end());
    }
    const std::vector<int> commit={0,3,14,31,14,31,14,31,14,31,14,31,14,31,14,20,2,1,15,0};
    w.insert(w.end(),commit.begin(),commit.end());
    return w;
}
inline std::vector<int> tree_feedback_confirm_program(int slot){
    // Require work+94, then use the unchanged context/grade/uniqueness guards.
    std::vector<int> w={16,1,0,3,14,31,14,31,14,31,14,31,14,31,14,31,14,20,4,1,18,20,15,0};
    auto confirm=tree_context_grade_confirm_program(slot);
    w.insert(w.end(),confirm.begin(),confirm.end());
    return w;
}
