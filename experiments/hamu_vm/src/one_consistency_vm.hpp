#pragma once
#include <vector>
#include <stdexcept>
// Three-bit attempted answer at input+1..+3, teacher grade at input+4.
// Return whether the constant ONE (111) agrees with the grade at output+1.
inline std::vector<int> one_consistency_program() {
    std::vector<int> code;
    auto emit=[&](int op,int param){int at=int(code.size()/2);code.push_back(op);code.push_back(param);return at;};
    emit(16,1);emit(0,0);emit(14,17);
    int mismatch_jumps[3];
    for(int bit=0;bit<3;++bit) {
        if(bit)emit(14,17);
        emit(4,1);
        emit(24,2); // bit 1 skips the mismatch jump
        mismatch_jumps[bit]=emit(26,0);
    }
    emit(14,17);emit(4,1); // expected 111, read grade at input+4
    emit(0,2);emit(14,17);emit(9,1);emit(15,0);
    const int mismatch=int(code.size()/2);
    for(int at:mismatch_jumps) {
        const int delta=mismatch-at;
        if(delta<=0||delta>31)throw std::logic_error("mismatch branch out of range");
        code[2*at+1]=delta;
    }
    emit(0,0);emit(14,20);emit(4,1); // grade
    emit(0,2);emit(14,17);emit(2,1);emit(14,1);emit(5,1);emit(15,0);
    return code;
}
