#define main prior_reject_main
#include "test_tree_reject_mask.cpp"
#undef main
static HamsterParams extended(){auto p=cfg(true,2);p.tree_confirm_three_bits_enabled=true;return p;}
static void confirm3(Hamster& h,int id,int answer,int mode){set_id_candidate(h,id,answer);execute(h,{30,mode,15,0});}
int main(){
 int checks=0;
 for(int initial=0;initial<8;++initial){
  for(int legacy=0;legacy<4;++legacy){
   Hamster h(5000+initial*4+legacy,extended());
   set_id_candidate(h,0,0);execute(h,{28,1,15,0});
   mark(h,1,0);mark(h,1,7);
   confirm3(h,1,initial,5);
   const uint32_t mask=h.segment_row(1)&(255u<<23);
   set_id_candidate(h,1,0);h.val_reg[17]=(legacy>>1)&1;h.val_reg[18]=legacy&1;execute(h,{30,1,15,0});
   confirm3(h,1,0,4);
   int actual=0;for(int b=17;b<=19;++b)actual=(actual<<1)|int(h.val_reg[b]);
   require(h.val_reg[16]&&actual==legacy,"legacy write failed to clear high answer bit");
   require((h.segment_row(1)&(255u<<23))==mask,"legacy write damaged rejection mask");
   confirm3(h,1,7,5);
   set_id_candidate(h,1,0);execute(h,{30,0,15,0});
   require(h.val_reg[16]&&h.val_reg[17]&&h.val_reg[18],"legacy read did not preserve low bits");
   confirm3(h,1,0,4);
   actual=0;for(int b=17;b<=19;++b)actual=(actual<<1)|int(h.val_reg[b]);
   require(actual==7,"new read after legacy read failed");
   ++checks;
  }
 }
 std::cout<<"PASS "<<checks<<" mixed ABI writes/read combinations, rejection mask preserved\n";
}
