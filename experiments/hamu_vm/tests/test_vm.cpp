#include "../src/hamu_vm_core.hpp"
#include <cassert>
#include <iostream>
#include <random>

static void load(Hamster& h, std::initializer_list<int> words) {
    int at=h.params.layout.program_start;
    std::fill(h.memory.begin()+at,h.memory.end(),false);
    for(int v:words) for(bool b:SpiralToken(v,h.params.op_order,h.params.op_lvl).bits) h.memory.at(at++)=b;
    h.pro_1=h.params.layout.program_start; h.pro_2=at-1;
}
static Problem question(int v,int n=2) {
    Problem p; p.type=ProblemType::EAZY;
    p.question={SpiralToken(0,n,1),SpiralToken(v,n,1)};
    p.answer=SpiralToken(v,n,1); return p;
}
static void copy_test(int vmn,int taskn) {
    HamsterParams p; p.op_order=vmn; p.layout.total_size=200;
    const int sign=1<<(vmn-1);
    Hamster donor(0,p);
    load(donor,{14,sign+taskn+2,4,taskn+1,0,2,14,sign+1,9,taskn+1,15});
    donor.new_his(); Hamster archive(1,p); archive.copy_hamu(donor);
    Hamster child(2,p); child.copy_hamu(archive);
    for(int v=0;v<(1<<taskn);++v) {
        child.write_prob(question(v,taskn)); simulate_spiral_program(child);
        assert(Check_ans(child,question(v,taskn)));
    }
}
int main() {
    assert(decodeSpiral(std::vector<bool>{0,0,0},2,1).value==0);
    assert(decodeSpiral(std::vector<bool>{0,0,0},1,2).value==0);
    assert(decode_op(SpiralToken(4,4,1))==decode_op(SpiralToken(4,5,1)));
    bool rejected=false; try{SpiralToken bad(4,2,1);}catch(const std::invalid_argument&){rejected=true;} assert(rejected);
    assert(HamsterParams{}.op_order==5);
    HamsterParams p; p.op_order=4; p.layout.total_size=200; p.layout.val_reg_size=16;
    { Hamster h(0,p); h.write_prob(question(3)); const auto before=h.memory;
      load(h,{4,7,15}); simulate_spiral_program(h);
      for(int i=0;i<7;++i) assert(h.val_reg[i]==before[i]);
      for(int i=0;i<p.layout.status_start;++i) assert(h.memory[i]==before[i]); }
    { Hamster a(0,p),b(1,p),c(2,p); a.memory[90]=true;a.val_reg[2]=true;a.new_his();
      b.copy_hamu(a);c.copy_hamu(b);assert(c.memory[90]&&c.val_reg[2]);
      c.pro_1=190;c.pro_2=100;c.executed_steps=3;float hp=c.hp;c.use_hp();assert(c.hp<hp); }
    { Hamster h(0,p); Problem q; q.question={SpiralToken(1,18,1)};h.write_prob(q);assert(h.memory[18]);
      auto before=h.memory;q.question={SpiralToken(1,19,1)};bool bad=false;
      try{h.write_prob(q);}catch(const std::invalid_argument&){bad=true;}assert(bad&&before==h.memory); }
    copy_test(4,2);copy_test(5,2);copy_test(4,3);
    { Hamster h(0,p); auto q=question(0);h.write_prob(q); assert(!Check_ans(h,q));
      for(int i=31;i<34;++i)h.written[i]=true;assert(Check_ans(h,q));
      h.written[34]=true;assert(!Check_ans(h,q));h.write_prob(q);assert(!Check_ans(h,q)); }
    { Hamster h(0,p);h.write_prob(question(3));load(h,{14,9,10,3,15});
      auto before=h.memory;simulate_spiral_program(h);assert(before==h.memory); }
    { Hamster h(0,p);h.params.strict_work_insert=false; // legacy VAG exchange test
      h.write_prob(question(1));load(h,{0,3,10,2,15});
      h.memory[78]=true;h.val_reg[0]=true;simulate_spiral_program(h);
      assert(h.memory[60]&&h.val_reg[0]);
      load(h,{0,3,11,2,15});h.stop=false;simulate_spiral_program(h);
      assert(h.val_reg[0]); }
    { Hamster h(0,p);h.write_prob(question(1));load(h,{0,0,0,0,0,0,15});
      h.step_limit=2;simulate_spiral_program(h);assert(h.stop&&h.budget_exhausted&&h.executed_steps==2); }
    { // n=4 preserves the original SET_AREA 8 alias for input area.
      Hamster h(0,p);h.ptr=61;load(h,{0,8,15});simulate_spiral_program(h);
      assert(h.ptr==p.layout.input_start);
    }
    HamsterParams jumping=p;jumping.op_order=5;
    { // Without a version mark, zero-valued n=2 and n=3 questions collide.
      Hamster h(0,jumping);
      h.write_prob(question(0,2));
      const auto zero2=std::vector<bool>(h.memory.begin(),h.memory.begin()+jumping.layout.status_start);
      h.write_prob(question(0,3));
      const auto zero3=std::vector<bool>(h.memory.begin(),h.memory.begin()+jumping.layout.status_start);
      assert(zero2==zero3);
      for(int tag=0;tag<=1;++tag) {
        h.write_prob(question(0,tag?3:2),tag);
        assert(h.memory[jumping.layout.status_start-1]==static_cast<bool>(tag));
        load(h,{0,1,14,1,4,1,15});
        simulate_spiral_program(h);
        assert(h.val_reg[0]==static_cast<bool>(tag));
      }
      bool rejected=false;
      try {h.write_prob(question(0),2);}catch(const std::invalid_argument&){rejected=true;}
      assert(rejected);
    }
    assert(decode_op(SpiralToken(16,5,1))==SpiralOp::JUMP_MODE);
    assert(decode_op(SpiralToken(17,5,1))==SpiralOp::JUMP_IF_1);
    assert(decode_op(SpiralToken(18,5,1))==SpiralOp::JUMP_IF_LOCAL);
    { // New n=5 opcode 16: immediate jump skips the write at word 4.
      Hamster h(0,jumping);h.write_prob(question(1));
      load(h,{16,1,12,22,2,1,0,3,2,1,15});h.ptr=p.layout.work_start+1;
      simulate_spiral_program(h);
      assert(h.memory[p.layout.work_start] && !h.memory[p.layout.work_start+1]);
      assert(h.stop && !h.budget_exhausted);
    }
    { // New n=5 opcode 16: deferred switch after the original window.
      Hamster h(0,jumping);h.write_prob(question(1));
      load(h,{16,0,12,22,13,22,0,3,2,1,15});
      h.pro_2=p.layout.program_start+6*(jumping.op_order+jumping.op_lvl)-1;
      simulate_spiral_program(h);
      assert(h.memory[p.layout.work_start] && h.stop && !h.budget_exhausted);
    }
    { // READ chooses one of two paths; zero stops before the one branch.
      for (int bit=0;bit<=1;++bit) {
        Hamster h(0,jumping);h.write_prob(question(bit));
        h.memory[jumping.layout.work_start]=bit;
        load(h,{0,3,4,1,0,2,16,1,17,30,3,1,15,0,2,1,15});
        simulate_spiral_program(h);
        assert(h.read_seen[jumping.layout.work_start]);
        assert(h.written[jumping.layout.output_start]);
        assert(h.memory[jumping.layout.output_start]==static_cast<bool>(bit));
        assert(h.stop&&!h.budget_exhausted);
      }
    }
    { // Backward jump to the same code is bounded, even without OUT_AREA.
      Hamster h(0,jumping);h.write_prob(question(1));
      load(h,{16,1,12,20,12,4});h.step_limit=9;
      simulate_spiral_program(h);assert(h.stop&&h.budget_exhausted&&h.executed_steps==9);
    }
    { // Host expands capacity; old and appended code survive two-hop inheritance.
      Hamster h(0,jumping);load(h,{0,2,2,1,15});
      const int oldEnd=h.pro_2, oldSize=h.memory.size(), width=6;
      int newStart=jumping.layout.program_start;
      while(newStart+width<=oldSize)newStart+=width;
      h.extend_program_capacity(6);
      assert(h.memory.size()==oldSize+6*width && h.pro_2==oldEnd);
      int at=newStart;
      for(int value:{0,2,3,1,15})
        for(bool bit:SpiralToken(value,5,1).bits)h.memory.at(at++)=bit;
      h.new_his();Hamster archive(1,jumping),child(2,jumping);
      archive.copy_hamu(h);child.copy_hamu(archive);
      assert(child.memory.size()==h.memory.size());
      for(int variant=0;variant<2;++variant) {
        child.write_prob(question(variant));
        child.pro_1=variant ? newStart : jumping.layout.program_start;
        child.pro_2=variant ? at-1 : oldEnd;
        simulate_spiral_program(child);
        assert(child.written[jumping.layout.output_start]);
        assert(child.memory[jumping.layout.output_start]==(variant==0));
      }
    }
    { // One inherited program reads the explicit version bit and routes 12 cases.
      HamsterParams q=jumping;q.layout.total_size=q.layout.program_start+60;
      Hamster donor(0,q);donor.extend_program_capacity(36);
      const int words[]={0,1,14,1,4,1,16,1,18,31,
                         0,0,14,20,4,3,0,2,14,17,9,3,15,
                         0,0,14,21,4,4,0,2,14,17,9,4,15};
      int at=q.layout.program_start;
      for(int v:words)for(bool bit:SpiralToken(v,5,1).bits)donor.memory.at(at++)=bit;
      donor.new_his();Hamster archive(1,q),child(2,q);
      archive.copy_hamu(donor);child.copy_hamu(archive);
      int passed=0;
      for(int version=0;version<2;++version) {
        const int order=version?3:2;
        for(int value=0;value<(1<<order);++value) {
          const auto problem=question(value,order);
          child.write_prob(problem,version);
          child.pro_1=q.layout.program_start;child.pro_2=at-1;
          simulate_spiral_program(child);
          assert(!child.budget_exhausted);
          passed+=Check_ans(child,problem);
        }
      }
      assert(passed==12);
      for(int version=0;version<2;++version) {
        const auto problem=question(version?4:1,version?3:2);
        child.write_prob(problem,1-version);
        child.pro_1=q.layout.program_start;child.pro_2=at-1;
        simulate_spiral_program(child);
        assert(!Check_ans(child,problem));
      }
    }
    // Deterministic hostile guest genomes; immutable input/status/code and bounded work.
    std::mt19937 rng(927);
    for(int trial=0;trial<3000;++trial) {
        Hamster h(0,p);for(size_t i=0;i<h.memory.size();++i)h.memory[i]=rng()&1;
        h.write_prob(question(trial%4));const auto before=h.memory;
        h.step_limit=8;simulate_spiral_program(h);
        for(int i=0;i<p.layout.output_start;++i)assert(h.memory[i]==before[i]);
        for(int i=p.layout.program_start;i<p.layout.total_size;++i)assert(h.memory[i]==before[i]);
        assert(h.executed_steps<=h.step_limit);
    }
    { // Random five-bit genomes include mode changes and conditional branches.
      HamsterParams q=jumping;q.layout.total_size=256;
      for(int trial=0;trial<3000;++trial) {
        Hamster h(0,q);h.write_prob(question(trial%4));
        const int start=q.layout.program_start;
        for(int j=0;j<20;++j) {
          int code=rng()%32;
          int at=start+j*6;
          for(bool bit:SpiralToken(code,5,1).bits)h.memory.at(at++)=bit;
        }
        h.pro_1=start;h.pro_2=start+20*6-1;
        const auto before=h.memory;
        h.step_limit=24;simulate_spiral_program(h);
        for(int i=0;i<q.layout.output_start;++i)assert(h.memory[i]==before[i]);
        for(int i=q.layout.program_start;i<q.layout.total_size;++i)assert(h.memory[i]==before[i]);
        assert(h.executed_steps<=h.step_limit);
      }
    }
    std::cout<<"PASS: decoding, READ, inheritance, I/O, COPY, branching, protection, budget; 6000 random guests\n";
}
