#include "../src/promoting_flip_program.hpp"
#include "../src/math_questions.hpp"
#include <iostream>

int main() {
    const auto code=promoting_flip_program();
    HamsterParams p;p.op_order=5;p.layout.total_size=p.layout.program_start+int(code.size())*6;
    Hamster h(0,p);int at=p.layout.program_start;
    for(int w:code)for(bool b:SpiralToken(w,5,1).bits)h.memory.at(at++)=b;
    const int marker[]={1,1,0,1,1,0,1,1,1,0};
    for(int j=0;j<10;++j)h.memory[p.layout.work_start+j]=marker[j];
    const auto q=elementary_problem_with_operator_order(ElementaryTask::Flip,3,3,5);
    put_started_question(h,q);
    h.memory[p.layout.program_start-1]=true; // live bit would be displaced
    const auto before=h.memory;
    h.pro_1=p.layout.program_start;h.pro_2=at-1;h.step_limit=220;
    simulate_spiral_program(h);
    if(!h.work_insert_blocked||!h.stop||h.budget_exhausted||h.memory!=before||
       h.written[p.layout.work_start+5]||h.written[p.layout.output_start+1]||
       Check_ans(h,q))return 1;
    h.memory[p.layout.program_start-1]=false; // capacity made available
    put_started_question(h,q);
    h.pro_1=p.layout.program_start;h.pro_2=at-1;h.step_limit=220;
    simulate_spiral_program(h);
    if(h.work_insert_blocked||h.budget_exhausted||!Check_ans(h,q)||
       !h.memory[p.layout.work_start+5])return 2;
    std::cout<<"PASS full growth rolls back work/output on blocked INSERT,"
                " retry with free capacity answers and promotes\n";
}
