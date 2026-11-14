#include "../src/splice_operator.hpp"
#include "../src/flip_vm_program.hpp"
#include "../src/math_questions.hpp"
#include "../src/task_upgrade.hpp"
#include <iostream>

int main() {
    const auto old=copy_loop_program(),grown=splice_operator_from_copy();
    auto target=flip_loop_program();
    if(grown.size()!=old.size()+8||grown.size()!=target.size())return 1;
    int differences=0;
    for(size_t i=0;i<grown.size();++i)if(grown[i]!=target[i]) {
        if(grown[i]!=16 || (target[i]!=4 && target[i]!=25)) {
            std::cerr<<"unexpected difference at "<<i<<": "<<grown[i]<<" vs "<<target[i]<<"\n";
            return 2;
        }
        ++differences;
    }
    if(differences!=2)return 3;
    HamsterParams p;p.op_order=5;
    p.layout.total_size=p.layout.program_start+int(old.size())*6;
    Hamster donor(0,p);
    if(donor.memory.size()>=size_t(p.layout.program_start+int(grown.size())*6))return 4;
    donor.extend_program_capacity(8);
    int at=p.layout.program_start;
    for(int word:grown)for(bool b:SpiralToken(word,5,1).bits)donor.memory.at(at++)=b;
    for(int j=0;j<9;++j)donor.memory[p.layout.work_start+j]=(j%3!=2);
    donor.new_his();
    Hamster h(1,p);h.copy_hamu(donor);
    CopyUpgradeCurriculum teacher(4,6);
    int old_ok=0,trigger_ok=0,copy_ok=0,flip_ok=0;
    auto solve=[&](const Problem& q) {
        put_started_question(h,q);
        h.pro_1=p.layout.program_start;h.pro_2=at-1;h.step_limit=160;
        simulate_spiral_program(h);
        return !h.budget_exhausted&&Check_ans(h,q);
    };
    for(int i=0;i<4;++i)old_ok+=solve(teacher.next());
    for(int i=0;i<6;++i)trigger_ok+=solve(teacher.next());
    for(int v=0;v<8;++v)copy_ok+=solve(elementary_problem(ElementaryTask::Copy,3,v));
    for(int v=0;v<8;++v)flip_ok+=solve(elementary_problem(ElementaryTask::Flip,3,v));
    if(old_ok!=4||trigger_ok!=6||copy_ok!=8||flip_ok!=0||
       !h.memory[p.layout.work_start+8])return 5;
    std::cout<<"PASS: splice 118->126 aligned words; inherited expanded program"
                " preserves COPY 4/4,6/6,8/8 and waits for two FLIP mutations\n";
}
