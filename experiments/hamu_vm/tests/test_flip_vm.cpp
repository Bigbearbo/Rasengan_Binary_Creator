#include "../src/math_questions.hpp"
#include "../src/task_upgrade.hpp"
#include "../src/flip_vm_program.hpp"
#include <iostream>

int main() {
    const auto code=flip_loop_program();
    HamsterParams p;p.op_order=5;p.layout.total_size=p.layout.program_start+int(code.size())*6;
    Hamster h(0,p);int at=p.layout.program_start;
    for(int word:code)for(bool b:SpiralToken(word,5,1).bits)h.memory.at(at++)=b;
    for(int j=0;j<9;++j)h.memory[p.layout.work_start+j]=(j%3!=2);
    auto solve=[&](const Problem& q) {
        put_started_question(h,q);
        h.pro_1=p.layout.program_start;h.pro_2=at-1;h.step_limit=130;
        simulate_spiral_program(h);
        if(h.budget_exhausted)throw std::runtime_error("VM step budget exhausted");
        return Check_ans(h,q);
    };
    int old_copy=0,trigger_copy=0,new_copy=0,new_flip=0;
    CopyUpgradeCurriculum teacher(4,6);
    for(int i=0;i<4;++i)old_copy+=solve(teacher.next());
    if(h.memory[p.layout.work_start+8])return 2;
    for(int i=0;i<6;++i)trigger_copy+=solve(teacher.next());
    if(!h.memory[p.layout.work_start+8])return 3;
    for(int value=0;value<8;++value)
        new_copy+=solve(elementary_problem(ElementaryTask::Copy,3,value));
    for(int value=0;value<8;++value) {
        const auto q=elementary_problem(ElementaryTask::Flip,3,value);
        if(q.question[1].order!=3 || q.answer.order!=3 ||
           q.answer.value!=7-value || q.question[0].bits!=SpiralToken(1,2,1).bits)
            return 5;
        new_flip+=solve(q);
    }
    int alternating_copy=0,alternating_flip=0;
    for(int value=0;value<8;++value) {
        alternating_flip+=solve(elementary_problem(ElementaryTask::Flip,3,value));
        alternating_copy+=solve(elementary_problem(ElementaryTask::Copy,3,value));
    }
    bool range_rejected=false;
    try {(void)elementary_problem(ElementaryTask::Flip,2,4);}
    catch(const std::invalid_argument&) {range_rejected=true;}
    if(old_copy!=4||trigger_copy!=6||new_copy!=8||new_flip!=8||
       alternating_copy!=8||alternating_flip!=8||!range_rejected)return 4;
    std::cout<<"PASS staged VM program: COPY n2="<<old_copy<<"/4 triggers="<<trigger_copy
             <<"/6 stable_n3="<<new_copy<<"/8; then FLIP n3="<<new_flip
             <<"/8; alternating FLIP/COPY="<<alternating_flip<<"/8,"
             <<alternating_copy<<"/8; no n2 questions after promotion\n";
}
