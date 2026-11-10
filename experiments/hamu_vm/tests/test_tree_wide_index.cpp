#include "../src/hamu_vm_core.hpp"
#include <iostream>
#include <stdexcept>
#include <vector>
#include <algorithm>
#include <cassert>
static void req(bool ok,const char* s){if(!ok)throw std::runtime_error(s);}
static std::vector<int> key(int n){return {7,(n>>9)&7,(n>>6)&7,(n>>3)&7,n&7};}
static std::vector<int> program(int op,const std::vector<int>& k){
 std::vector<int> p; for(int x:k){p.push_back(op);p.push_back(x);}p.insert(p.end(),{15,0});return p;
}
static int run(Hamster& h,const std::vector<int>& words,bool keep_reg=false){
 const int base=h.params.layout.program_start;int at=base;
 for(int w:words)for(bool bit:SpiralToken(w,h.params.op_order,h.params.op_lvl).bits)h.memory.at(at++)=bit;
 if(!keep_reg)std::fill(h.val_reg.begin(),h.val_reg.end(),false);
 h.stop=false;h.tree_capacity_blocked=false;h.executed_steps=0;h.step_limit=250;
 h.pro_1=base;h.pro_2=at-1;simulate_spiral_program(h);
 int id=0;for(int i=0;i<h.params.tree_id_bits;++i)id=(id<<1)|int(h.val_reg[i]);return id;
}
static HamsterParams config(bool index,int bits=10){
 HamsterParams p;p.layout.status_start=45;p.layout.output_start=50;p.layout.work_start=80;
 p.tree_id_bits=bits;p.tree_capacity=8;p.tree_start=350;
 p.layout.program_start=350+8*(bits+7);p.stable_work_bits=8*(bits+7);
 p.layout.total_size=p.layout.program_start+1024;p.layout.val_reg_size=20;
 p.tree_index_enabled=index;return p;
}
static void same(const Hamster& a,const Hamster& b,const char* where){
 req(a.params.tree_capacity==b.params.tree_capacity,"capacity mismatch");
 req(a.params.layout.program_start==b.params.layout.program_start,"program start mismatch");
 req(a.memory==b.memory,where);
 req(a.val_reg==b.val_reg,"register mismatch");
}
int main(int argc,char** argv){
 const bool stress=argc>1 && std::string(argv[1])=="--stress-3000";
 const int paths=stress?3000:600;
 const int bits=stress?12:10;
 Hamster fast(1,config(true,bits)), slow(2,config(false,bits));
 int first=0,last=0,grows=0;
 for(int n=0;n<paths;++n){
  for(;;){
   int x=run(fast,program(28,key(n))),y=run(slow,program(28,key(n)));
   req(x==y,"add handle mismatch");req(fast.tree_capacity_blocked==slow.tree_capacity_blocked,"full status mismatch");
   same(fast,slow,"add changed canonical rows");
   if(!fast.tree_capacity_blocked){if(n==0)first=x;last=x;break;}
   const int new_cap=std::min((1<<bits)-1,fast.params.tree_capacity*2);
   fast.grow_wide_tree_capacity(new_cap);slow.grow_wide_tree_capacity(new_cap);++grows;
   same(fast,slow,"growth changed canonical rows");
  }
  if(n%73==0){
   int x=run(fast,program(27,key(n))),y=run(slow,program(27,key(n)));
   req(x==y&&x!=0,"find mismatch");same(fast,slow,"find changed canonical rows");
  }
 }
 req(last>(stress?1023:255)&&grows>=(stress?9:7),"did not grow");
 if(stress) {
  req(run(fast,program(27,key(0)))==run(slow,program(27,key(0))),"stress early handle divergence");
  req(run(fast,program(27,key(paths-1)))==run(slow,program(27,key(paths-1))),"stress late handle divergence");
  same(fast,slow,"stress final canonical tree mismatch");
  std::cout<<"PASS 3000-path VM indexed/linear differential: nodes="<<last
           <<", grows="<<grows<<", indexed_rows="<<fast.tree_lookup_rows_examined
           <<", linear_rows="<<slow.tree_lookup_rows_examined
           <<", packed_index_bytes="<<fast.tree_index_slots.capacity()*sizeof(uint32_t)
           <<", hash_probes="<<fast.tree_index_probes<<"\n";
  return 0;
 }
 // Duplicate insertion is not a second node.
 req(run(fast,program(28,key(0)))==first,"indexed duplicate");
 req(run(slow,program(28,key(0)))==first,"linear duplicate");
 same(fast,slow,"duplicate mutated tree");
 // Store action and compare its inherited value.
 req(run(fast,program(27,key(0)))==first,"select indexed leaf");
 req(run(slow,program(27,key(0)))==first,"select linear leaf");
 fast.val_reg[11]=slow.val_reg[11]=true;
 fast.val_reg[12]=slow.val_reg[12]=false;
 run(fast,{30,1,15,0},true);run(slow,{30,1,15,0},true);
 same(fast,slow,"action changed canonical rows");
 // Editing a structural bit through guest WRITE_0 must invalidate cache.
 req(run(fast,program(27,key(599)))==last,"indexed final selection");
 req(run(slow,program(27,key(599)))==last,"linear final selection");
 const int last_row=fast.params.tree_start+(last-1)*(fast.params.tree_id_bits+7);
 fast.ptr=slow.ptr=last_row;
 const auto invalid0=fast.tree_index_invalidations;
 run(fast,{3,1,15,0},true);run(slow,{3,1,15,0},true);
 req(fast.tree_index_invalidations>invalid0,"guest row mutation did not invalidate");
 same(fast,slow,"guest row mutation mismatch");
 req(run(fast,program(27,key(599)))==0,"deleted path remained in index");
 req(run(slow,program(27,key(599)))==0,"deleted path remained in linear lookup");
 req(run(fast,program(28,key(599)))==last,"recycled node changed ID indexed");
 req(run(slow,program(28,key(599)))==last,"recycled node changed ID linear");
 same(fast,slow,"recycled row mismatch");
 // Rebuild from canonical rows, not from a secretly inherited hash table.
 fast.new_his();slow.new_his();Hamster fchild(3,fast.params),schild(4,slow.params);
 fchild.copy_hamu(fast);schild.copy_hamu(slow);
 req(!fchild.tree_index_valid,"cache should not inherit as state");
 req(run(fchild,program(27,key(599)))==last,"indexed child lost learned path");
 req(run(schild,program(27,key(599)))==last,"linear child lost learned path");
 same(fchild,schild,"child canonical mismatch");
 req(run(fchild,program(27,key(0)))==first,"indexed child lost old path");
 run(fchild,{30,0,15,0},true);
 req(fchild.val_reg[10]&&fchild.val_reg[11]&&!fchild.val_reg[12],"child action lost");
 // Failed long add rolls back all rows and invalidates derived cache.
 Hamster ft(5,config(true)),st(6,config(false));ft.grow_wide_tree_capacity(9);st.grow_wide_tree_capacity(9);
 req(run(ft,program(28,key(0)))==5,"tiny indexed baseline");
 req(run(st,program(28,key(0)))==5,"tiny linear baseline");
 req(run(ft,program(28,key(512)))==9,"tiny indexed fill");
 req(run(st,program(28,key(512)))==9,"tiny linear fill");
 same(ft,st,"small tree canonical mismatch");
 const auto before=ft.memory;
 req(run(ft,program(28,key(256)))==0&&ft.tree_capacity_blocked,"indexed failure not reported");
 req(run(st,program(28,key(256)))==0&&st.tree_capacity_blocked,"linear failure not reported");
 req(std::equal(before.begin()+ft.params.tree_start,before.begin()+ft.params.layout.program_start,ft.memory.begin()+ft.params.tree_start),"indexed atomic rollback failed");same(ft,st,"rollback divergence");
 ft.grow_wide_tree_capacity(20);st.grow_wide_tree_capacity(20);
 req(run(ft,program(28,key(256)))==run(st,program(28,key(256))),"retry divergence");
 same(ft,st,"post-retry divergence");
 req(fast.tree_lookup_rows_examined<slow.tree_lookup_rows_examined/20,"index did not reduce scans");
 std::cout<<"PASS: VM indexed/linear differential 600 paths, "<<grows<<" grows, reused ID, guest edit, inheritance, rollback/retry\n"
          <<"indexed scanned_rows="<<fast.tree_lookup_rows_examined
          <<", linear scanned_rows="<<slow.tree_lookup_rows_examined
          <<", cache_builds="<<fast.tree_index_rebuilds
          <<", cache_lookups="<<fast.tree_index_lookups
          <<", cache_updates="<<fast.tree_index_updates
          <<", live_index_entries="<<fast.tree_index_count
          <<", cache_bytes="<<fast.tree_index_slots.size()*sizeof(uint32_t)
          <<", cache_probes="<<fast.tree_index_probes
          <<", next_free_id="<<fast.tree_first_free_id<<"\n";
}
