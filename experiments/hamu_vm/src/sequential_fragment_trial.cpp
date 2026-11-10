#include "guest_fragment_request.hpp"
#include "single_entry_program.hpp"
#include "fragment_transaction.hpp"
#include "guest_trial_checkpoint.hpp"
#include "layer_packet.hpp"
#include "math_questions.hpp"
#include <iostream>
#include <cstdlib>

int main(int argc,char** argv) {
    const int max_trials=argc>=2?std::atoi(argv[1]):4;
    const int winner=argc==3?std::atoi(argv[2]):3;
    if(max_trials<1||max_trials>4||(winner!=-1&&winner!=0&&winner!=3)||argc>3)return 12;
    long long control_steps=0,trial_steps=0,old_steps=0;
    int trials=0,rollbacks=0;
    auto genome=single_entry_program(15,-2);
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
        control_steps+=h.executed_steps;
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
        if(op==3)trial_steps+=h.executed_steps;
        else old_steps+=h.executed_steps;
        return !h.budget_exhausted&&!h.work_insert_blocked&&Check_ans(h,q);
    };
    if(!solve(0,2,2,2)||!solve(0,1,2,3)||!solve(1,5,3,3))return 9;
    if(!h.memory[p.layout.work_start+45]||h.memory[p.layout.work_start+40])return 10;
    std::vector<std::vector<int>> library={
        {0,2,14,17,2,4,15,0},{0,2,14,17,3,3,15,0},
        {0,2,14,17,3,5,15,0},{0,2,14,17,3,4,15,0}};
    if(winner==0)std::swap(library[0],library[3]);
    if(winner==-1)library[3]={0,2,14,17,2,4,15,0};
    bool feedback=false,passed=false;
    for(int candidate=0;candidate<4;++candidate) {
        auto choice=request(feedback,passed);
        if(choice.verb!=2||choice.fragment!=candidate||choice.slot!=0)return 1;
        if(trials==max_trials) {
            if(candidate!=max_trials||genome.words!=original)return 13;
            std::cout<<"DENIED candidate="<<candidate<<" trials="<<trials
                     <<" rollbacks="<<rollbacks<<" control_steps="<<control_steps
                     <<" trial_steps="<<trial_steps<<" old_steps="<<old_steps<<'\n';
            return 0;
        }
        ++trials;
        { GuestTrialCheckpoint guest_trial(h);
          FragmentTransaction trial(genome,library.at(choice.fragment));sync_slot();
        int zero=0;
        for(int v=0;v<8;++v)zero+=solve(3,v);
        std::cout<<"hamster 42 requests "<<choice.fragment<<" ZERO="<<zero<<"/8\n"<<std::flush;
        if(candidate!=winner) {
            if(zero!=0)return 2;
            // Transaction destructor restores code; control memory is retained.
        } else {
            if(zero!=8)return 3;
            int old=0;
            for(int v=0;v<8;++v) {
                old+=solve(0,v);old+=solve(1,v);
                if(v<7)old+=solve(2,v);
            }
            if(old!=23)return 4;
            auto decision=request(true,true);
            if(decision.verb!=1||decision.fragment!=winner)return 5;
            trial.commit();
            guest_trial.commit();
        }
        }
        sync_slot();
        if(candidate!=winner&&genome.words!=original)return 8;
        if(candidate!=winner) {
            // A rejected virus must leave executable old behavior intact,
            // not merely restore the host's word vector.
            int old_after_rollback=0;
            for(int v=0;v<8;++v) {
                old_after_rollback+=solve(0,v);
                old_after_rollback+=solve(1,v);
                if(v<7)old_after_rollback+=solve(2,v);
            }
            if(old_after_rollback!=23)return 18;
            ++rollbacks;
        }
        else break;
        feedback=true;passed=false;
    }
    if(winner==-1) {
        if(trials!=4||rollbacks!=4||genome.words!=original||
           !h.memory[p.layout.work_start+45])return 15;
        auto stopped=request(true,false);
        if(stopped.verb!=0||stopped.slot!=0||!h.memory[p.layout.work_start+42])return 16;
        h.new_his();Hamster child(43,p);child.copy_hamu(h);h=std::move(child);
        stopped=request(false,false);
        if(stopped.verb!=0||!h.memory[p.layout.work_start+42]||
           genome.words!=original)return 17;
        std::cout<<"EXHAUSTED trials="<<trials<<" rollbacks="<<rollbacks
                 <<" control_steps="<<control_steps<<" trial_steps="<<trial_steps
                 <<" old_steps="<<old_steps<<" original_program_inherited=1\n";
        return 0;
    }
    if(h.memory[p.layout.work_start+40]!=bool(winner&2)||
       h.memory[p.layout.work_start+41]!=bool(winner&1)||
       !h.memory[p.layout.work_start+45])return 6;
    h.new_his();Hamster child(43,p);child.copy_hamu(h);h=std::move(child);
    if(h.memory[p.layout.work_start+40]!=bool(winner&2)||
       h.memory[p.layout.work_start+41]!=bool(winner&1)||
       !h.memory[p.layout.work_start+45]||!solve(3,7))return 7;
    if(trials!=winner+1||rollbacks!=winner)return 14;
    std::cout<<"COST winner="<<winner<<" trials="<<trials<<" rollbacks="<<rollbacks
             <<" control_steps="<<control_steps<<" trial_steps="<<trial_steps
             <<" old_steps="<<old_steps<<" program_bits="<<genome.words.size()*6<<'\n';
    std::cout<<"PASS sequential resident trial winner="<<winner
             <<" ZERO=8/8 old=23/23; inherited\n";
}
