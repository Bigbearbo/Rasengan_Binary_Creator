#pragma once
#include "layered_vm_program.hpp"
#include "next_two_bit_program.hpp"
#include "next_carry_program.hpp"

// Narrow integration: operator n=2, data n=2. NEXT's first information bit
// is 1; COPY/FLIP have 0 there. Validation and period checking run first.
inline std::vector<int> layered_next_program(int data_n=2) {
    if(data_n!=2&&data_n!=3)throw std::invalid_argument("NEXT data width");
    const auto all=layered_vm_program(-1);
    const auto body=promoting_flip_program(true);
    auto next=data_n==2?next_two_bit_program():next_carry_program(3);
    if(data_n==3) {
        // The 43-pair subroutine is beyond a single 5-bit forward jump.
        // NEXT skips the trampoline; COPY/FLIP jump to it and then past NEXT.
        const int island=24;
        next.insert(next.begin()+2*island,{26,2,26,20});
    }
    std::vector<int> c(all.begin(),all.end()-body.size());
    auto e=[&](int op,int param){c.push_back(op);c.push_back(param);};
    e(0,0);e(14,31);e(14,20);e(4,1); // input_start+19: operator high bit
    e(24,2);                 // NEXT=1: skip the jump to COPY/FLIP
    e(26,data_n==2?int(next.size()/2+1):26); // via island for n=3
    c.insert(c.end(),next.begin(),next.end());
    c.insert(c.end(),body.begin(),body.end());
    return c;
}
