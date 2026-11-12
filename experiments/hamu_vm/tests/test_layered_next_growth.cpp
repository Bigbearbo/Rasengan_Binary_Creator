#include "../src/layered_next_both.hpp"
#include "../src/layer_packet.hpp"
#include "../src/math_questions.hpp"
#include <iostream>

int main() {
    const auto code=layered_next_both_program();
    HamsterParams p;p.op_order=5;p.layout.status_start=45;p.layout.output_start=50;
    p.layout.work_start=80;p.layout.program_start=140;
    p.layout.total_size=p.layout.program_start+int(code.size())*6;
    Hamster h(0,p);int at=p.layout.program_start;
    for(int w:code)for(bool b:SpiralToken(w,5,1).bits)h.memory.at(at++)=b;
    int pos=p.layout.work_start;
    for(int i=0;i<18;++i)h.memory[pos++]=1;
    h.memory[pos++]=0;
    for(int word=0;word<2;++word) {
        h.memory[pos++]=1;h.memory[pos++]=1;h.memory[pos++]=0;
    }
    auto solve=[&](ElementaryTask task,int n,int value) {
        const auto q=elementary_problem_with_operator_order(task,2,n,value);
        const auto bits=encode_layer_packet(q.question[0].value,2,value,n);
        h.write_prob(q);
        for(size_t j=0;j<bits.size();++j)h.memory[p.layout.input_start+1+j]=bits[j];
        h.pro_1=p.layout.program_start;h.pro_2=at-1;h.step_limit=850;
        simulate_spiral_program(h);
        if(h.budget_exhausted||h.work_insert_blocked||
           !h.memory[p.layout.work_start-1]||!Check_ans(h,q)) {
            std::cerr<<"FAIL "<<q.readable<<" n="<<n
                     <<" steps="<<h.executed_steps<<" out=";
            for(int j=0;j<n+1;++j)std::cerr<<h.memory[p.layout.output_start+1+j];
            std::cerr<<'\n';return false;
        }
        return true;
    };
    for(int value=0;value<4;++value)
        for(auto task:{ElementaryTask::Copy,ElementaryTask::Flip,ElementaryTask::Next}) {
            if(task==ElementaryTask::Next&&value==3)continue;
            if(!solve(task,2,value))return 1;
        }
    if(h.memory[p.layout.work_start+19+3+2])return 2;
    if(!solve(ElementaryTask::Copy,3,1))return 3; // first data promotion
    if(!h.memory[p.layout.work_start+19+3+2])return 4;
    h.new_his();Hamster child(1,p);child.copy_hamu(h);h=std::move(child);
    if(!h.memory[p.layout.work_start+19+3+2])return 6;
    for(int value=0;value<8;++value)
        for(auto task:{ElementaryTask::Copy,ElementaryTask::Flip,ElementaryTask::Next}) {
            if(task==ElementaryTask::Next&&value==7)continue;
            if(!solve(task,3,value))return 5;
        }
    std::cout<<"PASS one VM and its child: old COPY/FLIP/NEXT 11/11, data n2->3"
                " trigger, new COPY/FLIP/NEXT 23/23 including 011->100\n";
}
