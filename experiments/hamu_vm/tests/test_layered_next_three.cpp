#include "../src/layered_next_program.hpp"
#include "../src/layer_packet.hpp"
#include "../src/math_questions.hpp"
#include <iostream>

int main() {
    const auto code=layered_next_program(3);
    HamsterParams p;p.op_order=5;p.layout.status_start=45;p.layout.output_start=50;
    p.layout.work_start=80;p.layout.program_start=140;
    p.layout.total_size=p.layout.program_start+int(code.size())*6;
    Hamster h(0,p);int at=p.layout.program_start;
    for(int w:code)for(bool b:SpiralToken(w,5,1).bits)h.memory.at(at++)=b;
    int pos=p.layout.work_start;
    for(int i=0;i<18;++i)h.memory[pos++]=1;
    h.memory[pos++]=0;
    for(int width:{2,3}) {
        for(int j=0;j<width;++j)h.memory[pos++]=1;
        h.memory[pos++]=0;
    }
    int copy=0,flip=0,next=0;
    for(int value=0;value<8;++value)
      for(auto task:{ElementaryTask::Copy,ElementaryTask::Flip,ElementaryTask::Next}) {
        if(task==ElementaryTask::Next&&value==7)continue;
        const auto q=elementary_problem(task,3,value);
        const auto bits=encode_layer_packet(q.question[0].value,2,value,3);
        h.write_prob(q);
        for(size_t j=0;j<bits.size();++j)h.memory[p.layout.input_start+1+j]=bits[j];
        h.pro_1=p.layout.program_start;h.pro_2=at-1;h.step_limit=750;
        simulate_spiral_program(h);
        if(h.budget_exhausted||h.work_insert_blocked||
           !h.memory[p.layout.work_start-1]||!Check_ans(h,q)) {
            std::cerr<<"FAIL task="<<q.readable<<" steps="<<h.executed_steps<<'\n';
            return 1;
        }
        (task==ElementaryTask::Copy?copy:
         task==ElementaryTask::Flip?flip:next)++;
    }
    if(copy!=8||flip!=8||next!=7)return 2;
    std::cout<<"PASS one n3 layered VM dispatches COPY 8/8, FLIP 8/8,"
                " NEXT 7/7 including 011->100 carry\n";
}
