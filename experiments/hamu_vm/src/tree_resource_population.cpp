#include "tree_resource_birth.hpp"
#include "tree_question_experiment.hpp"
#include <iostream>
#include <vector>

struct TreePopulationTotals {
    int64_t initial=0,balance=0,spent=0,rewarded=0,in=0,out=0,answers=0;
    void add(const TreeResourceAccount& a){
        if(!a.conserved())throw std::logic_error("individual resource conservation");
        initial+=a.initial;balance+=a.balance;spent+=a.spent;rewarded+=a.rewarded;
        in+=a.transferred_in;out+=a.transferred_out;answers+=a.correct_answers;
    }
};
struct TreePopulationRow {
    int round=0,living=0,births=0,retired=0,confirmed=0,route_answers=0;
    std::array<int,4> policies{};TreePopulationTotals totals;
};
struct TreePopulationResult {std::vector<TreePopulationRow> rows;};
struct TreeQuestionTrace {
    int seed=0,round=0,id=0,width=0,op=0,data=0,before_slots=0,after_slots=0;
    int candidate=-1;bool route=false,attempt=false,valid=false,correct=false,confirmed=false;
    int64_t balance_before=0,balance_after=0;
};
static void population_check(bool ok,const char* message){if(!ok)throw std::logic_error(message);}

enum class TreeQuestionSchedule { LegacySingle, CleanSingle, CleanVaried, CleanPermuted, CleanDelay, CleanReview };
TreePopulationResult run_tree_resource_population(int reward,bool breeding,bool reverse,
    TreeQuestionSchedule schedule=TreeQuestionSchedule::LegacySingle,int permutation_seed=0,
    std::vector<TreeQuestionTrace>* trace=nullptr){
    if(schedule==TreeQuestionSchedule::CleanPermuted&&(permutation_seed<1||permutation_seed>4))
        throw std::invalid_argument("population permutation seed");
    HamsterParams p;p.layout.status_start=45;p.layout.output_start=50;p.layout.work_start=80;
    p.layout.program_start=700;p.layout.total_size=24000;p.stable_work_bits=100;
    p.tree_start=600;p.tree_capacity=8;p.layout.val_reg_size=12;
    const bool clean=schedule!=TreeQuestionSchedule::LegacySingle;
    const std::array<std::vector<int>,4> table=clean?tree_question_fragments():
        std::array<std::vector<int>,4>{std::vector<int>{16,1,12,20,12,4},
        tree_four_trial_program(2),tree_four_trial_program(0),tree_four_trial_program(1)};
    TreeResourceRates rates;rates.correct_reward=reward;rates.observation_fee=200;rates.recovery_reserve=30000;
    TreeResourceBirthRules rules;constexpr int capacity=8;
    const bool extended=schedule==TreeQuestionSchedule::CleanDelay||schedule==TreeQuestionSchedule::CleanReview;
    const int rounds=extended?16:12;int next_id=4,births=0,retired=0;
    int confirmed=0,route_answers=0;
    std::vector<std::unique_ptr<TreeResourceIndividual>> population;
    for(int i=0;i<4;++i){const int mode=reverse?3-i:i;
        auto individual=std::make_unique<TreeResourceIndividual>(i,p,table,50000,rates,static_cast<TreeResourcePolicy>(mode));
        initialize_tree_resource_policy(individual->learner,individual->account,individual->policy);
        population.push_back(std::move(individual));
    }
    TreePopulationTotals removed;TreePopulationResult result;
    for(int round=1;round<=rounds;++round){
        for(auto& who:population){
            charge_tree_resource_maintenance(who->account,1000);
            if(!who->account.balance)continue;
            if(schedule==TreeQuestionSchedule::CleanDelay&&round>=9&&round<=12)continue;
            const TreeQuestion q=extended?(round<=8?tree_question_permuted(round,3):
                round<=12?TreeQuestion{2,round%2?3:1,0,
                    round%2?TreeQuestionKind::Flip:TreeQuestionKind::ToggleLast}:
                    tree_question_variant(round-4)):
                schedule==TreeQuestionSchedule::CleanVaried?
                tree_question_variant(round):schedule==TreeQuestionSchedule::CleanPermuted?
                tree_question_permuted(round,permutation_seed):TreeQuestion{2,1,5,TreeQuestionKind::Zero};
            write_tree_question(who->learner.hamster,q);
            auto& h=who->learner.hamster;
            TreeQuestionTrace event;event.seed=permutation_seed;event.round=round;event.id=h.id;
            event.width=q.operator_width;event.op=q.operator_id;event.data=q.data;
            event.balance_before=who->account.balance;
            event.before_slots=int(h.memory[p.layout.work_start+47])+int(h.memory[p.layout.work_start+60]);
            // In the clean controls a confirmed tree is an answer pathway. A
            // learning turn on an already bound leaf can return no attempt;
            // routing it first avoids counting learned individuals as idle.
            if(clean&&run_tree_resource_route(who->learner,who->account,tree_question_answer(q))){
                ++route_answers;event.route=true;
                event.after_slots=int(h.memory[p.layout.work_start+47])+int(h.memory[p.layout.work_start+60]);
                event.balance_after=who->account.balance;if(trace)trace->push_back(event);continue;
            }
            const auto turn=run_tree_resource_learning_turn(who->learner,who->account,tree_question_answer(q),who->policy);
            if(!clean&&turn)population_check(!turn->learning.confirmed,"unknown loop cannot be semantically confirmed");
            if(turn&&turn->learning.confirmed)++confirmed;
            if(turn){event.attempt=true;event.candidate=turn->learning.candidate;
                event.valid=turn->learning.valid;event.correct=turn->learning.correct;
                event.confirmed=turn->learning.confirmed;}
            event.after_slots=int(h.memory[p.layout.work_start+47])+int(h.memory[p.layout.work_start+60]);
            event.balance_after=who->account.balance;if(trace)trace->push_back(event);
        }
        for(size_t i=0;i<population.size();){
            if(population[i]->account.balance==0){removed.add(population[i]->account);population.erase(population.begin()+i);++retired;}
            else ++i;
        }
        const size_t parents=population.size();
        if(breeding)for(size_t k=0;k<parents;++k){
            // Rotate eligible-parent priority; newborns first work next round.
            auto& parent=*population[(round+k)%parents];const auto before=parent.account.balance;
            auto child=try_tree_resource_birth(parent,next_id,rules,population.size(),capacity);
            if(child){population_check(child->account.correct_answers==0,"newborn eligibility reset");
                population_check(before-parent.account.balance==rules.grant+rules.fee,"birth accounting");
                population.push_back(std::move(child));++next_id;++births;}
        }
        TreePopulationRow row;row.round=round;row.births=births;row.retired=retired;
        row.living=int(population.size());row.confirmed=confirmed;row.route_answers=route_answers;row.totals=removed;
        for(const auto& who:population){row.totals.add(who->account);++row.policies[int(who->policy)];}
        population_check(row.living<=capacity&&row.living==4+births-retired,"population accounting");
        population_check(row.totals.initial==200000&&row.totals.in==row.totals.out,"closed transfers");
        population_check(row.totals.balance==row.totals.initial+row.totals.rewarded-row.totals.spent,"world resource conservation");
        population_check(row.confirmed<=row.totals.answers&&row.route_answers<=row.totals.answers,
            "question outcome accounting");
        result.rows.push_back(row);
    }
    return result;
}

// Preserve the previous four-argument entry for callers of the first varied
// experiment. New controlled comparisons use the explicit schedule enum.
TreePopulationResult run_tree_resource_population(int reward,bool breeding,bool reverse,bool varied){
    return run_tree_resource_population(reward,breeding,reverse,
        varied?TreeQuestionSchedule::CleanVaried:TreeQuestionSchedule::LegacySingle);
}

#ifndef TREE_RESOURCE_POPULATION_NO_MAIN
int main(){
    std::cout<<"reward,breeding,reverse,round,living,births,retired,off,on,after_failure,reserve,balance,spent,rewarded,correct_answers\n";
    for(int reward:{0,12000})for(bool breeding:{false,true})for(bool reverse:{false,true}){
        const auto result=run_tree_resource_population(reward,breeding,reverse);
        for(const auto& r:result.rows){const auto& t=r.totals;
            std::cout<<reward<<','<<breeding<<','<<reverse<<','<<r.round<<','<<r.living<<','<<r.births<<','<<r.retired;
            for(int count:r.policies)std::cout<<','<<count;
            std::cout<<','<<t.balance<<','<<t.spent<<','<<t.rewarded<<','<<t.answers<<'\n';}
    }
    std::cout<<"PASS 8 closed population scenarios, 96 censuses, resource and population conservation\n";
}
#endif
