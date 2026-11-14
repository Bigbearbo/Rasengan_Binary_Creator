#include "../src/layered_next_program.hpp"
#include "../src/layer_packet.hpp"
#include "../src/math_questions.hpp"
#include <iostream>

int main() {
    const auto code=layered_next_program();
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
    int copy=0,flip=0,next=0;
    for(int value=0;value<4;++value)
      for(auto task:{ElementaryTask::Copy,ElementaryTask::Flip,ElementaryTask::Next}) {
        if(task==ElementaryTask::Next&&value==3)continue;
        const auto q=elementary_problem(task,2,value);
        const auto bits=encode_layer_packet(q.question[0].value,2,value,2);
        h.write_prob(q);
        for(size_t j=0;j<bits.size();++j)h.memory[p.layout.input_start+1+j]=bits[j];
        h.pro_1=p.layout.program_start;h.pro_2=at-1;h.step_limit=700;
        simulate_spiral_program(h);
        if(h.budget_exhausted||h.work_insert_blocked||
           !h.memory[p.layout.work_start-1]||!Check_ans(h,q)) {
            std::cerr<<"FAIL task="<<q.readable<<" steps="<<h.executed_steps<<'\n';
            return 1;
        }
        (task==ElementaryTask::Copy?copy:
         task==ElementaryTask::Flip?flip:next)++;
    }
    if(copy!=4||flip!=4||next!=3)return 2;
    std::cout<<"PASS same layered VM dispatches COPY 4/4, FLIP 4/4,"
                " NEXT 3/3 including carry\n";
}
