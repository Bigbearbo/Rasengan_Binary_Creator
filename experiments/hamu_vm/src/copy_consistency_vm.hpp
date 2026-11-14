#pragma once
#include <stdexcept>
#include <vector>
// Input+1..+3 attempted answer, +4..+6 task data, +7 teacher grade.
// Output+1..+3 are temporary XOR bits; output+5 is consistency.
inline std::vector<int> bitwise_consistency_program(bool flip) {
    std::vector<int> code;
    auto e=[&](int op,int param){const int i=int(code.size()/2);code.push_back(op);code.push_back(param);return i;};
    e(16,1);e(0,0);e(14,20);e(4,3);
    e(0,2);e(14,17);e(9,3); // copy data into writable output temporary bits
    e(0,0);e(14,17);e(4,3);
    e(0,2);e(14,17);e(5,3); // XOR attempted answer against task data
    int branches[3];
    for(int bit=0;bit<3;++bit) {
        e(0,2);e(14,17+bit);e(4,1);
        if(flip)e(24,2); // XOR=1 matches FLIP, skip mismatch jump
        branches[bit]=e(flip?26:24,0); // COPY mismatches on XOR=1
    }
    e(0,0);e(14,23);e(4,1); // answer matches: keep iff correct
    e(0,2);e(14,21);e(9,1);e(15,0);
    const int mismatch=int(code.size()/2);
    for(int branch:branches) {
        const int delta=mismatch-branch;
        if(delta<=0||delta>31)throw std::logic_error("bitwise comparison jump range");
        code[2*branch+1]=delta;
    }
    e(0,0);e(14,23);e(4,1); // answer differs: keep iff wrong
    e(0,2);e(14,21);e(2,1);e(14,1);e(5,1);e(15,0);
    return code;
}
inline std::vector<int> copy_consistency_program() {
    return bitwise_consistency_program(false);
}
