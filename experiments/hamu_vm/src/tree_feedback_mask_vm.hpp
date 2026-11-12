#pragma once
#include "tree_grade_guard_vm.hpp"

// Intersect one slot's COPY/FLIP hypotheses with a saved, context-bound
// teacher observation. Candidate choice is not needed: compare the actual
// saved attempt with each hypothesis's prediction, then compare with grade.
inline std::vector<int> tree_feedback_mask_body(int slot,bool flip) {
    if(slot!=57&&slot!=70)throw std::invalid_argument("pending slot");
    std::vector<int> w;
    const int mask=(slot==57?55:68)+(flip?1:0);
    auto e=[&](int op,int arg){w.push_back(op);w.push_back(arg);};
    auto move=[&](int d){while(d>=15){e(14,31);d-=15;}if(d)e(14,16+d);};
    auto at=[&](int area,int pos){e(0,area);move(pos);};
    at(3,86);e(4,3);at(2,20);e(9,3);
    at(3,89);e(4,3);at(2,20);e(5,3); // attempt XOR data
    at(2,23);e(3,1); // accumulate any prediction mismatch
    for(int bit=0;bit<3;++bit){
        at(2,20+bit);e(4,1);
        if(flip){
            at(2,24);e(2,1);e(14,1);e(5,1);e(4,1); // NOT xor
        }
        at(2,23);e(7,1);
    }
    at(3,34);e(4,1);at(2,23);e(5,1); // consistency = grade XOR mismatch
    e(4,1);
    at(3,mask);e(6,1); // AND never resurrects an eliminated hypothesis
    e(15,0);
    return w;
}

inline std::vector<int> tree_feedback_mask_program(int slot,bool flip){
    auto w=tree_grade_guard_program(slot);
    auto body=tree_feedback_mask_body(slot,flip);
    w.insert(w.end(),body.begin(),body.end());
    return w;
}
