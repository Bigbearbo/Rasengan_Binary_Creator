#include "../src/guest_trial_checkpoint.hpp"
#include <cassert>
#include <iostream>
#include <vector>

static void install(Hamster& h,const std::vector<int>& words) {
    int at=h.params.layout.program_start;
    for(int word:words)for(bool bit:SpiralToken(word,5,1).bits)h.memory.at(at++)=bit;
    h.pro_1=h.params.layout.program_start;h.pro_2=at-1;
}
static int add(Hamster& h,int parent,int key) {
    install(h,{28,key,15,0});
    std::fill(h.val_reg.begin(),h.val_reg.end(),false);
    for(int b=0;b<5;++b)h.val_reg[b]=(parent>>(4-b))&1;
    h.stop=false;h.executed_steps=0;h.step_limit=12;
    simulate_spiral_program(h);
    int id=0;for(int b=0;b<5;++b)id=(id<<1)|int(h.val_reg[b]);
    assert(h.val_reg[5]);return id;
}
static void bind(Hamster& h,int id,int action){
    install(h,{30,1,15,0});
    std::fill(h.val_reg.begin(),h.val_reg.end(),false);
    for(int b=0;b<5;++b)h.val_reg[b]=(id>>(4-b))&1;
    h.val_reg[6]=(action>>1)&1;h.val_reg[7]=action&1;
    h.stop=false;h.executed_steps=0;h.step_limit=12;
    simulate_spiral_program(h);assert(h.val_reg[5]);
}
static void run(Hamster& h,int category,int operation,int value,int result) {
    for(int i=0;i<h.params.layout.status_start;++i)h.memory[i]=false;
    h.memory[1]=true; // 01 | category(3+0) | operation(3+0) | value(3+0)
    for(int i=0;i<4;++i)h.memory[2+i]=SpiralToken(category,3,1).bits[i];
    for(int i=0;i<4;++i)h.memory[6+i]=SpiralToken(operation,3,1).bits[i];
    for(int i=0;i<4;++i)h.memory[10+i]=SpiralToken(value,3,1).bits[i];
    for(int i=h.params.layout.output_start;i<h.params.layout.work_start;++i){h.memory[i]=false;h.written[i]=false;}
    std::fill(h.val_reg.begin(),h.val_reg.end(),false);
    std::fill(h.read_seen.begin(),h.read_seen.end(),false);
    h.val_ptr=0;h.stop=false;h.executed_steps=0;h.step_limit=64;
    h.pro_1=h.params.layout.program_start;
    simulate_spiral_program(h);
    assert(h.stop&&!h.budget_exhausted);
    for(int i=2;i<5;++i)if(!h.read_seen[i]){
        std::cerr<<"missing read category="<<category<<" op="<<operation<<" value="<<value<<" step="<<h.executed_steps<<"\n";assert(false);
    }
    for(int i=6;i<9;++i)assert(h.read_seen[i]==(category==1||category==2));
    for(int i=0;i<3;++i){
        const int at=h.params.layout.output_start+i;
        assert(h.written[at]==(result>=0));
        if(result>=0)assert(h.memory[at]==bool((result>>(2-i))&1));
    }
}
int main(){
    HamsterParams p;p.op_order=5;p.layout.status_start=45;p.layout.output_start=50;
    p.layout.work_start=80;p.layout.program_start=400;p.layout.total_size=900;
    p.stable_work_bits=60;p.tree_start=340;p.tree_capacity=5;p.layout.val_reg_size=12;
    Hamster h(1,p);
    const int b=add(h,0,2),a=add(h,0,1);
    assert(b==1&&a==2);
    const int flip=add(h,b,3),copy=add(h,a,3);
    assert(flip==3&&copy==4);
    bind(h,flip,2);bind(h,copy,0);
    assert(add(h,a,4)==5); // existing path with no committed action
    // The second lookup uses the first lookup's child ID as its parent.
    const std::vector<int> program={
        16,1, 0,0, 14,18, 8,22, 4,3, 29,0, 8,1, 18,20, 15,0,
        0,0, 14,22, 8,17, 4,3, 29,0, 8,1, 18,20, 15,0,
        30,0, 18,20, 15,0, 8,17, 24,8,
        0,0, 14,26, 8,2, 4,3, 0,2, 9,3, 15,0,
        0,0, 14,26, 8,2, 4,3, 0,2, 2,3, 14,3, 5,3, 15,0
    };
    assert(program.size()==76);install(h,program);
    for(int value=0;value<8;++value){
        run(h,1,3,value,value);
        run(h,2,3,value,value^7);
        run(h,1,4,value,-1); // known child, action not yet committed
        run(h,5,3,value,-1); // unseen category
    }
    bind(h,copy,2);install(h,program);run(h,1,3,5,2); // action changes without rebuilding the tree
    bind(h,copy,0);install(h,program);run(h,1,3,5,5);
    // A trial may touch a previously learned branch and an unbound child.
    // Rejecting it restores the whole guest; neither change may leak.
    const Hamster original=h;
    {
        GuestTrialCheckpoint trial(h);
        bind(h,copy,2);bind(h,5,2);install(h,program);
        run(h,1,3,5,2);run(h,1,4,5,2);
    }
    assert(h.memory==original.memory&&h.written==original.written);
    assert(h.val_reg==original.val_reg&&h.read_seen==original.read_seen);
    assert(h.hp==original.hp&&h.pro_1==original.pro_1&&h.pro_2==original.pro_2);
    run(h,1,3,5,5);run(h,1,4,5,-1);
    // An accepted trial makes the new child available and leaves the old one.
    {
        GuestTrialCheckpoint trial(h);
        bind(h,5,2);install(h,program);
        run(h,1,3,5,5);run(h,1,4,5,2);
        trial.commit();
    }
    run(h,1,3,6,6);run(h,1,4,6,1);
    h.new_his();Hamster child(2,p);child.copy_hamu(h);install(child,program);
    run(child,1,3,5,5);run(child,2,3,5,2);
    std::cout<<"PASS two-level guest tree routing, shared child key, unknown paths, inheritance\n";
}
