#include "../src/tree_confirm_bridge.hpp"
#include "../src/hamu_vm_core.hpp"
#include <cassert>
#include <iostream>

int main(){
    HamsterParams p;p.op_order=5;p.layout.status_start=45;p.layout.output_start=50;
    p.layout.work_start=80;p.layout.program_start=400;p.layout.total_size=1200;
    p.stable_work_bits=36;p.tree_start=364;p.tree_capacity=3;p.layout.val_reg_size=12;
    Hamster h(1,p);
    auto execute=[&](const std::vector<int>& words,int id){
        int at=p.layout.program_start;
        for(int w:words)for(bool bit:SpiralToken(w,5,1).bits)h.memory.at(at++)=bit;
        std::fill(h.val_reg.begin(),h.val_reg.end(),false);
        for(int b=0;b<5;++b)h.val_reg[b]=(id>>(4-b))&1;
        h.val_ptr=0;h.stop=false;h.executed_steps=0;h.step_limit=100;
        h.pro_1=p.layout.program_start;h.pro_2=at-1;
        simulate_spiral_program(h);assert(h.stop&&!h.budget_exhausted);
    };
    execute({28,3,15,0},0);
    execute({28,4,15,0},0);
    auto action=[&](int id){
        execute({30,0,15,0},id);
        return std::pair<bool,int>{h.val_reg[5],int(h.val_reg[6])*2+int(h.val_reg[7])};
    };
    auto first=tree_confirm_bridge_program(57),second=tree_confirm_bridge_program(70);
    h.memory[80+47]=true;h.memory[80+60]=true;
    h.memory[80+48]=true;h.memory[80+61]=true;
    for(int b=0;b<3;++b){
        h.memory[80+52+b]=(3>>(2-b))&1;
        h.memory[80+65+b]=(4>>(2-b))&1;
    }
    h.memory[80+58]=true;h.memory[80+71]=false; // partial candidate bits are not confirmation
    execute(first,0);execute(second,0);
    assert((action(1)==std::pair<bool,int>{false,0}));
    assert((action(2)==std::pair<bool,int>{false,0}));
    h.memory[80+57]=true;h.memory[80+58]=true;
    h.memory[80+70]=true;h.memory[80+71]=false;
    execute(first,0);execute(second,0);
    assert((action(1)==std::pair<bool,int>{true,2}));
    assert((action(2)==std::pair<bool,int>{true,0}));
    h.memory[80+57]=false;h.memory[80+58]=false;
    execute(first,0); // an unconfirmed update cannot overwrite an old action
    assert((action(1)==std::pair<bool,int>{true,2}));
    h.memory[80+57]=true;h.memory[80+58]=false;
    for(int b=0;b<3;++b)h.memory[80+52+b]=(5>>(2-b))&1;
    execute(first,0); // no node for the saved key 5
    assert((action(1)==std::pair<bool,int>{true,2}));
    assert((action(2)==std::pair<bool,int>{true,0}));
    for(int b=0;b<3;++b)h.memory[80+52+b]=(3>>(2-b))&1;
    h.memory[80+48]=false;
    execute(first,0); // a shorter word with the same numeric value is distinct
    assert((action(1)==std::pair<bool,int>{true,2}));
    h.memory[80+48]=true;
    execute(first,2); // correct key under the wrong parent is not a match
    assert((action(1)==std::pair<bool,int>{true,2}));
    h.new_his();Hamster child(2,p);child.copy_hamu(h);
    for(int i=364;i<400;++i)assert(child.memory[i]==h.memory[i]);
    std::cout<<"PASS confirmed local IDs bind two tree actions, unconfirmed ignored, inherited\n";
}
