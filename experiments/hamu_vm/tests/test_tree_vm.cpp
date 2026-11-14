#include "../src/hamu_vm_core.hpp"
#include <cassert>
#include <iostream>

int main() {
    HamsterParams p;p.op_order=5;p.layout.status_start=45;p.layout.output_start=50;
    p.layout.work_start=80;p.layout.program_start=200;p.layout.total_size=230;
    p.stable_work_bits=27;p.tree_start=173;p.tree_capacity=3;
    p.layout.val_reg_size=12;
    Hamster h(1,p);
    auto run=[&](int op,int key,int parent) {
        int at=200;
        for(int w:{op,key,15,0})for(bool bit:SpiralToken(w,5,1).bits)h.memory.at(at++)=bit;
        for(int b=0;b<5;++b)h.val_reg[b]=(parent>>(4-b))&1;
        h.stop=false;h.executed_steps=0;h.step_limit=10;
        h.pro_1=200;h.pro_2=at-1;
        simulate_spiral_program(h);
        int id=0;for(int b=0;b<5;++b)id=(id<<1)|int(h.val_reg[b]);
        return std::pair<int,bool>{id,h.val_reg[5]};
    };
    assert((run(27,3,0)==std::pair<int,bool>{0,false}));
    assert((run(28,3,0)==std::pair<int,bool>{1,true}));
    assert((run(28,3,0)==std::pair<int,bool>{1,true})); // no duplicate
    assert((run(28,4,1)==std::pair<int,bool>{2,true})); // child of child
    assert((run(28,5,0)==std::pair<int,bool>{3,true}));
    const auto full=h.memory;
    assert((run(28,6,0)==std::pair<int,bool>{0,false}));
    for(int i=173;i<200;++i)assert(h.memory[i]==full[i]);
    assert((run(28,7,4)==std::pair<int,bool>{0,false})); // missing parent
    assert((run(27,4,1)==std::pair<int,bool>{2,true}));
    h.new_his();Hamster child(2,p);child.copy_hamu(h);
    for(int i=173;i<200;++i)assert(child.memory[i]==h.memory[i]);
    std::cout<<"PASS VM tree add/find, duplicate, full, missing parent, inheritance\n";
}
