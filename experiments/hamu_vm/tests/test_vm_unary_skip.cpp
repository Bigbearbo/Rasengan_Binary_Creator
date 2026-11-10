#include "../src/hamu_vm_core.hpp"
#include <array>
#include <cassert>
#include <iostream>

// The VM reads one unary marker bit on each trip through words 10..25.
static constexpr std::array<int,34> code={
    0,0, 14,17, 19,0, 0,3, 16,1,
    4,1, 18,20, 20,30,
    14,17, 19,0, 14,17, 19,0, 20,14,
    16,31, 19,0, 4,1, 15,0
};

int main() {
    HamsterParams p;p.op_order=5;p.layout.total_size=p.layout.program_start+34*6;
    Hamster h(0,p);
    int at=p.layout.program_start;
    for(int word:code)for(bool b:SpiralToken(word,5,1).bits)h.memory.at(at++)=b;
    for(int prefix=2;prefix<=3;++prefix) {
        h.write_prob(Problem{});
        const int start=p.layout.input_start+1;
        for(int j=0;j<prefix;++j)h.memory.at(start+j)=j%2;
        h.memory.at(start+prefix)=1;
        for(int j=0;j<prefix;++j)h.memory.at(p.layout.work_start+j)=1;
        h.memory.at(p.layout.work_start+prefix)=0;
        h.pro_1=p.layout.program_start;h.pro_2=at-1;h.step_limit=100;
        simulate_spiral_program(h);
        if(h.budget_exhausted || !h.read_seen[start+prefix] ||
           !h.val_reg[0] || h.ptr!=start+prefix || h.secondary_ptr!=p.layout.work_start+prefix) {
            std::cerr<<"FAIL prefix="<<prefix<<" ptr="<<h.ptr
                     <<" other="<<h.secondary_ptr<<" steps="<<h.executed_steps<<"\n";
            return 1;
        }
        for(int j=0;j<prefix;++j)if(h.read_seen[start+j])return 2;
    }
    std::cout<<"PASS: VM opcode loop skips unary lengths 110 and 1110 bit by bit\n";
}
