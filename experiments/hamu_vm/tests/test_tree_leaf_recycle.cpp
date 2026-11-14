#define main prior_reject_main
#include "test_tree_reject_mask.cpp"
#undef main
static HamsterParams extended(){auto p=cfg(true,3);p.tree_confirm_three_bits_enabled=true;return p;}
static void confirm3(Hamster& h,int id,int answer,int mode){set_id_candidate(h,id,answer);execute(h,{30,mode,15,0});}
// Host-only prototype: never expose this as an unguarded guest opcode.
static bool recycle_leaf(Hamster& h,int id){
 if(id<1||id>h.params.tree_capacity || !(h.segment_row(id)&1u))return false;
 const unsigned bits=h.params.tree_id_bits;
 for(int other=1;other<=h.params.tree_capacity;++other){
  uint32_t row=h.segment_row(other);
  if(other!=id && (row&1u) && (row>>7)==unsigned(id))return false;
 }
 h.segment_row_ref(id)=0;
 h.invalidate_segment_index();
 h.rebuild_segment_first_free_id();
 return true;
}
int main(){
 Hamster h(6001,extended());
 set_id_candidate(h,0,0);execute(h,{28,1,15,0});
 require((h.segment_row(1)&1u)!=0,"initial add");
 mark(h,1,0);mark(h,1,7);confirm3(h,1,7,5);
 require((h.segment_row(1)&(1u<<31))!=0,"high answer bit setup");
 // Nonleaf deletion must be refused, preserving both records.
 set_id_candidate(h,1,1);execute(h,{28,1,15,0});
 require((h.segment_row(2)&1u)!=0,"child add");
 require(!recycle_leaf(h,1),"nonleaf deletion accepted");
 require((h.segment_row(1)&1u)!=0,"parent destroyed");
 require(recycle_leaf(h,2),"leaf deletion failed");
 require(h.segment_row(2)==0,"deleted leaf retained bits");
 require(recycle_leaf(h,1),"root leaf deletion failed");
 require(h.segment_row(1)==0,"deleted root retained answer/rejection bits");
 set_id_candidate(h,0,0);execute(h,{28,1,15,0});
 require((h.segment_row(1)&1u)!=0,"reallocation failed");
 require((h.segment_row(1)&(14u|(255u<<23)|(1u<<31)))==0,"reused row retained old metadata");
 for(int c=0;c<8;++c)require(!rejected(h,1,c),"reused row retained rejection");
 confirm3(h,1,0,4);require(!h.val_reg[16],"reused row retained confirmation");
 // A copied offspring inherits canonical rows, not a stale derived index.
 h.new_his();Hamster child(6002,h.params);child.copy_hamu(h);
 require(child.segment_row(1)==h.segment_row(1),"offspring row mismatch");
 std::cout<<"PASS host-only guarded leaf recycle, 3-bit and reject cleanup, index invalidation, reuse, offspring\n";
}
