#include "../src/mask_choice_vm.hpp"
#include "../src/hamu_vm_core.hpp"
#include <cassert>
#include <iostream>
int main() {
    const auto code=mask_choice_program();
    HamsterParams p;p.op_order=5;p.layout.status_start=45;p.layout.output_start=50;
    p.layout.work_start=80;p.layout.program_start=140;p.stable_work_bits=20;
    p.layout.total_size=140+int(code.size())*6;
    Hamster h(3,p);int at=140;
    for(int word:code)for(bool bit:SpiralToken(word,5,1).bits)h.memory.at(at++)=bit;
    auto choose=[&](const char* mask,int id) {
        Problem q;h.write_prob(q);
        for(int i=0;i<4;++i)h.memory[120+i]=mask[i]=='1';
        h.pro_1=140;h.pro_2=at-1;h.step_limit=50;
        simulate_spiral_program(h);assert(!h.budget_exhausted);
        for(int j=0;j<3;++j)assert(h.written[51+j]==(id>=0));
        if(id>=0) {
            assert(h.memory[51]==bool(id&2));
            assert(h.memory[52]==bool(id&1));
            assert(!h.memory[53]);
        }
    };
    choose("1111",0);choose("0101",1);choose("0011",2);
    choose("0001",3);choose("0000",-1);
    for(int i=0;i<4;++i)h.memory[120+i]=(i==2);
    h.new_his();Hamster child(4,p);child.copy_hamu(h);h=std::move(child);
    Problem q;h.write_prob(q);h.pro_1=140;h.pro_2=at-1;h.step_limit=50;
    simulate_spiral_program(h);
    assert(h.written[51]&&h.memory[51]&&!h.memory[52]&&!h.memory[53]);
    std::cout<<"PASS guest mask choice: priority IDs 0..3, empty stop, inherited mask\n";
}
