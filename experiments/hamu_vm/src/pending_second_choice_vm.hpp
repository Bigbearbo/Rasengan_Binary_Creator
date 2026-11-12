#pragma once
#include <stdexcept>
#include <vector>

// Match the second slot by saved width and raw word before consulting its
// two independent candidate bits at work+68,+69, or the committed ID at
// work+71 after work+70 is set.
inline std::vector<int> pending_second_choice_program() {
    std::vector<int> c;
    auto e=[&](int op,int p){int i=int(c.size()/2);c.push_back(op);c.push_back(p);return i;};
    auto work=[&](int offset) {
        e(0,3);
        while(offset>=15){e(14,31);offset-=15;}
        if(offset)e(14,16+offset);
    };
    e(16,1);
    work(60);e(4,1);e(24,2);e(15,0); // no second word
    work(61);e(4,4);
    e(0,2);e(14,22);e(9,4); // scratch output+6..9
    work(21);e(4,1);
    e(0,2);e(14,22);e(5,1);
    e(0,0);e(14,31);e(14,20);e(4,3);
    e(0,2);e(14,23);e(5,3);
    for(int bit=0;bit<4;++bit) {
        e(0,2);e(14,22+bit);e(4,1);
        e(24,2);e(26,2);e(15,0); // mismatch -> stop
    }
    work(70);e(4,1);
    const int confirmed_jump=e(24,0);
    work(68);e(4,1);const int first=e(24,0);
    e(14,17);e(4,1);const int second=e(24,0);
    e(15,0);
    const int zero=int(c.size()/2);
    e(0,2);e(14,17);e(3,3);e(15,0);
    const int one=int(c.size()/2);
    e(0,2);e(14,17);e(3,1);e(2,1);e(3,1);e(15,0);
    const int confirmed=int(c.size()/2);
    work(71);e(4,1);
    e(0,2);e(14,17);e(3,1);e(9,1);e(14,17);e(3,1);e(15,0);
    if(zero-first>31||one-second>31)throw std::logic_error("second choice jump range");
    if(confirmed-confirmed_jump>31)throw std::logic_error("second confirmed jump range");
    c[2*first+1]=zero-first;c[2*second+1]=one-second;
    c[2*confirmed_jump+1]=confirmed-confirmed_jump;
    return c;
}
