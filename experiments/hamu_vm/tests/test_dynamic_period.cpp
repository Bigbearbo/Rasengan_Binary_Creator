#include "../src/layered_vm_program.hpp"
#include "../src/layer_packet.hpp"
#include "../src/math_questions.hpp"
#include <iostream>

int main() {
    const auto code=layered_vm_program(-1);
    HamsterParams p;p.op_order=5;p.layout.status_start=45;p.layout.output_start=50;
    p.layout.work_start=80;p.layout.program_start=140;
    p.layout.total_size=p.layout.program_start+int(code.size())*6;
    auto run=[&](ElementaryTask task,int op_n,int data_n,int value,bool changed_end) {
        Hamster h(0,p);int at=p.layout.program_start;
        for(int w:code)for(bool b:SpiralToken(w,5,1).bits)h.memory.at(at++)=b;
        const int op=task==ElementaryTask::Copy?0:1;
        const auto q=elementary_problem_with_operator_order(task,op_n,data_n,value);
        h.write_prob(q);
        auto bits=encode_layer_packet(op,op_n,value,data_n);
        if(changed_end) {
            const auto other=SpiralToken(14,4,1).bits; // known L1 PREV word
            for(int j=0;j<5;++j)bits[bits.size()-5+j]=other[j];
        }
        for(size_t j=0;j<bits.size();++j)h.memory[p.layout.input_start+1+j]=bits[j];
        int pos=p.layout.work_start;
        for(int j=0;j<18;++j)h.memory[pos++]=1;
        h.memory[pos++]=0;
        for(int n:{op_n,data_n}) {
            for(int j=0;j<n;++j)h.memory[pos++]=1;
            h.memory[pos++]=0;
        }
        h.memory[p.layout.work_start-1]=true; // stale prior success must be cleared
        h.pro_1=p.layout.program_start;h.pro_2=at-1;h.step_limit=570;
        simulate_spiral_program(h);
        if(h.budget_exhausted||h.work_insert_blocked)return false;
        const bool accepted=!changed_end;
        if(h.memory[p.layout.work_start-1]!=accepted)return false;
        if(Check_ans(h,q)!=accepted)return false;
        if(!accepted && h.written[p.layout.output_start+1])return false;
        if(accepted)for(int j=0;j<18;++j)
            if(!h.read_seen[p.layout.input_start+1+j])return false;
        if(accepted)for(int j=0;j<5;++j)
            if(!h.read_seen[p.layout.input_start+1+int(bits.size())-5+j])return false;
        return true;
    };
    int accepted=0,rejected=0;
    for(int op_n:{2,3})for(int data_n:{2,3})
      for(int v=0;v<(1<<data_n);++v)
        for(auto task:{ElementaryTask::Copy,ElementaryTask::Flip}) {
            if(!run(task,op_n,data_n,v,false))return 1;
            ++accepted;
            if(!run(task,op_n,data_n,v,true))return 2;
            ++rejected;
        }
    std::cout<<"PASS one VM program finds period via mixed unary lengths: "
             <<accepted<<" answers; valid L1 replacement blocks "<<rejected<<"\n";
}
