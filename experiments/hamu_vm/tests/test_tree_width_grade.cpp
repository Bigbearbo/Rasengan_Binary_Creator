#include "../src/tree_width_grade_vm.hpp"
#include "../src/tree_width_pending_vm.hpp"
#include "../src/tree_width_scaffold_vm.hpp"
#include "../src/tree_width_trial_vm.hpp"
#include "../src/tree_width_feedback_vm.hpp"
#include "../src/tree_trial_grade.hpp"
#include "../src/hamu_vm_core.hpp"
#include <algorithm>
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
        for(int word:words)for(bool bit:SpiralToken(word,5,1).bits)h.memory.at(at++)=bit;
        std::fill(h.val_reg.begin(),h.val_reg.end(),false);
        h.val_ptr=0;h.stop=false;h.budget_exhausted=false;
        h.executed_steps=0;h.step_limit=1400;
        h.pro_1=p.layout.program_start;h.pro_2=at-1;
        simulate_spiral_program(h);
        assert(h.stop&&!h.budget_exhausted);
    };
    auto question=[&](int width,int op,int data){
        std::fill(h.memory.begin(),h.memory.begin()+45,false);
        h.memory[1]=true;
        auto category=SpiralToken(1,3,1).bits;
        for(int b=0;b<4;++b)h.memory[2+b]=category[b];
        auto key=SpiralToken(op,width,1).bits;
        for(int b=0;b<width+1;++b)h.memory[6+b]=key[b];
        auto datum=SpiralToken(data,3,1).bits;
        for(int b=0;b<4;++b)h.memory[7+width+b]=datum[b];
        run(tree_width_scaffold_program());
    };
    auto graded=[&](int expected){
        std::array<bool,3> bits{};
        for(int b=0;b<3;++b)bits[b]=(expected>>(2-b))&1;
        assert(run_tree_graded_trial(h,bits,[&]{run(tree_width_trial_program(false));}));
        assert(h.memory[80+93]);
        run(tree_width_snapshot_program());
        assert(h.memory[80+92]&&h.memory[80+34]);
    };
    auto accepts=[&](int slot){
        auto code=tree_width_grade_guard_program(slot);
        code.insert(code.end(),{0,3});
        for(int i=0;i<6;++i)code.insert(code.end(),{14,31});
        code.insert(code.end(),{14,29,2,1,15,0});
        h.memory[80+103]=false;
        run(code);
        return h.memory[80+103];
    };
    question(2,1,5);run(tree_width_pending_program(57));graded(5);
    assert(!h.memory[80+102]&&accepts(57)&&!accepts(70));
    h.memory[9]=!h.memory[9];assert(!accepts(57));h.memory[9]=!h.memory[9];
    h.memory[50]=!h.memory[50];assert(!accepts(57));h.memory[50]=!h.memory[50];
    question(3,1,5);run(tree_width_pending_program(70));
    assert(!accepts(57)&&!accepts(70)); // old grade cannot enter new width
    run(tree_width_feedback_cycle_program(70));
    assert(!h.memory[80+94]&&h.memory[80+68]&&h.memory[80+69]);
    run(tree_width_feedback_confirm_program(70));assert(!h.memory[80+70]);
    graded(5);
    assert(h.memory[80+102]&&accepts(70)&&!accepts(57));
    h.memory[10]=!h.memory[10];assert(!accepts(70));h.memory[10]=!h.memory[10];
    h.memory[80+102]=false;assert(!accepts(70));h.memory[80+102]=true;
    run(tree_width_feedback_confirm_program(70));assert(!h.memory[80+70]);
    run(tree_width_feedback_cycle_program(70));
    assert(h.memory[80+94]&&h.memory[80+68]&&!h.memory[80+69]);
    run(tree_width_feedback_confirm_program(70));
    assert(h.memory[80+70]&&!h.memory[80+71]);
    // A later grade for the other width may not mutate the confirmed slot.
    h.memory[80+93]=false;
    run(tree_width_feedback_cycle_program(70));assert(!h.memory[80+94]);
    std::cout<<"PASS width-bound grade snapshot and pending guard\n";
}
