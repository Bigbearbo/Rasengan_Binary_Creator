#include "../src/hamu_vm_core.hpp"
#include <array>
#include <iostream>

int main() {
    constexpr std::array<int,8> code={0,3,14,17,10,1,15,0};
    HamsterParams p;p.op_order=5;p.layout.total_size=p.layout.program_start+int(code.size())*6;
    auto run=[&](bool occupied) {
        Hamster h(0,p);int at=p.layout.program_start;
        for(int w:code)for(bool b:SpiralToken(w,5,1).bits)h.memory.at(at++)=b;
        h.memory[p.layout.work_start]=1;
        h.memory[p.layout.work_start+1]=1;
        h.memory[p.layout.program_start-1]=occupied;
        const auto before=h.memory;
        h.pro_1=p.layout.program_start;h.pro_2=at-1;h.step_limit=20;
        simulate_spiral_program(h);
        if(h.budget_exhausted||h.work_insert_blocked!=occupied)return false;
        if(occupied) {
            if(h.memory!=before || h.written[p.layout.work_start+1] ||
               h.written[p.layout.program_start-1])return false;
        } else {
            if(h.memory[p.layout.work_start+1]||!h.memory[p.layout.work_start+2]||
               !h.written[p.layout.work_start+1])return false;
        }
        return true;
    };
    if(!run(true)||!run(false))return 1;
    std::cout<<"PASS INSERT refuses occupied work tail without shifting;"
                " free tail still permits insertion\n";
}
