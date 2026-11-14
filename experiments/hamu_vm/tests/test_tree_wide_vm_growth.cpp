#include "../src/hamu_vm_core.hpp"
#include <iostream>
#include <stdexcept>
#include <vector>

static void require(bool b,const char* message){if(!b)throw std::runtime_error(message);}
static std::vector<int> key(int n){
    return {7,(n>>9)&7,(n>>6)&7,(n>>3)&7,n&7};
}
static std::vector<int> program(int opcode,const std::vector<int>& keys){
    std::vector<int> p;
    for(int k:keys){p.push_back(opcode);p.push_back(k);}
    p.insert(p.end(),{15,0});return p;
}
static int run(Hamster& h,const std::vector<int>& words,bool preserve_reg=false){
    int at=h.params.layout.program_start;
    for(int w:words){
        for(bool bit:SpiralToken(w,h.params.op_order,h.params.op_lvl).bits)
            h.memory.at(at++)=bit;
    }
    if(!preserve_reg)std::fill(h.val_reg.begin(),h.val_reg.end(),false);
    h.stop=false;h.tree_capacity_blocked=false;
    h.executed_steps=0;h.step_limit=300;
    h.pro_1=h.params.layout.program_start;h.pro_2=at-1;
    simulate_spiral_program(h);
    int id=0;for(int b=0;b<h.params.tree_id_bits;++b)
        id=(id<<1)|int(h.val_reg[b]);
    return id;
}
static HamsterParams config(int cap,int id_bits=10){
    HamsterParams p;
    p.layout.status_start=45;p.layout.output_start=50;p.layout.work_start=80;
    p.tree_id_bits=id_bits;p.tree_capacity=cap;
    p.tree_start=350;
    p.layout.program_start=350+cap*(p.tree_id_bits+7);
    p.stable_work_bits=cap*(p.tree_id_bits+7);
    p.layout.total_size=p.layout.program_start+1024;
    p.layout.val_reg_size=20;
    return p;
}
int main(int argc,char** argv){
    const bool stress=argc>1 && std::string(argv[1])=="--stress-3000";
    const int total_paths=stress?3000:600;
    const auto p=config(8,stress?12:10);Hamster h(1,p);
    int first=0,last=0,max_id=0,growth_events=0;
    unsigned long long scans_before=h.tree_lookup_rows_examined;
    for(int n=0;n<total_paths;++n){
        int id=0;
        for(;;){
            id=run(h,program(28,key(n)));
            if(!h.tree_capacity_blocked)break;
            const int old_capacity=h.params.tree_capacity;
            require(old_capacity<(1<<h.params.tree_id_bits)-1,"unexpected ID-width exhaustion");
            auto old_memory=h.memory;
            const int old_program=h.params.layout.program_start;
            const int old_pro1=h.pro_1,old_pro2=h.pro_2;
            h.grow_wide_tree_capacity(std::min((1<<h.params.tree_id_bits)-1,old_capacity*2));
            const int shift=h.params.layout.program_start-old_program;
            require(h.pro_1==old_pro1+shift && h.pro_2==old_pro2+shift,
                    "program execution window not relocated");
            for(int j=0;j<12;++j)
                require(h.memory[h.params.layout.program_start+j]==
                        old_memory[old_program+j],"program bits not relocated");
            require(run(h,program(27,key(0)))==(n?first:0),
                    "old handle changed after growth");
            ++growth_events;
        }
        require(id>0 && h.val_reg[p.tree_id_bits],"wide VM did not return handle");
        if(n==0)first=id;
        last=id;max_id=std::max(max_id,id);
        if(n%53==0){
            require(run(h,program(27,key(n)))==id,"wide VM find mismatch");
            require(run(h,program(27,key(0)))==first,"old handle moved");
        }
    }
    require(max_id>(stress?1023:255) && growth_events>=(stress?9:7),
            "test did not cross multiple growth boundaries");
    require(h.tree_lookup_rows_examined>scans_before,
            "native tree scan costs were not counted");
    require(run(h,program(27,key(total_paths-1)))==last,"wide final handle lost");
    require(run(h,program(27,key(0)))==first,"wide first handle lost");
    // TREE_ACTION uses the same VM opcode with a wider handle register ABI.
    require(run(h,program(27,key(0)))==first,"failed to select action leaf");
    h.val_reg[p.tree_id_bits+1]=true;
    h.val_reg[p.tree_id_bits+2]=false;  // memorized option 2
    run(h,{30,1,15,0},true);
    require(h.val_reg[p.tree_id_bits],"wide action did not commit");
    run(h,program(27,key(0)));
    run(h,{30,0,15,0},true);
    require(h.val_reg[p.tree_id_bits] &&
            h.val_reg[p.tree_id_bits+1] && !h.val_reg[p.tree_id_bits+2],
            "wide action did not persist option 2");
    bool unpublished_rejected=false;
    try{Hamster bad(99,h.params);bad.copy_hamu(h);}
    catch(const std::invalid_argument&){unpublished_rejected=true;}
    require(unpublished_rejected,"unpublished growth checkpoint was accepted");
    h.new_his();Hamster child(2,h.params);child.copy_hamu(h);
    require(run(child,program(27,key(0)))==first,"wide inherited first handle mismatch");
    run(child,{30,0,15,0},true);
    require(child.val_reg[p.tree_id_bits] && child.val_reg[p.tree_id_bits+1],
            "wide inherited answer mismatch");
    require(run(child,program(27,key(total_paths-1)))==last,"wide inherited final handle mismatch");
    bool reject=false;
    auto q=h.params;q.tree_id_bits=9;
    try{Hamster bad(3,q);bad.copy_hamu(h);}catch(const std::invalid_argument&){reject=true;}
    require(reject,"mismatched ID width accepted as snapshot");
    // Atomic rollback if one path runs out of capacity mid-execution.
    const auto tiny_config=config(3);Hamster tiny(5,tiny_config);
    const auto bits=tiny.memory;
    const int fail=run(tiny,program(28,key(0)));
    require(!fail && tiny.tree_capacity_blocked,"capacity failure not signaled");
    for(int i=tiny_config.tree_start;i<tiny_config.layout.program_start;++i)
        require(tiny.memory[i]==bits[i],"partial path survived capacity failure");
    require(run(tiny,program(28,{1,2,3}))==3,"full three-node path not stored");
    require(!tiny.tree_capacity_blocked,"unexpected capacity signal");
    require(run(tiny,program(27,{1,2,3}))==3,"failed to find valid full path");
    const auto before=tiny.memory;
    require(run(tiny,program(28,{1,2,4,5}))==0 && tiny.tree_capacity_blocked,
            "full tree did not reject new path");
    for(int i=tiny_config.tree_start;i<tiny_config.layout.program_start;++i)
        require(tiny.memory[i]==before[i],"refusal modified existing tree");
    require(run(tiny,program(27,{1,2,3}))==3,"refusal destroyed old answer");
    // Explicit host growth should preserve old handles and live program bytes.
    tiny.grow_wide_tree_capacity(8);
    require(tiny.params.tree_capacity==8,"wide tree cap not changed");
    require(run(tiny,program(27,{1,2,3}))==3,"growth moved old handle");
    require(run(tiny,program(28,{1,2,4,5}))==5 && !tiny.tree_capacity_blocked,
            "retry after capacity growth failed");
    require(run(tiny,program(27,{1,2,3}))==3,"growth+retry lost old handle");
    tiny.new_his();Hamster grown_child(6,tiny.params);grown_child.copy_hamu(tiny);
    require(run(grown_child,program(27,{1,2,4,5}))==5,
            "grown snapshot failed to inherit new handle");
    std::cout<<"PASS guest VM wide tree "<<total_paths<<" paths, maximum handle "<<max_id
             <<", capacity "<<h.params.tree_capacity<<", "<<growth_events
             <<" dynamic growth events, scanned_rows="<<h.tree_lookup_rows_examined
             <<", reserved_tree_bits="<<h.params.tree_capacity*(h.params.tree_id_bits+7)
             <<", index_slots="<<h.tree_index_slots.size()
             <<", index_allocated_bytes="<<h.tree_index_slots.capacity()*sizeof(uint32_t)
             <<", index_probes="<<h.tree_index_probes
             <<", inheritance, action memory, layout mismatch, atomic full refusal\n";
}
