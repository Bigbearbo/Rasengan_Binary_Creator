#include "../src/guest_fragment_request.hpp"
#include <cassert>
#include <iostream>

int main() {
    const auto code=fragment_sequential_policy();
    for(int winner=0;winner<4;++winner) {
        HamsterParams p;p.op_order=5;p.layout.status_start=45;p.layout.output_start=50;
        p.layout.work_start=80;p.layout.program_start=140;p.stable_work_bits=20;
        p.layout.total_size=140+int(code.size())*6;
        Hamster h(winner,p);int at=140;
        for(int word:code)for(bool bit:SpiralToken(word,5,1).bits)h.memory.at(at++)=bit;
        h.memory[125]=1;
        auto request=[&](bool feedback,bool passed) {
            Problem q;h.write_prob(q);
            h.memory[1]=feedback;h.memory[2]=passed;
            h.pro_1=140;h.pro_2=at-1;h.step_limit=100;
            simulate_spiral_program(h);assert(!h.budget_exhausted);
            assert(h.memory[125]);
            return read_fragment_request(h);
        };
        auto r=request(false,false);
        assert(r.verb==2&&r.fragment==0);
        for(int id=1;id<=winner;++id) {
            r=request(true,false);
            assert(r.verb==2&&r.fragment==id);
        }
        r=request(true,true);
        assert(r.verb==1&&r.fragment==winner);
        r=request(false,false); // New initial message retains the current choice.
        assert(r.verb==2&&r.fragment==winner);
        assert(h.memory[120]==bool(winner&2)&&h.memory[121]==bool(winner&1));
    }
    {
        HamsterParams p;p.op_order=5;p.layout.status_start=45;p.layout.output_start=50;
        p.layout.work_start=80;p.layout.program_start=140;p.stable_work_bits=20;
        p.layout.total_size=140+int(code.size())*6;
        Hamster h(10,p);int at=140;
        for(int word:code)for(bool bit:SpiralToken(word,5,1).bits)h.memory.at(at++)=bit;
        for(int turn=0;turn<7;++turn) {
            Problem q;h.write_prob(q);h.memory[1]=turn>0;h.memory[2]=0;
            h.pro_1=140;h.pro_2=at-1;h.step_limit=120;
            simulate_spiral_program(h);assert(!h.budget_exhausted);
            const auto r=read_fragment_request(h);
            assert(r.verb==(turn<4?2:0));
            if(turn<4)assert(r.fragment==turn);
            if(turn>=4)assert(h.memory[122]);
        }
    }
    std::cout<<"PASS sequential VM policy: all four winning positions, persistent state\n";
}
