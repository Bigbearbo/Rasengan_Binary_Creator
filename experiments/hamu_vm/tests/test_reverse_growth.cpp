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
            std::cerr<<'\n';return false;
        }
        return true;
    };
    for(int value=0;value<4;++value)
        for(auto task:{ElementaryTask::Copy,ElementaryTask::Flip})
            if(!solve(task,2,2,value))return 1;
    if(h.memory[p.layout.work_start+8])return 2;
    // First operator n=3 word must carry one at the old tail position.
    if(!solve(ElementaryTask::Flip,3,2,1))return 3;
    const int intermediate[]={1,1,0,1,1,1,0,1,1,0}; // 110 1110 110
    for(int j=0;j<10;++j)if(h.memory[p.layout.work_start+j]!=intermediate[j])return 4;
    if(!h.written[p.layout.work_start+5]||!h.written[p.layout.work_start+6])return 5;
    for(int value=0;value<4;++value)
        for(auto task:{ElementaryTask::Copy,ElementaryTask::Flip})
            if(!solve(task,3,2,value))return 6;
    // The data marker has moved; its own old tail now sits at work_start+9.
    if(!solve(ElementaryTask::Copy,3,3,1))return 7;
    const int grown[]={1,1,0,1,1,1,0,1,1,1,0};
    for(int j=0;j<11;++j)if(h.memory[p.layout.work_start+j]!=grown[j])return 8;
    if(!h.written[p.layout.work_start+9]||h.written[p.layout.work_start+5])return 9;
    for(int value=0;value<8;++value)
        for(auto task:{ElementaryTask::Copy,ElementaryTask::Flip}) {
            if(!solve(task,3,3,value))return 10;
            if(h.written[p.layout.work_start+5]||h.written[p.layout.work_start+9])return 11;
        }
    h.new_his();Hamster child(1,p);child.copy_hamu(h);h=std::move(child);
    if(!solve(ElementaryTask::Flip,3,3,6))return 12;
    for(int j=0;j<11;++j)if(h.memory[p.layout.work_start+j]!=grown[j])return 13;
    std::cout<<"PASS same VM: old 8/8, operator promotion 1/1, intermediate 8/8,"
                " data promotion at shifted position 1/1, final 16/16, child inherits both\n";
}
