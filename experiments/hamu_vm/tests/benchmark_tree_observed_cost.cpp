#include "../src/tree_observed_learner.hpp"
#include <chrono>
#include <iostream>
#include <stdexcept>

// Controlled counterfactual: full observation bypasses the request program,
// supplying a synthetic all-ones mask at the host boundary. It is a benchmark
// policy, not a guest learning capability or a claim about the historical binary.
struct Cost { long long guest=0, request=0, fragment=0, observations=0, calls=0; };
struct Episode { Cost cost; std::vector<int> trace; double seconds=0; };
static void check(bool ok,const char* context="unspecified"){if(!ok)throw std::runtime_error(context);}

Episode episode(bool selective){
    HamsterParams p;p.op_order=5;p.layout.status_start=45;p.layout.output_start=50;p.layout.work_start=80;
    p.layout.program_start=700;p.layout.total_size=24000;p.stable_work_bits=100;p.tree_start=600;p.tree_capacity=8;p.layout.val_reg_size=12;
    auto xor_one=tree_width_trial_program(false);xor_one.resize(xor_one.size()-2);
    const std::vector<int> toggle={0,0,14,17,4,1,0,2,14,18,5,1,15,0};
    xor_one.insert(xor_one.end(),toggle.begin(),toggle.end());
    const std::array<std::vector<int>,4> code={tree_four_trial_program(2),xor_one,tree_four_trial_program(0),tree_four_trial_program(1)};
    TreeObservedLearner learner(1,p,code);Episode result;
    const auto request0=tree_observed_request_program(57),request1=tree_observed_request_program(70);
    auto run=[&](Hamster& h,const std::vector<int>& words){
        const bool request=words==request0||words==request1;
        if(request&&!selective){
            for(int j=0;j<4;++j){h.memory[50+20+j]=true;h.written[50+20+j]=true;}
            return;
        }
        int at=p.layout.program_start;
        for(int word:words)for(bool bit:SpiralToken(word,5,1).bits)h.memory.at(at++)=bit;
        std::fill(h.val_reg.begin(),h.val_reg.end(),false);h.val_ptr=0;
        h.stop=false;h.budget_exhausted=false;h.executed_steps=0;h.step_limit=4000;
        h.pro_1=p.layout.program_start;h.pro_2=at-1;simulate_spiral_program(h);
        check(h.stop&&!h.budget_exhausted,"execution");++result.cost.calls;
        if(&h!=&learner.hamster){result.cost.fragment+=h.executed_steps;++result.cost.observations;}
        else if(request)result.cost.request+=h.executed_steps;
        else result.cost.guest+=h.executed_steps;
    };
    auto question=[&](Hamster& h,int width,int op,int data){
        std::fill(h.memory.begin(),h.memory.begin()+45,false);h.memory[1]=true;
        for(int b=0;b<4;++b)h.memory[2+b]=SpiralToken(1,3,1).bits[b];
        for(int b=0;b<width+1;++b)h.memory[6+b]=SpiralToken(op,width,1).bits[b];
        for(int b=0;b<4;++b)h.memory[7+width+b]=SpiralToken(data,3,1).bits[b];
    };
    const auto start=std::chrono::steady_clock::now();
    const int tasks[][4]={{2,1,0,1},{2,1,2,3},{2,2,0,0},{2,2,3,3},{2,2,5,5},{2,3,0,7},{2,3,3,4},{2,3,4,3},{3,1,0,0},{3,1,5,0}};
    std::optional<TreeObservedLearner> n2_child;int turn_index=0;
    for(const auto& q:tasks){
        if(turn_index++==8)n2_child.emplace(learner,2);
        question(learner.hamster,q[0],q[1],q[2]);
        const std::array<bool,3> expected={bool(q[3]&4),bool(q[3]&2),bool(q[3]&1)};
        const auto t=run_tree_observed_learning_turn(learner,expected,run);check(bool(t),"learning turn");
        const auto& l=t->learning;
        result.trace.insert(result.trace.end(),{l.slot,l.candidate,int(l.valid),int(l.correct),int(l.confirmed)});
        for(int slot:{57,70})for(int j=0;j<4;++j)result.trace.push_back(learner.hamster.memory[80+tree_four_mask(slot)+j]);
    }
    result.seconds=std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
    // Validation is outside the timed learning phase and its cost totals.
    const Cost learning_cost=result.cost;
    for(int data=0;data<8;++data)for(int op=1;op<=4;++op){
        const int width=op==4?3:2,key=op==4?1:op;
        const int expected=op==1?(data^1):op==2?data:op==3?(data^7):0;
        auto& who=op==4?learner:*n2_child;
        question(who.hamster,width,key,data);const auto id=run_tree_observed_route(who,run);
        check(id&&*id==(op==4?0:op),"route index");
        for(int b=0;b<3;++b)check(who.hamster.written[50+b]&&who.hamster.memory[50+b]==bool(expected&(4>>b)),"route answer");
    }
    result.cost=learning_cost;
    for(int pos=600;pos<681;++pos)result.trace.push_back(learner.hamster.memory[pos]);
    return result;
}

int main(){
    constexpr int repeats=12;double full_time=0,selective_time=0;Episode full,selective;
    for(int repeat=0;repeat<repeats;++repeat){
        // Alternate execution order to reduce one-sided warm-up/order effects.
        if(repeat%2){selective=episode(true);full=episode(false);}
        else {full=episode(false);selective=episode(true);}
        check(full.trace==selective.trace,"trace equality");full_time+=full.seconds;selective_time+=selective.seconds;
    }
    std::cout<<"policy,episodes,turns_per_episode,guest_steps_per_episode,request_steps_per_episode,fragment_steps_per_episode,observations_per_episode,vm_calls_per_episode,mean_learning_seconds\n";
    auto print=[&](const char* name,const Episode& e,double time){const auto& c=e.cost;
        std::cout<<name<<','<<repeats<<",10,"<<c.guest<<','<<c.request<<','<<c.fragment<<','<<c.observations<<','<<c.calls<<','<<time/repeats<<'\n';};
    print("full_host_reference",full,full_time);print("guest_requested",selective,selective_time);
    std::cout<<"PASS identical per-turn outcomes, masks and final trees; 32 routed answers per episode; learning timing excludes validation\n";
}
