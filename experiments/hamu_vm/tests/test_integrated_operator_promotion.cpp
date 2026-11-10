#include "../src/promoting_flip_program.hpp"
#include "../src/math_questions.hpp"
#include <iostream>

int main() {
    const auto code=promoting_flip_program();
    HamsterParams p;p.op_order=5;
    p.layout.total_size=p.layout.program_start+int(code.size())*6;
    Hamster h(0,p);int at=p.layout.program_start;
    for(int word:code)for(bool b:SpiralToken(word,5,1).bits)h.memory.at(at++)=b;
    const int marker[]={1,1,0,1,1,0,1,1,1,0}; // startup 2, operator 2, data 3
    for(int j=0;j<10;++j)h.memory[p.layout.work_start+j]=marker[j];
    auto solve=[&](ElementaryTask task,int op_n,int data_n,int value) {
        const auto q=elementary_problem_with_operator_order(task,op_n,data_n,value);
        put_started_question(h,q);
        h.pro_1=p.layout.program_start;h.pro_2=at-1;h.step_limit=200;
        simulate_spiral_program(h);
        if(h.budget_exhausted || !Check_ans(h,q)) {
            std::cerr<<"FAIL op="<<op_n<<" data="<<data_n<<" task="
                     <<(task==ElementaryTask::Copy?"COPY":"FLIP")<<" value="<<value
                     <<" steps="<<h.executed_steps<<" ptr="<<h.ptr<<"\n";
            return false;
        }
        return true;
    };
    for(int value=0;value<8;++value)
        for(auto task:{ElementaryTask::Copy,ElementaryTask::Flip})
            if(!solve(task,2,3,value))return 1;
    if(h.memory[p.layout.work_start+5])return 2;
    // The first new operator must change the *old tail* from 0 to 1.
    if(!solve(ElementaryTask::Flip,3,3,5))return 3;
    const int input=p.layout.input_start+1;
    if(!h.read_seen[input+2+2]||!h.read_seen[input+2+3])return 10;
    const int grown[]={1,1,0,1,1,1,0,1,1,1,0};
    for(int j=0;j<11;++j)if(h.memory[p.layout.work_start+j]!=grown[j])return 4;
    if(!h.written[p.layout.work_start+5]||!h.written[p.layout.work_start+6])return 5;
    // Following questions have no lower-order operator and cannot repromote.
    for(int value=0;value<8;++value)
        for(auto task:{ElementaryTask::Copy,ElementaryTask::Flip}) {
            if(!solve(task,3,3,value))return 6;
            if(h.memory[p.layout.work_start+5]!=1||
               h.written[p.layout.work_start+5]||
               h.memory[p.layout.work_start+10])return 7;
        }
    h.new_his();Hamster child(1,p);child.copy_hamu(h);
    if(!child.memory[p.layout.work_start+5]||!child.memory[p.layout.work_start+9]||
       child.memory[p.layout.work_start+10])return 8;
    h=std::move(child);
    if(!solve(ElementaryTask::Flip,3,3,6))return 9;
    std::cout<<"PASS integrated VM: old COPY/FLIP 16/16, first operator trigger"
                " answers FLIP and grows marker, later n3 COPY/FLIP 16/16, child inherits\n";
}
