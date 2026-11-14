#include "../src/hamu_vm_core.hpp"
#include <cstdint>
#include <iostream>
#include <random>

int main(){
    std::mt19937 rng(91517);uint64_t hash=1469598103934665603ull;
    auto add=[&](bool bit){hash=(hash^uint64_t(bit+1))*1099511628211ull;};
    auto number=[&](int n){for(int i=0;i<32;++i)add((uint32_t(n)>>i)&1);};
    for(int trial=0;trial<6000;++trial){
        HamsterParams p;p.op_order=trial%2?4:5;
        p.layout.total_size=2048;p.layout.val_reg_size=12;
        Hamster h(0,p);const int width=p.op_order+p.op_lvl;
        for(int i=0;i<80;++i)h.memory[i]=rng()&1;
        for(int i=0;i<12;++i)h.val_reg[i]=rng()&1;
        for(int i=0;i<160;++i){
            const int start=p.layout.program_start+i*width;
            const auto bits=SpiralToken(int(rng()%(1<<p.op_order)),p.op_order,p.op_lvl).bits;
            for(int j=0;j<width;++j)h.memory[start+j]=bits[j];
        }
        h.pro_1=p.layout.program_start+(trial%4==0?width*(rng()%30):0);
        h.pro_2=p.layout.program_start+160*width-1-(trial%5==0?rng()%width:0);
        h.step_limit=4+int(rng()%60);
        h.ptr=int(rng()%100);h.val_ptr=int(rng()%12);
        simulate_spiral_program(h);
        for(bool b:h.memory)add(b);
        for(bool b:h.written)add(b);
        for(bool b:h.read_seen)add(b);
        for(bool b:h.val_reg)add(b);
        number(h.ptr);number(h.val_ptr);number(h.pro_1);number(h.pro_2);
        number(h.executed_steps);add(h.stop);add(h.budget_exhausted);add(h.work_insert_blocked);
    }
    if(hash!=0x88c085a021cbfdb7ull)throw std::runtime_error("old VM state differs");
    std::cout<<"PASS 6000 old/new VM state snapshots: "<<std::hex<<hash<<'\n';
}
