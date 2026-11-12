#include "../src/hamu_vm_core.hpp"
#include <cassert>
#include <iostream>
#include <vector>

static void install(Hamster& h, const std::vector<int>& words) {
    int at=h.params.layout.program_start;
    for(int word:words) for(bool bit:SpiralToken(word,5,1).bits) h.memory.at(at++)=bit;
    h.pro_1=h.params.layout.program_start;
    h.pro_2=at-1;
}

static int node(Hamster& h,int key) {
    install(h,{28,key,15,0});
    std::fill(h.val_reg.begin(),h.val_reg.end(),false);
    h.stop=false;h.executed_steps=0;h.step_limit=16;
    simulate_spiral_program(h);
    int id=0;for(int b=0;b<5;++b)id=(id<<1)|int(h.val_reg[b]);
    assert(h.val_reg[5]);
    return id;
}

static void answer(Hamster& h,int op,int value,bool known) {
    for(int i=0;i<h.params.layout.status_start;++i)h.memory[i]=false;
    h.memory[1]=true; // activation 01
    for(int i=0;i<4;++i)h.memory[2+i]=SpiralToken(op,3,1).bits[i];
    for(int i=0;i<4;++i)h.memory[6+i]=SpiralToken(value,3,1).bits[i];
    for(int i=h.params.layout.output_start;i<h.params.layout.work_start;++i) {
        h.memory[i]=false;h.written[i]=false;
    }
    std::fill(h.val_reg.begin(),h.val_reg.end(),false);
    std::fill(h.read_seen.begin(),h.read_seen.end(),false);
    h.val_ptr=0;h.stop=false;h.executed_steps=0;h.step_limit=64;
    h.pro_1=h.params.layout.program_start;
    simulate_spiral_program(h);
    assert(h.stop&&!h.budget_exhausted);
    for(int i=2;i<5;++i)assert(h.read_seen[i]);
    for(int i=0;i<3;++i) {
        const int at=h.params.layout.output_start+i;
        assert(h.written[at]==known);
        if(known&&h.memory[at]!=bool(((op==3?value:(value^7))>>(2-i))&1)) {
            std::cerr<<"op="<<op<<" value="<<value<<" bit="<<i
                     <<" actual="<<h.memory[at]<<" steps="<<h.executed_steps<<"\n";
            assert(false);
        }
    }
}

int main() {
    HamsterParams p;p.op_order=5;p.layout.status_start=45;p.layout.output_start=50;
    p.layout.work_start=80;p.layout.program_start=400;p.layout.total_size=730;
    p.stable_work_bits=27;p.tree_start=373;p.tree_capacity=3;
    p.layout.val_reg_size=12;
    Hamster h(1,p);
    assert(node(h,3)==1);assert(node(h,4)==2);
    // The VM reads the operator token into registers 6..8, looks it up under
    // root, then branches on the returned node ID. Host never selects a body.
    const std::vector<int> program={
        16,1, 0,0, 14,18, 8,22, 4,3, 29,0, 8,1, 18,20, 15,0,
        8,1, 24,10,
        0,0, 14,22, 8,4, 4,3, 0,2, 2,3, 14,3, 5,3, 15,0,
        0,0, 14,22, 8,4, 4,3, 0,2, 9,3, 15,0
    };
    assert(program.size()==54);
    install(h,program);
    for(int value=0;value<8;++value) {
        answer(h,3,value,true);
        answer(h,4,value,true);
        answer(h,5,value,false); // previously unseen word has no branch
    }
    h.new_his();Hamster child(2,p);child.copy_hamu(h);
    install(child,program);
    answer(child,3,5,true);answer(child,4,2,true);
    std::cout<<"PASS guest tree routing: 16 COPY/FLIP answers, unseen word, descendant\n";
}
