#include "../src/tree_width_scaffold_vm.hpp"
#include "../src/hamu_vm_core.hpp"
#include <cassert>
#include <iostream>

int main(){
    HamsterParams p;p.op_order=5;p.layout.status_start=45;
    p.layout.output_start=50;p.layout.work_start=80;
    p.layout.program_start=500;p.layout.total_size=4000;
    p.stable_work_bits=72;p.tree_start=428;p.tree_capacity=6;
    p.layout.val_reg_size=12;
    Hamster h(1,p);
    auto run=[&](const std::vector<int>& words,int node=0,int action=-1){
        int at=p.layout.program_start;
        for(int word:words)for(bool bit:SpiralToken(word,5,1).bits)
            h.memory.at(at++)=bit;
        std::fill(h.val_reg.begin(),h.val_reg.end(),false);
        for(int bit=0;bit<5;++bit)h.val_reg[bit]=(node>>(4-bit))&1;
        if(action>=0){h.val_reg[6]=(action>>1)&1;h.val_reg[7]=action&1;}
        h.val_ptr=0;h.stop=false;h.executed_steps=0;
        h.budget_exhausted=false;h.step_limit=200;
        h.pro_1=p.layout.program_start;h.pro_2=at-1;
        simulate_spiral_program(h);
        assert(h.stop&&!h.budget_exhausted);
        int id=0;for(int bit=0;bit<5;++bit)id=(id<<1)|int(h.val_reg[bit]);
        return std::pair<int,bool>{id,h.val_reg[5]};
    };
    auto question=[&](int n,int op){
        std::fill(h.memory.begin(),h.memory.begin()+45,false);
        h.memory[1]=true;
        for(int bit=0;bit<4;++bit)
            h.memory[2+bit]=SpiralToken(1,3,1).bits[bit];
        for(int bit=0;bit<n+1;++bit)
            h.memory[6+bit]=SpiralToken(op,n,1).bits[bit];
    };
    const auto scaffold=tree_width_scaffold_program();
    question(2,1);assert((run(scaffold)==std::pair<int,bool>{3,true}));
    assert(!h.memory[176]); // still width 2
    run({30,1,15,0},3,0); // old COPY action
    const int actions=428+6*9;
    assert(h.memory[actions+6]);
    const auto old=h.memory;
    assert((run(scaffold)==std::pair<int,bool>{3,true}));
    for(int bit=428;bit<500;++bit)assert(h.memory[bit]==old[bit]);
    question(3,1);h.memory[9]=true;run(scaffold); // invalid new tail
    assert(!h.memory[176]);
    for(int bit=428;bit<500;++bit)assert(h.memory[bit]==old[bit]);
    question(2,1);h.memory[5]=true;run(scaffold); // invalid category tail
    for(int bit=428;bit<500;++bit)assert(h.memory[bit]==old[bit]);
    question(2,1);h.memory[1]=false;run(scaffold); // invalid opening frame
    for(int bit=428;bit<500;++bit)assert(h.memory[bit]==old[bit]);
    question(3,1);assert((run(scaffold)==std::pair<int,bool>{5,true}));
    assert(h.memory[176]); // old tail 0 -> 1 triggered promotion
    assert(h.memory[actions+6]&&!h.memory[actions+12]);
    run({30,1,15,0},5,2); // new FLIP action, old COPY remains
    assert(h.memory[actions+12]&&h.memory[actions+13]);
    const auto promoted_tree=h.memory;
    question(3,0);h.memory[9]=true;run(scaffold); // invalid tail after promotion
    assert(h.memory[176]);
    for(int bit=428;bit<500;++bit)assert(h.memory[bit]==promoted_tree[bit]);
    question(3,0);assert((run(scaffold)==std::pair<int,bool>{6,true}));
    assert(h.memory[176]); // third information bit may be 0 after promotion
    question(3,1);assert((run(scaffold)==std::pair<int,bool>{5,true}));
    assert(h.memory[actions+6]&&h.memory[actions+12]);
    h.new_his();Hamster child(2,p);child.copy_hamu(h);
    for(int bit=428;bit<500;++bit)assert(child.memory[bit]==h.memory[bit]);
    assert(child.memory[176]);
    std::cout<<"PASS width promotion preserves old branch and separates same numeric key\n";
}
