#include "../src/tree_scaffold_vm.hpp"
#include "../src/tree_pending_context_vm.hpp"
#include "../src/tree_learning_turn.hpp"
#include "../src/hamu_vm_core.hpp"
#include <cassert>
#include <iostream>

int main(){
    HamsterParams p;p.op_order=5;p.layout.status_start=45;
    p.layout.output_start=50;p.layout.work_start=80;
    p.layout.program_start=400;p.layout.total_size=16000;
    p.stable_work_bits=60;p.tree_start=340;p.tree_capacity=5;
    p.layout.val_reg_size=12;
    Hamster h(1,p);
    auto run=[&](const std::vector<int>& words){
        int at=p.layout.program_start;
        for(int word:words)for(bool bit:SpiralToken(word,5,1).bits)
            h.memory.at(at++)=bit;
        std::fill(h.val_reg.begin(),h.val_reg.end(),false);
        h.val_ptr=0;h.stop=false;h.budget_exhausted=false;
        h.executed_steps=0;h.step_limit=1200;
        h.pro_1=p.layout.program_start;h.pro_2=at-1;
        simulate_spiral_program(h);
        assert(h.stop&&!h.budget_exhausted);
        int id=0;for(int b=0;b<5;++b)id=(id<<1)|int(h.val_reg[b]);
        return std::pair<int,bool>{id,h.val_reg[5]};
    };
    auto question=[&](int category,int op){
        std::fill(h.memory.begin(),h.memory.begin()+45,false);
        h.memory[1]=true;
        for(int i=0;i<4;++i){
            h.memory[2+i]=SpiralToken(category,3,1).bits[i];
            h.memory[6+i]=SpiralToken(op,3,1).bits[i];
        }
    };
    const auto scaffold=tree_scaffold_question_program();
    question(1,3);assert((run(scaffold)==std::pair<int,bool>{2,true}));
    const auto original=h.memory;
    assert((run(scaffold)==std::pair<int,bool>{2,true}));
    for(int i=340;i<400;++i)assert(h.memory[i]==original[i]);
    run(tree_pending_context_program(57));
    assert(h.memory[127]&&h.memory[135]&&h.memory[136]);
    question(1,4);assert((run(scaffold)==std::pair<int,bool>{3,true}));
    run(tree_pending_context_program(70));
    assert(h.memory[140]&&h.memory[148]&&h.memory[149]);
    question(2,3);assert((run(scaffold)==std::pair<int,bool>{5,true}));
    const auto full=h.memory;
    question(3,3);assert((run(scaffold)==std::pair<int,bool>{0,false}));
    for(int i=340;i<400;++i)assert(h.memory[i]==full[i]);
    const std::array<std::vector<int>,2> candidates={
        std::vector<int>{16,1,0,0,14,26,4,3,0,2,9,3,15,0},
        std::vector<int>{16,1,0,0,14,26,4,3,0,2,2,3,14,3,5,3,15,0}
    };
    auto learn=[&](int op,int data,int expected){
        question(1,op);
        for(int bit=0;bit<4;++bit)h.memory[10+bit]=SpiralToken(data,3,1).bits[bit];
        std::array<bool,3> answer{};
        for(int bit=0;bit<3;++bit)answer[bit]=(expected>>(2-bit))&1;
        return run_tree_learning_turn(h,answer,candidates,
            [&](const std::vector<int>& code){run(code);});
    };
    auto a=learn(3,1,1);
    assert(a&&a->slot==57&&a->candidate==0&&a->correct&&a->confirmed);
    auto b=learn(4,2,5);
    assert(b&&b->slot==70&&b->candidate==0&&!b->correct&&!b->confirmed);
    auto c=learn(4,3,4);
    assert(c&&c->slot==70&&c->candidate==1&&c->correct&&c->confirmed);
    const int action_base=340+5*9;
    assert(h.memory[action_base+3]&&!h.memory[action_base+4]&&!h.memory[action_base+5]);
    assert(h.memory[action_base+6]&&h.memory[action_base+7]&&!h.memory[action_base+8]);
    assert(!learn(3,2,2));
    const std::vector<int> route={
        16,1, 0,0, 14,18, 8,22, 4,3, 29,0, 8,1, 18,20, 15,0,
        0,0, 14,22, 8,17, 4,3, 29,0, 8,1, 18,20, 15,0,
        30,0, 18,20, 15,0, 8,17, 24,8,
        0,0, 14,26, 8,2, 4,3, 0,2, 9,3, 15,0,
        0,0, 14,26, 8,2, 4,3, 0,2, 2,3, 14,3, 5,3, 15,0
    };
    auto answer=[&](int op,int value,int expected){
        question(1,op);
        for(int bit=0;bit<4;++bit)
            h.memory[10+bit]=SpiralToken(value,3,1).bits[bit];
        for(int at=50;at<80;++at){h.memory[at]=false;h.written[at]=false;}
        run(route);
        for(int bit=0;bit<3;++bit){
            assert(h.written[50+bit]);
            assert(h.memory[50+bit]==bool((expected>>(2-bit))&1));
        }
    };
    answer(3,6,6);answer(4,6,1);

    h.new_his();Hamster child(2,p);child.copy_hamu(h);
    for(int i=340;i<400;++i)assert(child.memory[i]==h.memory[i]);
    h=child;answer(3,5,5);answer(4,5,2);
    std::cout<<"PASS guest adds dynamic category and operator keys, pending leaf, capacity and inheritance\n";
}
