#include "tree_compact_reference.hpp"
#include <iostream>
#include <memory>
#include <set>

struct CompactWorldAgent {
    Hamster h;int resource=1000,attempts=0;
    std::array<std::set<int>,2> choices;
    explicit CompactWorldAgent(int id,const HamsterParams& p):h(id,p){h.memory[1]=true;}
};
struct CompactWorldRow {int round,question,mastered,correct,resource;};
struct CompactWorldResult {
    std::vector<CompactWorldRow> rows;
    int promotion_round=0,laggards=0;
    long long vm_steps=0,vm_calls=0;
    int peak_vm_steps=0,used_question_nodes=0;
    int reserved_tree_bits=0,reserved_payload_bits=0;
};
inline CompactWorldResult run_compact_world(int tree_capacity=31){
    HamsterParams p;p.layout.status_start=45;p.layout.output_start=50;
    p.layout.work_start=80;p.layout.program_start=1100;p.layout.total_size=24000;
    p.stable_work_bits=800;p.tree_start=300;p.tree_capacity=tree_capacity;
    p.layout.val_reg_size=12;
    std::vector<std::unique_ptr<CompactWorldAgent>> agents;
    for(int i=0;i<4;++i)agents.emplace_back(std::make_unique<CompactWorldAgent>(i,p));
    CompactWorldResult result;
    result.reserved_tree_bits=4*tree_capacity*9;
    result.reserved_payload_bits=4*tree_capacity*12;
    auto run=[&](Hamster& h,const std::vector<int>& words){
        int at=p.layout.program_start;
        for(int word:words)for(bool bit:SpiralToken(word,5,1).bits)h.memory.at(at++)=bit;
        std::fill(h.val_reg.begin(),h.val_reg.end(),false);h.val_ptr=0;
        h.stop=false;h.budget_exhausted=false;h.executed_steps=0;h.step_limit=4000;
        h.pro_1=p.layout.program_start;h.pro_2=at-1;simulate_spiral_program(h);
        result.vm_steps+=h.executed_steps;++result.vm_calls;
        result.peak_vm_steps=std::max(result.peak_vm_steps,h.executed_steps);
        if(!h.stop||h.budget_exhausted)throw std::runtime_error("compact world VM execution");
    };
    int question=1;
    for(int round=1;round<=16;++round){
        int correct=0,mastered=0;
        for(auto& agent:agents){
            auto& a=*agent;
            if(a.resource<100)continue;
            TreeCompactReference tree{a.h,672};
            int target=question;
            if(question==2){
                run(a.h,tree_compact_guest_read_program(1,672,p.layout.work_start));
                if(!a.h.val_reg[8])target=1; // finish the earlier lesson
            }
            if(!tree_error_has_free_node(a.h)){
                // An existing question remains usable when the tree is full.
                run(a.h,{8,11,27,target,15,0});
                if(!a.h.val_reg[5])continue;
            }
            const int option=tree.next(target,run,a.h.id);
            // The guest choice program has already READ all 12 payload bits,
            // including success at val_reg[8]. No second VM read is needed.
            const bool already=a.h.val_reg[8];
            if(option<0)continue;
            if(!already&&!a.choices[size_t(target-1)].insert(option).second)
                throw std::logic_error("repeated compact wrong answer");
            a.resource-=100;++a.attempts;
            const bool right=option==(target==1?6:3);
            if(right){if(target==question)++correct;a.resource+=200;}
            if(!already)tree.record(target,option,right,run);
        }
        for(auto& agent:agents){
            run(agent->h,tree_compact_guest_read_program(question,672,p.layout.work_start));
            mastered+=agent->h.val_reg[8];
        }
        int resources=0;for(const auto& a:agents)resources+=a->resource;
        result.rows.push_back({round,question,mastered,correct,resources});
        if(question==1&&mastered>=3){
            result.promotion_round=round;result.laggards=4-mastered;question=2;
        }
        if(question==2&&mastered==4&&result.promotion_round<round)break;
    }
    for(const auto& a:agents)
        for(int id=0;id<tree_capacity;++id)
            result.used_question_nodes+=a->h.memory[p.tree_start+id*9];
    return result;
}
#ifndef TREE_COMPACT_WORLD_NO_MAIN
int main(){
    auto r=run_compact_world();
    std::cout<<"round,question,mastered,correct,resource\n";
    for(auto x:r.rows)std::cout<<x.round<<','<<x.question<<','<<x.mastered<<','<<x.correct<<','<<x.resource<<'\n';
    std::cout<<"vm_calls="<<r.vm_calls<<" vm_steps="<<r.vm_steps
             <<" peak_vm_steps="<<r.peak_vm_steps<<" used_question_nodes="<<r.used_question_nodes
             <<" reserved_tree_bits="<<r.reserved_tree_bits
             <<" reserved_payload_bits="<<r.reserved_payload_bits<<'\n';
}
#endif
