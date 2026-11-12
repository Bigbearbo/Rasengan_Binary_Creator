#include "../src/math_questions.hpp"
#include <array>
#include <iostream>

// VM microprogram: branch on the old operator tail bit, read the new zero
// tail, overwrite unary 0 with 1, then INSERT a 0 before the data marker.
static constexpr std::array<int,28> code={
    0,0,14,21,4,1,16,1,18,20,15,0,
    0,0,14,22,4,1,0,3,14,21,2,1,10,1,15,0
};

static bool run(int operator_order) {
    HamsterParams p;p.op_order=5;p.layout.total_size=p.layout.program_start+28*6;
    Hamster h(0,p);int at=p.layout.program_start;
    for(int word:code)for(bool b:SpiralToken(word,5,1).bits)h.memory.at(at++)=b;
    const int marker[]={1,1,0,1,1,0,1,1,1,0}; // 110 110 1110
    for(int j=0;j<10;++j)h.memory[p.layout.work_start+j]=marker[j];
    const auto q=elementary_problem_with_operator_order(ElementaryTask::Flip,operator_order,3,5);
    put_started_question(h,q);
    h.pro_1=p.layout.program_start;h.pro_2=at-1;h.step_limit=40;
    simulate_spiral_program(h);
    const int input=p.layout.input_start+1;
    if(h.budget_exhausted||!h.read_seen[input+2+2])return false;
    if(operator_order==2) {
        for(int j=0;j<10;++j)if(h.memory[p.layout.work_start+j]!=marker[j])return false;
        return !h.written[p.layout.work_start+5];
    }
    const int promoted[]={1,1,0,1,1,1,0,1,1,1,0}; // 110 1110 1110
    for(int j=0;j<11;++j)if(h.memory[p.layout.work_start+j]!=promoted[j])return false;
    return h.read_seen[input+2+3] && h.written[p.layout.work_start+5] &&
           h.written[p.layout.work_start+6];
}

int main() {
    if(!run(2)||!run(3))return 1;
    std::cout<<"PASS: VM detects first operator n2->n3 trigger, inserts unary"
                " zero and shifts data-length record; old operator unchanged\n";
}
