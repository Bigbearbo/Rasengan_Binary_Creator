#pragma once
#include <stdexcept>
#include <vector>

// Confirm a unique COPY/FLIP hypothesis only for that exact current word,
// after a correct graded trial. Store the candidate ID before the commit bit.
inline std::vector<int> pending_confirm_program() {
    std::vector<int> c;
    auto e=[&](int op,int p){int i=int(c.size()/2);c.push_back(op);c.push_back(p);return i;};
    e(16,1);
    auto require_one=[&](int offset) {
        e(0,3);e(14,31);e(14,31);e(14,31);
        e(14,16+offset-45);e(4,1);e(24,2);e(15,0);
    };
    require_one(47); // pending word exists
    // Compare saved width+raw word to the current question, using output
    // scratch bits. A correct grade from an unrelated word cannot confirm it.
    e(0,3);e(14,31);e(14,31);e(14,31);e(14,19);e(4,4);
    e(0,2);e(14,22);e(9,4);
    e(0,3);e(14,31);e(14,22);e(4,1);
    e(0,2);e(14,22);e(5,1);
    e(0,0);e(14,31);e(14,20);e(4,3);
    e(0,2);e(14,23);e(5,3);
    for(int bit=0;bit<4;++bit) {
        e(0,2);e(14,22+bit);e(4,1);
        e(24,2);e(26,2);e(15,0); // mismatched bit -> STOP
    }
    e(0,3);e(14,31);e(14,31);e(14,20);e(4,1);e(24,2);e(15,0); // grade work+34
    e(0,3);e(14,31);e(14,31);e(14,31);e(14,26);e(4,1);
    const int choose_zero=e(24,0); // wide jump to candidate 0 branch
    require_one(56); // otherwise only candidate 1 may survive
    e(0,3);e(14,31);e(14,31);e(14,31);e(14,29);e(2,1); // ID 1 at work+58
    e(0,3);e(14,31);e(14,31);e(14,31);e(14,28);e(2,1); // commit work+57 last
    e(15,0);
    const int zero=int(c.size()/2);
    e(0,3);e(14,31);e(14,31);e(14,31);e(14,27);e(4,1);
    e(24,2);e(26,2);e(15,0); // both candidates present -> no confirmation
    e(0,3);e(14,31);e(14,31);e(14,31);e(14,29);e(3,1); // ID 0
    e(0,3);e(14,31);e(14,31);e(14,31);e(14,28);e(2,1); // commit last
    e(15,0);
    if(zero-choose_zero>31)
        throw std::logic_error("pending confirm jump range");
    c[2*choose_zero+1]=zero-choose_zero;
    return c;
}
