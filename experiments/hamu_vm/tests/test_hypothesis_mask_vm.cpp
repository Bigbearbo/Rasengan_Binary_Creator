#include "../src/hypothesis_mask_vm.hpp"
#include "../src/hamu_vm_core.hpp"
#include <cassert>
#include <iostream>
int main() {
    const auto code=hypothesis_mask_program();
    HamsterParams p;p.op_order=5;p.layout.status_start=45;p.layout.output_start=50;
    p.layout.work_start=80;p.layout.program_start=140;p.stable_work_bits=20;
    p.layout.total_size=140+int(code.size())*6;
    Hamster h(5,p);int at=140;
    for(int word:code)for(bool bit:SpiralToken(word,5,1).bits)h.memory.at(at++)=bit;
    for(int i=0;i<4;++i)h.memory[120+i]=1;
    h.memory[125]=1;
    auto round=[&](const char* keep) {
        Problem q;h.write_prob(q);
        for(int i=0;i<4;++i)h.memory[1+i]=keep[i]=='1';
        h.pro_1=140;h.pro_2=at-1;h.step_limit=30;
        simulate_spiral_program(h);
        assert(!h.budget_exhausted&&h.memory[125]);
    };
    round("0101"); // data 0: COPY wrong; FLIP right; ONE remains possible
    assert(!h.memory[120]&&h.memory[121]&&!h.memory[122]&&h.memory[123]);
    round("0100"); // data 1: correct FLIP distinguishes it from ONE
    assert(!h.memory[120]&&h.memory[121]&&!h.memory[122]&&!h.memory[123]);
    h.new_his();Hamster child(6,p);child.copy_hamu(h);
    for(int i=0;i<4;++i)assert(child.memory[120+i]==h.memory[120+i]);
    assert(child.memory[125]);
    std::cout<<"PASS guest VM four-bit mask update 1111->0101->0100 and inheritance\n";
}
