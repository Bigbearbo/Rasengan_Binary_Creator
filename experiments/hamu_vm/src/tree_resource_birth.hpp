#pragma once
#include "tree_observed_resources.hpp"
#include <memory>

struct TreeResourceIndividual {
    TreeObservedLearner learner;
    TreeResourceAccount account;
    TreeResourcePolicy policy;
    int parent_id=-1,generation=0;
    TreeResourceIndividual(int id,const HamsterParams& p,const std::array<std::vector<int>,4>& code,
        int64_t initial,const TreeResourceRates& rates,TreeResourcePolicy mode)
        :learner(id,p,code),account(initial,rates),policy(mode){}
    explicit TreeResourceIndividual(const TreeResourceIndividual& parent,int id)
        :learner(parent.learner,id),account(0,parent.account.rates),policy(parent.policy),
         parent_id(parent.learner.hamster.id),generation(parent.generation+1){}
};
struct TreeResourceBirthRules {
    int64_t grant=20000,fee=1000,parent_reserve=5000,required_answers=2;
    void validate()const{
        if(grant<1||grant>TreeResourceAccount::capacity||fee<0||fee>TreeResourceAccount::capacity||
           parent_reserve<0||parent_reserve>TreeResourceAccount::capacity||required_answers<1||required_answers>1000000)
            throw std::invalid_argument("birth rules");
    }
};

// Allocate/copy before modifying the parent, so allocation failure cannot debit
// it. No population endowment is created here: child starts at zero and receives
// exactly the grant transferred from its parent. Only the fee is consumed.
inline std::unique_ptr<TreeResourceIndividual> try_tree_resource_birth(TreeResourceIndividual& parent,
    int child_id,const TreeResourceBirthRules& rules,size_t population_size,size_t population_capacity){
    rules.validate();if(population_capacity<1)throw std::invalid_argument("population capacity");
    auto& a=parent.account;
    if(child_id==parent.learner.hamster.id)throw std::invalid_argument("distinct child id required");
    if(population_size>=population_capacity||a.correct_answers-a.answers_at_last_birth<rules.required_answers||
       a.balance<rules.grant+rules.fee+rules.parent_reserve)return nullptr;
    auto child=std::make_unique<TreeResourceIndividual>(parent,child_id);
    a.debit(rules.fee);a.birth_spent+=rules.fee;
    a.balance-=rules.grant;a.transferred_out+=rules.grant;
    child->account.balance=rules.grant;child->account.transferred_in=rules.grant;
    a.answers_at_last_birth=a.correct_answers;++a.births;
    return child;
}

inline void charge_tree_resource_maintenance(TreeResourceAccount& account,int64_t amount){
    if(amount<0||amount>TreeResourceAccount::capacity)throw std::invalid_argument("maintenance charge");
    const auto paid=std::min<int64_t>(account.balance,amount);account.debit(paid);account.maintenance_spent+=paid;
}
