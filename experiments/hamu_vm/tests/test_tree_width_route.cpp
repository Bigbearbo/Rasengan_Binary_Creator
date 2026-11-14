#include "../src/tree_width_scaffold_vm.hpp"
#include "../src/tree_width_route_vm.hpp"
#include "../src/hamu_vm_core.hpp"
#include <cassert>
#include <iostream>

int main() {
    HamsterParams p;p.op_order=5;p.layout.status_start=45;
    p.layout.output_start=50;p.layout.work_start=80;
    p.layout.program_start=500;p.layout.total_size=4000;
    p.stable_work_bits=84;p.tree_start=416;p.tree_capacity=7;
    p.layout.val_reg_size=12;
    Hamster h(1,p);
    auto run=[&](const std::vector<int>& words,int node=0,int action=-1) {
        int at=p.layout.program_start;
        for(int word:words)for(bool bit:SpiralToken(word,5,1).bits)
            h.memory.at(at++)=bit;
        std::fill(h.val_reg.begin(),h.val_reg.end(),false);
        for(int bit=0;bit<5;++bit)h.val_reg[bit]=(node>>(4-bit))&1;
        if(action>=0){h.val_reg[6]=(action>>1)&1;h.val_reg[7]=action&1;}
        h.val_ptr=0;h.stop=false;h.executed_steps=0;h.budget_exhausted=false;
        h.step_limit=800;h.pro_1=p.layout.program_start;h.pro_2=at-1;
        simulate_spiral_program(h);
        assert(h.stop&&!h.budget_exhausted);
        int id=0;for(int bit=0;bit<5;++bit)id=(id<<1)|int(h.val_reg[bit]);
        return std::pair<int,bool>{id,h.val_reg[5]};
    };
    auto question=[&](int width,int op,int data) {
        std::fill(h.memory.begin(),h.memory.begin()+45,false);
        h.memory[1]=true;
        for(int bit=0;bit<4;++bit)
            h.memory[2+bit]=SpiralToken(1,3,1).bits[bit];
        for(int bit=0;bit<width+1;++bit)
            h.memory[6+bit]=SpiralToken(op,width,1).bits[bit];
        for(int bit=0;bit<4;++bit)
            h.memory[7+width+bit]=SpiralToken(data,3,1).bits[bit];
    };
    const auto scaffold=tree_width_scaffold_program();
    const auto route=tree_width_route_program();
    auto answer=[&](int width,int op,int data,int expected){
        question(width,op,data);
        for(int at=50;at<80;++at){h.memory[at]=false;h.written[at]=false;}
        run(route);
        for(int bit=0;bit<3;++bit){
            assert(h.written[50+bit]);
            assert(h.memory[50+bit]==bool((expected>>(2-bit))&1));
        }
        for(int at=53;at<80;++at)assert(!h.written[at]);
    };
    question(2,1,3);
    assert((run(scaffold)==std::pair<int,bool>{3,true}));
    run({30,1,15,0},3,0);
    for(int data=0;data<8;++data)answer(2,1,data,data);
    question(2,0,4);run(scaffold); // an unbound leaf
    std::fill(h.written.begin()+50,h.written.begin()+80,false);
    run(route);
    for(int at=50;at<80;++at)assert(!h.written[at]);
    question(3,1,3);
    assert((run(scaffold)==std::pair<int,bool>{6,true}));
    run({30,1,15,0},6,2); // same numeric key, distinct n=3 action
    for(int data=0;data<8;++data)answer(3,1,data,data^7);
    question(3,0,2);
    assert((run(scaffold)==std::pair<int,bool>{7,true}));
    std::fill(h.written.begin()+50,h.written.begin()+80,false);
    run(route);
    for(int at=50;at<80;++at)assert(!h.written[at]);
    h.new_his();Hamster child(2,p);child.copy_hamu(h);h=child;
    for(int data=0;data<8;++data)answer(3,1,data,data^7);
    std::cout<<"PASS width-aware guest route, unbound leaf, and inheritance\n";
}
