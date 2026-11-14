#include "../src/hamu_vm_core.hpp"
#include <chrono>
#include <iostream>

int main(){
    HamsterParams p;p.op_order=5;p.layout.status_start=45;p.layout.output_start=50;
    p.layout.work_start=80;p.layout.program_start=700;p.layout.total_size=24000;
    p.stable_work_bits=100;p.tree_start=600;p.tree_capacity=8;p.layout.val_reg_size=12;
    for(int pairs:{40,160,400}){
        Hamster h(1,p);int at=p.layout.program_start;
        for(int i=0;i<pairs;++i)for(int word:{16,1})
            for(bool bit:SpiralToken(word,5,1).bits)h.memory[at++]=bit;
        for(int word:{15,0})for(bool bit:SpiralToken(word,5,1).bits)h.memory[at++]=bit;
        h.pro_1=p.layout.program_start;h.pro_2=at-1;h.step_limit=2*pairs+5;
        const auto start=std::chrono::steady_clock::now();
        for(int repetition=0;repetition<10;++repetition){
            h.stop=false;h.executed_steps=0;h.budget_exhausted=false;
            simulate_spiral_program(h);
            if(!h.stop||h.budget_exhausted)throw std::runtime_error("benchmark failed");
        }
        auto seconds=std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
        std::cout<<pairs<<" pairs: "<<seconds<<" seconds / 10, steps="<<h.executed_steps<<'\n';
    }
}
