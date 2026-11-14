#include "tree_error_trial.hpp"
#include <iostream>
#include <memory>
#include <set>

struct ErrorWorldAgent {
    Hamster h;int resource=1000,attempts=0;
    std::array<std::set<int>,2> choices;
    explicit ErrorWorldAgent(int id,const HamsterParams& p):h(id,p){h.memory[1]=true;}
};
struct ErrorWorldRow {int round,question,mastered,correct,resource;};
struct ErrorWorldResult {std::vector<ErrorWorldRow> rows;int promotion_round=0,laggards=0;};
inline ErrorWorldResult run_error_world(int tree_capacity=31){
    HamsterParams p;p.layout.status_start=45;p.layout.output_start=50;p.layout.work_start=80;
    p.layout.program_start=700;p.layout.total_size=24000;p.stable_work_bits=400;
    p.tree_start=300;p.tree_capacity=tree_capacity;p.layout.val_reg_size=12;
    std::vector<std::unique_ptr<ErrorWorldAgent>> agents;
    for(int i=0;i<4;++i)agents.emplace_back(std::make_unique<ErrorWorldAgent>(i,p));
    auto run=[&](Hamster& h,const std::vector<int>& words){
        int at=p.layout.program_start;
        for(int word:words)for(bool bit:SpiralToken(word,5,1).bits)h.memory.at(at++)=bit;
        std::fill(h.val_reg.begin(),h.val_reg.end(),false);h.val_ptr=0;
        h.stop=false;h.budget_exhausted=false;h.executed_steps=0;h.step_limit=4000;
        h.pro_1=p.layout.program_start;h.pro_2=at-1;simulate_spiral_program(h);
        if(!h.stop||h.budget_exhausted)throw std::runtime_error("error world VM execution");
    };
    ErrorWorldResult result;int question=1;
    for(int round=1;round<=16;++round){
        int correct=0,mastered=0,total=0;
        for(auto& agent:agents){
            auto& a=*agent;
            tree_error_write_question(a.h,question);
            const int known=tree_error_next_from_input(a.h,0,run);
            const bool already=known>=0&&tree_error_probe(a.h,question,known,run).correct;
            if(a.resource<100)continue;
            // Search begins at a different option for each founder. The
            // environment grants one actual trial per turn, not free guesses.
            int option=already?known:tree_error_next_from_input(a.h,a.h.id,run);
            if(option<0)throw std::logic_error("error world exhausted candidates");
            if(!already&&!tree_error_has_free_node(a.h))continue;
            if(!already&&!a.choices[size_t(question-1)].insert(option).second)
                throw std::logic_error("repeated wrong answer");
            a.resource-=100;++a.attempts;++total;
            const bool right=option==(question==1?6:3);
            if(right){++correct;a.resource+=200;}
            if(!already)tree_error_record_from_input(a.h,option,right,run);
        }
        for(auto& agent:agents){
            const int known=tree_error_next_from_input(agent->h,0,run);
            mastered+=known>=0&&tree_error_probe(agent->h,question,known,run).correct;
        }
        int resources=0;for(const auto& a:agents)resources+=a->resource;
        result.rows.push_back({round,question,mastered,correct,resources});
        if(question==1&&mastered>=3){
            result.promotion_round=round;result.laggards=4-mastered;question=2;
        }
        if(question==2&&mastered==4&&result.promotion_round<round)break;
    }
    return result;
}
#ifndef TREE_ERROR_WORLD_NO_MAIN
int main(){
    auto result=run_error_world();
    std::cout<<"round,question,mastered,correct,resource\n";
    for(const auto& r:result.rows)std::cout<<r.round<<','<<r.question<<','<<r.mastered<<','<<r.correct<<','<<r.resource<<'\n';
    std::cout<<"PASS majority gate at round "<<result.promotion_round<<", laggards "<<result.laggards<<'\n';
}
#endif
