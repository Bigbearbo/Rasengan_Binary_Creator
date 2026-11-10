#include "../src/tree_context_confirm_bridge.hpp"
#include "../src/tree_category_capture_vm.hpp"
#include "../src/hamu_vm_core.hpp"
#include <cassert>
#include <iostream>

int main(){
    HamsterParams p;p.op_order=5;p.layout.status_start=45;p.layout.output_start=50;
    p.layout.work_start=80;p.layout.program_start=400;p.layout.total_size=1500;
    p.stable_work_bits=60;p.tree_start=340;p.tree_capacity=5;p.layout.val_reg_size=12;
    Hamster h(1,p);
    auto run=[&](const std::vector<int>& words,int parent){
        int at=p.layout.program_start;
        for(int w:words)for(bool bit:SpiralToken(w,5,1).bits)h.memory.at(at++)=bit;
        std::fill(h.val_reg.begin(),h.val_reg.end(),false);
        for(int b=0;b<5;++b)h.val_reg[b]=(parent>>(4-b))&1;
        h.val_ptr=0;h.stop=false;h.budget_exhausted=false;h.executed_steps=0;h.step_limit=400;
        h.pro_1=p.layout.program_start;h.pro_2=at-1;
        simulate_spiral_program(h);assert(h.stop&&!h.budget_exhausted);
        int id=0;for(int b=0;b<5;++b)id=(id<<1)|int(h.val_reg[b]);
        return id;
    };
    assert(run({28,1,15,0},0)==1);
    assert(run({28,2,15,0},0)==2);
    assert(run({28,3,15,0},1)==3);
    assert(run({28,3,15,0},2)==4);
    auto first=tree_context_confirm_program(57),second=tree_context_confirm_program(70);
    auto capture_first=tree_category_capture_program(57);
    auto capture_second=tree_category_capture_program(70);
    auto set3=[&](int offset,int value){
        for(int b=0;b<3;++b)h.memory[80+offset+b]=(value>>(2-b))&1;
    };
    h.memory[80+47]=h.memory[80+60]=true;
    h.memory[80+48]=h.memory[80+61]=true;
    set3(49,3);set3(52,3);set3(62,3);set3(65,3);
    h.memory[80+58]=true;h.memory[80+71]=false;
    h.memory[80+57]=h.memory[80+70]=true;
    auto question=[&](int category,int op){
        for(int i=0;i<45;++i)h.memory[i]=false;
        h.memory[1]=true;
        for(int i=0;i<4;++i){
            h.memory[2+i]=SpiralToken(category,3,1).bits[i];
            h.memory[6+i]=SpiralToken(op,3,1).bits[i];
        }
    };
    // Without a committed capture, confirmation must not assign either leaf.
    run(first,0);run(second,0);
    question(1,4);run(capture_first,0); // unrelated operator cannot claim the slot
    assert(!h.memory[80+78]);
    question(1,3);
    auto partial=h;
    // Exhaust the instruction budget just before category commit.
    bool saw_partial=false;
    for(int limit=1;limit<180;++limit){
        h=partial;
        int at=p.layout.program_start;
        for(int word:capture_first)for(bool bit:SpiralToken(word,5,1).bits)h.memory.at(at++)=bit;
        std::fill(h.val_reg.begin(),h.val_reg.end(),false);
        h.val_ptr=0;h.stop=false;h.budget_exhausted=false;h.executed_steps=0;h.step_limit=limit;
        h.pro_1=p.layout.program_start;h.pro_2=at-1;
        simulate_spiral_program(h);
        if(h.budget_exhausted&&h.memory[80+74]&&!h.memory[80+78]){saw_partial=true;break;}
    }
    assert(saw_partial);
    run(first,0); // partial category must not bind
    h=partial;
    run(capture_first,0);
    assert(h.memory[80+78]&&!h.memory[80+72]&&!h.memory[80+73]&&h.memory[80+74]);
    question(2,3);run(capture_second,0);
    assert(h.memory[80+79]&&!h.memory[80+75]&&h.memory[80+76]&&!h.memory[80+77]);
    question(5,3);run(capture_first,0); // committed context cannot change
    assert(!h.memory[80+72]&&!h.memory[80+73]&&h.memory[80+74]);
    run(first,0);run(second,0);
    auto action=[&](int id){
        run({30,0,15,0},id);
        return std::pair<bool,int>{h.val_reg[5],int(h.val_reg[6])*2+int(h.val_reg[7])};
    };
    assert((action(3)==std::pair<bool,int>{true,2}));
    assert((action(4)==std::pair<bool,int>{true,0}));
    h.memory[80+79]=false; // category data without commit is not enough
    h.memory[80+71]=true;run(second,0);
    assert((action(4)==std::pair<bool,int>{true,0}));
    h.memory[80+79]=true;
    h.memory[80+58]=false;set3(72,5); // changed record cannot find its category
    run(first,0);
    assert((action(3)==std::pair<bool,int>{true,2}));
    assert((action(4)==std::pair<bool,int>{true,0}));
    h.new_his();Hamster child(2,p);child.copy_hamu(h);
    for(int i=340;i<400;++i)assert(child.memory[i]==h.memory[i]);
    std::cout<<"PASS guest-captured category and operator locate distinct actions in two-level tree\n";
}
