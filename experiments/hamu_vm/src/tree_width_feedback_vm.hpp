#pragma once
#include "tree_width_grade_vm.hpp"
#include "tree_feedback_mask_vm.hpp"

inline std::vector<int> tree_width_feedback_cycle_program(int slot){
    std::vector<int> w={0,3,14,31,14,31,14,31,14,31,14,31,14,31,14,20,3,1};
    auto guard=tree_width_grade_guard_program(slot);
    w.insert(w.end(),guard.begin(),guard.end());
    for(bool flip:{false,true}){
        auto body=tree_feedback_mask_body(slot,flip);
        body.resize(body.size()-2);
        w.insert(w.end(),body.begin(),body.end());
    }
    const std::vector<int> commit={0,3,14,31,14,31,14,31,14,31,14,31,14,31,14,20,2,1,15,0};
    w.insert(w.end(),commit.begin(),commit.end());
    return w;
}

inline std::vector<int> tree_width_feedback_confirm_program(int slot){
    if(slot!=57&&slot!=70)throw std::invalid_argument("pending slot");
    // The complete mask update must precede confirmation.
    std::vector<int> w={16,1,0,3,14,31,14,31,14,31,14,31,14,31,14,31,14,20,4,1,18,20,15,0};
    auto guard=tree_width_grade_guard_program(slot);
    w.insert(w.end(),guard.begin(),guard.end());
    const int mask0=slot==57?55:68,mask1=mask0+1;
    auto e=[&](int op,int arg){int i=int(w.size()/2);w.push_back(op);w.push_back(arg);return i;};
    auto move=[&](int d){while(d>=15){e(14,31);d-=15;}if(d)e(14,16+d);};
    auto at=[&](int pos){e(0,3);move(pos);};
    auto require=[&](int pos){at(pos);e(4,1);e(18,20);e(15,0);};
    require(34);
    at(mask0);e(4,1);
    const int zero=e(24,0);
    require(mask1);
    at(slot+1);e(2,1);
    at(slot);e(2,1);e(15,0);
    const int choose_zero=int(w.size()/2);
    at(mask1);e(4,1);e(24,2);e(26,2);e(15,0);
    at(slot+1);e(3,1);
    at(slot);e(2,1);e(15,0);
    if(choose_zero-zero<=0||choose_zero-zero>31)
        throw std::logic_error("width confirm jump");
    w[2*zero+1]=choose_zero-zero;
    return w;
}
