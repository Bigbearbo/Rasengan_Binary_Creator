#pragma once
#include "tree_guest_selection.hpp"
#include "tree_trial_grade.hpp"
#include "tree_grade_snapshot_vm.hpp"
#include "tree_feedback_cycle_vm.hpp"
#include "tree_context_confirm_bridge.hpp"
#include <array>

struct TreeLearningTurn {
    int slot;
    int candidate;
    bool valid;
    bool correct;
    bool confirmed;
};

// The host supplies the teacher answer and two preinstalled programs. Every
// choice, snapshot, mask update, confirmation and tree binding runs in the VM.
template<class Runner>
std::optional<TreeLearningTurn> run_tree_learning_turn(
    Hamster& h,const std::array<bool,3>& expected,
    const std::array<std::vector<int>,2>& candidates,Runner run){
    auto selected=run_tree_guest_selection(h,run);
    if(!selected)return std::nullopt;
    const int slot=selected->slot,choice=selected->candidate;
    const bool correct=run_tree_graded_trial(h,expected,[&]{run(candidates[choice]);});
    const bool valid=h.memory[h.params.layout.work_start+93];
    run(tree_grade_snapshot_program());
    if(valid){
        run(tree_feedback_cycle_program(slot));
        run(tree_feedback_confirm_program(slot));
        run(tree_context_confirm_program(slot));
    }
    return TreeLearningTurn{slot,choice,valid,correct,
                            bool(h.memory[h.params.layout.work_start+slot])};
}
