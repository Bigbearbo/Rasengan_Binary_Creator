#include "../src/tree_width_scaffold_vm.hpp"
#include "../src/tree_width_trial_vm.hpp"
#include "../src/tree_trial_grade.hpp"
#include "../src/hamu_vm_core.hpp"
#include <cassert>
#include <iostream>

int main() {
    HamsterParams p;p.op_order=5;p.layout.status_start=45;
    p.layout.output_start=50;p.layout.work_start=80;
    p.layout.program_start=500;p.layout.total_size=4000;
    p.stable_work_bits=84;p.tree_start=416;p.tree_capacity=7;
    p.layout.val_reg_size=12;Hamster h(1,p);
    auto run=[&](const std::vector<int>& words){
        int at=p.layout.program_start;
        for(int word:words)for(bool bit:SpiralToken(word,5,1).bits)
            h.memory.at(at++)=bit;
        std::fill(h.val_reg.begin(),h.val_reg.end(),false);
        h.val_ptr=0;h.stop=false;h.executed_steps=0;h.budget_exhausted=false;
        h.step_limit=800;h.pro_1=p.layout.program_start;h.pro_2=at-1;
        simulate_spiral_program(h);
        assert(h.stop&&!h.budget_exhausted);
    };
    auto question=[&](int width,int data) {
        std::fill(h.memory.begin(),h.memory.begin()+45,false);
        h.memory[1]=true;
        for(int b=0;b<4;++b)
            h.memory[2+b]=SpiralToken(1,3,1).bits[b];
        for(int b=0;b<width+1;++b)
            h.memory[6+b]=SpiralToken(1,width,1).bits[b];
        for(int b=0;b<4;++b)
            h.memory[7+width+b]=SpiralToken(data,3,1).bits[b];
        run(tree_width_scaffold_program());
    };
    for(int width:{2,3})for(int data=0;data<8;++data){
        question(width,data);
        for(int choice=0;choice<2;++choice){
            const int expected=choice?data^7:data;
            std::array<bool,3> bits{};
            for(int b=0;b<3;++b)bits[b]=(expected>>(2-b))&1;
            const bool correct=run_tree_graded_trial(h,bits,[&]{
                run(tree_width_trial_program(bool(choice)));
            });
            assert(correct&&h.memory[173]&&h.memory[40]);
        }
    }
    std::cout<<"PASS guest trial reads n=2/n=3 data, teacher accepts fresh three-bit answers\n";
}
