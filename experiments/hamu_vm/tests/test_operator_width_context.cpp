#include "../src/flip_vm_program.hpp"
#include "../src/math_questions.hpp"
#include <iostream>

int main() {
    const auto code=flip_loop_program();
    HamsterParams p;p.op_order=5;p.layout.total_size=p.layout.program_start+int(code.size())*6;
    Hamster h(0,p);int at=p.layout.program_start;
    for(int word:code)for(bool b:SpiralToken(word,5,1).bits)h.memory.at(at++)=b;
    const int marker[]={1,1,0,1,1,1,0,1,1,1,0}; // startup 2, operator 3, data 3
    for(int j=0;j<11;++j)h.memory[p.layout.work_start+j]=marker[j];
    int copy_ok=0,flip_ok=0;
    for(int value=0;value<8;++value)
        for(auto task:{ElementaryTask::Copy,ElementaryTask::Flip}) {
            const auto q=elementary_problem_with_operator_order(task,3,3,value);
            put_started_question(h,q);
            h.pro_1=p.layout.program_start;h.pro_2=at-1;h.step_limit=160;
            simulate_spiral_program(h);
            if(h.budget_exhausted||!h.read_seen[p.layout.input_start+1+2+4]||
               !Check_ans(h,q)||h.memory[p.layout.work_start+10]) {
                std::cerr<<"FAIL task="<<(task==ElementaryTask::Copy?"COPY":"FLIP")
                         <<" value="<<value<<" steps="<<h.executed_steps<<"\n";return 1;
            }
            (task==ElementaryTask::Copy?copy_ok:flip_ok)++;
        }
    if(copy_ok!=8||flip_ok!=8)return 2;
    std::cout<<"PASS: supplied operator n=3 and data n=3, same VM program"
                " COPY 8/8 FLIP 8/8; data start follows expanded operator\n";
}
