#include "../src/tree_four_learning_turn.hpp"
#include "../src/tree_width_route_vm.hpp"
#include <cassert>
#include <iostream>

int main(){
    HamsterParams p;p.op_order=5;p.layout.status_start=45;
    p.layout.output_start=50;p.layout.work_start=80;
    p.layout.program_start=700;p.layout.total_size=24000;
    p.stable_work_bits=100;p.tree_start=600;p.tree_capacity=8;p.layout.val_reg_size=12;
    Hamster h(1,p);
    auto run=[&](const std::vector<int>& words,int budget=4000){
        int at=p.layout.program_start;
        for(int word:words)for(bool bit:SpiralToken(word,5,1).bits)h.memory.at(at++)=bit;
        std::fill(h.val_reg.begin(),h.val_reg.end(),false);
        h.val_ptr=0;h.stop=false;h.budget_exhausted=false;h.executed_steps=0;h.step_limit=budget;
        h.pro_1=p.layout.program_start;h.pro_2=at-1;simulate_spiral_program(h);
        if(budget==4000)assert(h.stop&&!h.budget_exhausted);
    };
    auto runner=[&](const std::vector<int>& w){run(w);};
    auto question=[&](int width,int op,int data){
        std::fill(h.memory.begin(),h.memory.begin()+45,false);h.memory[1]=true;
        for(int b=0;b<4;++b)h.memory[2+b]=SpiralToken(1,3,1).bits[b];
        for(int b=0;b<width+1;++b)h.memory[6+b]=SpiralToken(op,width,1).bits[b];
        for(int b=0;b<4;++b)h.memory[7+width+b]=SpiralToken(data,3,1).bits[b];
    };
    auto bits=[](int v){return std::array<bool,3>{bool(v&4),bool(v&2),bool(v&1)};};
    const std::array<std::vector<int>,4> candidates={tree_four_trial_program(0),tree_four_trial_program(1),tree_four_trial_program(2),tree_four_trial_program(3)};
    auto turn=[&](int expected){return run_tree_four_learning_turn(h,bits(expected),candidates,runner);};
    auto masks=[&](int slot){int v=0;for(int i=0;i<4;++i)if(h.memory[80+tree_four_mask(slot)+i])v|=1<<i;return v;};
    auto action=[&](int node){int at=600+72+(node-1)*3;assert(h.memory[at]);return 2*int(h.memory[at+1])+int(h.memory[at+2]);};
    auto answer=[&](int width,int op,int data,int expected){
        question(width,op,data);
        std::fill(h.written.begin()+50,h.written.begin()+80,false);
        std::fill(h.memory.begin()+50,h.memory.begin()+80,false);run(tree_width_route_program(true));
        for(int b=0;b<3;++b){assert(h.written[50+b]);assert(h.memory[50+b]==bits(expected)[b]);}
        for(int at=53;at<80;++at)assert(!h.written[at]);
    };
    // Fresh VM output for all four programs, all data values, both offsets.
    for(int width:{2,3})for(int data=0;data<8;++data){
        question(width,1,data);run(tree_width_prepare_program());
        for(int id=0;id<4;++id){
            int expected=id==0?data:id==1?data^7:id==2?0:7;
            assert(run_tree_graded_trial(h,bits(expected),[&]{run(candidates[id]);}));
        }
    }
    h=Hamster(2,p);
    question(2,1,0);auto ambiguous_zero=turn(0);
    assert(ambiguous_zero&&ambiguous_zero->correct&&!ambiguous_zero->confirmed&&masks(57)==5);
    const Hamster ambiguous=h;
    // Stale/context-swapped feedback may not alter any hypothesis.
    for(int fault=0;fault<4;++fault){
        h=ambiguous;
        if(fault==0)h.memory[50]=!h.memory[50];
        if(fault==1)h.memory[9]=!h.memory[9];
        if(fault==2)h.memory[80+102]=true;
        if(fault==3)h.memory[80+tree_four_format(57)]=false;
        run(tree_four_feedback_program(57));run(tree_four_confirm_program(57));
        assert(masks(57)==5&&!h.memory[80+57]&&!h.memory[80+94]);
    }
    h=ambiguous;
    question(2,2,7);auto ambiguous_one=turn(7);
    assert(ambiguous_one&&ambiguous_one->slot==70&&!ambiguous_one->confirmed&&masks(70)==9);
    question(2,1,5);auto zero_wrong=turn(0);
    assert(zero_wrong&&zero_wrong->candidate==0&&!zero_wrong->correct&&!zero_wrong->confirmed&&masks(57)==4);
    question(2,1,3);auto zero=turn(0);
    assert(zero&&zero->candidate==2&&zero->confirmed&&!h.memory[127]&&action(3)==1);
    assert(h.memory[140]&&masks(70)==9);
    question(2,2,3);auto one_wrong=turn(7);
    assert(one_wrong&&one_wrong->candidate==0&&!one_wrong->confirmed&&masks(70)==8);
    question(2,2,4);auto one=turn(7);
    assert(one&&one->candidate==3&&one->confirmed&&!h.memory[140]&&action(4)==3);
    question(2,3,5);assert(!turn(2)->correct);
    question(2,3,3);auto flip=turn(4);
    assert(flip&&flip->candidate==1&&flip->confirmed&&action(5)==2);
    h.new_his();Hamster n2_child(3,p);n2_child.copy_hamu(h);
    question(3,1,0);assert(!turn(0)->confirmed);
    question(3,1,5);auto copy=turn(5);
    assert(copy&&copy->candidate==0&&copy->confirmed&&action(7)==0);
    for(int data=0;data<8;++data)answer(3,1,data,data);
    h.new_his();Hamster n3_child(4,p);n3_child.copy_hamu(h);h=n3_child;
    for(int data=0;data<8;++data)answer(3,1,data,data);
    h=n2_child;
    for(int data=0;data<8;++data){answer(2,1,data,0);answer(2,2,data,7);answer(2,3,data,data^7);}

    // A correct answer outside this candidate set eliminates all hypotheses.
    h=Hamster(5,p);question(2,1,2);run(tree_width_prepare_program());run(tree_width_pending_program(57,true));
    assert(run_tree_graded_trial(h,bits(3),[&]{run({16,1,0,2,3,1,2,2,15,0});}));
    run(tree_width_snapshot_program());run(tree_four_feedback_program(57));run(tree_four_confirm_program(57));
    assert(masks(57)==0&&!h.memory[80+57]);run(tree_four_choice_program(57));assert(!h.memory[75]);

    // Incomplete output is not negative semantic evidence.
    h=Hamster(6,p);question(2,1,5);auto partial=candidates;partial[0]={16,1,0,2,3,1,15,0};
    auto invalid=run_tree_four_learning_turn(h,bits(5),partial,runner);
    assert(invalid&&!invalid->valid&&masks(57)==15&&!invalid->confirmed);

    // No confirmation between the final mask intersection and completion bit.
    h=Hamster(7,p);question(2,1,5);run(tree_width_prepare_program());run(tree_width_pending_program(57,true));
    assert(run_tree_graded_trial(h,bits(5),[&]{run(candidates[0]);}));run(tree_width_snapshot_program());
    const Hamster observed=h;auto feedback=tree_four_feedback_program(57);run(feedback);int steps=h.executed_steps;
    h=observed;run(feedback,steps-2);assert(h.budget_exhausted&&!h.memory[80+94]);
    run(tree_four_confirm_program(57));assert(!h.memory[80+57]);
    run(feedback);run(tree_four_confirm_program(57));run(tree_four_bind_program(57));assert(action(3)==0);
    const Hamster bound=h;
    h.memory[600+72+6+2]=true;run(tree_four_reclaim_program(57));assert(h.memory[127]);
    h=bound;run(tree_four_reclaim_program(57));assert(!h.memory[127]);
    std::cout<<"PASS four candidates: 64 fresh trials, ambiguity, four actions, 40 routed answers, guards and recovery\n";
}
