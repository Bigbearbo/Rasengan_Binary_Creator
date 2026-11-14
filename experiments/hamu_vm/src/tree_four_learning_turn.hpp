#pragma once
#include "tree_width_learning_turn.hpp"
#include "tree_four_vm.hpp"

// Four-candidate records use their own mask, action and format fields. Existing
// two-candidate records are retained; callers choose one protocol per learner.
template<class Runner>
std::optional<TreeLearningTurn> run_tree_four_learning_turn(
    Hamster& h,const std::array<bool,3>& expected,
    const std::array<std::vector<int>,4>& candidates,Runner run){
    const int work=h.params.layout.work_start,out=h.params.layout.output_start;
    if(work+123>=h.params.layout.program_start||out+29>=work)
        throw std::invalid_argument("four candidate layout");
    h.memory[work+104]=false;h.written[work+104]=false;
    run(tree_width_prepare_program());
    if(!h.stop||h.budget_exhausted||!h.written[work+104]||!h.memory[work+104])return std::nullopt;
    for(int slot:{57,70}){run(tree_four_bind_program(slot));run(tree_four_reclaim_program(slot));}
    for(int slot:{57,70})run(tree_width_pending_program(slot,true));
    for(int slot:{57,70}){
        for(int pos=out+25;pos<=out+27;++pos){h.memory[pos]=false;h.written[pos]=false;}
        run(tree_four_choice_program(slot));
        if(!h.stop||h.budget_exhausted||!h.memory[out+25]||!h.written[out+25]||!h.written[out+26]||!h.written[out+27])continue;
        const int id=2*int(h.memory[out+26])+int(h.memory[out+27]);
        const bool correct=run_tree_graded_trial(h,expected,[&]{run(candidates[id]);});
        const bool valid=h.memory[work+93];
        if(valid){
            run(tree_width_snapshot_program());run(tree_four_feedback_program(slot));
            run(tree_four_confirm_program(slot));run(tree_four_bind_program(slot));
        }
        const bool confirmed=h.memory[work+slot];
        run(tree_four_reclaim_program(slot));
        return TreeLearningTurn{slot,id,valid,correct,confirmed};
    }
    return std::nullopt;
}
