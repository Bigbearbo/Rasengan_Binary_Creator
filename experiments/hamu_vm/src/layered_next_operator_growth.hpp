#pragma once
#include "layered_next_both.hpp"

// Teach the same layered VM one extra operator width. A first n=3 FLIP
// changes the old operator tail 0 to 1 and updates its unary record in the
// existing COPY/FLIP loop. Subsequently NEXT=0100 must be recognized using
// the second information bit, whereas at n=2 NEXT=100 uses the first bit.
// Both data widths are routed from their own unary length record.
inline std::vector<int> layered_next_operator_growth_program() {
    const auto old=layered_next_both_program();
    const auto prefix=layered_vm_program(-1);
    const auto body=promoting_flip_program(true);
    const int prefix_pairs=int((prefix.size()-body.size())/2);
    std::vector<int> c(old.begin(),old.begin()+2*prefix_pairs);
    auto emit=[&](int op,int param) {
        int i=int(c.size()/2);c.push_back(op);c.push_back(param);return i;
    };
    auto patch=[&](int from,int to) {
        if(to<=from||to-from>31)throw std::logic_error("operator NEXT jump displacement "+std::to_string(from)+"->"+std::to_string(to));
        c[2*from+1]=to-from;
    };
    // Operator marker begins at work_start+19; its third bit says n=3.
    emit(0,3);emit(14,31);emit(14,22);emit(4,1);
    emit(24,2);
    const int old_width=emit(26,0);
    // n=3 NEXT=010: bit at input_start+20 is 1. The n=3 FLIP=001
    // follows the old COPY/FLIP loop, which reads the last information bit.
    emit(0,0);emit(14,31);emit(14,21);emit(4,1);
    emit(24,2);
    const int old_task=emit(26,0);
    // With the operator already n=3, its four-bit marker pushes the data
    // marker to work_start+23. Its third bit identifies data n=2 versus 3.
    emit(0,3);emit(14,31);emit(14,26);emit(4,1);
    emit(24,2);
    const int small_route=emit(26,0);
    const int large_route=emit(26,0);
    auto small=next_carry_program(2,3);
    small.insert(small.begin()+2*16,{26,2,26,0});
    const int small_start=int(c.size()/2);
    c.insert(c.end(),small.begin(),small.end());
    auto extra=next_carry_program(3,3);
    // Each bridge is two instructions: NEXT skips it; the old path jumps
    // through it to cross the 43-pair arithmetic routine with 5-bit jumps.
    extra.insert(extra.begin()+2*32,{26,2,26,0});
    extra.insert(extra.begin()+2*16,{26,2,26,0});
    const int extra_start=int(c.size()/2);
    c.insert(c.end(),extra.begin(),extra.end());
    const int old_start=int(c.size()/2);
    c.insert(c.end(),old.begin()+2*prefix_pairs,old.end());
    patch(old_width,small_start+17);
    patch(old_task,small_start+17);
    patch(small_route,small_start);
    patch(large_route,extra_start);
    patch(small_start+17,extra_start+17);
    patch(extra_start+17,extra_start+35);
    patch(extra_start+35,old_start);
    return c;
}
