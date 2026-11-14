#pragma once
#include <vector>
#include <stdexcept>
// Human written priority policy: work+40..+43 mask -> first live candidate
// as one n=2,k=1 word at output+1. All zero -> no output bits written.
inline std::vector<int> mask_choice_program() {
    std::vector<int> c;
    auto e=[&](int op,int param){int i=int(c.size()/2);c.push_back(op);c.push_back(param);return i;};
    e(16,1);e(0,3);e(14,31);e(14,31);e(14,26);
    int branches[4];
    for(int i=0;i<4;++i) {
        e(4,1);branches[i]=e(24,0);
        if(i<3)e(14,17);
    }
    e(15,0); // no viable hypothesis
    for(int id=0;id<4;++id) {
        const int target=int(c.size()/2);
        const int delta=target-branches[id];
        if(delta<=0||delta>31)throw std::logic_error("choice branch range");
        c[2*branches[id]+1]=delta;
        e(0,2);e(14,17);
        for(int bit=1;bit>=0;--bit)e((id>>bit)&1?2:3,1);
        e(3,1);e(15,0);
    }
    return c;
}
