#pragma once
#include "tree_grade_guard_vm.hpp"
inline std::vector<int> tree_context_grade_confirm_program(int commit_offset) {
    auto w=tree_grade_guard_program(commit_offset);
    const int mask0=commit_offset==57?55:68,mask1=mask0+1;
    const int local_id=commit_offset+1;
    auto e=[&](int op,int arg){int i=int(w.size()/2);w.push_back(op);w.push_back(arg);return i;};
    auto move=[&](int d){while(d>=15){e(14,31);d-=15;}if(d)e(14,16+d);};
    auto at_work=[&](int offset){e(0,3);move(offset);};
    auto require_one=[&](int offset){at_work(offset);e(4,1);e(18,20);e(15,0);};
    require_one(34);
    at_work(mask0);e(4,1);
    const int zero=e(24,0); // if candidate 0 survived, check candidate 1
    require_one(mask1);
    at_work(local_id);e(2,1); // candidate 1
    at_work(commit_offset);e(2,1);
    e(15,0);
    const int choose_zero=int(w.size()/2);
    at_work(mask1);e(4,1);e(24,2);e(26,2);e(15,0); // both survived -> stop
    at_work(local_id);e(3,1); // candidate 0
    at_work(commit_offset);e(2,1);
    e(15,0);
    const int distance=choose_zero-zero;
    if(distance<=0||distance>31)
        throw std::logic_error("context grade confirm jump range");
    w[2*zero+1]=distance;
    return w;
}
