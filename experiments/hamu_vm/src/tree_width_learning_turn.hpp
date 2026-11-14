#pragma once
#include "tree_learning_turn.hpp"
#include "tree_width_scaffold_vm.hpp"
#include "tree_width_pending_vm.hpp"
#include "tree_width_choice_vm.hpp"
#include "tree_width_grade_vm.hpp"
#include "tree_width_feedback_vm.hpp"
#include "tree_width_confirm_bridge.hpp"
#include "tree_width_reclaim_vm.hpp"

// Success marker follows the final TREE_ADD_REG success flag. Invalid frames
// stop within the scaffold; a full tree must not start a learning attempt.
inline std::vector<int> tree_width_prepare_program(){
    auto w=tree_width_scaffold_program();w.resize(w.size()-2);
    const std::vector<int> tail={8,11,8,21,18,20,15,0,0,3,
        14,31,14,31,14,31,14,31,14,31,14,31,14,30,2,1,15,0};
    w.insert(w.end(),tail.begin(),tail.end()); // work+104
    return w;
}

template<class Runner>
std::optional<TreeLearningTurn> run_tree_width_learning_turn(
    Hamster& h,const std::array<bool,3>& expected,
    const std::array<std::vector<int>,2>& candidates,Runner run,
    bool reuse_confirmed_slots=false){
    const int work=h.params.layout.work_start,out=h.params.layout.output_start;
    if(work+104>=h.params.layout.program_start||out+29>=work)
        throw std::invalid_argument("width learning layout");
    h.memory[work+104]=false;h.written[work+104]=false;
    run(tree_width_prepare_program());
    if(!h.stop||h.budget_exhausted||!h.written[work+104]||!h.memory[work+104])
        return std::nullopt;
    // Retry a confirmed but interrupted binding before looking for new work.
    for(int slot:{57,70})run(tree_width_confirm_bridge_program(slot));
    if(reuse_confirmed_slots)
        for(int slot:{57,70})run(tree_width_reclaim_program(slot));
    // Fixed host scheduling; capture and candidate applicability are guest decisions.
    for(int slot:{57,70})run(tree_width_pending_program(slot));
    for(int slot:{57,70}){
        for(int pos=out+25;pos<=out+26;++pos){h.memory[pos]=false;h.written[pos]=false;}
        run(tree_width_choice_program(slot));
        if(!h.stop||h.budget_exhausted||!h.written[out+25]||!h.written[out+26]||!h.memory[out+25])continue;
        const int choice=int(h.memory[out+26]);
        const bool correct=run_tree_graded_trial(h,expected,[&]{run(candidates[choice]);});
        const bool valid=h.memory[work+93];
        if(valid){
            run(tree_width_snapshot_program());
            run(tree_width_feedback_cycle_program(slot));
            run(tree_width_feedback_confirm_program(slot));
            run(tree_width_confirm_bridge_program(slot));
        }
        const bool confirmed=h.memory[work+slot];
        if(reuse_confirmed_slots)run(tree_width_reclaim_program(slot));
        return TreeLearningTurn{slot,choice,valid,correct,confirmed};
    }
    return std::nullopt;
}
