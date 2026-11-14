#pragma once
#include <vector>

// A fixed n=3 trial has category at input+2, operator at +6, data at +10,
// attempted answer at output+0 and the teacher's grade at input+40.
// Save all four three-bit fields before publishing work+92. The grade itself
// uses the existing work+34 slot and is committed with the same final bit.
inline std::vector<int> tree_grade_snapshot_program() {
    std::vector<int> w;
    auto e=[&](int op,int arg){w.push_back(op);w.push_back(arg);};
    auto move=[&](int d){while(d>=15){e(14,31);d-=15;}if(d)e(14,16+d);};
    auto copy=[&](int area,int source,int destination){
        e(0,area);move(source);e(4,3);
        e(0,3);move(destination);e(9,3);
    };
    e(16,1);
    e(0,3);move(92);e(3,1); // invalidate any previous snapshot first
    copy(0,2,80);copy(0,6,83);copy(0,10,86);copy(2,0,89);
    e(0,0);move(40);e(4,1);
    e(0,3);move(34);e(9,1);
    e(0,3);move(92);e(2,1); // commit after all question/attempt/grade bits
    e(15,0);
    return w;
}
