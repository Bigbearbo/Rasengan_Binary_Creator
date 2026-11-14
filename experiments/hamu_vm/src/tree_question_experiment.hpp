#pragma once
#include "tree_question_bank.hpp"
#include "tree_observed_resources.hpp"
#include <memory>

inline std::vector<int> tree_question_toggle_program(int output_bit){
    if(output_bit<0||output_bit>2)throw std::invalid_argument("toggle output bit");
    auto toggle=tree_width_trial_program(false);
    toggle.resize(toggle.size()-2); // replace STOP with an input-derived XOR
    TreeFourCode suffix;suffix.at(0,1);suffix.e(4,1);
    suffix.at(2,output_bit);suffix.e(5,1);suffix.e(15,0);
    toggle.insert(toggle.end(),suffix.w.begin(),suffix.w.end());return toggle;
}
inline std::array<std::vector<int>,4> tree_question_fragments(){
    return {tree_four_trial_program(2),tree_question_toggle_program(2),
        tree_four_trial_program(0),tree_four_trial_program(1)};
}
inline HamsterParams tree_question_params(){
    HamsterParams p;p.layout.status_start=45;p.layout.output_start=50;p.layout.work_start=80;
    p.layout.program_start=700;p.layout.total_size=24000;p.stable_work_bits=100;
    p.tree_start=600;p.tree_capacity=8;p.layout.val_reg_size=12;return p;
}
struct TreeQuestionSummary {
    int attempted=0,valid=0,correct=0,confirmed=0,routed=0;
    int64_t spent=0,balance=0;
};
inline TreeQuestionSummary run_tree_question_curriculum(){
    TreeObservedLearner learner(1,tree_question_params(),tree_question_fragments());
    TreeResourceRates rates;rates.correct_reward=0;rates.observation_fee=20;
    TreeResourceAccount account(1000000,rates);
    initialize_tree_resource_policy(learner,account,TreeResourcePolicy::Off);
    TreeQuestionSummary result;
    std::unique_ptr<TreeObservedLearner> narrow_child;
    for(const auto& q:tree_question_curriculum){
        write_tree_question(learner.hamster,q);
        auto t=run_tree_resource_learning_turn(learner,account,tree_question_answer(q),TreeResourcePolicy::Off);
        ++result.attempted;
        if(t){result.valid+=t->learning.valid;result.correct+=t->learning.correct;result.confirmed+=t->learning.confirmed;}
        if(result.attempted==8)narrow_child=std::make_unique<TreeObservedLearner>(learner,3);
        if(!account.conserved())throw std::logic_error("curriculum account conservation");
    }
    TreeObservedLearner child(learner,2);
    TreeResourceAccount child_account(1000000,rates);
    // Promotion is one-way, so the saved narrow descendant tests old routes.
    TreeResourceAccount narrow_account(1000000,rates);
    for(int data=0;data<8;++data)for(int op=1;op<=3;++op){
        TreeQuestion q{2,op,data,op==1?TreeQuestionKind::ToggleLast:
            op==2?TreeQuestionKind::Copy:TreeQuestionKind::Flip};
        write_tree_question(narrow_child->hamster,q);
        if(run_tree_resource_route(*narrow_child,narrow_account,tree_question_answer(q)))++result.routed;
    }
    for(int data=0;data<8;++data){
        TreeQuestion q{3,1,data,TreeQuestionKind::Zero};
        write_tree_question(child.hamster,q);
        if(run_tree_resource_route(child,child_account,tree_question_answer(q)))++result.routed;
    }
    result.spent=account.spent;result.balance=account.balance;
    return result;
}
