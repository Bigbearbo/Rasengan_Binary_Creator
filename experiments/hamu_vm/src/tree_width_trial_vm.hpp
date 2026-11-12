#pragma once
#include <stdexcept>
#include <vector>

// Two host-provided candidate programs. The guest selects the data offset
// from its own persistent width bit; the teacher grades the emitted 3 bits.
// The caller must validate/scaffold the question before invoking this code.
inline std::vector<int> tree_width_trial_program(bool flip) {
    std::vector<int> w;
    auto e=[&](int op,int arg){int i=int(w.size()/2);w.push_back(op);w.push_back(arg);return i;};
    auto move=[&](int d){while(d>=15){e(14,31);d-=15;}if(d)e(14,16+d);};
    auto at=[&](int area,int offset){e(0,area);move(offset);};
    auto patch=[&](int i,int target){
        if(target-i<=0||target-i>31)throw std::logic_error("trial width jump range");
        w[2*i+1]=target-i;
    };
    e(16,1);
    at(3,96);e(4,1);
    const int n3=e(24,0);
    at(0,9);e(8,18);e(4,3);
    const int done=e(26,0);
    const int load3=int(w.size()/2);
    at(0,10);e(8,18);e(4,3);
    const int output=int(w.size()/2);
    patch(n3,load3);patch(done,output);
    at(2,0);
    if(flip){e(2,3);e(14,3);e(5,3);}
    else e(9,3);
    e(15,0);
    return w;
}
