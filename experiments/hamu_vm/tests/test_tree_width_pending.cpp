#include "../src/tree_width_scaffold_vm.hpp"
#include "../src/tree_width_pending_vm.hpp"
#include "../src/tree_width_choice_vm.hpp"
#include "../src/hamu_vm_core.hpp"
#include <cassert>
#include <iostream>

int main(){
    HamsterParams p;p.op_order=5;p.layout.status_start=45;
    p.layout.output_start=50;p.layout.work_start=80;
    p.layout.program_start=700;p.layout.total_size=8000;
    p.stable_work_bits=100;p.tree_start=600;p.tree_capacity=8;
    p.layout.val_reg_size=12;
    Hamster h(1,p);
    auto run=[&](const std::vector<int>& words){
        int at=p.layout.program_start;
        for(int word:words)for(bool bit:SpiralToken(word,5,1).bits)
            h.memory.at(at++)=bit;
        std::fill(h.val_reg.begin(),h.val_reg.end(),false);
        h.val_ptr=0;h.stop=false;h.budget_exhausted=false;
        h.executed_steps=0;h.step_limit=1400;
        h.pro_1=p.layout.program_start;h.pro_2=at-1;
        simulate_spiral_program(h);
        assert(h.stop&&!h.budget_exhausted);
    };
    auto question=[&](int width,int op){
        std::fill(h.memory.begin(),h.memory.begin()+45,false);
        h.memory[1]=true;
        for(int b=0;b<4;++b)h.memory[2+b]=SpiralToken(1,3,1).bits[b];
        for(int b=0;b<width+1;++b)
            h.memory[6+b]=SpiralToken(op,width,1).bits[b];
        run(tree_width_scaffold_program());
    };
    question(2,1);run(tree_width_pending_program(57));
    assert(h.memory[127]&&h.memory[128]&&h.memory[158]);
    assert(!h.memory[180]); // work+100: width n=2
    assert(!h.memory[129]&&!h.memory[130]&&h.memory[131]); // padded key 001
    run(tree_width_choice_program(57));
    assert(h.memory[75]&&!h.memory[76]); // n=2 COPY candidate
    run(tree_width_pending_program(70));
    assert(!h.memory[140]); // same path cannot take a second slot
    question(3,1);run(tree_width_pending_program(70));
    assert(h.memory[140]&&h.memory[141]&&h.memory[159]);
    assert(h.memory[181]); // work+101: width n=3
    assert(!h.memory[142]&&!h.memory[143]&&h.memory[144]);
    run(tree_width_choice_program(57));assert(!h.memory[75]);
    run(tree_width_choice_program(70));assert(h.memory[75]&&!h.memory[76]);
    h.memory[80+68]=false; // guest mask would be eliminated by feedback
    run(tree_width_choice_program(70));assert(h.memory[75]&&h.memory[76]);
    question(3,0);run(tree_width_choice_program(70));assert(!h.memory[75]);
    question(3,1);run(tree_width_pending_program(57));
    assert(!h.memory[180]&&h.memory[181]); // occupied slot immutable
    h.new_his();Hamster child(2,p);child.copy_hamu(h);
    for(int i:{127,128,129,130,131,140,141,142,143,144,158,159,180,181})
        assert(child.memory[i]==h.memory[i]);
    std::cout<<"PASS width-aware guest pending contexts remain distinct and inherited\n";
}
