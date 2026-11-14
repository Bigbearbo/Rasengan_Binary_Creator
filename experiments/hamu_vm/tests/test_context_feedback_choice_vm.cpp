#include "../src/context_feedback_choice_vm.hpp"
#include "../src/hamu_vm_core.hpp"
#include <array>
#include <cassert>
#include <iostream>

int main() {
    HamsterParams p;p.op_order=5;p.layout.status_start=45;p.layout.output_start=50;
    p.layout.work_start=80;p.layout.program_start=140;p.stable_work_bits=20;
    std::array<std::vector<int>,4> programs;
    std::array<int,4> starts;
    int end=140;
    for(int base:{0,2})for(int candidate:{0,1}) {
        const int i=base+candidate;
        starts[i]=end;programs[i]=context_feedback_choice_program(base,candidate);
        end+=int(programs[i].size())*6;
    }
    p.layout.total_size=end;
    Hamster h(111,p);int at=140;
    for(const auto& program:programs)
        for(int word:program)for(bool bit:SpiralToken(word,5,1).bits)h.memory.at(at++)=bit;
    for(int i=0;i<4;++i)h.memory[120+i]=1;
    auto update_choose=[&](Hamster& guest,int i,bool keep,int expected) {
        Problem blank;guest.write_prob(blank);
        guest.memory[55]=keep;guest.written[55]=true;
        guest.pro_1=starts[i];guest.pro_2=i==3?end-1:starts[i+1]-1;
        guest.step_limit=65;simulate_spiral_program(guest);
        assert(!guest.budget_exhausted&&guest.written[120+i]);
        assert(guest.memory[120+i]==keep);
        if(expected<0)assert(!guest.written[51]);
        else {
            assert(guest.written[51]&&guest.written[52]&&guest.written[53]);
            assert(!guest.memory[51]&&guest.memory[52]==bool(expected)&&!guest.memory[53]);
        }
    };
    update_choose(h,0,false,1); // context A: eliminate first, choose second
    update_choose(h,3,false,0); // context B: eliminate second, choose first
    h.new_his();Hamster child(112,p);child.copy_hamu(h);
    update_choose(child,1,false,-1); // A exhausted
    update_choose(child,2,true,0);   // B unaffected
    assert(!child.memory[120]&&!child.memory[121]&&child.memory[122]&&!child.memory[123]);
    std::cout<<"PASS one entry update+choice: two isolated contexts, exhaustion, inheritance\n";
}
