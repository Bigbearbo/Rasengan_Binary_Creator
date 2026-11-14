#include "../src/guest_trial_checkpoint.hpp"
#include <cassert>
#include <iostream>

int main() {
    HamsterParams p;p.layout.output_start=50;p.layout.work_start=80;
    p.layout.program_start=140;p.layout.total_size=200;
    Hamster h(1,p);
    const std::vector<int> hostile{0,3,14,17,2,1,15,0};
    int at=140;
    for(int word:hostile)for(bool bit:SpiralToken(word,5,1).bits)h.memory.at(at++)=bit;
    h.memory[120]=true;h.written[120]=true;
    h.val_reg[0]=true;h.hp=17;h.pro_1=141;h.output_ptr=51;
    h.new_his();
    const Hamster before=h;
    {
        GuestTrialCheckpoint rejected(h);
        h.pro_1=140;h.pro_2=at-1;h.step_limit=20;
        simulate_spiral_program(h); // candidate really writes into work+1
        assert(h.memory[81]&&h.written[81]);
        h.memory[120]=false;h.written[120]=false;
        h.memory[139]=true;h.written[139]=true;
        h.memory[145]=true;h.memory[51]=true;
        h.val_reg[0]=false;h.hp=3;h.pro_1=150;h.output_ptr=70;
        h.new_his();
    }
    assert(h.memory==before.memory&&h.written==before.written);
    assert(h.memory_his==before.memory_his&&h.val_reg==before.val_reg);
    assert(h.hp==before.hp&&h.pro_1==before.pro_1&&h.output_ptr==before.output_ptr);
    {
        GuestTrialCheckpoint accepted(h);
        h.memory[139]=true;h.hp=12;
        accepted.commit();
    }
    assert(h.memory[139]&&h.hp==12);
    std::cout<<"PASS VM work write and other guest state rollback; commit retains\n";
}
