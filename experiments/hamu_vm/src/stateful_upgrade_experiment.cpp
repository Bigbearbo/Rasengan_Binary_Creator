#include "task_upgrade.hpp"
#include <array>
#include <iostream>

// Controlled program: read the old tail, retain its OR in work[0], then
// route to the 3-bit or 4-bit COPY routine. No host version tag is supplied.
static constexpr std::array<int,42> program={
    0,0, 14,22, 4,1, 0,3, 7,1, 4,1, 8,17,
    0,0, 14,20, 4,4, 0,2, 14,17, 8,1, 16,1, 18,24,
    8,17, 9,3, 15,0,
    8,17, 9,4, 15,0
};

int main() {
    HamsterParams p;p.op_order=5;
    p.layout.total_size=p.layout.program_start+44*6;
    Hamster h(0,p);
    const int start=p.layout.program_start;
    int at=start;
    for(int code:program)for(bool bit:SpiralToken(code,5,1).bits)h.memory.at(at++)=bit;
    h.pro_1=start;h.pro_2=at-1;
    h.step_limit=40;
    CopyUpgradeCurriculum teacher(4,6);
    for(int i=0;i<26;++i) {
        const auto q=teacher.next();
        h.write_prob(q);
        h.pro_1=start;h.pro_2=at-1;
        simulate_spiral_program(h);
        const bool learned=h.memory[p.layout.work_start];
        const bool expected=i>=4;
        const bool pass=Check_ans(h,q);
        const int tail=p.layout.input_start+1+3+2;
        if(learned!=expected||!pass||!h.read_seen[tail]||h.budget_exhausted) {
            std::cerr<<"FAIL question="<<i<<" value="<<q.question[1].value
                     <<" learned="<<learned<<" expected="<<expected
                     <<" pass="<<pass<<" steps="<<h.executed_steps<<"\n";
            for(int j=0;j<5;++j)std::cerr<<"out"<<j<<"="<<h.memory[p.layout.output_start+1+j]
                <<" written="<<h.written[p.layout.output_start+1+j]<<" ";
            std::cerr<<"\n";
            return 1;
        }
        if(i==10) {
            // Carry the stored work bit through the existing inheritance API.
            h.new_his();
            Hamster child(1,p);child.copy_hamu(h);
            if(!child.memory[p.layout.work_start])return 2;
            h=std::move(child);
        }
    }
    std::cout<<"PASS: 4 old, 6 triggers, 16 stable n=3; VM work bit persists"
                " across questions and inheritance; all COPY answers correct\n";
}
