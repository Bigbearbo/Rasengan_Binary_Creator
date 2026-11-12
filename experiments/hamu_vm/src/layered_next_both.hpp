#pragma once
#include "layered_next_program.hpp"

inline std::vector<int> layered_next_both_program() {
    const auto all=layered_vm_program(-1);
    const auto body=promoting_flip_program(true);
    std::vector<int> c(all.begin(),all.end()-body.size());
    auto e=[&](int op,int param) {const int i=int(c.size()/2);c.push_back(op);c.push_back(param);return i;};
    auto patch=[&](int from,int to) {
        if(to<=from||to-from>31)throw std::logic_error("jump displacement");
        c[2*from+1]=to-from;
    };
    // n=2 operator high bit: NEXT=1; COPY and FLIP=0.
    e(0,0);e(14,31);e(14,20);e(4,1);
    e(24,2);
    const int bypass=e(26,0);
    // Data marker starts after 19 prefix bits and a 3-bit operator marker.
    // At +24, the third data marker bit is 0 for n=2, 1 for n=3.
    e(0,3);e(1,20);e(4,1);
    const int width_branch=e(24,0);
    auto small=next_two_bit_program();
    const int small_island=12;
    small.insert(small.begin()+2*small_island,{26,2,26,0});
    const int small_start=int(c.size()/2);
    c.insert(c.end(),small.begin(),small.end());
    auto large=next_carry_program(3);
    const int large_island=16;
    large.insert(large.begin()+2*large_island,{26,2,26,0});
    const int large_start=int(c.size()/2);
    c.insert(c.end(),large.begin(),large.end());
    const int body_start=int(c.size()/2);
    c.insert(c.end(),body.begin(),body.end());
    patch(bypass,small_start+small_island+1);
    patch(width_branch,large_start);
    patch(small_start+small_island+1,large_start+large_island+1);
    patch(large_start+large_island+1,body_start);
    return c;
}
