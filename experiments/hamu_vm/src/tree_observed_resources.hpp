#pragma once
#include "tree_observed_learner.hpp"
#include <cstdint>

// Experimental integer resource account, independent of legacy Hamster::hp.
// Rates are model parameters, not measurements of physical execution cost.
struct TreeResourceRates {
    int guest_step=1,fragment_step=1,observation_fee=100,correct_reward=10000;
    int recovery_reserve=5000;
    void validate()const{
        for(int v:{guest_step,fragment_step,observation_fee,correct_reward,recovery_reserve})
            if(v<0||v>1000000)throw std::invalid_argument("resource rate");
        if(!guest_step||!fragment_step)throw std::invalid_argument("positive step rates required");
    }
};
struct TreeResourceAccount {
    static constexpr int64_t capacity=1000000000;
    const int64_t initial;
    int64_t balance,spent=0,rewarded=0,guest_steps=0,fragment_steps=0,observations=0,setup_spent=0,denied=0,exhausted=0;
    int64_t transferred_in=0,transferred_out=0,birth_spent=0,maintenance_spent=0;
    int64_t correct_answers=0,answers_at_last_birth=0,births=0;
    const TreeResourceRates rates;
    explicit TreeResourceAccount(int64_t initial,const TreeResourceRates& r={}):initial(initial),balance(initial),rates(r){
        r.validate();if(initial<0||initial>capacity)throw std::invalid_argument("resource balance");
    }
    TreeResourceAccount(const TreeResourceAccount&)=delete;
    TreeResourceAccount& operator=(const TreeResourceAccount&)=delete;
    void debit(int64_t amount){
        if(amount<0||amount>balance)throw std::logic_error("resource overdraft");
        balance-=amount;spent+=amount;
    }
    void reward(){const auto amount=std::min<int64_t>(rates.correct_reward,capacity-balance);balance+=amount;rewarded+=amount;}
    void reward_answer(){++correct_answers;reward();}
    bool conserved()const{return balance==initial+rewarded+transferred_in-spent-transferred_out;}
};

// Only this runner installs code. Actual attempted execution, including failed
// probes and policy decisions, is billed; lack of funds limits the VM budget.
struct TreeResourceRunner {
    TreeObservedLearner& learner;TreeResourceAccount& account;
    void operator()(Hamster& h,const std::vector<int>& words)const{
        const bool probe=&h!=&learner.hamster;auto& a=account;
        h.stop=false;h.budget_exhausted=false;h.work_insert_blocked=false;h.executed_steps=0;
        if(probe){
            ++a.observations;
            const auto fee=std::min<int64_t>(a.balance,a.rates.observation_fee);a.debit(fee);a.setup_spent+=fee;
            if(fee<a.rates.observation_fee){h.stop=true;h.budget_exhausted=true;++a.denied;return;}
        }
        const int rate=probe?a.rates.fragment_step:a.rates.guest_step;
        const int budget=int(std::min<int64_t>(4000,a.balance/rate));
        if(!budget){h.stop=true;h.budget_exhausted=true;++a.denied;return;}
        const int width=h.params.op_order+h.params.op_lvl;
        if(words.size()>size_t((int(h.memory.size())-h.params.layout.program_start)/width))
            throw std::invalid_argument("resource runner program capacity");
        int at=h.params.layout.program_start;
        for(int word:words)for(bool bit:SpiralToken(word,h.params.op_order,h.params.op_lvl).bits)h.memory.at(at++)=bit;
        std::fill(h.val_reg.begin(),h.val_reg.end(),false);h.val_ptr=0;
        h.step_limit=budget;h.pro_1=h.params.layout.program_start;h.pro_2=at-1;
        simulate_spiral_program(h);a.debit(int64_t(h.executed_steps)*rate);
        if(h.budget_exhausted)++a.exhausted;
        if(probe)a.fragment_steps+=h.executed_steps;else a.guest_steps+=h.executed_steps;
    }
};

inline std::vector<int> tree_observed_resource_export_program(bool gated){
    TreeFourCode c;c.e(16,1);c.at(3,158);c.e(4,1);c.at(2,28);c.e(9,1);
    if(gated){c.at(3,160);c.e(4,1);c.at(2,28);c.e(6,1);}
    c.at(2,29);c.e(2,1);c.e(15,0);return c.w;
}

enum class TreeResourcePolicy { Off, On, AfterFailure, ReserveAfterFailure };
inline void initialize_tree_resource_policy(TreeObservedLearner& learner,TreeResourceAccount& account,TreeResourcePolicy policy){
    TreeResourceRunner{learner,account}(learner.hamster,tree_observed_policy_set_program(policy==TreeResourcePolicy::On));
}

inline std::optional<TreeObservedTurn> run_tree_resource_learning_turn(TreeObservedLearner& learner,
    TreeResourceAccount& account,const std::array<bool,3>& expected,TreeResourcePolicy policy){
    auto& h=learner.hamster;const auto l=h.params.layout;
    if(l.work_start+160>=l.program_start||l.output_start+29>=l.work_start)
        throw std::invalid_argument("resource policy layout");
    TreeResourceRunner run{learner,account};
    // A coarse host sensor, sampled before policy execution; not a reservation
    // or guarantee that the remainder of the turn can be fully funded.
    h.memory[l.work_start+160]=account.balance>=account.rates.recovery_reserve;
    for(int j=28;j<=29;++j){h.memory[l.output_start+j]=false;h.written[l.output_start+j]=false;}
    run(h,tree_observed_resource_export_program(policy==TreeResourcePolicy::ReserveAfterFailure));
    if(!h.stop||h.budget_exhausted||!h.written[l.output_start+28]||
       !h.written[l.output_start+29]||!h.memory[l.output_start+29]){
        publish_tree_fragment_answer(h,{});return std::nullopt;
    }
    const auto result=run_tree_observed_learning_turn(learner,expected,run,h.memory[l.output_start+28]);
    if(!result)publish_tree_fragment_answer(h,{});
    if(result){
        // Reward is for a valid actual answer, even if later learning bookkeeping
        // exhausted its budget. Never reward a hypothetical prediction alone.
        if(result->learning.valid&&result->learning.correct)account.reward_answer();
        h.memory[l.work_start+159]=result->initially_invalid;
        if(policy==TreeResourcePolicy::AfterFailure||policy==TreeResourcePolicy::ReserveAfterFailure)
            run(h,tree_observed_policy_react_program());
    }
    return result;
}

inline bool run_tree_resource_route(TreeObservedLearner& learner,TreeResourceAccount& account,
    const std::array<bool,3>& expected){
    const auto id=run_tree_observed_route(learner,TreeResourceRunner{learner,account});
    if(!id)return false;const int out=learner.hamster.params.layout.output_start;
    for(int b=0;b<3;++b)if(!learner.hamster.written[out+b]||learner.hamster.memory[out+b]!=expected[b])return false;
    account.reward_answer();return true;
}
