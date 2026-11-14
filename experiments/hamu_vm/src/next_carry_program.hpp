#pragma once
#include <vector>
#include <stdexcept>

// Unroll a low-to-high carry circuit into existing VM instructions.
// The L2 prefix is 18 bits and the NEXT operator is n=2,k=1.
inline std::vector<int> next_carry_program(int n,int operator_n=2) {
    if(n!=2&&n!=3)throw std::invalid_argument("NEXT circuit width");
    if(operator_n!=2&&operator_n!=3)throw std::invalid_argument("NEXT operator width");
    std::vector<int> code;
    auto e=[&](int op,int param){code.push_back(op);code.push_back(param);};
    auto input_bit=[&](int bit) {
        const int addr=22+(operator_n-2)+bit;
        e(0,0);e(14,31);e(14,16+addr-15);
    };
    auto output_bit=[&](int bit) {
        e(0,2);e(14,17+bit);
    };
    // Low bit: output 1 XOR old bit; reg[1] holds carry=old bit.
    input_bit(n-1);e(8,17);e(4,1);e(8,1);e(4,1);
    output_bit(n-1);e(2,1);e(14,1);e(5,1);
    for(int bit=n-2;bit>=0;--bit) {
        input_bit(bit);e(4,1);e(25,1); // reg[0] = old bit XOR carry
        output_bit(bit);e(9,1);
        if(bit) {
            // Re-read old bit and AND with the incoming carry in a scratch
            // work bit; store the resulting carry in reg[1].
            input_bit(bit);e(4,1);
            e(0,3);e(1,21);e(9,1); // work_start+30, beyond current length records
            e(8,17);e(6,1);e(4,1);e(8,1);
        }
    }
    output_bit(n);e(3,1); // position n+1 relative output_start: tail zero
    e(15,0);
    return code;
}
