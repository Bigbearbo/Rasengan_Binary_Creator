#include "../src/task_upgrade.hpp"
#include <array>
#include <iostream>

// VM COPY loop. Its zero-tail branch promotes the unary marker in work memory
// when the old tail position carries 1, then copies the new zero tail.
static constexpr std::array<int,78> code={
    0,0, 14,22, 19,0, 0,2, 14,17, 21,0, 0,3, 14,26, 16,1,
    4,1, 24,19, 19,0, 4,1, 18,24, 21,0, 3,1, 15,0,
    19,0, 2,1, 19,0, 21,0, 9,1, 14,17, 21,0, 14,17,
    4,1, 21,0, 9,1, 15,0,
    14,17, 19,0, 4,1, 21,0, 9,1, 14,17,
    21,0, 14,17, 19,0, 23,29
};

int main() {
    HamsterParams p;p.op_order=5;p.layout.total_size=p.layout.program_start+78*6;
    Hamster h(0,p);
    int at=p.layout.program_start;
    for(int word:code)for(bool b:SpiralToken(word,5,1).bits)h.memory.at(at++)=b;
    h.memory.at(p.layout.work_start+10)=1;
    h.memory.at(p.layout.work_start+11)=1;
    h.memory.at(p.layout.work_start+12)=0;
    CopyUpgradeCurriculum teacher(4,6);
    int changed=0,even_stable=0;
    for(int i=0;i<26;++i) {
        Problem q=teacher.next();h.write_prob(q);
        const int payload=p.layout.input_start+1;
        const int count=3+int(q.question[1].bits.size());
        for(int j=count-1;j>=0;--j)h.memory.at(payload+j+2)=h.memory.at(payload+j);
        h.memory.at(payload)=0;h.memory.at(payload+1)=1;
        const bool before=h.memory[p.layout.work_start+12];
        h.pro_1=p.layout.program_start;h.pro_2=at-1;h.step_limit=100;
        simulate_spiral_program(h);
        const bool after=h.memory[p.layout.work_start+12];
        changed+=before!=after;
        if(i>=10 && !h.memory[payload+2+3+2])++even_stable;
        if(!Check_ans(h,q)||h.budget_exhausted||after!=(i>=4)||
           h.written[p.layout.work_start+12]!=(i==4)) {
            std::cerr<<"FAIL question="<<i<<" value="<<q.question[1].value
                     <<" changed="<<changed<<" marker="<<after
                     <<" steps="<<h.executed_steps<<"\n";return 1;
        }
        if(i==10) {
            h.new_his();Hamster child(1,p);child.copy_hamu(h);
            if(!child.memory[p.layout.work_start+12])return 2;
            h=std::move(child);
        }
    }
    if(changed!=1||even_stable==0)return 3;
    std::cout<<"PASS: VM bit loop promotes unary 110 to 1110 once;"
                " 4 old, 6 trigger, 16 stable COPY; inherited marker\n";
}
