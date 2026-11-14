#include "../src/layered_vm_program.hpp"
#include "../src/layer_packet.hpp"
#include "../src/math_questions.hpp"
#include <iostream>

int main() {
    if(elementary_problem(ElementaryTask::Next,2,1).answer.value!=2||
       elementary_problem(ElementaryTask::Next,3,3).answer.value!=4)return 5;
    const auto code=layered_vm_program(-1);
    HamsterParams p;p.op_order=5;p.layout.status_start=45;p.layout.output_start=50;
    p.layout.work_start=80;p.layout.program_start=140;
    p.layout.total_size=p.layout.program_start+int(code.size())*6;
    int wrong=0,covered=0;
    for(int n:{2,3})for(int value=0;value<(1<<n)-1;++value) {
        const auto q=elementary_problem(ElementaryTask::Next,n,value);
        if(q.answer.value!=value+1||q.question[0].value!=2||
           q.answer.bits.back())return 1;
        Hamster h(0,p);int at=p.layout.program_start;
        for(int w:code)for(bool b:SpiralToken(w,5,1).bits)h.memory.at(at++)=b;
        h.write_prob(q);
        const auto bits=encode_layer_packet(2,2,value,n);
        for(size_t j=0;j<bits.size();++j)h.memory[p.layout.input_start+1+j]=bits[j];
        int pos=p.layout.work_start;
        for(int i=0;i<18;++i)h.memory[pos++]=1;
        h.memory[pos++]=0;
        for(int width:{2,n}) {
            for(int i=0;i<width;++i)h.memory[pos++]=1;
            h.memory[pos++]=0;
        }
        h.pro_1=p.layout.program_start;h.pro_2=at-1;h.step_limit=570;
        simulate_spiral_program(h);
        if(h.budget_exhausted||h.work_insert_blocked||
           !h.memory[p.layout.work_start-1])return 2;
        for(int j=0;j<n+1;++j)
            if(!h.written[p.layout.output_start+1+j])return 3;
        wrong+=!Check_ans(h,q);++covered;
    }
    bool overflow_rejected=false;
    try {(void)elementary_problem(ElementaryTask::Next,2,3);}
    catch(const std::invalid_argument&){overflow_rejected=true;}
    if(covered!=10||wrong!=10||!overflow_rejected)return 4;
    std::cout<<"PASS NEXT oracle 10 finite successor questions; existing layered VM"
                " parses all but answers 0/10 (COPY baseline)\n";
}
