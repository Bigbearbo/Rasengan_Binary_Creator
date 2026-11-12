#include "guest_fragment_request.hpp"
#include "single_entry_program.hpp"
#include "fragment_transaction.hpp"
#include "layer_packet.hpp"
#include "math_questions.hpp"
#include <iostream>

int main() {
    auto genome=single_entry_program(15);
    const auto original=genome.words;
    HamsterParams p;p.op_order=5;p.layout.status_start=45;p.layout.output_start=50;
    p.layout.work_start=80;p.layout.program_start=140;
    p.stable_work_bits=20; // [120,140) survives work-region insertion/deletion
    const int control_start=p.layout.program_start+int(genome.words.size())*6;
    p.layout.total_size=control_start;
    Hamster h(42,p);int at=p.layout.program_start;
    for(int w:genome.words)for(bool bit:SpiralToken(w,5,1).bits)h.memory.at(at++)=bit;
    int pos=p.layout.work_start;
    for(int i=0;i<18;++i)h.memory[pos++]=1;
    h.memory[pos++]=0;
    for(int word=0;word<2;++word)
        for(bool bit:{true,true,false})h.memory[pos++]=bit;
    h.memory[p.layout.work_start+45]=1; // persistent-state canary
    auto sync_slot=[&]() {
        int target=p.layout.program_start+genome.reserve_start*12;
        for(int i=2*genome.reserve_start;i<2*(genome.reserve_start+16);++i)
            for(bool bit:SpiralToken(genome.words[i],5,1).bits)h.memory.at(target++)=bit;
    };
    auto request=[&](bool feedback,bool passed) {
        Problem q;h.write_prob(q);
        h.memory[p.layout.input_start+1]=feedback;
        h.memory[p.layout.input_start+2]=passed;
        h.memory[p.layout.input_start+44]=1;
        h.pro_1=p.layout.program_start;h.pro_2=p.layout.total_size-1;h.step_limit=120;
        simulate_spiral_program(h);
        if(h.budget_exhausted)throw std::runtime_error("control budget");
        return read_fragment_request(h);
    };
    auto solve=[&](int op,int value,int op_n=3,int data_n=3) {
        auto task=op==1?ElementaryTask::Flip:op==2?ElementaryTask::Next:ElementaryTask::Copy;
        auto q=elementary_problem_with_operator_order(task,op_n,data_n,value);
        q.question[0]=SpiralToken(op,op_n,1);
        if(op==3)q.answer=SpiralToken(0,3,1);
        const auto bits=encode_layer_packet(op,op_n,value,data_n);
        h.write_prob(q);
        for(size_t j=0;j<bits.size();++j)h.memory[p.layout.input_start+1+j]=bits[j];
        h.pro_1=p.layout.program_start;h.pro_2=p.layout.total_size-1;h.step_limit=900;
        simulate_spiral_program(h);
        return !h.budget_exhausted&&!h.work_insert_blocked&&Check_ans(h,q);
    };
    if(!solve(0,2,2,2)||!solve(0,1,2,3)||!solve(1,5,3,3))return 9;
    if(!h.memory[p.layout.work_start+45]||h.memory[p.layout.work_start+40])return 10;
    const std::vector<std::vector<int>> library={
        {0,2,14,17,2,4,15,0},{0,2,14,17,3,4,15,0}};
    auto first=request(false,false);
    if(first.verb!=2||first.fragment!=0)return 1;
    {
        FragmentTransaction trial(genome,library.at(first.fragment));sync_slot();
        for(int v=0;v<8;++v)if(solve(3,v))return 2;
    }
    sync_slot();
    if(genome.words!=original)return 3;
    auto second=request(true,false);
    if(second.verb!=2||second.fragment!=1)return 4;
    std::cout<<"resident hamster 42: rejected fragment 0, requested 1\n"<<std::flush;
    {
        FragmentTransaction trial(genome,library.at(second.fragment));sync_slot();
        int old=0,zero=0;
        for(int v=0;v<8;++v) {
            old+=solve(0,v);old+=solve(1,v);
            if(v<7)old+=solve(2,v);
            zero+=solve(3,v);
        }
        if(old!=23||zero!=8)return 5;
        auto decision=request(true,true);
        if(decision.verb!=1||decision.fragment!=1)return 6;
        trial.commit();
    }
    if(!h.memory[p.layout.work_start+40]||!h.memory[p.layout.work_start+45])return 7;
    h.new_his();Hamster child(43,p);child.copy_hamu(h);h=std::move(child);
    if(!h.memory[p.layout.work_start+40]||!h.memory[p.layout.work_start+45]||!solve(3,7))return 8;
    std::cout<<"PASS single-entry VM: data/operator promotion->control->trial->commit;"
                " ZERO=8/8 old=23/23; state and installed program inherited\n";
}
