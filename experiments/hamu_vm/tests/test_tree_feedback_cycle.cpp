#include "../src/tree_pending_context_vm.hpp"
#include "../src/tree_context_confirm_bridge.hpp"
#include "../src/tree_context_grade_confirm_vm.hpp"
#include "../src/tree_grade_snapshot_vm.hpp"
#include "../src/tree_trial_grade.hpp"
#include "../src/tree_feedback_cycle_vm.hpp"
#include "../src/tree_candidate_choice_vm.hpp"
#include "../src/tree_guest_selection.hpp"
#include "../src/tree_learning_turn.hpp"
#include "../src/hamu_vm_core.hpp"
#include <cassert>
#include <iostream>

int main(){
    HamsterParams p;p.op_order=5;p.layout.status_start=45;p.layout.output_start=50;
    p.layout.work_start=80;p.layout.program_start=400;p.layout.total_size=16000;
    p.stable_work_bits=60;p.tree_start=340;p.tree_capacity=5;p.layout.val_reg_size=12;
    Hamster h(1,p);
    auto run=[&](const std::vector<int>& words,int parent=0,int limit=1200){
        int at=p.layout.program_start;
        for(int word:words)for(bool bit:SpiralToken(word,5,1).bits)h.memory.at(at++)=bit;
        std::fill(h.val_reg.begin(),h.val_reg.end(),false);
        for(int b=0;b<5;++b)h.val_reg[b]=(parent>>(4-b))&1;
        h.val_ptr=0;h.stop=false;h.budget_exhausted=false;h.executed_steps=0;
        h.step_limit=limit;h.pro_1=p.layout.program_start;h.pro_2=at-1;
        simulate_spiral_program(h);
        if(limit==1200)assert(h.stop&&!h.budget_exhausted);
        int id=0;for(int b=0;b<5;++b)id=(id<<1)|int(h.val_reg[b]);
        return id;
    };
    assert(run({28,1,15,0})==1);
    assert(run({28,2,15,0})==2);
    assert(run({28,3,15,0},1)==3);
    assert(run({28,3,15,0},2)==4);
    assert(run({28,4,15,0},1)==5); // alternate unbound operator
    auto question=[&](int category,int op){
        for(int i=0;i<45;++i)h.memory[i]=false;
        h.memory[1]=true;
        for(int i=0;i<4;++i){
            h.memory[2+i]=SpiralToken(category,3,1).bits[i];
            h.memory[6+i]=SpiralToken(op,3,1).bits[i];
        }
    };
    const auto first=tree_pending_context_program(57);
    const auto second=tree_pending_context_program(70);
    question(1,3);run(first);
    question(2,3);run(second);
    const auto confirm_first=tree_feedback_confirm_program(57);
    const auto confirm_second=tree_feedback_confirm_program(70);
    const auto snapshot=tree_grade_snapshot_program();
    auto trial=[&](int category,int op,int data,int attempt,bool correct){
        question(category,op);
        for(int i=0;i<3;++i)h.memory[10+i]=(data>>(2-i))&1;
        // Execute COPY or FLIP rather than letting the host fill output bytes.
        const bool flip=attempt==(data^7);
        assert(flip||attempt==data);
        const std::vector<int> candidate=flip?
            std::vector<int>{16,1,0,0,14,26,4,3,0,2,2,3,14,3,5,3,15,0}:
            std::vector<int>{16,1,0,0,14,26,4,3,0,2,9,3,15,0};
        std::array<bool,3> expected{};
        const int target=category==1?data:(data^7);
        for(int i=0;i<3;++i)expected[i]=(target>>(2-i))&1;
        const bool grade=run_tree_graded_trial(h,expected,[&]{run(candidate);});
        assert(grade==correct);
        run(snapshot);
        assert(h.memory[80+92]&&h.memory[80+34]==correct);
    };
    assert(h.memory[135]&&h.memory[136]&&h.memory[148]&&h.memory[149]);
    auto choose=[&](int slot){
        run(tree_candidate_choice_program(slot));
        if(!h.memory[75+0])return -1; // output+25 is at address 75
        return h.memory[76]?1:0;
    };
    auto select=[&](){return run_tree_guest_selection(h,[&](const std::vector<int>& words){run(words);});};
    question(1,3);assert(select()&&select()->slot==57&&select()->candidate==0);
    question(2,3);assert(select()&&select()->slot==70&&select()->candidate==0);
    question(2,4);assert(!select());
    question(1,3);assert(choose(57)==0);
    question(2,3);assert(choose(70)==0);
    question(2,4);assert(choose(70)==-1);
    question(1,3);
    const Hamster pending=h;
    std::cout<<"pending slots ready"<<std::endl;
    auto update=[&](int slot){
        run(tree_feedback_cycle_program(slot));
    };
    question(2,3);assert(choose(70)==0);
    trial(2,3,1,1,false);update(70);run(confirm_second);
    question(2,3);assert(select()&&select()->slot==70&&select()->candidate==1);
    assert(!h.memory[148]&&h.memory[149]&&!h.memory[150]);
    const auto selected=select();
    assert(selected&&selected->slot==70&&selected->candidate==1);
    const int chosen=selected->candidate;
    trial(2,3,2,chosen?5:2,true);update(70);run(confirm_second);
    assert(!select());
    assert(h.memory[150]&&h.memory[151]);
    assert(h.memory[135]&&h.memory[136]);
    update(57);run(confirm_first);assert(!h.memory[137]);
    question(1,3);assert(select()&&select()->slot==57&&select()->candidate==0);
    trial(1,3,3,3,true);update(57);run(confirm_first);
    assert(!select());
    assert(h.memory[135]&&!h.memory[136]&&h.memory[137]&&!h.memory[138]);
    const Hamster confirmed=h;
    h=pending;trial(1,3,1,1,true);h.memory[10]=true;update(57);
    assert(h.memory[135]&&h.memory[136]);
    h=pending;trial(1,3,1,1,true);h.memory[50]=true;update(57);
    assert(h.memory[135]&&h.memory[136]);
    h=pending;trial(1,3,1,1,true);h.memory[172]=false;update(57);
    assert(h.memory[135]&&h.memory[136]);
    h=pending;trial(2,3,1,1,false);update(70);update(70);
    assert(!h.memory[148]&&h.memory[149]);
    h=pending;question(1,3);h.memory[12]=true;
    assert(!run_tree_graded_trial(h,{false,false,true},[&]{run({0,2,3,3,15,0});}));
    run(snapshot);update(57);assert(h.memory[135]&&h.memory[136]);
    run(confirm_first);assert(!h.memory[137]);
    h=pending;question(1,3);
    assert(!run_tree_graded_trial(h,{false,false,false},[&]{run({15,0});}));
    run(snapshot);update(57);
    assert(!h.memory[173]&&h.memory[135]&&h.memory[136]);
    h=pending;question(1,3);
    assert(!run_tree_graded_trial(h,{false,false,false},[&]{run({0,2,3,3,15,0},0,2);}));
    run(snapshot);update(57);
    assert(!h.memory[173]&&h.memory[135]&&h.memory[136]);
    // A correct answer outside COPY/FLIP rejects both. Interrupt between
    // candidate updates: the transient singleton must not be confirmable.
    h=pending;question(1,3);h.memory[12]=true;
    assert(run_tree_graded_trial(h,{false,false,false},[&]{run({0,2,3,3,15,0});}));
    run(snapshot);const Hamster outside=h;
    run(tree_feedback_mask_program(57,false));
    const int first_steps=h.executed_steps;
    h=outside;run(tree_feedback_cycle_program(57),0,first_steps+10);
    assert(h.budget_exhausted&&!h.memory[174]);
    run(confirm_first);assert(!h.memory[137]);
    h=outside;update(57);run(confirm_first);
    assert(!h.memory[135]&&!h.memory[136]&&!h.memory[137]);
    std::cout<<"feedback edge cases passed"<<std::endl;
    for(int category=1;category<=2;++category)
        for(int value=0;value<8;++value)for(int candidate=0;candidate<2;++candidate){
            std::cout<<"matrix "<<category<<" "<<value<<" "<<candidate<<std::endl;
            h=pending;
            const int target=category==1?value:(value^7);
            const int attempt=candidate?value^7:value;
            trial(category,3,value,attempt,attempt==target);
            const int slot=category==1?57:70;
            update(slot);
            const int mask=category==1?135:148;
            assert(h.memory[mask]==(category==1));
            assert(h.memory[mask+1]==(category==2));
        }
    h=confirmed;trial(1,3,1,6,false);update(57);
    assert(h.memory[135]&&!h.memory[136]);
    run(tree_context_confirm_program(57));
    run(tree_context_confirm_program(70));
    run({30,0,15,0},3);assert(h.val_reg[5]&&!h.val_reg[6]&&!h.val_reg[7]);
    run({30,0,15,0},4);assert(h.val_reg[5]&&h.val_reg[6]&&!h.val_reg[7]);
    const Hamster learned=h;
    h.memory[80+47]=h.memory[80+78]=false; // isolated empty-slot probe
    question(1,3);run(first);
    assert(!h.memory[80+47]&&!h.memory[80+78]); // learned leaf is not pending
    h=learned;
    question(1,4);run(second); // occupied slot cannot be relabeled
    // The preinstalled two-level answer program must consume the newly bound
    // actions, rather than merely reading back their labels.
    const std::vector<int> route={
        16,1, 0,0, 14,18, 8,22, 4,3, 29,0, 8,1, 18,20, 15,0,
        0,0, 14,22, 8,17, 4,3, 29,0, 8,1, 18,20, 15,0,
        30,0, 18,20, 15,0, 8,17, 24,8,
        0,0, 14,26, 8,2, 4,3, 0,2, 9,3, 15,0,
        0,0, 14,26, 8,2, 4,3, 0,2, 2,3, 14,3, 5,3, 15,0
    };
    auto answer=[&](int category,int op,int value,int expected){
        question(category,op);
        for(int i=0;i<4;++i)h.memory[10+i]=SpiralToken(value,3,1).bits[i];
        for(int i=50;i<80;++i){h.memory[i]=false;h.written[i]=false;}
        run(route);
        for(int bit=0;bit<3;++bit){
            assert(h.written[50+bit]==(expected>=0));
            if(expected>=0)assert(h.memory[50+bit]==bool((expected>>(2-bit))&1));
        }
    };
    for(int value=0;value<8;++value){
        answer(1,3,value,value);
        answer(2,3,value,value^7);
        answer(1,4,value,-1); // unbound leaf remains unknown
    }
    h.new_his();Hamster child(2,p);child.copy_hamu(h);
    for(int i=127;i<160;++i)assert(child.memory[i]==h.memory[i]);
    for(int i=340;i<400;++i)assert(child.memory[i]==h.memory[i]);
    h=child;
    answer(1,3,6,6);
    answer(2,3,6,1);
    // The whole learning turn now consumes the guest-selected slot/candidate.
    h=pending;
    const std::array<std::vector<int>,2> candidates={
        std::vector<int>{16,1,0,0,14,26,4,3,0,2,9,3,15,0},
        std::vector<int>{16,1,0,0,14,26,4,3,0,2,2,3,14,3,5,3,15,0}
    };
    auto turn=[&](int category,int data,int expected){
        question(category,3);
        for(int bit=0;bit<4;++bit)
            h.memory[10+bit]=SpiralToken(data,3,1).bits[bit];
        std::array<bool,3> target{};
        for(int bit=0;bit<3;++bit)target[bit]=(expected>>(2-bit))&1;
        return run_tree_learning_turn(h,target,candidates,
            [&](const std::vector<int>& program){run(program);});
    };
    auto t1=turn(2,1,6);
    assert(t1&&t1->slot==70&&t1->candidate==0&&t1->valid&&!t1->correct&&!t1->confirmed);
    auto t2=turn(2,2,5);
    assert(t2&&t2->slot==70&&t2->candidate==1&&t2->valid&&t2->correct&&t2->confirmed);
    auto t3=turn(1,3,3);
    assert(t3&&t3->slot==57&&t3->candidate==0&&t3->valid&&t3->correct&&t3->confirmed);
    assert(!turn(2,4,3));
    answer(1,3,7,7);answer(2,3,7,0);
    h.new_his();Hamster next(3,p);next.copy_hamu(h);h=next;
    answer(1,3,6,6);answer(2,3,6,1);
    std::cout<<"PASS guest selects slots, executes candidates, learns two tree routes and inherits\n";
}
