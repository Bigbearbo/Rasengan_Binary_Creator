#pragma once
#include <stdexcept>
#include <vector>

// Confirm only a correctly graded trial of the exact second word. Store
// candidate ID at work+71, then publish it with work+70 as the last write.
inline std::vector<int> pending_second_confirm_program() {
    std::vector<int> c;
    auto e=[&](int op,int p){int i=int(c.size()/2);c.push_back(op);c.push_back(p);return i;};
    auto work=[&](int offset) {
        e(0,3);
        while(offset>=15){e(14,31);offset-=15;}
        if(offset)e(14,16+offset);
    };
    auto require_one=[&](int offset){work(offset);e(4,1);e(24,2);e(15,0);};
    e(16,1);
    require_one(60);
    work(61);e(4,4); // saved width and raw word
    e(0,2);e(14,22);e(9,4);
    work(21);e(4,1);
    e(0,2);e(14,22);e(5,1);
    e(0,0);e(14,31);e(14,20);e(4,3);
    e(0,2);e(14,23);e(5,3);
    for(int bit=0;bit<4;++bit) {
        e(0,2);e(14,22+bit);e(4,1);
        e(24,2);e(26,2);e(15,0);
    }
    require_one(34); // teacher grade captured by guest
    work(68);e(4,1);
    const int zero_branch=e(24,0);
    require_one(69); // candidate 0 absent, candidate 1 present
    work(71);e(2,1);
    work(70);e(2,1); // commit last
    e(15,0);
    const int zero=int(c.size()/2);
    work(69);e(4,1);e(24,2);e(26,2);e(15,0); // both present -> stop
    work(71);e(3,1);
    work(70);e(2,1);
    e(15,0);
    if(zero-zero_branch>31)throw std::logic_error("second confirm jump range");
    c[2*zero_branch+1]=zero-zero_branch;
    return c;
}
