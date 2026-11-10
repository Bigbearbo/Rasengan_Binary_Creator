#include "../src/guest_fragment_request.hpp"
#include <cassert>
#include <iostream>
int main() {
    for(int gene=0;gene<4;++gene) {
        auto code=fragment_choice_policy(gene);
        HamsterParams p;p.op_order=5;p.layout.status_start=45;p.layout.output_start=50;
        p.layout.work_start=80;p.layout.program_start=140;p.stable_work_bits=20;
        p.layout.total_size=140+int(code.size())*6;
        Hamster h(gene,p);int at=140;
        for(int w:code)for(bool b:SpiralToken(w,5,1).bits)h.memory.at(at++)=b;
        for(int phase=0;phase<3;++phase) {
            Problem q;h.write_prob(q);
            h.memory[1]=phase>0;h.memory[2]=phase==2;
            h.pro_1=140;h.pro_2=at-1;h.step_limit=100;
            simulate_spiral_program(h);assert(!h.budget_exhausted);
            const auto r=read_fragment_request(h);
            assert(r.verb==(phase==2?1:2));
            assert(r.fragment==(phase?gene:0));
        }
    }
    std::cout<<"PASS four choice genes: first request, feedback choice, matching COMMIT\n";
}
