#pragma once
#include <stdexcept>
#include <vector>

// Only the one recorded unseen operator (same width and raw word) may use
// its own two hypothesis bits at stable work+55,+56. Once confirmed, use
// the durable ID at work+58 instead. Other words produce no choice.
inline std::vector<int> pending_choice_program() {
    std::vector<int> c;
    auto e=[&](int op,int param){int i=int(c.size()/2);c.push_back(op);c.push_back(param);return i;};
    e(16,1);
    e(0,3);e(14,31);e(14,31);e(14,31);e(14,18);e(4,1); // pending work+47
    e(24,2);e(15,0); // no pending -> STOP
    e(0,3);e(14,31);e(14,31);e(14,31);e(14,19);e(4,4); // width+raw
    e(0,2);e(14,22);e(9,4); // scratch output+6..9
    e(0,3);e(14,31);e(14,22);e(4,1); // current width
    e(0,2);e(14,22);e(5,1); // XOR scratch width
    e(0,0);e(14,31);e(14,20);e(4,3); // current raw input+19..21
    e(0,2);e(14,23);e(5,3); // XOR scratch raw
    for(int bit=0;bit<4;++bit) {
        e(0,2);e(14,22+bit);e(4,1);
        e(24,2);e(26,2);e(15,0); // mismatch -> STOP
    }
    e(0,3);e(14,31);e(14,31);e(14,31);e(14,28);e(4,1);
    const int confirmed_jump=e(24,0); // work+57 commit bit
    e(0,3);e(14,31);e(14,31);e(14,31);e(14,26); // work+55
    e(4,1);const int first=e(24,0);
    e(14,17);e(4,1);const int second=e(24,0);
    e(15,0);
    const int zero=int(c.size()/2);e(0,2);e(14,17);e(3,3);e(15,0);
    const int one=int(c.size()/2);e(0,2);e(14,17);e(3,1);e(2,1);e(3,1);e(15,0);
    const int confirmed=int(c.size()/2);
    e(0,3);e(14,31);e(14,31);e(14,31);e(14,29);e(4,1); // work+58
    e(0,2);e(14,17);e(3,1);e(9,1);e(14,17);e(3,1);e(15,0);
    if(zero-first>31||one-second>31)throw std::logic_error("pending choice jump range");
    if(confirmed-confirmed_jump>31)throw std::logic_error("confirmed choice jump range");
    c[2*first+1]=zero-first;c[2*second+1]=one-second;
    c[2*confirmed_jump+1]=confirmed-confirmed_jump;
    return c;
}
