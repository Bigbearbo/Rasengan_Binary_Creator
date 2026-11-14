#include "tree_resource_fixture.hpp"
#include <iostream>
#include <type_traits>
static_assert(!std::is_copy_constructible<TreeResourceAccount>::value,"accounts cannot clone balances");
static_assert(!std::is_copy_constructible<TreeResourceIndividual>::value,"birth requires explicit transfer");
int main(){
    const auto p=resource_fixture_params();const auto zero=tree_four_trial_program(2);
    const std::array<std::vector<int>,4> code={zero,tree_four_trial_program(0),tree_four_trial_program(1),tree_four_trial_program(3)};
    TreeResourceRates rates;rates.correct_reward=1000;
    TreeResourceIndividual parent(1,p,code,100000,rates,TreeResourcePolicy::On);
    TreeResourceBirthRules rules;initialize_tree_resource_policy(parent.learner,parent.account,parent.policy);
    const auto initial_balance=parent.account.balance;
    require_resource(!try_tree_resource_birth(parent,2,rules,1,4)&&parent.account.balance==initial_balance,"wealth alone cannot reproduce");
    resource_fixture_question(parent.learner.hamster,5);
    auto learned=run_tree_resource_learning_turn(parent.learner,parent.account,{false,false,false},parent.policy);
    require_resource(learned&&learned->learning.confirmed&&parent.account.correct_answers==1,"first earned answer");
    resource_fixture_question(parent.learner.hamster,6);
    require_resource(!run_tree_resource_route(parent.learner,parent.account,{true,true,true})&&parent.account.correct_answers==1,"wrong answer earns no birth credit");
    require_resource(!try_tree_resource_birth(parent,2,rules,1,4),"not enough new answers");
    resource_fixture_question(parent.learner.hamster,6);
    require_resource(run_tree_resource_route(parent.learner,parent.account,{false,false,false}),"second earned answer");
    const auto before=parent.account.balance;const auto memory=parent.learner.hamster.memory;
    require_resource(!try_tree_resource_birth(parent,2,rules,4,4)&&parent.account.balance==before,"full population costs nothing");
    auto child=try_tree_resource_birth(parent,2,rules,1,4);
    require_resource(bool(child),"birth");
    require_resource(parent.account.balance==before-rules.fee-rules.grant&&child->account.balance==rules.grant,"transfer plus fee");
    require_resource(parent.account.conserved()&&child->account.conserved(),"per account conservation");
    require_resource(parent.account.balance+child->account.balance==before-rules.fee,"no new resources");
    require_resource(parent.learner.hamster.memory==memory,"parent memory preserved");
    require_resource(child->parent_id==1&&child->generation==1&&child->account.initial==0&&child->account.correct_answers==0,"lineage and fresh eligibility");
    require_resource(child->learner.fragments==parent.learner.fragments&&child->learner.hamster.memory[238],"fragment and policy inheritance");
    require_resource(!try_tree_resource_birth(parent,3,rules,2,4),"answers cannot be reused");
    require_resource(!try_tree_resource_birth(*child,3,rules,2,4),"child cannot inherit eligibility");
    for(int data=0;data<8;++data){resource_fixture_question(child->learner.hamster,data);
        require_resource(run_tree_resource_route(child->learner,child->account,{false,false,false}),"inherited bound tree answers");}
    auto too_large=rules;too_large.grant=TreeResourceAccount::capacity;
    const auto balance=child->account.balance;
    require_resource(!try_tree_resource_birth(*child,3,too_large,2,4)&&child->account.balance==balance,"insufficient funds no debit");
    auto invalid=rules;invalid.required_answers=0;bool rejected=false;
    try{try_tree_resource_birth(*child,3,invalid,2,4);}catch(const std::invalid_argument&){rejected=true;}
    require_resource(rejected,"reject free eligibility");
    auto smaller=rules;smaller.grant=5000;
    auto grandchild=try_tree_resource_birth(*child,3,smaller,2,4);
    require_resource(grandchild&&grandchild->generation==2&&grandchild->parent_id==2&&grandchild->account.correct_answers==0,"second generation transfer");
    resource_fixture_question(grandchild->learner.hamster,7);
    require_resource(run_tree_resource_route(grandchild->learner,grandchild->account,{false,false,false}),"second generation learned route");
    require_resource(parent.account.conserved()&&child->account.conserved()&&grandchild->account.conserved(),"three account identities");
    require_resource(parent.account.balance+child->account.balance+grandchild->account.balance==100000+
        parent.account.rewarded+child->account.rewarded+grandchild->account.rewarded-
        parent.account.spent-child->account.spent-grandchild->account.spent,"multi generation conservation");
    const auto earned=child->account.correct_answers;charge_tree_resource_maintenance(child->account,TreeResourceAccount::capacity);
    require_resource(child->account.balance==0&&child->account.conserved()&&child->account.correct_answers==earned,"maintenance depletion");
    std::cout<<"PASS birth: real answer eligibility, parent transfer, fee, capacity, no reused or inherited credit, 9 child/grandchild routes, multi-generation conservation, depletion\n";
}
