#pragma once
#include <stdexcept>
#include <vector>

// The preceding guest capture stores attempted answer in work+28..30,
// question data in work+31..33, and teacher grade in work+34.
// The following programs read that memory directly. No host bit forwarding.
inline std::vector<int> work_constant_consistency_program(bool one) {
    std::vector<int> code;
    auto e=[&](int op,int param){int i=int(code.size()/2);code.push_back(op);code.push_back(param);return i;};
    e(16,1);e(0,3);e(14,31);e(14,29); // work+28
    int mismatch[3];
    for(int bit=0;bit<3;++bit) {
        if(bit)e(14,17);
        e(4,1);
        if(one)e(24,2); // ONE: bit 1 matches, skip mismatch jump
        mismatch[bit]=e(one?26:24,0); // ZERO: bit 1 mismatches
    }
    e(14,20);e(4,1); // work+34: all match, retain iff grade is correct
    e(0,2);e(14,17);e(9,1);e(15,0);
    const int target=int(code.size()/2);
    for(int at:mismatch) {
        if(target-at<=0||target-at>31)throw std::logic_error("constant check jump range");
        code[2*at+1]=target-at;
    }
    e(0,3);e(14,31);e(14,31);e(14,20);e(4,1); // grade
    e(0,2);e(14,17);e(2,1);e(14,1);e(5,1);e(15,0); // invert
    return code;
}

inline std::vector<int> work_bitwise_consistency_program(bool flip) {
    std::vector<int> code;
    auto e=[&](int op,int param){int i=int(code.size()/2);code.push_back(op);code.push_back(param);return i;};
    e(16,1);e(0,3);e(14,31);e(14,31);e(14,17);e(4,3); // data at work+31
    e(0,2);e(14,17);e(9,3); // output temporary XOR bits
    e(0,3);e(14,31);e(14,29);e(4,3); // attempt at work+28
    e(0,2);e(14,17);e(5,3);
    int mismatch[3];
    for(int bit=0;bit<3;++bit) {
        e(0,2);e(14,17+bit);e(4,1);
        if(flip)e(24,2);
        mismatch[bit]=e(flip?26:24,0);
    }
    auto grade=[&](){e(0,3);e(14,31);e(14,31);e(14,20);e(4,1);};
    grade();e(0,2);e(14,21);e(9,1);e(15,0);
    const int target=int(code.size()/2);
    for(int at:mismatch) {
        if(target-at<=0||target-at>31)throw std::logic_error("bitwise check jump range");
        code[2*at+1]=target-at;
    }
    grade();e(0,2);e(14,21);e(2,1);e(14,1);e(5,1);e(15,0);
    return code;
}
