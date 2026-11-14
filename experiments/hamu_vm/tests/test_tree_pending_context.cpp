#include "../src/tree_pending_context_vm.hpp"
#include "../src/tree_context_confirm_bridge.hpp"
#include "../src/tree_context_grade_confirm_vm.hpp"
#include "../src/tree_grade_snapshot_vm.hpp"
#include "../src/tree_trial_grade.hpp"
#include "../src/hamu_vm_core.hpp"
#include <cassert>
#include <iostream>

int main(){
    HamsterParams p;p.op_order=5;p.layout.status_start=45;p.layout.output_start=50;
    p.layout.work_start=80;p.layout.program_start=400;p.layout.total_size=6400;
    p.stable_work_bits=60;p.tree_start=340;p.tree_capacity=5;p.layout.val_reg_size=12;
    Hamster h(1,p);
    auto run=[&](const std::vector<int>& words,int parent=0,int limit=500){
        int at=p.layout.program_start;
        for(int word:words)for(bool bit:SpiralToken(word,5,1).bits)h.memory.at(at++)=bit;
        std::fill(h.val_reg.begin(),h.val_reg.end(),false);
        for(int b=0;b<5;++b)h.val_reg[b]=(parent>>(4-b))&1;
        h.val_ptr=0;h.stop=false;h.budget_exhausted=false;h.executed_steps=0;
        h.step_limit=limit;h.pro_1=p.layout.program_start;h.pro_2=at-1;
        simulate_spiral_program(h);
        if(limit==500)assert(h.stop&&!h.budget_exhausted);
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
    question(5,3);run(first); // unknown category
    assert(!h.memory[80+47]&&!h.memory[80+78]);
    question(1,5);run(first); // unknown child
    assert(!h.memory[80+47]&&!h.memory[80+78]);
    question(1,3);
    const Hamster before=h;
    bool interrupted=false;
    for(int budget=1;budget<200;++budget){
        h=before;run(first,0,budget);
        if(h.budget_exhausted&&h.memory[80+78]&&!h.memory[80+47]){
            interrupted=true;break;
        }
    }
    assert(interrupted);
    h.memory[80+57]=h.memory[80+58]=true;
    run(tree_context_confirm_program(57)); // partial record cannot bind
    run({30,0,15,0},3);assert(!h.val_reg[5]);
    h=before;
    run(first);
    assert(h.memory[80+47]&&h.memory[80+48]&&h.memory[80+78]);
    assert(!h.memory[80+72]&&!h.memory[80+73]&&h.memory[80+74]);
    for(int i=0;i<3;++i){
        assert(h.memory[80+49+i]==h.memory[6+i]);
        assert(h.memory[80+52+i]==h.memory[6+i]);
    }
    const Hamster after_first=h;
    run(second); // same unconfirmed path cannot consume the other slot
    assert(!h.memory[80+60]&&!h.memory[80+79]);
    question(1,4);run(second); // different operator under the same category
    assert(h.memory[80+60]&&h.memory[80+79]);
    for(int bit=0;bit<3;++bit)
        assert(h.memory[80+62+bit]==bool((4>>(2-bit))&1));
    h=after_first;
    question(2,3);run(second);
    assert(h.memory[80+60]&&h.memory[80+61]&&h.memory[80+79]);
    assert(!h.memory[80+75]&&h.memory[80+76]&&!h.memory[80+77]);
    const Hamster after_two=h;
    h=before;question(2,3);run(second); // reverse slot order
    assert(h.memory[80+60]&&h.memory[80+79]);
    run(first);assert(!h.memory[80+47]&&!h.memory[80+78]);
    question(1,3);run(first);
    assert(h.memory[80+47]&&h.memory[80+78]);
    h=after_two;
    question(1,4);run(first); // no relabel after publishing
    assert(!h.memory[80+72]&&!h.memory[80+73]&&h.memory[80+74]);
    const auto confirm_first=tree_context_grade_confirm_program(57);
    const auto confirm_second=tree_context_grade_confirm_program(70);
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
    h.memory[80+55]=true;h.memory[80+56]=false; // only COPY survives
    h.memory[80+68]=false;h.memory[80+69]=true; // only FLIP survives
    question(2,3);
    for(int i=0;i<3;++i){
        h.memory[10+i]=(1>>(2-i))&1;
        h.memory[50+i]=(6>>(2-i))&1;
    }
    h.memory[40]=true;
    const Hamster before_snapshot=h;
    bool partial_snapshot=false;
    for(int budget=1;budget<180;++budget){
        h=before_snapshot;run(snapshot,0,budget);
        if(h.budget_exhausted&&h.memory[80+34]&&!h.memory[80+92]){
            partial_snapshot=true;break;
        }
    }
    assert(partial_snapshot);
    run(confirm_second);assert(!h.memory[80+70]);
    h=before_snapshot;
    trial(2,3,1,6,true);
    question(1,3);run(confirm_first); // old grade belongs to category 2
    assert(!h.memory[80+57]);
    question(1,4);run(confirm_first); // same category, different operator
    assert(!h.memory[80+57]);
    trial(1,3,1,6,false);run(confirm_first);
    assert(!h.memory[80+57]); // no correct grade
    trial(1,3,1,1,true);
    h.memory[10]=true;run(confirm_first); // changed data cannot use older grade
    assert(!h.memory[80+57]);h.memory[10]=false;
    h.memory[50]=true;run(confirm_first); // changed attempt cannot use older grade
    assert(!h.memory[80+57]);h.memory[50]=false;
    h.memory[80+56]=true;
    run(confirm_first);assert(!h.memory[80+57]); // ambiguous survivors
    h.memory[80+56]=false;
    run(confirm_first);
    assert(h.memory[80+57]&&!h.memory[80+58]);
    h.memory[80+55]=false;h.memory[80+56]=true;
    run(confirm_first);assert(h.memory[80+57]&&!h.memory[80+58]);
    h.memory[80+55]=true;h.memory[80+56]=false;
    question(1,3);run(confirm_second);
    assert(!h.memory[80+70]); // cannot borrow category 1's grade
    trial(2,3,2,5,true);run(confirm_second);
    assert(h.memory[80+70]&&h.memory[80+71]);
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
    std::cout<<"PASS guest records paired context and learns two working tree routes\n";
}
