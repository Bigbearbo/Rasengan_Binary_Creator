#include "../src/context_choice_vm.hpp"
#include "../src/hamu_vm_core.hpp"
#include <cassert>
#include <iostream>

int main() {
    auto a=context_choice_program(0),b=context_choice_program(2);
    HamsterParams p;p.op_order=5;p.layout.status_start=45;p.layout.output_start=50;
    p.layout.work_start=80;p.layout.program_start=140;p.stable_work_bits=20;
    const int second=140+int(a.size())*6;
    p.layout.total_size=second+int(b.size())*6;
    Hamster h(107,p);int at=140;
    for(const auto& program:{a,b})
        for(int word:program)for(bool bit:SpiralToken(word,5,1).bits)h.memory.at(at++)=bit;
    auto choose=[&](Hamster& guest,int base)->int {
        Problem blank;guest.write_prob(blank);
        guest.pro_1=base?second:140;
        guest.pro_2=base?p.layout.total_size-1:second-1;
        guest.step_limit=45;simulate_spiral_program(guest);
        assert(!guest.budget_exhausted);
        if(!guest.written[51])return -1;
        assert(guest.written[52]&&guest.written[53]&&!guest.memory[51]&&!guest.memory[53]);
        return guest.memory[52];
    };
    for(int base:{0,2}) {
        h.memory[120+base]=1;h.memory[121+base]=1;
        assert(choose(h,base)==0);
        h.memory[120+base]=0;
        assert(choose(h,base)==1);
        h.memory[121+base]=0;
        assert(choose(h,base)==-1);
    }
    h.memory[120]=1;h.memory[123]=1;
    h.new_his();Hamster child(108,p);child.copy_hamu(h);
    assert(choose(child,0)==0&&choose(child,2)==1);
    std::cout<<"PASS independent two-candidate contexts: 11->0, 01->1, 00->stop, inherited\n";
}
