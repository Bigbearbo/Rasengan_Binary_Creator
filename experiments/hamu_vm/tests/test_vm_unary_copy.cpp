#include "../src/task_upgrade.hpp"
#include <array>
#include <iostream>

// A real VM program: unary marker controls the number of READ 1/WRITE_VAL 1
// iterations. It appends the fixed zero tail after the marker terminates.
static constexpr std::array<int,50> code={
    0,0, 14,22, 19,0, 0,2, 14,17, 21,0, 0,3, 14,26, 16,1,
    4,1, 18,26, 21,0, 3,1, 15,0, 16,31,
    14,17, 19,0, 4,1, 21,0, 9,1, 14,17,
    21,0, 14,17, 19,0, 22,30
};

int main() {
    HamsterParams p;p.op_order=5;p.layout.total_size=p.layout.program_start+50*6;
    Hamster h(0,p);
    int at=p.layout.program_start;
    for(int word:code)for(bool b:SpiralToken(word,5,1).bits)h.memory.at(at++)=b;
    for(int n:{2,3})for(int value=0;value<(1<<n);++value) {
        Problem q;q.type=ProblemType::EAZY;
        q.question={SpiralToken(0,2,1),SpiralToken(value,n,1)};
        q.answer=SpiralToken(value,n,1);
        h.write_prob(q);
        const int payload=p.layout.input_start+1;
        const int count=3+int(q.question[1].bits.size());
        for(int j=count-1;j>=0;--j)h.memory.at(payload+j+2)=h.memory.at(payload+j);
        h.memory.at(payload)=0;h.memory.at(payload+1)=1;
        for(int j=0;j<5;++j)h.memory.at(p.layout.work_start+10+j)=j<n;
        h.pro_1=p.layout.program_start;h.pro_2=at-1;h.step_limit=100;
        simulate_spiral_program(h);
        if(!Check_ans(h,q)||h.budget_exhausted||h.ptr!=p.layout.output_start+2+n) {
            std::cerr<<"FAIL n="<<n<<" value="<<value<<" steps="<<h.executed_steps
                     <<" output_ptr="<<h.output_ptr<<" ptr="<<h.ptr<<" secondary="<<h.secondary_ptr<<"\n";
            for(int j=0;j<5;++j)std::cerr<<h.memory[p.layout.output_start+1+j]
                <<"/"<<h.written[p.layout.output_start+1+j]<<" ";
            std::cerr<<"\n";return 1;
        }
        for(int j=0;j<n;++j)if(!h.read_seen[payload+2+3+j])return 2;
    }
    std::cout<<"PASS: VM unary COPY loop reads/writes each bit for n=2 and n=3\n";
}
