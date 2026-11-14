#include "../src/tree_width_learning_turn.hpp"
#include "../src/tree_width_trial_vm.hpp"
#include "../src/tree_width_route_vm.hpp"
#include <cassert>
#include <iostream>

int main(){
    HamsterParams p;p.op_order=5;p.layout.status_start=45;
    p.layout.output_start=50;p.layout.work_start=80;
    p.layout.program_start=700;p.layout.total_size=10000;
    p.stable_work_bits=100;p.tree_start=600;p.tree_capacity=8;
    p.layout.val_reg_size=12;
    Hamster h(1,p);
    bool interrupt_binding=false;
    auto run=[&](const std::vector<int>& words){
        int at=p.layout.program_start;
        for(int word:words)for(bool bit:SpiralToken(word,5,1).bits)h.memory.at(at++)=bit;
        std::fill(h.val_reg.begin(),h.val_reg.end(),false);
        h.val_ptr=0;h.stop=false;h.budget_exhausted=false;
        const bool interrupt=interrupt_binding&&h.memory[80+57]&&words==tree_width_confirm_bridge_program(57);
        if(interrupt)interrupt_binding=false;
        h.executed_steps=0;h.step_limit=interrupt?1:1600;
        h.pro_1=p.layout.program_start;h.pro_2=at-1;
        simulate_spiral_program(h);
        if(interrupt)assert(h.budget_exhausted);else assert(h.stop&&!h.budget_exhausted);
    };
    auto question=[&](int width,int op,int data){
        std::fill(h.memory.begin(),h.memory.begin()+45,false);h.memory[1]=true;
        for(int b=0;b<4;++b)h.memory[2+b]=SpiralToken(1,3,1).bits[b];
        for(int b=0;b<width+1;++b)h.memory[6+b]=SpiralToken(op,width,1).bits[b];
        for(int b=0;b<4;++b)h.memory[7+width+b]=SpiralToken(data,3,1).bits[b];
    };
    const std::array<std::vector<int>,2> candidates={tree_width_trial_program(false),tree_width_trial_program(true)};
    auto turn=[&](int expected){
        std::array<bool,3> bits{};for(int b=0;b<3;++b)bits[b]=(expected>>(2-b))&1;
        return run_tree_width_learning_turn(h,bits,candidates,run);
    };
    auto action=[&](int node){
        int at=p.tree_start+p.tree_capacity*9+(node-1)*3;
        assert(h.memory[at]);return int(h.memory[at+1])*2+int(h.memory[at+2]);
    };
    auto answer=[&](int width,int data,int expected){
        question(width,1,data);
        std::fill(h.memory.begin()+50,h.memory.begin()+80,false);
        std::fill(h.written.begin()+50,h.written.begin()+80,false);
        run(tree_width_route_program());
        for(int b=0;b<3;++b){assert(h.written[50+b]);assert(h.memory[50+b]==bool((expected>>(2-b))&1));}
        for(int at=53;at<80;++at)assert(!h.written[at]);
    };
    question(2,1,5);auto first=turn(5);
    assert(first&&first->slot==57&&first->candidate==0&&first->valid&&first->correct&&first->confirmed);
    assert(action(3)==0);
    for(int data=0;data<8;++data)answer(2,data,data);
    question(2,1,4);assert(!turn(4)); // learned leaf does not re-enter pending
    h.new_his();Hamster old_child(2,p);old_child.copy_hamu(h);
    // Invalid promotion must leave inherited memory and the tree untouched.
    question(3,1,5);h.memory[9]=true;
    auto before=h.memory;
    assert(!turn(2));
    for(int at=80;at<700;++at)if(at!=80+104)assert(h.memory[at]==before[at]);
    question(3,1,5);auto wrong=turn(2);
    assert(wrong&&wrong->slot==70&&wrong->candidate==0&&wrong->valid&&!wrong->correct&&!wrong->confirmed);
    assert(action(3)==0);
    question(3,1,6);auto learned=turn(1);
    assert(learned&&learned->slot==70&&learned->candidate==1&&learned->correct&&learned->confirmed);
    assert(action(3)==0&&action(5)==2);
    for(int data=0;data<8;++data)answer(3,data,data^7);
    // Saved width determines the binding path, even after promotion.
    h.memory[p.tree_start+p.tree_capacity*9+2*3]=false;
    run(tree_width_confirm_bridge_program(57));
    assert(action(3)==0&&action(5)==2);
    h.memory[80+58]=true;run(tree_width_confirm_bridge_program(57));
    assert(action(3)==0&&action(5)==2);
    h.new_his();Hamster child(3,p);child.copy_hamu(h);h=child;
    for(int data=0;data<8;++data)answer(3,data,data^7);
    assert(action(3)==0&&action(5)==2);
    h=old_child;
    for(int data=0;data<8;++data)answer(2,data,data);
    h=Hamster(4,p);interrupt_binding=true;
    question(2,1,5);auto interrupted=turn(5);
    assert(interrupted&&interrupted->confirmed&&!h.memory[p.tree_start+p.tree_capacity*9+2*3]);
    question(2,1,4);assert(!turn(4)); // next turn repairs binding without re-learning
    assert(action(3)==0);answer(2,4,4);
    // Capacity failure cannot publish preparation success or start a trial.
    p.tree_capacity=2;h=Hamster(5,p);
    question(2,1,5);assert(!turn(5));assert(!h.memory[80+47]&&!h.memory[80+60]);
    std::cout<<"PASS width learning: COPY then promoted FLIP, guest binding, rejection, inheritance\n";
}
