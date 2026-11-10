#include "../src/tree_wide_segment_migration.hpp"
#include <algorithm>
#include <iostream>
#include <stdexcept>
#include <vector>
static void check(bool ok,const char* msg){if(!ok)throw std::runtime_error(msg);}
static HamsterParams wide_config(){
    HamsterParams p;
    p.layout.status_start=45;p.layout.output_start=50;p.layout.work_start=80;
    p.layout.program_start=350;p.layout.total_size=1374;
    p.layout.val_reg_size=16;p.tree_id_bits=12;p.tree_capacity=5;
    p.tree_start=100;p.stable_work_bits=250;
    return p;
}
static HamsterParams page_config(int cap=5,bool indexed=true){
    auto p=wide_config();p.tree_segmented_enabled=true;
    p.tree_start=-1;p.stable_work_bits=0;p.tree_capacity=cap;
    p.tree_index_enabled=indexed;
    return p;
}
static void put_row(Hamster& h,int id,int parent,int key,int action){
    const int bits=h.params.tree_id_bits,at=h.params.tree_start+(id-1)*(bits+7);
    h.memory[at]=true;
    for(int b=0;b<bits;++b)h.memory[at+1+b]=(parent>>(bits-1-b))&1;
    for(int b=0;b<3;++b)h.memory[at+bits+1+b]=(key>>(2-b))&1;
    for(int b=0;b<3;++b)h.memory[at+bits+4+b]=(action>>(2-b))&1;
}
static std::vector<int> program(int op,const std::vector<int>& keys){
    std::vector<int> words;
    for(int k:keys){words.push_back(op);words.push_back(k);}
    words.insert(words.end(),{15,0});return words;
}
static int run(Hamster& h,const std::vector<int>& words,bool keep=false){
    int at=h.params.layout.program_start;
    for(int w:words)for(bool bit:SpiralToken(w,h.params.op_order,h.params.op_lvl).bits)
        h.memory.at(at++)=bit;
    if(!keep)std::fill(h.val_reg.begin(),h.val_reg.end(),false);
    h.stop=false;h.tree_capacity_blocked=false;h.executed_steps=0;h.step_limit=200;
    h.pro_1=h.params.layout.program_start;h.pro_2=at-1;
    simulate_spiral_program(h);
    int id=0;for(int i=0;i<h.params.tree_id_bits;++i)id=(id<<1)|int(h.val_reg[i]);
    return id;
}
static void expect_reject(Hamster& dst,const Hamster& src,const char* label){
    const auto before=dst.segment_pages;
    bool failed=false;
    try{import_wide_tree_rows_into_segmented(dst,src);}catch(const std::invalid_argument&){failed=true;}
    check(failed,label);
    check(dst.segment_pages==before&&dst.segment_used==0,"failed migration mutated destination");
}
int main(){
    Hamster src(1,wide_config());
    put_row(src,1,0,1,0);put_row(src,3,1,2,6);put_row(src,4,3,3,5);
    const auto original=src.memory;
    Hamster seg(2,page_config());
    const auto stats=import_wide_tree_rows_into_segmented(seg,src);
    check(stats.live_nodes==3&&stats.free_holes==1&&stats.highest_live_id==4,"import statistics");
    check(src.memory==original,"migration changed source");
    check(seg.segment_row(2)==0,"hole not preserved");
    check(run(seg,program(27,{1,2}))==3,"migrated path not found");
    run(seg,{30,0,15,0},true);
    check(seg.val_reg[12]&&seg.val_reg[13]&&!seg.val_reg[14],"migrated answer not preserved");
    check(run(seg,program(27,{1,2,3}))==4,"migrated nested path not found");
    // Two available slots (2,5) must both roll back when third ADD fails.
    const auto before=seg.segment_pages;
    check(run(seg,program(28,{4,5,6}))==0&&seg.tree_capacity_blocked,"capacity did not block");
    check(seg.segment_pages==before&&seg.segment_used==4,"hole or appended row survived rollback");
    check(run(seg,program(27,{4}))==0,"rolled-back branch still found");
    seg.grow_segmented_tree_capacity(8);
    check(run(seg,program(28,{4,5,6}))==6,"retry did not reuse smallest free ID");
    check(run(seg,program(27,{4}))==2,"smallest free hole not reused");
    check(run(seg,program(27,{1,2,3}))==4,"old IDs moved on retry");
    seg.new_his();Hamster child(3,seg.params);child.copy_hamu(seg);
    check(run(child,program(27,{4,5,6}))==6,"offspring lost new branch");
    check(run(child,program(27,{1,2}))==3,"offspring lost old branch");
    run(child,{30,0,15,0},true);
    check(child.val_reg[12]&&child.val_reg[13]&&!child.val_reg[14],"offspring lost migrated answer");
    // Index-disabled mode must preserve the same allocation and answer semantics.
    Hamster linear(4,page_config(5,false));
    import_wide_tree_rows_into_segmented(linear,src);
    check(run(linear,program(28,{4}))==2,"linear hole reuse differs");
    check(run(linear,program(27,{1,2}))==3,"linear import lookup failed");
    // Rejected corrupt source must never publish partial canonical state.
    Hamster duplicate(5,wide_config());
    put_row(duplicate,1,0,1,0);put_row(duplicate,3,0,1,0);
    Hamster reject1(6,page_config());expect_reject(reject1,duplicate,"duplicate edge accepted");
    Hamster cycle(7,wide_config());
    put_row(cycle,1,3,1,0);put_row(cycle,3,1,2,0);
    Hamster reject2(8,page_config());expect_reject(reject2,cycle,"cycle accepted");
    Hamster dead(9,wide_config());
    put_row(dead,1,0,1,0);put_row(dead,3,2,2,0);
    Hamster reject3(10,page_config());expect_reject(reject3,dead,"dead parent accepted");
    Hamster small(11,page_config(4));expect_reject(small,src,"undersized destination accepted");
    // Sparse IDs across three physical pages, including an inherited 12->16
    // handle-width expansion. No relocation or renumbering is permitted.
    auto cross_cfg=wide_config();
    cross_cfg.tree_capacity=70;cross_cfg.layout.program_start=1700;
    cross_cfg.layout.total_size=2724;cross_cfg.stable_work_bits=1600;
    Hamster cross_src(13,cross_cfg);
    put_row(cross_src,1,0,1,0);
    put_row(cross_src,32,1,2,7);
    put_row(cross_src,65,32,3,5);
    auto cross_target_cfg=page_config(70);
    cross_target_cfg.tree_id_bits=16;
    cross_target_cfg.layout.val_reg_size=20;
    Hamster cross_dst(14,cross_target_cfg);
    const auto cross_stats=import_wide_tree_rows_into_segmented(cross_dst,cross_src);
    check(cross_stats.live_nodes==3&&cross_stats.free_holes==62,
          "cross-page sparse stats");
    check(run(cross_dst,program(27,{1,2,3}))==65,
          "cross-page stable handle lost");
    check(run(cross_dst,program(28,{4}))==2,
          "cross-page lowest hole not reused");
    check(run(cross_dst,program(27,{1,2}))==32,
          "cross-page ancestor ID changed");
    cross_dst.new_his();Hamster cross_child(15,cross_dst.params);
    cross_child.copy_hamu(cross_dst);
    check(run(cross_child,program(27,{1,2,3}))==65,
          "cross-page inherited handle lost");
    check(run(cross_child,program(28,{5}))==3,
          "cross-page inherited free cursor wrong");
    Hamster nonempty(12,page_config());
    run(nonempty,program(28,{1}));
    bool refused=false;
    try{import_wide_tree_rows_into_segmented(nonempty,src);}catch(const std::invalid_argument&){refused=true;}
    check(refused&&nonempty.segment_used==1,"nonempty destination accepted");
    std::cout<<"PASS wide->segmented semantic migration, sparse-ID reuse, rollback, inheritance, index differential, corrupt-source rejection\n";
}
