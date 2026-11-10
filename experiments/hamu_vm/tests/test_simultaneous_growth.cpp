#include "../src/promoting_flip_program.hpp"
#include "../src/math_questions.hpp"
#include <iostream>

int main() {
    const auto code=promoting_flip_program();
    HamsterParams p;p.op_order=5;p.layout.total_size=p.layout.program_start+int(code.size())*6;
    Hamster h(0,p);int at=p.layout.program_start;
    for(int word:code)for(bool b:SpiralToken(word,5,1).bits)h.memory.at(at++)=b;
    for(int j=0;j<9;++j)h.memory[p.layout.work_start+j]=(j%3!=2); // 110 110 110
    auto solve=[&](ElementaryTask task,int op_n,int data_n,int value) {
        const auto q=elementary_problem_with_operator_order(task,op_n,data_n,value);
        put_started_question(h,q);
        h.pro_1=p.layout.program_start;h.pro_2=at-1;h.step_limit=220;
        simulate_spiral_program(h);
        if(h.budget_exhausted||!Check_ans(h,q)) {
            std::cerr<<"FAIL task="<<(task==ElementaryTask::Copy?"COPY":"FLIP")
                     <<" op="<<op_n<<" data="<<data_n<<" value="<<value
                     <<" steps="<<h.executed_steps<<" work=";
            for(int j=0;j<11;++j)std::cerr<<h.memory[p.layout.work_start+j];
            std::cerr<<" output=";
            for(int j=0;j<8;++j)std::cerr<<h.memory[p.layout.output_start+1+j];
            std::cerr<<" expected=";
            for(bool b:q.answer.bits)std::cerr<<b;
            std::cerr<<'\n';return false;
        }
        return true;
    };
    for(int value=0;value<4;++value)
        for(auto task:{ElementaryTask::Copy,ElementaryTask::Flip})
            if(!solve(task,2,2,value))return 1;
    if(h.memory[p.layout.work_start+8])return 2;
    // Both old tail positions turn to one in the same question.
    if(!solve(ElementaryTask::Flip,3,3,1))return 3;
    const int grown[]={1,1,0,1,1,1,0,1,1,1,0};
    for(int j=0;j<11;++j)if(h.memory[p.layout.work_start+j]!=grown[j])return 4;
    if(!h.written[p.layout.work_start+5]||!h.written[p.layout.work_start+6]||
       !h.written[p.layout.work_start+9])return 5;
    for(int value=0;value<8;++value)
        for(auto task:{ElementaryTask::Copy,ElementaryTask::Flip}) {
            if(!solve(task,3,3,value))return 6;
            if(h.written[p.layout.work_start+5]||h.written[p.layout.work_start+9])return 7;
        }
    h.new_his();Hamster child(1,p);child.copy_hamu(h);h=std::move(child);
    if(!solve(ElementaryTask::Flip,3,3,6))return 8;
    for(int j=0;j<11;++j)if(h.memory[p.layout.work_start+j]!=grown[j])return 9;
    std::cout<<"PASS same VM: old 8/8, both positions promote in one FLIP,"
                " final 16/16, child inherits both\n";
}
