#include "../src/work_trial_checkpoint.hpp"
#include <cassert>
#include <iostream>

int main() {
    HamsterParams p;p.layout.output_start=50;p.layout.work_start=80;
    p.layout.program_start=140;p.layout.total_size=160;
    Hamster h(1,p);
    h.memory[120]=true;h.written[120]=true;
    {
        WorkTrialCheckpoint rejected(h);
        h.memory[120]=false;h.written[120]=false;
        h.memory[139]=true;h.written[139]=true;
    }
    assert(h.memory[120]&&h.written[120]);
    assert(!h.memory[139]&&!h.written[139]);
    {
        WorkTrialCheckpoint accepted(h);
        h.memory[139]=true;h.written[139]=true;
        accepted.commit();
    }
    assert(h.memory[139]&&h.written[139]);
    std::cout<<"PASS rejected work changes restored, accepted changes retained\n";
}
