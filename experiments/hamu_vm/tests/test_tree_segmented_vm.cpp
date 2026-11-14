#include "../src/hamu_vm_core.hpp"
#include <iostream>
#include <stdexcept>
#include <vector>
#include <array>
#include <algorithm>

static void check(bool v,const char* what){if(!v)throw std::runtime_error(what);}
static std::vector<int> key(int n){
    return {7,(n>>12)&7,(n>>9)&7,(n>>6)&7,(n>>3)&7,n&7};
}
static std::vector<int> word_program(int op,const std::vector<int>& keys){
    std::vector<int> result;
    for(int k:keys){result.push_back(op);result.push_back(k);}
    result.insert(result.end(),{15,0});return result;
}
static int run(Hamster& h,const std::vector<int>& words,bool keep_reg=false){
    int at=h.params.layout.program_start;
    for(int w:words)for(bool bit:SpiralToken(w,h.params.op_order,h.params.op_lvl).bits)
        h.memory.at(at++)=bit;
    if(!keep_reg)std::fill(h.val_reg.begin(),h.val_reg.end(),false);
    h.stop=false;h.tree_capacity_blocked=false;h.executed_steps=0;h.step_limit=400;
    h.pro_1=h.params.layout.program_start;h.pro_2=at-1;
    simulate_spiral_program(h);
    int id=0;for(int i=0;i<h.params.tree_id_bits;++i)id=(id<<1)|int(h.val_reg[i]);
    return id;
}
static HamsterParams config(int capacity=8,bool index=true,int bits=16){
    HamsterParams p;
    p.layout.status_start=45;p.layout.output_start=50;p.layout.work_start=80;
    p.layout.program_start=350;p.layout.total_size=350+1024;
    p.layout.val_reg_size=bits+4;
    p.tree_segmented_enabled=true;p.tree_id_bits=bits;
    p.tree_capacity=capacity;p.tree_start=-1;p.tree_index_enabled=index;
    return p;
}
static void same(const Hamster& a,const Hamster& b){
    check(a.segment_pages==b.segment_pages,"canonical pages differ");
    check(a.segment_used==b.segment_used,"canonical used rows differ");
    check(a.memory==b.memory,"program memory differs");
}
int main(int argc,char**argv){
    const bool stress=argc>1&&std::string(argv[1])=="--stress-10000";
    const int paths=stress?10000:600;
    const int bits=stress?16:12;
    Hamster a(1,config(8,true,bits)),b(2,config(8,false,bits));
    const auto program_start=a.params.layout.program_start;
    auto *first_page=&a.segment_pages.front();
    int expansions=0, first=0,last=0;
    for(int n=0;n<paths;++n){
        for(;;){
            int f=run(a,word_program(28,key(n)));
            int s=run(b,word_program(28,key(n)));
            check(f==s&&a.tree_capacity_blocked==b.tree_capacity_blocked,"indexed and linear add diverged");
            if(!stress || n%503==0) same(a,b);
            if(!a.tree_capacity_blocked){if(n==0)first=f;last=f;break;}
            const int limit=(1<<bits)-1;
            check(a.params.tree_capacity<limit,"unexpected ID exhaustion");
            const int new_cap=std::min(limit,a.params.tree_capacity*2);
            a.grow_segmented_tree_capacity(new_cap);
            b.grow_segmented_tree_capacity(new_cap);
            ++expansions;
            check(&a.segment_pages.front()==first_page,"page physical location moved");
            check(a.params.layout.program_start==program_start,"VM code section moved");
            check(a.segment_pages.size()==(std::size_t(new_cap)+30)/31,"unexpected segment count");
            check(run(a,word_program(27,key(0)))==(n?first:0),"old reference broken by growth");
            check(run(b,word_program(27,key(0)))==(n?first:0),"linear reference broken by growth");
        }
        if(n%199==0){
            check(run(a,word_program(27,key(n)))==last,"indexed find mismatch");
            check(run(b,word_program(27,key(n)))==last,"linear find mismatch");
        }
    }
    check(a.segment_used>4095 || !stress,"stress did not exceed legacy ID bound");
    check(a.segment_used>31&&expansions>=7,"did not cross legacy node bound");
    check(run(a,word_program(27,key(0)))==first,"first handle lost");
    check(run(a,word_program(27,key(paths-1)))==last,"last handle lost");
    check(run(b,word_program(27,key(paths-1)))==last,"linear last handle lost");
    // Answer, inherited answer, and cache not inherited.
    run(a,word_program(27,key(0)));
    a.val_reg[bits+1]=true;a.val_reg[bits+2]=false;
    run(a,{30,1,15,0},true);
    run(a,word_program(27,key(0)));
    run(a,{30,0,15,0},true);
    check(a.val_reg[bits]&&a.val_reg[bits+1]&&!a.val_reg[bits+2],"action memory failure");
    a.new_his();Hamster child(3,a.params);child.copy_hamu(a);
    check(!child.segment_edge_index_valid&&child.segment_used==a.segment_used,"snapshot cache or count wrong");
    check(run(child,word_program(27,key(0)))==first,"child lost original ID");
    run(child,{30,0,15,0},true);
    check(child.val_reg[bits]&&child.val_reg[bits+1]&&!child.val_reg[bits+2],"child answer lost");
    check(run(child,word_program(27,key(paths-1)))==last,"child lost late ID");
    // No legacy to segment reinterpretation, no stale capacity snapshot.
    auto incompatible=a.params;incompatible.tree_segmented_enabled=false;
    incompatible.tree_id_bits=12;incompatible.tree_capacity=8;
    incompatible.tree_start=80;incompatible.stable_work_bits=72;
    incompatible.layout.program_start=350;
    Hamster old(9,incompatible);bool rejected=false;
    try{old.copy_hamu(a);}catch(const std::invalid_argument&){rejected=true;}
    check(rejected,"legacy layout accidentally accepted segmented snapshot");
    Hamster small(4,config(3));
    const auto blank=small.segment_pages;
    check(run(small,word_program(28,key(0)))==0&&small.tree_capacity_blocked,"too-small path should fail");
    check(small.segment_pages==blank&&small.segment_used==0,"capacity failure left partially created nodes");
    check(run(small,word_program(28,{1,2,3}))==3,"three-node capacity insert failed");
    check(run(small,word_program(27,{1,2,3}))==3,"three-node path lookup failed");
    // Action writes before an allocation failure must roll back as well.
    run(small,word_program(27,{1,2,3}));
    const int small_bits=small.params.tree_id_bits;
    small.val_reg[small_bits+1]=true;small.val_reg[small_bits+2]=true;
    check(run(small,{30,1,28,7,15,0},true)==0&&small.tree_capacity_blocked,
          "action+allocation transaction did not block");
    run(small,word_program(27,{1,2,3}));run(small,{30,0,15,0},true);
    check(!small.val_reg[small_bits],"partial action survived full rollback");
    const auto before=small.segment_pages;
    small.grow_segmented_tree_capacity(8);
    check(small.segment_pages.size()==1,"wrong page count after partial-page growth");
    check(run(small,word_program(28,{1,2,4,5}))==5,"growth retry did not finish path");
    check(run(small,word_program(27,{1,2,3}))==3,"existing branch lost on retry");
    // Host must not silently change the encoded handle width.
    bool refused=false;
    try{small.grow_segmented_tree_capacity((1<<small.params.tree_id_bits));}
    catch(const std::invalid_argument&){refused=true;}
    check(refused&&small.params.tree_capacity==8,"ID width limit not enforced");
    // Register-key opcodes must use the same stable tree structure.
    run(small,word_program(27,{1,2,4}));
    small.val_reg[small_bits+1]=true;
    small.val_reg[small_bits+2]=false;
    small.val_reg[small_bits+3]=true;  // key 5; branch is already learned
    check(run(small,{29,0,15,0},true)==5,"TREE_FIND_REG wrong handle");
    run(small,word_program(27,{1,2,4}));
    small.val_reg[small_bits+1]=true;
    small.val_reg[small_bits+2]=false;
    small.val_reg[small_bits+3]=true;
    check(run(small,{31,0,15,0},true)==5,"TREE_ADD_REG duplicated existing branch");
    small.new_his();Hamster small_child(5,small.params);small_child.copy_hamu(small);
    check(run(small_child,word_program(27,{1,2,4,5}))==5,"post-growth offspring lost path");
    // A capacity increase invalidates published checkpoints until re-snapshotted.
    small.grow_segmented_tree_capacity(12);
    bool stale_snapshot_refused=false;
    try { Hamster stale(6,small.params); stale.copy_hamu(small); }
    catch (const std::invalid_argument&) { stale_snapshot_refused=true; }
    check(stale_snapshot_refused,"post-growth unpublished snapshot accepted");
    small.new_his(); Hamster fresh(7,small.params); fresh.copy_hamu(small);
    check(run(fresh,word_program(27,{1,2,4,5}))==5,
          "republished post-growth inheritance failed");
    std::cout<<"PASS segmented VM "<<paths<<" paths, nodes="<<a.segment_used
             <<", capacity="<<a.params.tree_capacity<<", growth_events="<<expansions
             <<", pages="<<a.segment_pages.size()
             <<", native_row_bytes="<<a.segment_pages.size()*sizeof(Hamster::SegmentPage)
             <<", program_start="<<a.params.layout.program_start
             <<", indexed_rebuild_rows="<<a.segment_edge_rebuild_rows
             <<", indexed_lookups="<<a.segment_edge_lookups
             <<", linear_rows="<<b.segment_edge_linear_rows
             <<", inheritance and atomic rollback\n";
}
