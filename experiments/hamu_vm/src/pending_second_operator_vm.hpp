#pragma once
#include <stdexcept>
#include <vector>

// A second n=3 unseen operator, stored at work+60..67. The existing first
// slot at work+47..58 remains untouched. Both slots need stable work space.
inline std::vector<int> pending_second_operator_program() {
    std::vector<int> c;
    auto e=[&](int op,int p){int i=int(c.size()/2);c.push_back(op);c.push_back(p);return i;};
    auto work=[&](int offset) {
        e(0,3);
        while(offset>=15){e(14,31);offset-=15;}
        if(offset)e(14,16+offset);
    };
    auto require_one=[&](int offset){work(offset);e(4,1);e(24,2);e(15,0);};
    e(16,1);
    work(45);e(4,1);e(24,2);e(26,2);e(15,0); // known -> stop
    require_one(47); // first slot exists
    require_one(21); // this initial second-slot experiment uses n=3
    work(60);e(4,1);e(24,2);e(26,2);e(15,0); // second already present -> stop
    work(48);e(4,4); // first slot width + raw
    e(0,2);e(14,22);e(9,4); // scratch output+6..9
    work(21);e(4,1);
    e(0,2);e(14,22);e(5,1);
    e(0,0);e(14,31);e(14,20);e(4,3); // input+19..21
    e(0,2);e(14,23);e(5,3);
    int mismatch[4];
    for(int bit=0;bit<4;++bit){
        e(0,2);e(14,22+bit);e(4,1);
        mismatch[bit]=e(24,0); // a different word can claim slot two
    }
    e(15,0); // same first word: do not duplicate it
    const int write=int(c.size()/2);
    for(int at:mismatch){
        if(write-at>31)throw std::logic_error("second slot jump range");
        c[2*at+1]=write-at;
    }
    work(61);e(2,1); // n=3
    e(0,0);e(14,31);e(14,20);e(4,3);
    work(62);e(9,3); // raw word
    e(0,0);e(14,31);e(14,20);e(4,3);
    work(65);e(9,3); // left-padded numeric ID, n=3 here
    work(60);e(2,1); // presence commit last
    e(15,0);
    return c;
}
