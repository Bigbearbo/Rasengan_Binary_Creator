#include "integrated_zero_program.hpp"
#include "layer_packet.hpp"
#include "math_questions.hpp"
#include <iostream>
#include <random>

struct Result {int old=0,zero=0;};
static Result evaluate_program(const IntegratedZero& g,bool verify_old=true) {
    if(g.mutation_pair<g.reserve_start||
       g.mutation_pair>=g.reserve_start+g.reserve_pairs)
        throw std::logic_error("ZERO gene outside reserved window");
    HamsterParams p;p.op_order=5;p.layout.status_start=45;p.layout.output_start=50;
    p.layout.work_start=80;p.layout.program_start=140;
    p.layout.total_size=p.layout.program_start+int(g.words.size())*6;
    Hamster h(0,p);int at=p.layout.program_start;
    for(int w:g.words)for(bool b:SpiralToken(w,5,1).bits)h.memory.at(at++)=b;
    int pos=p.layout.work_start;
    for(int i=0;i<18;++i)h.memory[pos++]=1;
    h.memory[pos++]=0;
    for(int word=0;word<2;++word)
        for(bool bit:{true,true,true,false})h.memory[pos++]=bit;
    auto run=[&](int op,ElementaryTask task,int v,bool zero) {
        auto q=elementary_problem_with_operator_order(task,3,3,v);
        q.question[0]=SpiralToken(op,3,1);
        if(zero){q.answer=SpiralToken(0,3,1);q.readable="ZERO "+std::to_string(v);}
        const auto bits=encode_layer_packet(op,3,v,3);
        h.write_prob(q);
        for(size_t j=0;j<bits.size();++j)h.memory[p.layout.input_start+1+j]=bits[j];
        h.pro_1=p.layout.program_start;h.pro_2=at-1;h.step_limit=900;
        simulate_spiral_program(h);
        return !h.budget_exhausted&&!h.work_insert_blocked&&
               h.memory[p.layout.work_start-1]&&Check_ans(h,q);
    };
    Result r;
    for(int v=0;v<8;++v) {
        if(verify_old) {
            r.old+=run(0,ElementaryTask::Copy,v,false);
            r.old+=run(1,ElementaryTask::Flip,v,false);
            if(v<7)r.old+=run(2,ElementaryTask::Next,v,false);
        }
        r.zero+=run(3,ElementaryTask::Copy,v,true);
    }
    return r;
}

static Result evaluate(int opcode,bool verify_old=true,int write_count=4) {
    return evaluate_program(integrated_zero_program(opcode,write_count),verify_old);
}

#ifndef INTEGRATED_ZERO_NO_MAIN
int main() {
    const auto before=evaluate(2);
    std::cerr<<"baseline old="<<before.old<<" ZERO="<<before.zero<<'\n';
    if(before.old!=23||before.zero!=0)return 1;
    std::mt19937 rng(67);
    int best=2,attempts=0;
    for(;attempts<50;++attempts) {
        const int mutated=best^(1<<int(rng()%5));
        if(mutated>26)continue;
        const auto quick=evaluate(mutated,false);
        if(quick.zero==8) {
            const auto s=evaluate(mutated);
            if(s.old!=23||s.zero!=8)return 3;
            std::cout<<"PASS integrated VM: old=23/23 ZERO="<<s.zero
                     <<"/8 mutation="<<best<<"->"<<mutated
                     <<" attempt="<<attempts+1<<" reserved_pairs=64"
                     <<" mutation_pair="<<integrated_zero_program(mutated).mutation_pair<<"\n";
            return 0;
        }
    }
    std::cerr<<"FAIL integrated search\n";return 2;
}
#endif
