#include "../src/task_upgrade.hpp"
#include <cassert>
#include <iostream>

int main() {
    CopyUpgradeCurriculum teacher(4,6);
    HamsterParams params;Hamster h(0,params);
    int at=params.layout.program_start;
    for(int value:{0,0,14,22,4,1,15})
        for(bool bit:SpiralToken(value,5,1).bits)h.memory.at(at++)=bit;
    h.pro_1=params.layout.program_start;h.pro_2=at-1;
    bool promoted=false;
    for(int i=0;i<18;++i) {
        const Problem p=teacher.next();
        h.write_prob(p); // no out-of-band version tag
        const int data_start=params.layout.input_start+1+3;
        const bool old_tail=h.memory[data_start+2];
        simulate_spiral_program(h);
        assert(h.read_seen[data_start+2] && h.val_reg[0]==old_tail);
        if(i<4) {
            assert(p.question[1].order==2 && !old_tail && !promoted);
        } else if(i<10) {
            assert(p.question[1].order==3 && old_tail);
            assert(!h.memory[data_start+3]); // the new tail is zero
            promoted=true;
        } else {
            assert(promoted && p.question[1].order==3);
            assert(p.answer.order==3);
            assert(!h.memory[data_start+3]);
            assert(p.question[1].value==(i-10)%8);
        }
        assert(!h.memory[params.layout.status_start-1]);
    }
    assert(CopyUpgradeCurriculum(0,1).next().question[1].bits==SpiralToken(1,3,1).bits);
    bool rejected=false;
    try {CopyUpgradeCurriculum invalid(4,0);}catch(const std::invalid_argument&){rejected=true;}
    assert(rejected);
    std::cout<<"PASS: four old, six 0-to-1 trigger, eight stable n=3 questions; no version tag or downgrade\n";
}
