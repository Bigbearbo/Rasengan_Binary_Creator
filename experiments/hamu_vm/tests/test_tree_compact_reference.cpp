#include "../src/tree_compact_reference.hpp"
#include <iostream>
int main(){
    HamsterParams p;p.layout.status_start=45;p.layout.output_start=50;
    p.layout.work_start=80;p.layout.program_start=1100;p.layout.total_size=24000;
    p.stable_work_bits=800;p.tree_start=300;p.tree_capacity=31;p.layout.val_reg_size=12;
    Hamster h(1,p);
    auto run=[&](Hamster& who,const std::vector<int>& words){
        int at=p.layout.program_start;
        for(int word:words)for(bool bit:SpiralToken(word,5,1).bits)who.memory.at(at++)=bit;
        std::fill(who.val_reg.begin(),who.val_reg.end(),false);who.val_ptr=0;
        who.stop=false;who.budget_exhausted=false;who.executed_steps=0;who.step_limit=4000;
        who.pro_1=p.layout.program_start;who.pro_2=at-1;simulate_spiral_program(who);
    };
    TreeCompactReference tree{h,672};
    for(int q=1;q<=7;++q){
        for(int option=0;option<8;++option){
            if(tree.next(q,run)!=option)throw std::runtime_error("duplicate wrong choice");
            if(h.val_reg[8])throw std::runtime_error("unmastered flagged as known on choice");
            tree.record(q,option,false,run);
        }
        if(tree.next(q,run)!=-1)throw std::runtime_error("exhaustion");
        tree.record(q,q%8,true,run);
        if(tree.next(q,run)!=q%8)throw std::runtime_error("positive reuse");
        if(!h.val_reg[8])throw std::runtime_error("mastery flag absent after guest choice");
    }
    int nodes=0;for(int id=0;id<p.tree_capacity;++id)
        nodes+=h.memory[p.tree_start+id*9];
    if(nodes!=7)throw std::runtime_error("answer trials consumed tree nodes");
    Hamster snapshot=h;snapshot.new_his();Hamster child(2,p);child.copy_hamu(snapshot);
    TreeCompactReference inherited{child,672};
    for(int q=1;q<=7;++q){
        if(inherited.next(q,run)!=q%8 || !child.val_reg[8])
            throw std::runtime_error("compact memory inheritance or guest mastery flag");
    }
    Hamster high(3,p);
    for(int root=0;root<7;++root)run(high,{8,11,28,root,15,0});
    for(int root=0;root<3;++root)
        for(int option=0;option<8;++option){
            if(root==2&&option==7)break; // 7 roots + 23 children = 30 nodes
            run(high,{8,11,28,root,28,option,15,0});
        }
    TreeCompactReference last{high,672};
    if(last.node(7,run)!=31||last.next(7,run)!=0)
        throw std::runtime_error("node 31 guest addressing");
    last.record(7,0,false,run);
    if(last.next(7,run)!=1)throw std::runtime_error("node 31 wrong memory");
    last.record(7,7,true,run);
    if(last.next(7,run)!=7 || !high.val_reg[8])
        throw std::runtime_error("node 31 success memory or mastery flag");
    std::cout<<"PASS guest chooses known or untried options and addresses payload, IDs 1..7 and 31; inheritance\n";
}
