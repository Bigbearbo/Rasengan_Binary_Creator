#include "../src/tree_width_learning_turn.hpp"
#include "../src/tree_width_trial_vm.hpp"
#include "../src/tree_width_route_vm.hpp"
#include <cassert>
#include <iostream>

int main(){
    HamsterParams p;p.op_order=5;p.layout.status_start=45;
    p.layout.output_start=50;p.layout.work_start=80;
    p.layout.program_start=700;p.layout.total_size=10000;
    p.stable_work_bits=100;p.tree_start=600;p.tree_capacity=8;
    p.layout.val_reg_size=12;
    Hamster h(1,p);
    auto run=[&](const std::vector<int>& words,int budget=1800){
        int at=p.layout.program_start;
        for(int word:words)for(bool bit:SpiralToken(word,5,1).bits)h.memory.at(at++)=bit;
        std::fill(h.val_reg.begin(),h.val_reg.end(),false);
        h.val_ptr=0;h.stop=false;h.budget_exhausted=false;
        h.executed_steps=0;h.step_limit=budget;
        h.pro_1=p.layout.program_start;h.pro_2=at-1;
        simulate_spiral_program(h);
        if(budget==1800)assert(h.stop&&!h.budget_exhausted);
    };
    auto question=[&](int width,int op,int data){
        std::fill(h.memory.begin(),h.memory.begin()+45,false);h.memory[1]=true;
        for(int b=0;b<4;++b)h.memory[2+b]=SpiralToken(1,3,1).bits[b];
        for(int b=0;b<width+1;++b)h.memory[6+b]=SpiralToken(op,width,1).bits[b];
        for(int b=0;b<4;++b)h.memory[7+width+b]=SpiralToken(data,3,1).bits[b];
    };
    const std::array<std::vector<int>,2> candidates={tree_width_trial_program(false),tree_width_trial_program(true)};
    auto runner=[&](const std::vector<int>& words){run(words);};
    auto turn=[&](int expected,bool reuse=true){
        std::array<bool,3> bits{};for(int b=0;b<3;++b)bits[b]=(expected>>(2-b))&1;
        return run_tree_width_learning_turn(h,bits,candidates,runner,reuse);
    };
    auto answer=[&](int width,int op,int data,int expected){
        question(width,op,data);
        std::fill(h.memory.begin()+50,h.memory.begin()+80,false);
        std::fill(h.written.begin()+50,h.written.begin()+80,false);
        run(tree_width_route_program());
        for(int b=0;b<3;++b){assert(h.written[50+b]);assert(h.memory[50+b]==bool((expected>>(2-b))&1));}
    };
    const int action3=p.tree_start+p.tree_capacity*9+6;
    question(2,1,5);assert(turn(5,false)->confirmed);
    const Hamster retained=h;
    const auto reclaim=tree_width_reclaim_program(57);
    // A missing/mismatched/unconfirmed target must keep its pending record.
    for(int fault=0;fault<7;++fault){
        h=retained;
        if(fault==0)h.memory[action3]=false;
        if(fault==1)h.memory[action3+1]=true;
        if(fault==2)h.memory[action3+2]=true;
        if(fault==3)h.memory[80+57]=false;
        if(fault==4)h.memory[80+78]=false;
        if(fault==5)h.memory[80+100]=true;
        if(fault==6)h.memory[p.tree_start+18]=false; // leaf missing
        const auto before=h.memory;run(reclaim);
        assert(h.memory[80+47]);
        for(int at=80;at<700;++at)assert(h.memory[at]==before[at]);
    }
    h=retained;run(reclaim);const int steps=h.executed_steps;
    assert(!h.memory[80+47]&&!h.memory[80+92]&&!h.memory[80+93]&&!h.memory[80+94]);
    // Check the release boundary and retry on both sides of the final write.
    for(int budget:{1,steps/2,steps-3,steps-2,steps-1,steps}){
        h=retained;run(reclaim,budget);
        for(int at=80;at<700;++at)
            if(at!=80+47&&(at<80+92||at>80+94))assert(h.memory[at]==retained.memory[at]);
        if(budget<=steps-2)assert(h.memory[80+47]);
        run(reclaim);assert(!h.memory[80+47]);
    }
    // Same slot can be captured again without inheriting old confirmation.
    h=retained;run(reclaim);question(3,1,5);run(tree_width_prepare_program());
    run(tree_width_pending_program(57));
    assert(h.memory[80+47]&&!h.memory[80+57]&&!h.memory[80+58]);
    assert(h.memory[80+55]&&h.memory[80+56]&&h.memory[80+100]);
    // TREE_ACTION must not erase either upper bit of the captured key.
    h=Hamster(2,p);question(3,1,5);run(tree_width_prepare_program());
    question(3,4,5);run(tree_width_prepare_program());run(tree_width_pending_program(57));
    assert(h.memory[80+49]&&!h.memory[80+50]&&!h.memory[80+51]);
    run(tree_width_choice_program(57));assert(h.memory[75]&&!h.memory[76]);

    // Learn four paths through two reusable slots, keeping an unresolved slot.
    h=Hamster(2,p);question(2,1,5);auto first=turn(5);
    assert(first&&first->confirmed&&!h.memory[80+47]);
    h.new_his();Hamster n2_child(3,p);n2_child.copy_hamu(h);
    question(3,1,5);auto wrong=turn(2);
    assert(wrong&&wrong->slot==57&&!wrong->correct&&!wrong->confirmed&&h.memory[80+47]);
    question(3,0,4);auto second=turn(4);
    assert(second&&second->slot==70&&second->confirmed&&!h.memory[80+60]);
    assert(h.memory[80+47]&&!h.memory[80+57]&&!h.memory[80+55]&&h.memory[80+56]);
    question(3,1,6);auto flip=turn(1);
    assert(flip&&flip->slot==57&&flip->candidate==1&&flip->confirmed&&!h.memory[80+47]);
    question(3,2,3);auto fourth_wrong=turn(4);
    assert(fourth_wrong&&fourth_wrong->candidate==0&&!fourth_wrong->confirmed);
    question(3,2,6);auto fourth=turn(1);
    assert(fourth&&fourth->candidate==1&&fourth->confirmed);
    assert(!h.memory[80+47]&&!h.memory[80+60]);
    for(int op:{0,1,2})for(int data=0;data<8;++data)answer(3,op,data,op?data^7:data);
    h.new_his();Hamster child(4,p);child.copy_hamu(h);h=child;
    for(int op:{0,1,2})for(int data=0;data<8;++data)answer(3,op,data,op?data^7:data);
    assert(h.memory[action3]&&!h.memory[action3+1]&&!h.memory[action3+2]);
    // Only one more leaf fits; the next new path cannot capture any slot.
    question(3,3,4);assert(turn(4)->confirmed);
    const auto full=h.memory;question(3,4,5);assert(!turn(5));
    assert(!h.memory[80+47]&&!h.memory[80+60]);
    for(int at=600;at<696;++at)assert(h.memory[at]==full[at]);
    h=n2_child;for(int data=0;data<8;++data)answer(2,1,data,data);
    std::cout<<"PASS reusable width slots: action readback, interrupted release, five learned paths, inheritance\n";
}
