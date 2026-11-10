#define main previous_reject_mask_main
#include "test_tree_reject_mask.cpp"
#undef main
static HamsterParams extended(bool enable=true){auto p=cfg(true,2);p.tree_confirm_three_bits_enabled=enable;return p;}
static void confirm3(Hamster& h,int id,int answer,int mode){set_id_candidate(h,id,answer);execute(h,{30,mode,15,0});}
int main(){
 int checks=0;
 for(int answer=0;answer<8;++answer){
  Hamster h(answer+1000,extended());set_id_candidate(h,0,0);execute(h,{28,1,15,0});
  mark(h,1,0);mark(h,1,7);
  const uint32_t before=h.segment_row(1);
  confirm3(h,1,answer,5);
  require(h.val_reg[16]&&h.val_reg[20],"commit failed");
  require((h.segment_row(1)&(255u<<23))==(before&(255u<<23)),"commit corrupted rejected mask");
  confirm3(h,1,0,4);
  require(h.val_reg[16]&&h.val_reg[20],"read failed");
  int actual=0;for(int b=17;b<=19;++b)actual=(actual<<1)|int(h.val_reg[b]);
  require(actual==answer,"wrong three-bit answer");
  h.new_his();Hamster child(2000+answer,h.params);child.copy_hamu(h);
  confirm3(child,1,0,4);int inherited=0;for(int b=17;b<=19;++b)inherited=(inherited<<1)|int(child.val_reg[b]);
  require(child.val_reg[16]&&inherited==answer,"inheritance failed");
  const auto snapshot=h.segment_pages;
  confirm3(h,1,(answer+1)%8,5);
  require(child.segment_pages==snapshot,"offspring isolation failed");
  // A failed capacity transaction must roll back a new confirmation.
  Hamster rollback(3000+answer,extended());set_id_candidate(rollback,0,0);execute(rollback,{28,1,15,0});
  const auto old=rollback.segment_pages;
  set_id_candidate(rollback,1,answer);execute(rollback,{30,5,28,2,28,3,28,4,15,0});
  require(rollback.tree_capacity_blocked,"capacity guard not triggered");
  require(rollback.segment_pages==old,"three-bit commit not rolled back");
  ++checks;
 }
 Hamster old(10,extended(false));set_id_candidate(old,0,0);execute(old,{28,1,15,0});
 const auto old_row=old.segment_row(1);confirm3(old,1,7,5);
 require(old.segment_row(1)==old_row,"disabled ABI mutated old snapshot");
 Hamster newer(11,extended());newer.new_his();bool blocked=false;
 try{old.copy_hamu(newer);}catch(const std::invalid_argument&){blocked=true;}
 require(blocked,"incompatible ABI copy accepted");
 std::cout<<"PASS "<<checks<<" three-bit answers: commit/read, mask isolation, inheritance, rollback, ABI gate\n";
}
