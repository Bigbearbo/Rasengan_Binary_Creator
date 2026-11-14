#include "../src/hamu_vm_core.hpp"
#include <cassert>
#include <iostream>

int main() {
    HamsterParams p;p.op_order=5;p.layout.status_start=45;p.layout.output_start=50;
    p.layout.work_start=80;p.layout.program_start=140;p.layout.total_size=500;
    p.stable_work_bits=20;
    Hamster h(0,p);
    // All persistent bits are live, including the first boundary bit.
    for(int j=120;j<140;++j)h.memory[j]=1;
    h.memory[90]=1;
    auto run=[&](int opcode,int at_work) {
        const int code[]={0,3,14,31,14,16+at_work-15,opcode,1,15,0};
        int at=p.layout.program_start;
        for(int w:code)for(bool b:SpiralToken(w,5,1).bits)h.memory.at(at++)=b;
        Problem q;h.write_prob(q);
        h.pro_1=p.layout.program_start;h.pro_2=at-1;h.step_limit=20;
        simulate_spiral_program(h);
        for(int j=120;j<140;++j)assert(h.memory[j]);
    };
    run(10,20); // INSERT before boundary, must not be blocked by stable 1s
    assert(!h.work_insert_blocked);
    run(11,20); // DELETE also excludes stable region
    h.memory[119]=1;
    run(10,20);assert(h.work_insert_blocked); // moving region itself is full
    h.new_his();Hamster child(1,p);child.copy_hamu(h);
    for(int j=120;j<140;++j)assert(child.memory[j]);
    auto mismatch=p;mismatch.stable_work_bits=0;
    Hamster other(2,mismatch);bool blocked=false;
    try {other.copy_hamu(h);}catch(const std::invalid_argument&){blocked=true;}
    assert(blocked);
    std::cout<<"PASS stable boundary: INSERT/DELETE, strict capacity, inheritance/layout guard\n";
}
