#include "../src/tree_wide_segment_migration.hpp"
#include <algorithm>
#include <iostream>
#include <stdexcept>
#include <vector>
static void require(bool x,const char* message){if(!x)throw std::runtime_error(message);}
static HamsterParams cfg(bool enabled=true,int capacity=3){
    HamsterParams p;
    p.layout.status_start=45;p.layout.output_start=50;p.layout.work_start=80;
    p.layout.program_start=350;p.layout.total_size=1374;p.layout.val_reg_size=21;
    p.tree_segmented_enabled=true;p.tree_reject_mask_enabled=enabled;
    p.tree_id_bits=16;p.tree_capacity=capacity;p.tree_index_enabled=true;
    return p;
}
static void set_id_candidate(Hamster& h,int id,int candidate){
    std::fill(h.val_reg.begin(),h.val_reg.end(),false);
    const int bits=h.params.tree_id_bits;
    for(int b=0;b<bits;++b)h.val_reg[b]=(id>>(bits-1-b))&1;
    for(int b=0;b<3;++b)h.val_reg[bits+1+b]=(candidate>>(2-b))&1;
}
static void execute(Hamster& h,std::initializer_list<int> words){
    int at=h.params.layout.program_start;
    for(int w:words)for(bool b:SpiralToken(w,h.params.op_order,h.params.op_lvl).bits)
        h.memory.at(at++)=b;
    h.pro_1=h.params.layout.program_start;h.pro_2=at-1;
    h.stop=false;h.tree_capacity_blocked=false;h.executed_steps=0;h.step_limit=100;
    simulate_spiral_program(h);
}
static bool rejected(Hamster& h,int id,int candidate){
    set_id_candidate(h,id,candidate);execute(h,{30,2,15,0});
    require(h.val_reg[20],"candidate read lost live-node status");
    return h.val_reg[16];
}
static void mark(Hamster& h,int id,int candidate){
    set_id_candidate(h,id,candidate);execute(h,{30,3,15,0});
    require(h.val_reg[16]&&h.val_reg[20],"candidate mark not visible");
}
int main(){
    Hamster h(1,cfg());
    set_id_candidate(h,0,0);execute(h,{28,1,15,0});
    require((h.segment_row(1)&1u)!=0,"setup node failed");
    for(int c=0;c<8;++c)require(!rejected(h,1,c),"new node already rejected");
    for(int c: {0,3,7})mark(h,1,c);
    for(int c=0;c<8;++c)
        require(rejected(h,1,c)==(c==0||c==3||c==7),"wrong candidate bit");
    const auto before_duplicate=h.segment_pages;
    mark(h,1,3);
    require(h.segment_pages==before_duplicate,"duplicate rejection changed canonical row");
    require(((h.segment_row(1)>>23)&255u)==0x89u,"mask layout mismatch");
    // TREE_ACTION(0/1) must not erase the rejection mask.
    set_id_candidate(h,1,5);execute(h,{30,1,15,0});
    require(((h.segment_row(1)>>23)&255u)==0x89u,"legacy action erased rejection mask");
    // A failed guest transaction must undo a newly rejected answer too.
    const auto before_fail=h.segment_pages;
    set_id_candidate(h,1,5);execute(h,{30,3,28,2,28,3,28,4,15,0});
    require(h.tree_capacity_blocked,"expected capacity failure did not occur");
    require(h.segment_pages==before_fail,"failed transaction retained rejection or node");
    require(!rejected(h,1,5),"rejected candidate survived rollback");
    // Published canonical pages are inherited; derived index is rebuilt.
    h.new_his();Hamster child(2,h.params);child.copy_hamu(h);
    for(int c=0;c<8;++c)
        require(rejected(child,1,c)==(c==0||c==3||c==7),"offspring lost rejection state");
    mark(child,1,5);
    require(!rejected(h,1,5),"offspring mutation leaked to parent");
    // Snapshot compatibility must not silently reinterpret old no-mask ABI.
    Hamster legacy(3,cfg(false));
    bool rejected_copy=false;
    try{legacy.copy_hamu(h);}catch(const std::invalid_argument&){rejected_copy=true;}
    require(rejected_copy,"mask ABI mismatch accepted");
    set_id_candidate(legacy,0,0);execute(legacy,{28,1,15,0});
    const auto legacy_row=legacy.segment_row(1);
    set_id_candidate(legacy,1,6);execute(legacy,{30,3,15,0});
    require(legacy.segment_row(1)==legacy_row,"mask-disabled opcode changed old VM");
    // Reading a missing ID reports not-found independently of the mask bit.
    set_id_candidate(h,3,7);execute(h,{30,2,15,0});
    require(!h.val_reg[16]&&!h.val_reg[20],"missing ID reported rejected or live");
    std::cout<<"PASS opt-in eight-candidate rejection, legacy action, rollback, inheritance, isolation, ABI gating\n";
    return 0;
}
