#pragma once
#include <vector>

// First arithmetic microprogram: fixed two-bit data location in an L2 packet.
// Work from low bit to high bit, retaining the low bit as the carry.
inline std::vector<int> next_two_bit_program() {
    std::vector<int> c;
    auto e=[&](int op,int param){c.push_back(op);c.push_back(param);};
    e(0,0);e(14,31);e(14,24); // input_start+23: data low bit
    e(8,17);e(4,1);e(8,1);e(4,1); // carry reg[1], old low reg[0]
    e(0,2);e(14,18);e(2,1);e(14,1);e(5,1); // output low = 1 XOR old low
    e(0,0);e(14,31);e(14,23);e(4,1); // input_start+22: data high
    e(25,1); // reg[0] = old high XOR carry
    e(0,2);e(14,17);e(9,1); // output high
    e(14,17);e(14,17);e(3,1); // explicit tail zero
    e(15,0);
    return c;
}
