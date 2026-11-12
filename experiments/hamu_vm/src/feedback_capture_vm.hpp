#pragma once
#include <stdexcept>
#include <vector>

// Fixed L2 -> L1 syntax, operator and data each n=2 or n=3. Their
// position-specific unary records begin at work+19 and work+(22 or 23).
// Two-bit answer and data are each left-padded to three bits in work.
inline std::vector<int> feedback_capture_program() {
    std::vector<int> code;
    auto e=[&](int op,int param){int i=int(code.size()/2);code.push_back(op);code.push_back(param);return i;};
    auto work=[&](int offset){
        e(0,3);e(14,31);
        if(offset>30)e(14,31);
        e(14,16+offset-(offset>30?30:15));
    };
    e(16,1);
    e(0,2);e(14,17);e(4,3);
    e(0,3);e(14,31);e(14,29);e(9,3); // attempt -> work+28..30
    e(0,3);e(14,31);e(14,22);e(4,1); // operator width bit, work+21
    work(35);e(9,1);                 // retain bit in transient work+35
    e(0,0);e(14,31);e(14,23);       // input+22
    e(24,2);e(26,2);e(14,17);     // n=3 operator: input+23
    e(4,3);work(31);e(9,3);        // n=2 data includes its tail zero
    work(35);e(4,1);               // select the data record's third bit
    e(0,3);e(14,31);e(14,25);     // work+24 if operator n=2
    e(24,2);e(26,2);e(14,17);     // work+25 if operator n=3
    e(4,1);
    work(36);e(9,1);               // preserve data width before copying bits
    const int already_three=e(24,0); // n=3 data: skip left padding
    work(31);e(4,2);work(32);e(9,2);work(31);e(3,1);
    const int finish=int(code.size()/2);
    if(finish-already_three>31)throw std::logic_error("data normalization jump range");
    code[2*already_three+1]=finish-already_three;
    work(36);e(4,1);
    const int answer_three=e(24,0); // n=3 answer already fits
    work(28);e(4,2);work(29);e(9,2);work(28);e(3,1);
    const int after_answer=int(code.size()/2);
    if(after_answer-answer_three>31)throw std::logic_error("answer normalization jump range");
    code[2*answer_three+1]=after_answer-answer_three;
    e(0,0);e(14,31);e(14,31);e(14,26);e(4,1); // input+40 grade
    work(34);e(9,1);e(15,0);
    return code;
}
