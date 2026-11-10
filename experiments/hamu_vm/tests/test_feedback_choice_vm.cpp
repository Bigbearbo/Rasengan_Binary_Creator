#include "../src/feedback_choice_vm.hpp"
#include "../src/hamu_vm_core.hpp"
#include <cassert>
#include <iostream>
int main() {
    const auto code=feedback_choice_program();
    HamsterParams p;p.op_order=5;p.layout.status_start=45;p.layout.output_start=50;
    p.layout.work_start=80;p.layout.program_start=140;p.stable_work_bits=20;
    p.layout.total_size=140+int(code.size())*6;
    Hamster h(8,p);int at=140;
    for(int word:code)for(bool bit:SpiralToken(word,5,1).bits)h.memory.at(at++)=bit;
    for(int i=0;i<4;++i)h.memory[120+i]=1;
    h.memory[125]=1;
    auto round=[&](bool update,const char* keep,int id) {
        Problem q;h.write_prob(q);
        for(int i=0;i<4;++i)h.memory[1+i]=keep[i]=='1';
        h.memory[5]=update;
        h.pro_1=140;h.pro_2=at-1;h.step_limit=90;
        simulate_spiral_program(h);
        assert(!h.budget_exhausted&&h.memory[125]);
        for(int i=0;i<3;++i)assert(h.written[51+i]==(id>=0));
        if(id>=0) {
            assert(h.memory[51]==bool(id&2));assert(h.memory[52]==bool(id&1));
            assert(!h.memory[53]);
        }
    };
    round(false,"0000",0); // ignored keep mask
    round(true,"0101",1);
    round(true,"0100",1);
    round(false,"0000",1); // preserved learned state
    round(true,"0000",-1);
    h.new_his();Hamster child(9,p);child.copy_hamu(h);h=std::move(child);
    round(false,"1111",-1); // empty mask survives inheritance
    std::cout<<"PASS one-entry VM feedback update and candidate choice; inherited stop\n";
}
